"""ENCODE Project MCP Server.

Exposes ENCODE REST API as Claude-compatible tools for searching experiments,
listing files, and downloading genomics data.

All data stays local. Only connects to encodeproject.org over HTTPS.
No telemetry, no analytics, no data sent elsewhere.
"""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from encode_connector.client.auth import CredentialManager
from encode_connector.client.downloader import FileDownloader
from encode_connector.client.encode_client import EncodeClient
from encode_connector.client.models import _human_size
from encode_connector.client.tracker import (
    ExperimentTracker,
    parse_encode_pipelines,
    parse_encode_publications,
)
from encode_connector.client.validation import (
    clamp_limit,
    validate_accession,
    validate_data_export_format,
    validate_encode_path,
    validate_export_format,
    validate_organize_by,
    validate_reference_type,
)

logger = logging.getLogger(__name__)

# --- Safety annotations for MCP tools ---
# Read-only tools that query the ENCODE API (network access, no local writes)
_READONLY_API = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)
# Read-only tools that read from local tracker DB only (no network)
_READONLY_LOCAL = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)
# Tools that write to local tracker DB (no network)
_WRITE_LOCAL = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)
# Tools that write to local tracker DB AND query ENCODE API (network)
_WRITE_LOCAL_API = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)
# Tools that download files to disk (network + disk writes)
_DOWNLOAD = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)
# Credential management (can clear credentials = destructive)
_CREDENTIAL_MGMT = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=True,
    idempotentHint=True,
    openWorldHint=False,
)

# Global client instances (managed via lifespan)
_client: EncodeClient | None = None
_downloader: FileDownloader | None = None
_credential_manager = CredentialManager()
_tracker: ExperimentTracker | None = None
_client_lock: asyncio.Lock | None = None


def _get_client_lock() -> asyncio.Lock:
    """Get or create the client lock in the current event loop."""
    global _client_lock
    if _client_lock is None:
        _client_lock = asyncio.Lock()
    return _client_lock


@asynccontextmanager
async def lifespan(server: FastMCP):
    """Manage client lifecycle."""
    global _client, _downloader, _tracker, _client_lock
    # Initialize lock eagerly in lifespan so it's always bound to the
    # correct event loop, rather than lazy-creating in _get_client_lock()
    _client_lock = asyncio.Lock()
    _client = EncodeClient(credential_manager=_credential_manager)
    _downloader = FileDownloader(credential_manager=_credential_manager)
    _tracker = ExperimentTracker()
    try:
        yield
    finally:
        if _client:
            await _client.close()
        if _tracker:
            _tracker.close()


mcp = FastMCP(
    "ENCODE Project",
    instructions=(
        "Query and download genomics data from the ENCODE Project (encodeproject.org). "
        "Search experiments by assay type, organism, organ, biosample, target, and more. "
        "List and download files (FASTQ, BAM, BED, bigWig, etc.). "
        "All data stays local - no telemetry or external data sharing."
    ),
    lifespan=lifespan,
)


async def _get_client() -> EncodeClient:
    async with _get_client_lock():
        if _client is None:
            raise RuntimeError("ENCODE client not initialized")
        return _client


def _get_downloader() -> FileDownloader:
    if _downloader is None:
        raise RuntimeError("File downloader not initialized")
    return _downloader


