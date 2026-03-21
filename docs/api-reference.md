# ENCODE MCP API Reference

*Author: Dr. Alex M. Mawla, PhD*

Complete reference for all 20 MCP tools provided by the ENCODE connector. Each tool includes its full parameter list, return format, and usage examples.

---

## Table of Contents

- [Search & Discovery](#search--discovery)
  - [encode_search_experiments](#encode_search_experiments)
  - [encode_get_facets](#encode_get_facets)
  - [encode_get_metadata](#encode_get_metadata)
- [Experiment Details](#experiment-details)
  - [encode_get_experiment](#encode_get_experiment)
- [File Operations](#file-operations)
  - [encode_list_files](#encode_list_files)
  - [encode_search_files](#encode_search_files)
  - [encode_get_file_info](#encode_get_file_info)
- [Downloads](#downloads)
  - [encode_download_files](#encode_download_files)
  - [encode_batch_download](#encode_batch_download)
- [Experiment Tracking](#experiment-tracking)
  - [encode_track_experiment](#encode_track_experiment)
  - [encode_list_tracked](#encode_list_tracked)
  - [encode_compare_experiments](#encode_compare_experiments)
- [Citations & Publications](#citations--publications)
  - [encode_get_citations](#encode_get_citations)
- [Data Provenance](#data-provenance)
  - [encode_log_derived_file](#encode_log_derived_file)
  - [encode_get_provenance](#encode_get_provenance)
- [Authentication](#authentication)
  - [encode_manage_credentials](#encode_manage_credentials)
- [Data Types & Constants](#data-types--constants)

---

## Search & Discovery

### `encode_search_experiments`

Search ENCODE experiments using 20+ filters. Returns paginated results with experiment metadata.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `assay_title` | string \| null | null | Assay type. See [Assay Types](#assay-types). |
| `organism` | string | `"Homo sapiens"` | Species name. Also: `"Mus musculus"`, `"Drosophila melanogaster"`, `"Caenorhabditis elegans"` |
| `organ` | string \| null | null | Organ or tissue system. See [Organs](#organs). |
| `biosample_type` | string \| null | null | Sample classification: `"tissue"`, `"cell line"`, `"primary cell"`, `"in vitro differentiated cells"`, `"organoid"` |
| `biosample_term_name` | string \| null | null | Specific biosample name (e.g., `"GM12878"`, `"HepG2"`, `"K562"`, `"pancreas"`) |
| `target` | string \| null | null | ChIP/CUT&RUN target (e.g., `"H3K27me3"`, `"H3K4me3"`, `"CTCF"`, `"p300"`) |
| `status` | string | `"released"` | Data status: `"released"`, `"archived"`, `"revoked"` |
| `lab` | string \| null | null | Submitting lab name |
| `award` | string \| null | null | Funding project identifier |
| `assembly` | string \| null | null | Genome assembly: `"GRCh38"`, `"hg19"`, `"mm10"`, `"mm9"` |
| `replication_type` | string \| null | null | `"isogenic"`, `"anisogenic"`, `"unreplicated"` |
| `life_stage` | string \| null | null | `"embryonic"`, `"postnatal"`, `"child"`, `"adult"` |
| `sex` | string \| null | null | `"male"`, `"female"`, `"mixed"` |
| `treatment` | string \| null | null | Treatment name for perturbation experiments |
| `genetic_modification` | string \| null | null | `"CRISPR"`, `"RNAi"` |
| `perturbed` | bool \| null | null | `true` for perturbation experiments only |
| `search_term` | string \| null | null | Free text search across all fields |
| `date_released_from` | string \| null | null | Start date (`YYYY-MM-DD`) |
| `date_released_to` | string \| null | null | End date (`YYYY-MM-DD`) |
| `limit` | int | 25 | Max results to return (capped at 1000) |
| `offset` | int | 0 | Skip first N results for pagination |

#### Returns

```json
{
  "total": 66,
  "results": [
    {
      "accession": "ENCSR133RZO",
      "assay_title": "Histone ChIP-seq",
      "target": "H3K27me3",
      "biosample_summary": "pancreas tissue, adult",
      "organism": "Homo sapiens",
      "assembly": ["GRCh38"],
      "status": "released",
      "date_released": "2023-05-15",
      "lab": "Bernstein, Broad Institute",
      "file_count": 24,
      "replication_type": "isogenic"
    }
  ],
  "limit": 25,
  "offset": 0
}
```

#### Examples

```
# Histone ChIP-seq on human pancreas
assay_title="Histone ChIP-seq", organ="pancreas", biosample_type="tissue"

# ATAC-seq on mouse brain
assay_title="ATAC-seq", organism="Mus musculus", organ="brain"

# RNA-seq on a specific cell line
assay_title="total RNA-seq", biosample_term_name="GM12878"

# Free text search
search_term="CRISPR screen pancreatic"

# Date range
date_released_from="2024-01-01", date_released_to="2024-12-31"
```

---

### `encode_get_facets`

Get live counts showing how many experiments or files exist for each filter value. Use this to explore data availability before searching.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `search_type` | string | `"Experiment"` | Object type: `"Experiment"` or `"File"` |
| `assay_title` | string \| null | null | Pre-filter by assay type |
| `organism` | string \| null | null | Pre-filter by organism |
| `organ` | string \| null | null | Pre-filter by organ |
| `biosample_type` | string \| null | null | Pre-filter by biosample type |

#### Returns

```json
{
  "assay_title": [
    {"key": "Histone ChIP-seq", "doc_count": 2400},
    {"key": "TF ChIP-seq", "doc_count": 1800},
    {"key": "ATAC-seq", "doc_count": 650}
  ],
  "target.label": [
    {"key": "H3K27me3", "doc_count": 12},
    {"key": "H3K4me3", "doc_count": 11}
  ],
  "biosample_ontology.classification": [
    {"key": "tissue", "doc_count": 45},
    {"key": "cell line", "doc_count": 21}
  ]
}
```

#### Examples

```
# What histone marks are available for pancreas?
assay_title="Histone ChIP-seq", organ="pancreas"

# What assays exist for mouse brain?
organism="Mus musculus", organ="brain"

# What organs have ATAC-seq data?
assay_title="ATAC-seq"
```

---

### `encode_get_metadata`

List all valid values for a given filter parameter. Useful for discovering the correct names to use in searches.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `metadata_type` | string | *required* | One of: `"assays"`, `"organisms"`, `"organs"`, `"biosample_types"`, `"file_formats"`, `"output_types"`, `"output_categories"`, `"assemblies"`, `"life_stages"`, `"replication_types"`, `"statuses"`, `"file_statuses"` |

#### Returns

```json
{
  "metadata_type": "assays",
  "values": [
    "Histone ChIP-seq",
    "TF ChIP-seq",
    "ATAC-seq",
    "DNase-seq",
    "RNA-seq",
    "..."
  ],
  "count": 86
}
```

---

## Experiment Details

### `encode_get_experiment`

Get complete metadata for a single experiment, including all associated files, quality metrics, controls, replicate information, and audit status.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `accession` | string | *required* | ENCODE experiment accession (e.g., `"ENCSR133RZO"`) |

#### Returns

```json
{
  "accession": "ENCSR133RZO",
  "assay_title": "Histone ChIP-seq",
  "target": "H3K27me3",
  "biosample_summary": "pancreas tissue, adult",
  "organism": "Homo sapiens",
  "assembly": ["GRCh38"],
  "status": "released",
  "date_released": "2023-05-15",
  "lab": "Bernstein, Broad Institute",
  "award": "U01HG007610",
  "replication_type": "isogenic",
  "controls": ["ENCSR000ABC"],
  "files": [
    {
      "accession": "ENCFF635JIA",
      "file_format": "bed",
      "file_type": "bed narrowPeak",
      "output_type": "IDR thresholded peaks",
      "assembly": "GRCh38",
      "file_size": 1258000,
      "file_size_human": "1.2 MB"
    }
  ],
  "audit": {
    "WARNING": 2,
    "ERROR": 0,
    "NOT_COMPLIANT": 0
  }
}
```

#### Accession format

ENCODE accessions follow the pattern `ENC` + 2-4 uppercase letters + 3-8 alphanumeric characters:

- Experiments: `ENCSR` + 6 characters (e.g., `ENCSR133RZO`)
- Files: `ENCFF` + 6 characters (e.g., `ENCFF635JIA`)
- Biosamples: `ENCBS` + 6 characters
- Donors: `ENCDO` + 6 characters

---

## File Operations

### `encode_list_files`

List all files for a specific experiment with optional format, type, and assembly filters.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `experiment_accession` | string | *required* | Experiment accession (e.g., `"ENCSR133RZO"`) |
| `file_format` | string \| null | null | `"fastq"`, `"bam"`, `"bed"`, `"bigWig"`, `"bigBed"`, `"tsv"`, `"hic"` |
| `file_type` | string \| null | null | `"bed narrowPeak"`, `"bed broadPeak"`, etc. |
| `output_type` | string \| null | null | See [Output Types](#output-types) |
| `output_category` | string \| null | null | `"raw data"`, `"alignment"`, `"signal"`, `"annotation"`, `"quantification"` |
| `assembly` | string \| null | null | `"GRCh38"`, `"hg19"`, `"mm10"` |
| `status` | string \| null | null | `"released"`, `"archived"`, `"in progress"` |
| `preferred_default` | bool \| null | null | `true` returns only recommended files |
| `limit` | int | 200 | Max files to return (capped at 1000) |

#### Returns

```json
[
  {
    "accession": "ENCFF635JIA",
    "file_format": "bed",
    "file_type": "bed narrowPeak",
    "output_type": "IDR thresholded peaks",
    "output_category": "annotation",
    "assembly": "GRCh38",
    "file_size": 1258000,
    "file_size_human": "1.2 MB",
    "md5sum": "a1b2c3d4...",
    "href": "/files/ENCFF635JIA/@@download/ENCFF635JIA.bed.gz",
    "biological_replicates": [1, 2],
    "status": "released"
  }
]
```

---

### `encode_search_files`

Search files across all experiments. Combines experiment filters (assay, organ, target) with file filters (format, output type, assembly).

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `file_format` | string \| null | null | File format filter |
| `file_type` | string \| null | null | Specific file type |
| `output_type` | string \| null | null | Output type filter |
| `output_category` | string \| null | null | Output category filter |
| `assembly` | string \| null | null | Genome assembly |
| `assay_title` | string \| null | null | Assay type of parent experiment |
| `organism` | string \| null | null | Organism of parent experiment |
| `organ` | string \| null | null | Organ of parent experiment |
| `biosample_type` | string \| null | null | Biosample type |
| `target` | string \| null | null | ChIP/CUT&RUN target |
| `status` | string | `"released"` | File status |
| `preferred_default` | bool \| null | null | Only recommended files |
| `search_term` | string \| null | null | Free text search |
| `limit` | int | 25 | Max results (capped at 1000) |
| `offset` | int | 0 | Pagination offset |

#### Returns

```json
{
  "total": 142,
  "results": [
    {
      "accession": "ENCFF635JIA",
      "file_format": "bed",
      "output_type": "IDR thresholded peaks",
      "assembly": "GRCh38",
      "dataset": "ENCSR133RZO",
      "file_size": 1258000,
      "file_size_human": "1.2 MB"
    }
  ],
  "limit": 25,
  "offset": 0
}
```

#### Examples

```
# All BED files from pancreas ChIP-seq
file_format="bed", assay_title="Histone ChIP-seq", organ="pancreas"

# IDR peaks for H3K27me3 in GRCh38
output_type="IDR thresholded peaks", target="H3K27me3", assembly="GRCh38"

# BigWig signal tracks from brain ATAC-seq
file_format="bigWig", assay_title="ATAC-seq", organ="brain"
```

---

### `encode_get_file_info`

Get detailed metadata for a single file by accession.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `accession` | string | *required* | File accession (e.g., `"ENCFF635JIA"`) |

#### Returns

Complete file metadata including format, size, MD5 checksum, download URL, assembly, output type, biological replicates, quality metrics, and parent dataset.

---

## Downloads

### `encode_download_files`

Download specific files by accession to a local directory. Supports MD5 verification and flexible file organization.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `file_accessions` | list[string] | *required* | File accessions to download |
| `download_dir` | string | *required* | Local directory path |
| `organize_by` | string | `"flat"` | Directory structure (see below) |
| `verify_md5` | bool | `true` | Verify file integrity after download |

#### `organize_by` options

| Value | Structure |
|-------|-----------|
| `"flat"` | All files in `download_dir/` |
| `"experiment"` | `download_dir/ENCSR.../filename` |
| `"format"` | `download_dir/bed/filename` |
| `"experiment_format"` | `download_dir/ENCSR.../bed/filename` |

#### Returns

```json
{
  "downloaded": [
    {
      "accession": "ENCFF635JIA",
      "file_path": "/Users/you/data/ENCFF635JIA.bed.gz",
      "file_size": 1258000,
      "success": true,
      "md5_verified": true
    }
  ],
  "errors": [],
  "summary": {
    "total_requested": 2,
    "successful": 2,
    "failed": 0,
    "total_size": 4058000,
    "total_size_human": "3.9 MB"
  }
}
```

---

### `encode_batch_download`

Search for files and download them all in one step. Defaults to **dry-run mode** (preview only).

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `download_dir` | string | *required* | Local directory path |
| `file_format` | string \| null | null | File format filter |
| `output_type` | string \| null | null | Output type filter |
| `output_category` | string \| null | null | Output category |
| `assembly` | string \| null | null | Genome assembly |
| `assay_title` | string \| null | null | Assay type |
| `organism` | string | `"Homo sapiens"` | Organism |
| `organ` | string \| null | null | Organ |
| `biosample_type` | string \| null | null | Biosample type |
| `target` | string \| null | null | ChIP/CUT&RUN target |
| `preferred_default` | bool \| null | null | Only recommended files |
| `organize_by` | string | `"experiment"` | File organization |
| `verify_md5` | bool | `true` | Verify checksums |
| `limit` | int | 100 | Max files (safety cap, max 1000) |
| `dry_run` | bool | `true` | **Preview only.** Set `false` to download. |

#### Returns (dry_run=true)

```json
{
  "message": "Found 58 files (120 MB). Set dry_run=False to download.",
  "file_count": 58,
  "total_size": 125829120,
  "total_size_human": "120.0 MB",
  "files": ["ENCFF635JIA.bed.gz", "ENCFF388RZD.bed.gz", "..."],
  "search_total": 142
}
```

#### Returns (dry_run=false)

Same format as `encode_download_files` with a download summary.

---

## Experiment Tracking

### `encode_track_experiment`

Add an experiment to your local library. Automatically fetches and stores associated publications and pipeline information.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `accession` | string | *required* | Experiment accession |
| `fetch_publications` | bool | `true` | Also fetch publications (PMIDs, DOIs, authors) |
| `fetch_pipelines` | bool | `true` | Also fetch pipeline info (software, versions) |
| `notes` | string | `""` | Optional notes to attach |

#### Returns

```json
{
  "tracking": {
    "accession": "ENCSR133RZO",
    "status": "tracked",
    "new": true
  },
  "publications_found": 2,
  "publications": [
    {
      "title": "Chromatin landscape of the human pancreas",
      "authors": "Smith J, Jones A, Lee B",
      "journal": "Nature Genetics",
      "year": "2023",
      "doi": "10.1038/ng.xxxx",
      "pmid": "12345678"
    }
  ],
  "pipelines_found": 1,
  "pipelines": [
    {
      "title": "ENCODE Histone ChIP-seq pipeline",
      "version": "v2.0",
      "software": ["bowtie2", "macs2", "samtools"]
    }
  ]
}
```

#### Storage

Data is stored in a local SQLite database at `~/.encode_connector/tracker.db`. The database uses WAL mode for concurrent read access and includes tables for experiments, publications, pipeline info, and derived files.

---

### `encode_list_tracked`

List all experiments in your local tracker with optional filters.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `assay_title` | string \| null | null | Filter by assay type (partial match) |
| `organism` | string \| null | null | Filter by organism (partial match) |
| `organ` | string \| null | null | Filter by organ (partial match) |

#### Returns

```json
{
  "experiments": [
    {
      "accession": "ENCSR133RZO",
      "assay_title": "Histone ChIP-seq",
      "target": "H3K27me3",
      "organism": "Homo sapiens",
      "organ": "pancreas",
      "biosample_type": "tissue",
      "status": "released",
      "publication_count": 2,
      "derived_file_count": 1,
      "tracked_at": "2026-03-06T14:30:00",
      "notes": ""
    }
  ],
  "count": 3,
  "stats": {
    "total_experiments": 3,
    "total_publications": 6,
    "total_derived_files": 2
  }
}
```

---

### `encode_compare_experiments`

Analyze whether two tracked experiments are compatible for combined analysis. Checks organism, assembly, assay type, biosample, organ, target, replication, and lab.

**Prerequisite:** Both experiments must be tracked first via `encode_track_experiment`.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `accession1` | string | *required* | First experiment accession |
| `accession2` | string | *required* | Second experiment accession |

#### Returns

```json
{
  "verdict": "compatible",
  "issues": [],
  "warnings": [
    "Different targets: H3K27me3 vs H3K4me3 - expected for multi-mark analysis.",
    "Different labs: Bernstein vs Ren - check for batch effects."
  ],
  "recommendations": [
    "Experiments can be combined for multi-mark chromatin analysis.",
    "Consider batch correction for cross-lab comparisons."
  ],
  "details": {
    "organism": {"match": true, "values": ["Homo sapiens", "Homo sapiens"]},
    "assembly": {"match": true, "values": ["GRCh38", "GRCh38"]},
    "assay_title": {"match": true, "values": ["Histone ChIP-seq", "Histone ChIP-seq"]},
    "organ": {"match": true, "values": ["pancreas", "pancreas"]},
    "target": {"match": false, "values": ["H3K27me3", "H3K4me3"]}
  }
}
```

#### Verdicts

| Verdict | Meaning |
|---------|---------|
| `"compatible"` | Safe to combine with no significant issues |
| `"compatible_with_caveats"` | Combinable but review the warnings |
| `"incompatible"` | Fundamental mismatches (different organism or assembly) |

---

## Citations & Publications

### `encode_get_citations`

Get publications for tracked experiments. Supports export in BibTeX (LaTeX) and RIS (Endnote/Zotero/Mendeley) formats.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `accession` | string \| null | null | Specific experiment. If null, returns all publications. |
| `export_format` | string | `"json"` | `"json"`, `"bibtex"`, or `"ris"` |

#### Returns (json)

```json
{
  "publications": [
    {
      "title": "Chromatin landscape of the human pancreas",
      "authors": "Smith J, Jones A, Lee B",
      "journal": "Nature Genetics",
      "year": "2023",
      "doi": "10.1038/ng.xxxx",
      "pmid": "12345678"
    }
  ],
  "count": 2
}
```

#### Returns (bibtex)

```bibtex
@article{PMID12345678,
  author  = {Smith, J. and Jones, A. and Lee, B.},
  title   = {Chromatin landscape of the human pancreas},
  journal = {Nature Genetics},
  year    = {2023},
  doi     = {10.1038/ng.xxxx},
  pmid    = {12345678},
}
```

#### Returns (ris)

```
TY  - JOUR
AU  - Smith, J.
AU  - Jones, A.
AU  - Lee, B.
TI  - Chromatin landscape of the human pancreas
JO  - Nature Genetics
PY  - 2023
DO  - 10.1038/ng.xxxx
ER  -
```

---

## Data Provenance

### `encode_log_derived_file`

Log a file you created from ENCODE data. Creates a provenance record linking your derived file back to the original source data.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `file_path` | string | *required* | Path to your derived file |
| `source_accessions` | list[string] | *required* | ENCODE accessions this was derived from (experiment or file accessions) |
| `description` | string | `""` | What the file contains |
| `file_type` | string | `""` | File type (e.g., `"filtered_peaks"`, `"merged_signal"`, `"differential"`) |
| `tool_used` | string | `""` | Software used (e.g., `"bedtools intersect"`, `"DESeq2"`, `"deepTools"`) |
| `parameters` | string | `""` | Command or parameters used |

#### Returns

```json
{
  "success": true,
  "record_id": 1,
  "file_path": "~/analysis/filtered_peaks.bed",
  "source_accessions": ["ENCSR133RZO", "ENCFF635JIA"],
  "message": "Provenance logged. Use encode_get_provenance to view the full chain."
}
```

---

### `encode_get_provenance`

View provenance chains from derived files back to original ENCODE source data.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `file_path` | string \| null | null | Get provenance for a specific derived file |
| `source_accession` | string \| null | null | List all files derived from a specific accession |

Provide one or the other. If `source_accession` is null, returns all derived files.

#### Returns (file_path)

```json
[
  {
    "file_path": "~/analysis/filtered_peaks.bed",
    "description": "H3K27me3 peaks filtered to promoter regions",
    "file_type": "filtered_peaks",
    "tool_used": "bedtools intersect",
    "parameters": "bedtools intersect -a ENCFF635JIA.bed -b promoters.bed -u",
    "created_at": "2026-03-06T14:30:00",
    "source_accessions": ["ENCSR133RZO", "ENCFF635JIA"]
  }
]
```

#### Returns (source_accession)

```json
{
  "derived_files": [
    {
      "file_path": "~/analysis/filtered_peaks.bed",
      "description": "H3K27me3 peaks filtered to promoter regions",
      "tool_used": "bedtools intersect",
      "created_at": "2026-03-06T14:30:00"
    }
  ],
  "count": 1
}
```

---

## Authentication

### `encode_manage_credentials`

Manage ENCODE API credentials for accessing restricted or unreleased data. Most ENCODE data is public and needs no authentication.

Credentials are stored in your OS keyring (macOS Keychain, Linux Secret Service, Windows Credential Locker) and encrypted at rest. Never stored in plaintext.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `action` | string | *required* | `"store"`, `"check"`, or `"clear"` |
| `access_key` | string \| null | null | ENCODE access key (required for `"store"`) |
| `secret_key` | string \| null | null | ENCODE secret key (required for `"store"`) |

#### Returns (check)

```json
{
  "credentials_configured": false,
  "message": "No credentials configured. You can still access all public ENCODE data."
}
```

#### Returns (store)

```json
{
  "success": true,
  "message": "Credentials stored securely in: os_keyring",
  "note": "Credentials are encrypted and never stored in plaintext."
}
```

#### Returns (clear)

```json
{
  "success": true,
  "message": "All stored credentials have been removed."
}
```

---

## Data Types & Constants

### Assay Types

The most commonly used assay types:

| Category | Assay Titles |
|----------|-------------|
| **Histone/Chromatin** | `"Histone ChIP-seq"`, `"TF ChIP-seq"`, `"ATAC-seq"`, `"DNase-seq"`, `"CUT&RUN"`, `"CUT&Tag"`, `"MNase-seq"` |
| **Transcription** | `"total RNA-seq"`, `"polyA plus RNA-seq"`, `"small RNA-seq"`, `"long read RNA-seq"`, `"CAGE"`, `"RAMPAGE"`, `"PRO-seq"`, `"GRO-seq"` |
| **3D Genome** | `"Hi-C"`, `"intact Hi-C"`, `"Micro-C"`, `"ChIA-PET"`, `"HiChIP"`, `"PLAC-seq"`, `"5C"` |
| **DNA Methylation** | `"WGBS"`, `"RRBS"`, `"MeDIP-seq"`, `"MRE-seq"` |
| **Functional** | `"STARR-seq"`, `"MPRA"`, `"CRISPR screen"`, `"eCLIP"`, `"iCLIP"` |
| **Single Cell** | `"scRNA-seq"`, `"snATAC-seq"`, `"snRNA-seq"`, `"long read scRNA-seq"` |
| **Perturbation** | `"CRISPRi RNA-seq"`, `"shRNA RNA-seq"`, `"siRNA RNA-seq"`, `"CRISPR RNA-seq"` |

### Organs

```
adipose tissue, adrenal gland, blood, blood vessel, bodily fluid,
bone element, bone marrow, brain, breast, bronchus, colon,
connective tissue, embryo, endocrine gland, epithelium, esophagus,
exocrine gland, eye, gonad, heart, immune organ, intestine, kidney,
large intestine, limb, liver, lung, lymph node, mammary gland, mouth,
musculature of body, nerve, nose, ovary, pancreas, penis, placenta,
prostate gland, skin of body, small intestine, spinal cord, spleen,
stomach, testis, thymus, thyroid gland, tongue, tonsil, trachea,
urinary bladder, uterus, vagina, vasculature, vein
```

### File Formats

```
fastq, bam, bed, bigWig, bigBed, tsv, csv, tar, hic,
tagAlign, bedpe, pairs, fasta, gff, gtf, vcf
```

### Output Types

| Category | Output Types |
|----------|-------------|
| **Raw** | `"reads"` |
| **Alignment** | `"alignments"`, `"unfiltered alignments"`, `"transcriptome alignments"` |
| **Signal** | `"signal of unique reads"`, `"signal of all reads"`, `"signal p-value"`, `"fold change over control"` |
| **Peaks** | `"IDR thresholded peaks"`, `"pseudoreplicated peaks"`, `"replicated peaks"`, `"conservative IDR thresholded peaks"`, `"optimal IDR thresholded peaks"` |
| **Quantification** | `"gene quantifications"`, `"transcript quantifications"`, `"exon quantifications"` |
| **3D Genome** | `"contact matrix"`, `"contact domains"`, `"topologically associated domains"`, `"chromatin interactions"` |
| **Methylation** | `"methylation state at CpG"`, `"methylation state at CHG"`, `"methylation state at CHH"` |

### Genome Assemblies

| Assembly | Organism |
|----------|----------|
| `GRCh38` | Human (current) |
| `hg19` | Human (legacy) |
| `mm10` | Mouse (current) |
| `mm9` | Mouse (legacy) |
| `GRCm39` | Mouse (newest) |
| `dm6` | Fly |
| `ce11` | Worm |

---

## Rate Limits & Performance

- ENCODE API rate limit: **10 requests per second** (automatically handled)
- Download concurrency: **3 parallel downloads**
- Search results: capped at **1000** per query (use pagination for larger sets)
- Download timeout: **5 minutes** per file
- All downloads verified with **MD5 checksums** by default

## Local Storage

| Path | Contents |
|------|----------|
| `~/.encode_connector/tracker.db` | SQLite database with tracked experiments, publications, pipelines, provenance |
| `~/.encode_connector/.salt` | PBKDF2 salt for credential encryption fallback (0600 permissions) |
| OS Keyring | Encrypted ENCODE API credentials (macOS Keychain / Linux Secret Service / Windows Credential Locker) |

## Security

- **SSRF prevention**: All API paths validated before requests
- **Path traversal prevention**: Download paths sanitized and resolved
- **Input validation**: Accessions, dates, URLs validated before use
- **Auth header stripping**: Credentials not sent to redirect destinations (S3/CDN)
- **Rate limiting**: Respects ENCODE's 10 req/sec policy
- **Encrypted credentials**: PBKDF2 + Fernet when OS keyring unavailable
- **Certificate verification**: Always enforced (no `verify=False`)
- **SQL injection prevention**: Parameterized queries + LIKE pattern escaping