def _serialize(obj: Any) -> Any:
    """Serialize Pydantic models and other objects to JSON-compatible dicts."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, list):
        return [_serialize(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    return obj


# ======================================================================
# Tool 1: Search Experiments
# ======================================================================


@mcp.tool(annotations=_READONLY_API, title="Search ENCODE Experiments")
async def encode_search_experiments(
    assay_title: str | None = None,
    organism: str = "Homo sapiens",
    organ: str | None = None,
    biosample_type: str | None = None,
    biosample_term_name: str | None = None,
    target: str | None = None,
    status: str = "released",
    lab: str | None = None,
    award: str | None = None,
    assembly: str | None = None,
    replication_type: str | None = None,
    life_stage: str | None = None,
    sex: str | None = None,
    treatment: str | None = None,
    genetic_modification: str | None = None,
    perturbed: bool | None = None,
    search_term: str | None = None,
    date_released_from: str | None = None,
    date_released_to: str | None = None,
    limit: int = 25,
    offset: int = 0,
) -> str:
    """Search ENCODE experiments with comprehensive filters.

    Examples:
    - Find all Histone ChIP-seq on human pancreas tissue:
      assay_title="Histone ChIP-seq", organ="pancreas", biosample_type="tissue"
    - Find ATAC-seq on human brain:
      assay_title="ATAC-seq", organ="brain"
    - Find RNA-seq on GM12878 cell line:
      assay_title="RNA-seq", biosample_term_name="GM12878"
    - Find ChIP-seq targeting H3K27me3:
      assay_title="Histone ChIP-seq", target="H3K27me3"
    - Find all mouse liver experiments:
      organism="Mus musculus", organ="liver"
    - Free text search:
      search_term="CRISPR screen pancreatic"

    Common assay_title values: "Histone ChIP-seq", "TF ChIP-seq", "ATAC-seq",
    "DNase-seq", "RNA-seq", "total RNA-seq", "WGBS", "Hi-C", "CUT&RUN",
    "CUT&Tag", "STARR-seq", "MPRA", "eCLIP", "CRISPR screen"

    Common organ values: "pancreas", "liver", "brain", "heart", "kidney",
    "lung", "intestine", "skin of body", "blood", "spleen", "thymus"

    biosample_type values: "tissue", "cell line", "primary cell",
    "in vitro differentiated cells", "organoid"

    WHEN TO USE: Use as the primary entry point when users want to find experiments.
    Start with encode_get_facets if unsure what filters to use.
    RELATED TOOLS: encode_get_facets, encode_get_metadata, encode_search_files

    Args:
        assay_title: Assay type (e.g., "Histone ChIP-seq", "ATAC-seq", "RNA-seq")
        organism: Species (default: "Homo sapiens"). Also: "Mus musculus"
        organ: Organ/tissue system (e.g., "pancreas", "brain", "liver")
        biosample_type: Sample classification ("tissue", "cell line", "primary cell", "organoid")
        biosample_term_name: Specific cell/tissue name (e.g., "GM12878", "HepG2", "pancreas")
        target: ChIP/CUT&RUN target (e.g., "H3K27me3", "CTCF", "p300")
        status: Data status (default: "released"). Also: "archived", "revoked"
        lab: Submitting lab name
        award: Funding project
        assembly: Genome assembly (e.g., "GRCh38", "mm10")
        replication_type: "isogenic", "anisogenic", or "unreplicated"
        life_stage: "embryonic", "postnatal", "child", "adult"
        sex: "male", "female", "mixed"
        treatment: Treatment name if perturbation experiment
        genetic_modification: Modification type ("CRISPR", "RNAi")
        perturbed: True for perturbation experiments only
        search_term: Free text search across all fields
        date_released_from: Start date (YYYY-MM-DD) for date range filter
        date_released_to: End date (YYYY-MM-DD) for date range filter
        limit: Max results to return (default 25, use larger for comprehensive searches)
        offset: Skip first N results (for pagination)

    Returns:
        JSON with experiment results, total count, and pagination info.
    """
    client = await _get_client()
    limit = clamp_limit(limit)
    result = await client.search_experiments(
        assay_title=assay_title,
        organism=organism,
        organ=organ,
        biosample_type=biosample_type,
        biosample_term_name=biosample_term_name,
        target=target,
        status=status,
        lab=lab,
        award=award,
        assembly=assembly,
        replication_type=replication_type,
        life_stage=life_stage,
        sex=sex,
        treatment=treatment,
        genetic_modification=genetic_modification,
        perturbed=perturbed,
        search_term=search_term,
        date_released_from=date_released_from,
        date_released_to=date_released_to,
        limit=limit,
        offset=offset,
    )
    total = result.get("total", 0)
    serialized = _serialize(result)
    serialized["has_more"] = total > (offset + limit)
    serialized["next_offset"] = offset + limit if total > (offset + limit) else None
    if not result.get("results"):
        serialized["suggestion"] = (
            "Try broadening your search filters. Use encode_get_facets to see what data is available for your criteria."
        )
    return json.dumps(serialized, indent=2)


# ======================================================================
# Tool 2: Get Experiment Details
# ======================================================================


@mcp.tool(annotations=_READONLY_API, title="Get Experiment Details")
async def encode_get_experiment(accession: str) -> str:
    """Get full details for a specific ENCODE experiment by accession ID.

    Returns complete experiment metadata including all associated files,
    quality metrics, controls, replicate information, and audit status.

    WHEN TO USE: Use when you have a specific accession and need full details
    including files, quality metrics, and audit status.
    RELATED TOOLS: encode_list_files, encode_track_experiment, encode_compare_experiments

    Args:
        accession: ENCODE experiment accession (e.g., "ENCSR133RZO", "ENCSR000AKS")

    Returns:
        JSON with full experiment details and file listing.
    """
    validate_accession(accession)
    client = await _get_client()
    result = await client.get_experiment(accession)
    return json.dumps(_serialize(result), indent=2)


# ======================================================================
# Tool 3: List Files for Experiment
# ======================================================================


@mcp.tool(annotations=_READONLY_API, title="List Experiment Files")
async def encode_list_files(
    experiment_accession: str,
    file_format: str | None = None,
    file_type: str | None = None,
    output_type: str | None = None,
    output_category: str | None = None,
    assembly: str | None = None,
    status: str | None = None,
    preferred_default: bool | None = None,
    limit: int = 200,
) -> str:
    """List all files for a specific ENCODE experiment, with optional filters.

    Examples:
    - All BED files: experiment_accession="ENCSR133RZO", file_format="bed"
    - FASTQs only: experiment_accession="ENCSR133RZO", file_format="fastq"
    - Signal tracks: experiment_accession="ENCSR133RZO", output_category="signal"
    - Default/recommended files: preferred_default=True
    - Peaks from GRCh38: file_format="bed", output_type="IDR thresholded peaks", assembly="GRCh38"

    Common file_format values: "fastq", "bam", "bed", "bigWig", "bigBed", "tsv", "hic"

    Common output_type values: "reads", "alignments", "signal of unique reads",
    "signal of all reads", "fold change over control", "IDR thresholded peaks",
    "pseudoreplicated peaks", "replicated peaks", "gene quantifications",
    "transcript quantifications", "contact matrix"

    WHEN TO USE: Use to browse files within a known experiment. Use encode_search_files
    instead to find files across experiments.
    RELATED TOOLS: encode_search_files, encode_get_file_info, encode_download_files

    Args:
        experiment_accession: ENCODE experiment accession (e.g., "ENCSR133RZO")
        file_format: Filter by format ("fastq", "bam", "bed", "bigWig", "bigBed", etc.)
        file_type: Filter by specific type ("bed narrowPeak", "bed broadPeak", etc.)
        output_type: Filter by output type ("reads", "peaks", "signal", etc.)
        output_category: Filter by category ("raw data", "alignment", "signal", "annotation")
        assembly: Filter by genome assembly ("GRCh38", "hg19", "mm10")
        status: Filter by status ("released", "archived", "in progress")
        preferred_default: If True, return only default/recommended files
        limit: Max files to return (default 200)

    Returns:
        JSON list of files with accession, format, size, download URL, and metadata.
    """
    validate_accession(experiment_accession)
    limit = clamp_limit(limit)
    client = await _get_client()
    results = await client.list_files(
        experiment_accession=experiment_accession,
        file_format=file_format,
        file_type=file_type,
        output_type=output_type,
        output_category=output_category,
        assembly=assembly,
        status=status,
        preferred_default=preferred_default,
        limit=limit,
    )
    return json.dumps(_serialize(results), indent=2)


# ======================================================================
# Tool 4: Search Files Across Experiments
# ======================================================================


@mcp.tool(annotations=_READONLY_API, title="Search Files Across Experiments")
async def encode_search_files(
    file_format: str | None = None,
    file_type: str | None = None,
    output_type: str | None = None,
    output_category: str | None = None,
    assembly: str | None = None,
    assay_title: str | None = None,
    organism: str | None = None,
    organ: str | None = None,
    biosample_type: str | None = None,
    target: str | None = None,
    status: str = "released",
    preferred_default: bool | None = None,
    search_term: str | None = None,
    limit: int = 25,
    offset: int = 0,
) -> str:
    """Search files across ALL experiments with combined experiment + file filters.

    This is powerful for finding specific file types across many experiments.

    Examples:
    - All BED files from human pancreas ChIP-seq:
      file_format="bed", assay_title="Histone ChIP-seq", organ="pancreas"
    - FASTQs from mouse liver RNA-seq:
      file_format="fastq", assay_title="RNA-seq", organ="liver", organism="Mus musculus"
    - All IDR peak files for H3K27me3:
      output_type="IDR thresholded peaks", target="H3K27me3"
    - BigWig signal tracks from ATAC-seq on brain tissue:
      file_format="bigWig", assay_title="ATAC-seq", organ="brain", biosample_type="tissue"

    WHEN TO USE: Use to find specific file types across ALL experiments. More powerful
    than encode_list_files for cross-experiment file discovery.
    RELATED TOOLS: encode_list_files, encode_batch_download, encode_get_file_info

    Args:
        file_format: File format ("fastq", "bam", "bed", "bigWig", etc.)
        file_type: Specific file type ("bed narrowPeak", "bed broadPeak", etc.)
        output_type: Output type ("reads", "peaks", "signal", etc.)
        output_category: Output category ("raw data", "alignment", "signal", "annotation")
        assembly: Genome assembly ("GRCh38", "hg19", "mm10")
        assay_title: Filter by assay type of parent experiment
        organism: Filter by organism of parent experiment
        organ: Filter by organ of parent experiment
        biosample_type: Filter by biosample type ("tissue", "cell line", etc.)
        target: Filter by ChIP/CUT&RUN target
        status: File status (default: "released")
        preferred_default: If True, only default/recommended files
        search_term: Free text search
        limit: Max results (default 25)
        offset: Skip first N results (pagination)

    Returns:
        JSON with file results, total count, and pagination info.
    """
    client = await _get_client()
    limit = clamp_limit(limit)
    result = await client.search_files(
        file_format=file_format,
        file_type=file_type,
        output_type=output_type,
        output_category=output_category,
        assembly=assembly,
        assay_title=assay_title,
        organism=organism,
        organ=organ,
        biosample_type=biosample_type,
        target=target,
        status=status,
        preferred_default=preferred_default,
        search_term=search_term,
        limit=limit,
        offset=offset,
    )
    total = result.get("total", 0)
    serialized = _serialize(result)
    serialized["has_more"] = total > (offset + limit)
    serialized["next_offset"] = offset + limit if total > (offset + limit) else None
    if not result.get("results"):
        serialized["suggestion"] = (
            "Verify assembly and file_format values. Use encode_get_metadata('file_formats') to see valid options."
        )
    return json.dumps(serialized, indent=2)


# ======================================================================
# Tool 5: Download Files
# ======================================================================


@mcp.tool(annotations=_DOWNLOAD, title="Download ENCODE Files")
async def encode_download_files(
    file_accessions: list[str],
    download_dir: str,
    organize_by: Literal["flat", "experiment", "format", "experiment_format"] = "flat",
    verify_md5: bool = True,
) -> str:
    """Download specific ENCODE files by accession to a local directory.

    Downloads files from ENCODE to your local machine. Supports MD5 verification,
    concurrent downloads, and skip-if-already-downloaded.

    WHEN TO USE: Use for downloading specific files by accession. For bulk downloads,
    prefer encode_batch_download.
    RELATED TOOLS: encode_batch_download, encode_search_files, encode_log_derived_file

    Args:
        file_accessions: List of file accessions to download (e.g., ["ENCFF635JIA", "ENCFF388RZD"])
        download_dir: Local directory path to save files (e.g., "/Users/you/data/encode")
        organize_by: How to organize downloaded files:
            - "flat": All files in download_dir (default)
            - "experiment": download_dir/ENCSR.../filename
            - "format": download_dir/bed/filename
            - "experiment_format": download_dir/ENCSR.../bed/filename
        verify_md5: Verify file integrity with MD5 checksum (default True)

    Returns:
        JSON with download results for each file (path, size, success/error, MD5 status).
    """
    validate_organize_by(organize_by)
    for acc in file_accessions:
        validate_accession(acc)

    client = await _get_client()
    downloader = _get_downloader()

    # Get file info for each accession
    file_infos = []
    errors = []
    for acc in file_accessions:
        try:
            info = await client.get_file_info(acc)
            file_infos.append(info)
        except Exception as e:
            errors.append({"accession": acc, "error": str(e)})

    # Download all files
    results = await downloader.download_batch(file_infos, download_dir, organize_by, verify_md5)

    output = {
        "downloaded": _serialize(results),
        "errors": errors,
        "summary": {
            "total_requested": len(file_accessions),
            "successful": sum(1 for r in results if r.success),
            "failed": sum(1 for r in results if not r.success) + len(errors),
            "total_size": sum(r.file_size for r in results if r.success),
            "total_size_human": _human_size(sum(r.file_size for r in results if r.success)),
        },
    }
    return json.dumps(output, indent=2)


# ======================================================================
# Tool 6: Get Metadata / Filter Values
# ======================================================================


@mcp.tool(annotations=_READONLY_API, title="Get Filter Values")
async def encode_get_metadata(
    metadata_type: Literal[
        "assays",
        "organisms",
        "organs",
        "biosample_types",
        "file_formats",
        "output_types",
        "output_categories",
        "assemblies",
        "life_stages",
        "replication_types",
        "statuses",
        "file_statuses",
    ],
) -> str:
    """Get available filter values for ENCODE searches.

    Use this to discover valid values for search parameters.

    WHEN TO USE: Use to discover valid filter values before searching. Helps prevent
    typos in assay_title, organ, biosample_type etc.
    RELATED TOOLS: encode_get_facets, encode_search_experiments

    Args:
        metadata_type: Type of metadata to retrieve. Options:
            - "assays": Available assay types (Histone ChIP-seq, ATAC-seq, RNA-seq, etc.)
            - "organisms": Available organisms (Homo sapiens, Mus musculus, etc.)
            - "organs": Available organ/tissue systems (pancreas, brain, liver, etc.)
            - "biosample_types": Biosample classifications (tissue, cell line, primary cell, etc.)
            - "file_formats": File format types (fastq, bam, bed, bigWig, etc.)
            - "output_types": Output data types (reads, peaks, signal, etc.)
            - "output_categories": Output categories (raw data, alignment, signal, etc.)
            - "assemblies": Genome assemblies (GRCh38, hg19, mm10, etc.)
            - "life_stages": Life stages (embryonic, adult, child, etc.)
            - "replication_types": Replication types (isogenic, anisogenic, unreplicated)
            - "statuses": Experiment statuses (released, archived, etc.)
            - "file_statuses": File statuses (released, archived, in progress, etc.)

    Returns:
        JSON list of valid values for the specified metadata type.
    """
    client = await _get_client()
    try:
        values = client.get_metadata(metadata_type)
        return json.dumps({"metadata_type": metadata_type, "values": values, "count": len(values)}, indent=2)
    except ValueError as e:
        return json.dumps({"error": str(e)}, indent=2)


# ======================================================================
# Tool 7: Batch Download from Search
# ======================================================================


@mcp.tool(annotations=_DOWNLOAD, title="Batch Search and Download")
async def encode_batch_download(
    download_dir: str,
    file_format: str | None = None,
    output_type: str | None = None,
    output_category: str | None = None,
    assembly: str | None = None,
    assay_title: str | None = None,
    organism: str = "Homo sapiens",
    organ: str | None = None,
    biosample_type: str | None = None,
    target: str | None = None,
    preferred_default: bool | None = None,
    organize_by: Literal["flat", "experiment", "format", "experiment_format"] = "experiment",
    verify_md5: bool = True,
    limit: int = 100,
    dry_run: bool = True,
) -> str:
    """Search for files and download them all in batch.

    First searches for files matching the criteria, then downloads them.
    By default runs in dry_run mode to preview what would be downloaded.
    Set dry_run=False to actually download.

    WHEN TO USE: Use for searching and downloading files in one step. Always use
    dry_run=True first to preview. For specific file accessions, use encode_download_files.
    RELATED TOOLS: encode_download_files, encode_search_files

    Examples:
    - Download all BED files from human pancreas ChIP-seq:
      file_format="bed", assay_title="Histone ChIP-seq", organ="pancreas",
      download_dir="/data/encode", dry_run=False
    - Preview FASTQ downloads for mouse brain RNA-seq:
      file_format="fastq", assay_title="RNA-seq", organ="brain",
      organism="Mus musculus", download_dir="/data/encode"
    - Download IDR peaks for H3K27me3 in GRCh38:
      output_type="IDR thresholded peaks", target="H3K27me3", assembly="GRCh38",
      download_dir="/data/encode", dry_run=False

    Args:
        download_dir: Local directory to save files
        file_format: File format filter ("fastq", "bam", "bed", "bigWig", etc.)
        output_type: Output type filter ("reads", "peaks", "signal", etc.)
        output_category: Output category ("raw data", "alignment", "annotation", etc.)
        assembly: Genome assembly ("GRCh38", "mm10", etc.)
        assay_title: Assay type ("Histone ChIP-seq", "ATAC-seq", "RNA-seq", etc.)
        organism: Organism (default: "Homo sapiens")
        organ: Organ/tissue ("pancreas", "brain", "liver", etc.)
        biosample_type: Biosample type ("tissue", "cell line", "primary cell", etc.)
        target: ChIP/CUT&RUN target ("H3K27me3", "CTCF", etc.)
        preferred_default: If True, only download default/recommended files
        organize_by: File organization ("flat", "experiment", "format", "experiment_format")
        verify_md5: Verify downloads with MD5 checksums (default True)
        limit: Max files to download (default 100, safety limit)
        dry_run: If True (default), only preview what would be downloaded. Set False to download.

    Returns:
        JSON with download preview (dry_run=True) or download results (dry_run=False).
    """
    client = await _get_client()
    downloader = _get_downloader()
    validate_organize_by(organize_by)
    limit = clamp_limit(limit)

    # Search for files
    search_result = await client.search_files(
        file_format=file_format,
        output_type=output_type,
        output_category=output_category,
        assembly=assembly,
        assay_title=assay_title,
        organism=organism,
        organ=organ,
        biosample_type=biosample_type,
        target=target,
        status="released",
        preferred_default=preferred_default,
        limit=limit,
    )

    files = search_result["results"]

    if not files:
        return json.dumps(
            {
                "message": "No files found matching the search criteria.",
                "total": 0,
                "has_more": False,
                "next_offset": None,
                "suggestion": "Try broadening your search filters. Use encode_get_facets to see what data is available for your criteria.",
            },
            indent=2,
        )

    if dry_run:
        # Preview mode
        search_total = search_result["total"]
        preview = downloader.preview_downloads(files, download_dir, organize_by)
        preview["message"] = (
            f"Found {preview['file_count']} files ({preview['total_size_human']}). Set dry_run=False to download."
        )
        preview["search_total"] = search_total
        preview["has_more"] = search_total > limit
        preview["next_offset"] = limit if search_total > limit else None
        return json.dumps(_serialize(preview), indent=2)

    # Actually download
    results = await downloader.download_batch(files, download_dir, organize_by, verify_md5)
    search_total = search_result["total"]

    output = {
        "downloaded": _serialize(results),
        "summary": {
            "total_found": search_total,
            "total_downloaded": len(results),
            "successful": sum(1 for r in results if r.success),
            "failed": sum(1 for r in results if not r.success),
            "total_size": sum(r.file_size for r in results if r.success),
            "total_size_human": _human_size(sum(r.file_size for r in results if r.success)),
        },
        "has_more": search_total > limit,
        "next_offset": limit if search_total > limit else None,
    }
    return json.dumps(output, indent=2)


# ======================================================================
# Tool 8: Store/Manage Credentials
# ======================================================================


@mcp.tool(annotations=_CREDENTIAL_MGMT, title="Manage API Credentials")
async def encode_manage_credentials(
    action: Literal["store", "check", "clear"],
    access_key: str | None = None,
    secret_key: str | None = None,
) -> str:
    """Manage ENCODE API credentials for accessing restricted/unreleased data.

    Most ENCODE data is public and requires no authentication.
    Credentials are only needed for unreleased or restricted datasets.

    Credentials are stored securely in your OS keyring (macOS Keychain,
    Linux Secret Service, Windows Credential Locker) and never in plaintext.

    WHEN TO USE: Use only for accessing unreleased/restricted ENCODE data.
    Public data requires no authentication.
    RELATED TOOLS: encode_search_experiments

    Args:
        action: What to do:
            - "store": Save new credentials (requires access_key and secret_key)
            - "check": Check if credentials are configured
            - "clear": Remove stored credentials
        access_key: Your ENCODE access key (only for action="store")
        secret_key: Your ENCODE secret key (only for action="store")

    Returns:
        JSON with action result.
    """
    if action == "store":
        if not access_key or not secret_key:
            return json.dumps(
                {
                    "error": "Both access_key and secret_key are required to store credentials.",
                    "help": "Get your access key pair from your ENCODE profile at https://www.encodeproject.org/",
                },
                indent=2,
            )

        location = _credential_manager.store_credentials(access_key, secret_key)
        # Reset client to pick up new credentials
        global _client
        async with _get_client_lock():
            if _client:
                await _client.close()
            _client = EncodeClient(credential_manager=_credential_manager)

        return json.dumps(
            {
                "success": True,
                "message": f"Credentials stored securely in: {location}",
                "note": "Credentials are encrypted and never stored in plaintext.",
            },
            indent=2,
        )

    elif action == "check":
        has_creds = _credential_manager.has_credentials
        return json.dumps(
            {
                "credentials_configured": has_creds,
                "message": (
                    "Credentials are configured. You can access restricted data."
                    if has_creds
                    else "No credentials configured. You can still access all public ENCODE data. "
                    "Use action='store' with your ENCODE access key pair to access restricted data."
                ),
            },
            indent=2,
        )

    elif action == "clear":
        _credential_manager.clear_credentials()
        # Reset client
        async with _get_client_lock():
            if _client:
                await _client.close()
            _client = EncodeClient(credential_manager=_credential_manager)

        return json.dumps(
            {
                "success": True,
                "message": "All stored credentials have been removed.",
            },
            indent=2,
        )

    else:
        return json.dumps(
            {
                "error": f"Unknown action: {action}. Use 'store', 'check', or 'clear'.",
            },
            indent=2,
        )


# ======================================================================
# Tool 9: Get Live Facets (Dynamic Filter Discovery)
# ======================================================================


@mcp.tool(annotations=_READONLY_API, title="Explore Available Data")
async def encode_get_facets(
    search_type: str = "Experiment",
    assay_title: str | None = None,
    organism: str | None = None,
    organ: str | None = None,
    biosample_type: str | None = None,
) -> str:
    """Get live filter counts from ENCODE to discover what data is available.

    Returns faceted counts showing how many experiments/files exist for each
    filter value. Useful for exploring what's available before searching.

    WHEN TO USE: Use to explore what data exists before searching. Shows counts
    per filter value. Best first step for unknown datasets.
    RELATED TOOLS: encode_get_metadata, encode_search_experiments

    Examples:
    - What assays are available for pancreas?
      organ="pancreas"
    - What organs have Histone ChIP-seq data?
      assay_title="Histone ChIP-seq"
    - What targets are available for mouse brain ChIP-seq?
      assay_title="Histone ChIP-seq", organism="Mus musculus", organ="brain"

    Args:
        search_type: Object type ("Experiment" or "File")
        assay_title: Pre-filter by assay type
        organism: Pre-filter by organism
        organ: Pre-filter by organ
        biosample_type: Pre-filter by biosample type

    Returns:
        JSON with facet names and their term counts.
    """
    client = await _get_client()
    filters = {}
    if assay_title:
        filters["assay_title"] = assay_title
    if organism:
        filters["replicates.library.biosample.donor.organism.scientific_name"] = organism
    if organ:
        filters["biosample_ontology.organ_slims"] = organ
    if biosample_type:
        filters["biosample_ontology.classification"] = biosample_type

    facets = await client.search_facets(search_type=search_type, **filters)

    # Simplify output - show most useful facets
    useful_facets = {}
    for field, terms in facets.items():
        # Only include facets with reasonable number of terms
        if len(terms) <= 200:
            useful_facets[field] = terms[:50]  # Cap at 50 terms per facet

    return json.dumps(useful_facets, indent=2)


# ======================================================================
# Tool 10: Get File Info
# ======================================================================


@mcp.tool(annotations=_READONLY_API, title="Get File Details")
async def encode_get_file_info(accession: str) -> str:
    """Get detailed information about a specific ENCODE file.

    WHEN TO USE: Use when you need detailed metadata for a specific file
    (size, md5, assembly, biological replicate info).
    RELATED TOOLS: encode_download_files, encode_list_files

    Args:
        accession: File accession ID (e.g., "ENCFF635JIA")

    Returns:
        JSON with file metadata including format, size, download URL, MD5, assembly, etc.
    """
    validate_accession(accession)
    client = await _get_client()
    info = await client.get_file_info(accession)
    return json.dumps(_serialize(info), indent=2)


# ======================================================================
# Tracker helper
# ======================================================================


def _get_tracker() -> ExperimentTracker:
    if _tracker is None:
        raise RuntimeError("Experiment tracker not initialized")
    return _tracker


# ======================================================================
# Tool 11: Track Experiment
# ======================================================================


@mcp.tool(annotations=_WRITE_LOCAL_API, title="Track Experiment Locally")
async def encode_track_experiment(
    accession: str,
    fetch_publications: bool = True,
    fetch_pipelines: bool = True,
    notes: str = "",
) -> str:
    """Track an ENCODE experiment locally with its publications, methods, and pipeline info.

    Fetches full experiment metadata from ENCODE and stores it in a local SQLite
    database along with any associated publications (PMIDs, DOIs, authors, journal)
    and pipeline/analysis information (software versions, methods).

    This is like adding an experiment to your "library" - similar to Endnote for papers.

    WHEN TO USE: Use to save an experiment to your local library with publications
    and pipeline info. Required before compare or citations.
    RELATED TOOLS: encode_compare_experiments, encode_get_citations, encode_export_data

    Args:
        accession: ENCODE experiment accession (e.g., "ENCSR133RZO")
        fetch_publications: Also fetch and store publications/citations (default True)
        fetch_pipelines: Also fetch and store pipeline/analysis info (default True)
        notes: Optional notes to attach to this experiment

    Returns:
        JSON with tracking result including publications and pipeline info found.
    """
    client = await _get_client()
    tracker = _get_tracker()
    validate_accession(accession)

    # Get full experiment data from ENCODE
    exp_data = await client.get_experiment_raw(accession)

    # Track the experiment
    from encode_connector.client.models import ExperimentDetail

    detail = ExperimentDetail.from_api(exp_data)
    result = tracker.track_experiment(detail.model_dump(), raw_metadata=exp_data)

    if notes:
        tracker.add_note(accession, notes)

    output: dict[str, Any] = {"tracking": result}

    # Auto-link cross-references from dbxrefs (GEO, PMID, etc.)
    dbxrefs = exp_data.get("dbxrefs", []) or []
    auto_linked = []
    for xref in dbxrefs:
        if not isinstance(xref, str):
            continue
        if xref.startswith("GEO:"):
            ref_result = tracker.link_reference(
                accession,
                "geo_accession",
                xref.replace("GEO:", ""),
                "Auto-extracted from ENCODE dbxrefs",
            )
            if ref_result.get("action") == "linked":
                auto_linked.append({"type": "geo_accession", "id": xref.replace("GEO:", "")})
        elif xref.startswith("PMID:"):
            ref_result = tracker.link_reference(
                accession,
                "pmid",
                xref.replace("PMID:", ""),
                "Auto-extracted from ENCODE dbxrefs",
            )
            if ref_result.get("action") == "linked":
                auto_linked.append({"type": "pmid", "id": xref.replace("PMID:", "")})
    if auto_linked:
        output["auto_linked_references"] = auto_linked

    # Fetch publications
    if fetch_publications:
        refs = exp_data.get("references", [])
        # If references are paths, fetch them (validate to prevent SSRF)
        resolved_refs = []
        for ref in refs:
            if isinstance(ref, str):
                try:
                    safe_path = validate_encode_path(ref)
                    ref_data = await client.get_json(safe_path, {"format": "json"})
                    resolved_refs.append(ref_data)
                except Exception as e:
                    logger.warning("Skipping ref %r: %s", ref, e)
            elif isinstance(ref, dict):
                resolved_refs.append(ref)

        pubs = parse_encode_publications(resolved_refs)
        pub_count = tracker.store_publications(accession, pubs)
        output["publications_found"] = pub_count
        output["publications"] = pubs

    # Fetch pipeline info
    if fetch_pipelines:
        analyses = exp_data.get("analyses", [])
        resolved_analyses = []
        for analysis in analyses:
            if isinstance(analysis, str):
                try:
                    safe_path = validate_encode_path(analysis)
                    a_data = await client.get_json(safe_path, {"format": "json"})
                    resolved_analyses.append(a_data)
                except Exception as e:
                    logger.warning("Skipping ref %r: %s", analysis, e)
            elif isinstance(analysis, dict):
                resolved_analyses.append(analysis)

        pipelines = parse_encode_pipelines(resolved_analyses)
        pipe_count = tracker.store_pipeline_info(accession, pipelines)
        output["pipelines_found"] = pipe_count
        output["pipelines"] = pipelines

    return json.dumps(output, indent=2)


# ======================================================================
# Tool 12: List Tracked Experiments
# ======================================================================


@mcp.tool(annotations=_READONLY_LOCAL, title="List Tracked Experiments")
async def encode_list_tracked(
    assay_title: str | None = None,
    organism: str | None = None,
    organ: str | None = None,
) -> str:
    """List all experiments you've tracked locally, with optional filters.

    Shows your local library of tracked ENCODE experiments, their metadata,
    publication counts, and derived file counts.

    WHEN TO USE: Use to see all experiments in your local library. Filter by assay,
    organism, or organ.
    RELATED TOOLS: encode_summarize_collection, encode_export_data

    Args:
        assay_title: Filter by assay type (partial match)
        organism: Filter by organism (partial match)
        organ: Filter by organ (partial match)

    Returns:
        JSON with tracked experiments metadata table and tracker stats.
    """
    tracker = _get_tracker()
    experiments = tracker.list_tracked_experiments(
        assay_title=assay_title,
        organism=organism,
        organ=organ,
    )

    # Build metadata table
    table = tracker.get_metadata_table([e["accession"] for e in experiments] if experiments else None)

    # Remove raw_metadata from output
    for row in table:
        row.pop("raw_metadata", None)

    return json.dumps(
        {
            "experiments": table,
            "count": len(table),
            "stats": tracker.stats,
        },
        indent=2,
    )


# ======================================================================
# Tool 13: Get Experiment Publications & Citations
# ======================================================================


@mcp.tool(annotations=_READONLY_LOCAL, title="Get Citations")
async def encode_get_citations(
    accession: str | None = None,
    export_format: Literal["json", "bibtex", "ris"] = "json",
) -> str:
    """Get publications and citations for tracked experiments.

    Returns publication data with authors, journal, DOI, PMID.
    Can export as BibTeX or RIS (Endnote/Zotero/Mendeley compatible).

    WHEN TO USE: Use to get publication data for tracked experiments. Supports
    BibTeX and RIS export for reference managers.
    RELATED TOOLS: encode_track_experiment, encode_link_reference

    Args:
        accession: Specific experiment accession. If None, returns all publications.
        export_format: Output format:
            - "json": Structured data (default)
            - "bibtex": BibTeX format for LaTeX
            - "ris": RIS format (Endnote, Zotero, Mendeley)

    Returns:
        Publications in the requested format.
    """
    validate_export_format(export_format)
    if accession:
        validate_accession(accession)
    tracker = _get_tracker()

    if export_format == "bibtex":
        bibtex = tracker.export_citations_bibtex([accession] if accession else None)
        return bibtex if bibtex else "No publications found."

    if export_format == "ris":
        ris = tracker.export_citations_ris([accession] if accession else None)
        return ris if ris else "No publications found."

    # JSON format
    if accession:
        pubs = tracker.get_publications(accession)
    else:
        # Get all from all tracked experiments
        experiments = tracker.list_tracked_experiments()
        pubs = []
        for exp in experiments:
            exp_pubs = tracker.get_publications(exp["accession"])
            pubs.extend(exp_pubs)

    return json.dumps(
        {
            "publications": pubs,
            "count": len(pubs),
        },
        indent=2,
        default=str,
    )


# ======================================================================
# Tool 14: Compare Experiments (Compatibility Analysis)
# ======================================================================


@mcp.tool(annotations=_READONLY_LOCAL, title="Compare Experiments")
async def encode_compare_experiments(
    accession1: str,
    accession2: str,
) -> str:
    """Analyze whether two ENCODE experiments are compatible for combined analysis.

    Compares organism, genome assembly, assay type, biosample, organ, target,
    replication strategy, and lab to identify potential issues.

    Both experiments must be tracked first (use encode_track_experiment).

    WHEN TO USE: Use to check if two experiments are compatible for combined analysis.
    Both must be tracked first.
    RELATED TOOLS: encode_track_experiment, encode_list_tracked

    Args:
        accession1: First experiment accession (e.g., "ENCSR133RZO")
        accession2: Second experiment accession (e.g., "ENCSR000AKS")

    Returns:
        JSON compatibility report with verdict, issues, warnings, and recommendations.
    """
    validate_accession(accession1)
    validate_accession(accession2)
    tracker = _get_tracker()
    result = tracker.analyze_compatibility(accession1, accession2)
    return json.dumps(result, indent=2)


# ======================================================================
# Tool 15: Log Derived File (Provenance)
# ======================================================================


@mcp.tool(annotations=_WRITE_LOCAL, title="Log Derived File")
async def encode_log_derived_file(
    file_path: str,
    source_accessions: list[str],
    description: str = "",
    file_type: str = "",
    tool_used: str = "",
    parameters: str = "",
) -> str:
    """Log a file you've derived from ENCODE data for provenance tracking.

    Use this when you create new files from ENCODE data (e.g., running a pipeline,
    filtering peaks, merging samples). This creates a provenance record linking
    your derived file back to the original ENCODE source data.

    WHEN TO USE: Use after creating files from ENCODE data (filtered peaks, merged
    signals). Creates provenance chain back to source.
    RELATED TOOLS: encode_get_provenance, encode_download_files

    Args:
        file_path: Path to the derived file you created
        source_accessions: List of ENCODE accessions this file was derived from
            (experiment or file accessions, e.g., ["ENCSR133RZO", "ENCFF635JIA"])
        description: What this derived file contains
        file_type: Type of file (e.g., "filtered_peaks", "merged_signal", "differential")
        tool_used: Tool/software used to create it (e.g., "bedtools intersect", "DESeq2")
        parameters: Parameters or command used

    Returns:
        JSON with the provenance record ID.
    """
    # Validate each source accession is a valid ENCODE identifier
    for acc in source_accessions:
        validate_accession(acc)

    tracker = _get_tracker()
    row_id = tracker.log_derived_file(
        file_path=file_path,
        source_accessions=source_accessions,
        description=description,
        file_type=file_type,
        tool_used=tool_used,
        parameters=parameters,
    )
    return json.dumps(
        {
            "success": True,
            "record_id": row_id,
            "file_path": file_path,
            "source_accessions": source_accessions,
            "message": "Provenance logged. Use encode_get_provenance to view the full chain.",
        },
        indent=2,
    )


# ======================================================================
# Tool 16: Get Provenance
# ======================================================================


@mcp.tool(annotations=_READONLY_LOCAL, title="Get File Provenance")
async def encode_get_provenance(
    file_path: str | None = None,
    source_accession: str | None = None,
) -> str:
    """Get provenance information for derived files.

    Shows the chain from your derived files back to original ENCODE data,
    including what tools and parameters were used.

    WHEN TO USE: Use to trace a derived file back to original ENCODE data.
    Shows tools and parameters used.
    RELATED TOOLS: encode_log_derived_file

    Args:
        file_path: Get provenance for a specific derived file
        source_accession: List all files derived from a specific ENCODE accession

    Returns:
        JSON provenance chain or list of derived files.
    """
    tracker = _get_tracker()

    if file_path:
        chain = tracker.get_provenance_chain(file_path)
        return json.dumps(chain, indent=2, default=str)

    derived = tracker.get_derived_files(source_accession)
    return json.dumps(
        {
            "derived_files": derived,
            "count": len(derived),
        },
        indent=2,
        default=str,
    )


# ======================================================================
# Tool 17: Export Tracked Data
# ======================================================================


@mcp.tool(annotations=_READONLY_LOCAL, title="Export Tracked Data")
async def encode_export_data(
    format: Literal["csv", "tsv", "json"] = "csv",
    assay_title: str | None = None,
    organism: str | None = None,
    organ: str | None = None,
) -> str:
    """Export tracked experiments as a table (CSV, TSV, or JSON).

    Creates a tabular export of all tracked experiments with metadata,
    publication counts, PMIDs, and derived file counts. Useful for loading
    into Excel, R, pandas, or sharing with collaborators.

    PMIDs in the output can be directly used with PubMed MCP tools for
    further literature analysis.

    WHEN TO USE: Use to create shareable tables of tracked experiments (CSV, TSV, JSON).
    Good for manuscripts and reports.
    RELATED TOOLS: encode_list_tracked, encode_summarize_collection

    Args:
        format: Output format:
            - "csv": Comma-separated values (default, for Excel/spreadsheets)
            - "tsv": Tab-separated values (for R, pandas)
            - "json": JSON array (for programmatic use)
        assay_title: Filter by assay type (partial match)
        organism: Filter by organism (partial match)
        organ: Filter by organ (partial match)

    Returns:
        Formatted table data in the requested format.
    """
    validate_data_export_format(format)
    tracker = _get_tracker()
    result = tracker.export_tracked_data(
        format=format,
        assay_title=assay_title,
        organism=organism,
        organ=organ,
    )
    if not result:
        return json.dumps({"message": "No tracked experiments found matching filters."})
    return result


# ======================================================================
# Tool 18: Summarize Collection
# ======================================================================


@mcp.tool(annotations=_READONLY_LOCAL, title="Summarize Collection")
async def encode_summarize_collection(
    assay_title: str | None = None,
    organism: str | None = None,
    organ: str | None = None,
) -> str:
    """Summarize your tracked experiment collection with grouped statistics.

    Provides an overview of tracked experiments grouped by assay type, target,
    organism, organ, biosample type, and lab. Shows total counts for publications,
    derived files, and external references.

    Useful when tracking 10+ experiments and needing a bird's-eye view of your
    research data collection.

    WHEN TO USE: Use for a bird's-eye view of tracked experiments grouped by assay,
    target, organ. Best for 10+ tracked experiments.
    RELATED TOOLS: encode_list_tracked, encode_export_data

    Args:
        assay_title: Filter by assay type (partial match)
        organism: Filter by organism (partial match)
        organ: Filter by organ (partial match)

    Returns:
        JSON summary with experiment counts grouped by multiple dimensions.
    """
    tracker = _get_tracker()
    summary = tracker.summarize_collection(
        assay_title=assay_title,
        organism=organism,
        organ=organ,
    )
    return json.dumps(summary, indent=2)


# ======================================================================
# Tool 19: Link External Reference
# ======================================================================


@mcp.tool(annotations=_WRITE_LOCAL, title="Link External Reference")
async def encode_link_reference(
    experiment_accession: str,
    reference_type: Literal["pmid", "doi", "nct_id", "preprint_doi", "geo_accession", "other"],
    reference_id: str,
    description: str = "",
) -> str:
    """Link an external reference to a tracked ENCODE experiment.

    This is the cross-server bridge. Attach PubMed IDs, bioRxiv DOIs,
    ClinicalTrials.gov NCT IDs, GEO accessions, or any external identifier
    to your tracked experiments for provenance and cross-referencing.

    After finding a relevant paper with PubMed MCP or a preprint on bioRxiv,
    link it to the ENCODE experiment for future reference.

    WHEN TO USE: Use to attach external IDs (PMID, DOI, GEO, NCT) to tracked
    experiments for cross-referencing.
    RELATED TOOLS: encode_get_references, encode_get_citations

    Args:
        experiment_accession: ENCODE experiment accession (e.g., "ENCSR133RZO")
        reference_type: Type of external reference:
            - "pmid": PubMed ID (e.g., "32728249")
            - "doi": DOI (e.g., "10.1038/s41586-020-2493-4")
            - "nct_id": ClinicalTrials.gov ID (e.g., "NCT04567890")
            - "preprint_doi": bioRxiv/medRxiv DOI
            - "geo_accession": GEO accession (e.g., "GSE123456")
            - "other": Any other identifier
        reference_id: The actual identifier value
        description: Optional description of why this reference is linked

    Returns:
        JSON with linking result.
    """
    validate_accession(experiment_accession)
    validate_reference_type(reference_type)
    tracker = _get_tracker()
    result = tracker.link_reference(
        accession=experiment_accession,
        reference_type=reference_type,
        reference_id=reference_id,
        description=description,
    )
    return json.dumps(result, indent=2)


# ======================================================================
# Tool 20: Get External References
# ======================================================================


@mcp.tool(annotations=_READONLY_LOCAL, title="Get Linked References")
async def encode_get_references(
    experiment_accession: str | None = None,
    reference_type: Literal["pmid", "doi", "nct_id", "preprint_doi", "geo_accession", "other"] | None = None,
) -> str:
    """Get external references linked to tracked experiments.

    Returns PMIDs, DOIs, NCT IDs, GEO accessions and other identifiers
    linked to experiments. These identifiers can be directly passed to
    PubMed, bioRxiv, ClinicalTrials.gov, or other MCP tools.

    WHEN TO USE: Use to retrieve external references linked to experiments.
    PMIDs can be passed to PubMed MCP tools.
    RELATED TOOLS: encode_link_reference, encode_get_citations

    Args:
        experiment_accession: Filter by specific experiment (optional)
        reference_type: Filter by reference type (optional):
            "pmid", "doi", "nct_id", "preprint_doi", "geo_accession", "other"

    Returns:
        JSON with linked external references.
    """
    if experiment_accession:
        validate_accession(experiment_accession)
    tracker = _get_tracker()
    refs = tracker.get_references(
        accession=experiment_accession,
        reference_type=reference_type,
    )
    return json.dumps(
        {
            "references": refs,
            "count": len(refs),
        },
        indent=2,
        default=str,
    )


# ======================================================================
# Entry point
# ======================================================================


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
