"""Pydantic models for ENCODE API response objects."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExperimentSummary(BaseModel):
    """Condensed experiment info returned from search results."""

    accession: str
    assay_title: str = ""
    target: str = ""
    biosample_summary: str = ""
    organism: str = ""
    organ: str = ""
    biosample_type: str = ""
    status: str = ""
    date_released: str = ""
    description: str = ""
    lab: str = ""
    file_count: int = 0
    replication_type: str = ""
    life_stage: str = ""
    assembly: list[str] = Field(default_factory=list)
    audit_error_count: int = 0
    audit_warning_count: int = 0
    dbxrefs: list[str] = Field(default_factory=list)
    url: str = ""

    @classmethod
    def from_api(cls, data: dict) -> ExperimentSummary:
        """Parse from ENCODE API experiment object (frame=object)."""
        # Extract target label
        target = ""
        if data.get("target"):
            t = data["target"]
            if isinstance(t, str):
                # Reference path like /targets/H3K27me3-human/
                target = t.strip("/").split("/")[-1] if "/" in t else t
            elif isinstance(t, dict):
                target = t.get("label", "")

        # Extract lab
        lab = ""
        if data.get("lab"):
            lab_raw = data["lab"]
            if isinstance(lab_raw, str):
                lab = lab_raw.strip("/").split("/")[-1]
            elif isinstance(lab_raw, dict):
                lab = lab_raw.get("title", lab_raw.get("name", ""))

        # Extract biosample type from ontology
        biosample_type = ""
        organ = ""
        if data.get("biosample_ontology"):
            ont = data["biosample_ontology"]
            if isinstance(ont, dict):
                biosample_type = ont.get("classification", "")
                organ_slims = ont.get("organ_slims", [])
                organ = ", ".join(organ_slims) if organ_slims else ""
            elif isinstance(ont, str):
                biosample_type = ont

        # Extract assembly list from files
        assemblies = sorted(
            set(f.get("assembly", "") for f in data.get("files", []) if isinstance(f, dict) and f.get("assembly"))
        )

        # Extract audit counts
        audit = data.get("audit", {})
        audit_errors = len(audit.get("ERROR", [])) if isinstance(audit, dict) else 0
        audit_warnings = len(audit.get("WARNING", [])) if isinstance(audit, dict) else 0

        # Extract dbxrefs (GEO accessions, etc.)
        dbxrefs = data.get("dbxrefs", []) or []

        accession_val = data.get("accession", "")

        return cls(
            accession=accession_val,
            assay_title=data.get("assay_title", ""),
            target=target,
            biosample_summary=data.get("biosample_summary", ""),
            organism=data.get("organism", {}).get("scientific_name", "")
            if isinstance(data.get("organism"), dict)
            else "",
            organ=organ,
            biosample_type=biosample_type,
            status=data.get("status", ""),
            date_released=data.get("date_released", ""),
            description=data.get("description", ""),
            lab=lab,
            file_count=len(data.get("files", [])),
            replication_type=data.get("replication_type", ""),
            life_stage=data.get("life_stage_age", ""),
            assembly=assemblies,
            audit_error_count=audit_errors,
            audit_warning_count=audit_warnings,
            dbxrefs=dbxrefs,
            url=f"https://www.encodeproject.org/experiments/{accession_val}/" if accession_val else "",
        )


class FileSummary(BaseModel):
    """Condensed file info from search/listing results."""

    accession: str
    file_format: str = ""
    file_type: str = ""
    output_type: str = ""
    output_category: str = ""
    file_size: int = 0
    file_size_human: str = ""
    assembly: str = ""
    biological_replicates: list[int] = Field(default_factory=list)
    technical_replicates: list[str] = Field(default_factory=list)
    status: str = ""
    download_url: str = ""
    s3_uri: str = ""
    md5sum: str = ""
    experiment_accession: str = ""
    experiment_assay: str = ""
    biosample_summary: str = ""
    preferred_default: bool = False
    date_created: str = ""

    @classmethod
    def from_api(cls, data: dict, base_url: str = "https://www.encodeproject.org") -> FileSummary:
        """Parse from ENCODE API file object."""
        href = data.get("href", "")
        download_url = f"{base_url}{href}" if href and not href.startswith("http") else href

        file_size = data.get("file_size", 0) or 0

        # Extract experiment accession from dataset path
        experiment_accession = ""
        dataset = data.get("dataset", "")
        if isinstance(dataset, str) and "/experiments/" in dataset:
            experiment_accession = dataset.strip("/").split("/")[-1]
        elif isinstance(dataset, dict):
            experiment_accession = dataset.get("accession", "")

        return cls(
            accession=data.get("accession", ""),
            file_format=data.get("file_format", ""),
            file_type=data.get("file_type", ""),
            output_type=data.get("output_type", ""),
            output_category=data.get("output_category", ""),
            file_size=file_size,
            file_size_human=_human_size(file_size),
            assembly=data.get("assembly", "") or "",
            biological_replicates=data.get("biological_replicates", []),
            technical_replicates=data.get("technical_replicates", []),
            status=data.get("status", ""),
            download_url=download_url,
            s3_uri=data.get("s3_uri", "") or "",
            md5sum=data.get("md5sum", "") or "",
            experiment_accession=experiment_accession,
            experiment_assay=data.get("assay_title", ""),
            biosample_summary=data.get("biosample_summary", "") or "",
            preferred_default=data.get("preferred_default", False) or False,
            date_created=data.get("date_created", ""),
        )


def _extract_organism(data: dict) -> str:
    """Extract organism from nested ENCODE API data."""
    # Direct organism field (frame=object)
    org = data.get("organism")
    if isinstance(org, dict):
        return org.get("scientific_name", "")
    if isinstance(org, str) and org:
        return org.strip("/").split("/")[-1]
    # Try replicates path (frame=embedded)
    for rep in data.get("replicates", []):
        if isinstance(rep, dict):
            lib = rep.get("library", {})
            if isinstance(lib, dict):
                bs = lib.get("biosample", {})
                if isinstance(bs, dict):
                    donor = bs.get("donor", {})
                    if isinstance(donor, dict):
                        org2 = donor.get("organism", {})
                        if isinstance(org2, dict):
                            name = org2.get("scientific_name", "")
                            if name:
                                return name
    return ""


class ExperimentDetail(BaseModel):
    """Full experiment details including files list."""

    accession: str
    assay_title: str = ""
    assay_term_name: str = ""
    target: str = ""
    biosample_summary: str = ""
    description: str = ""
    status: str = ""
    date_released: str = ""
    lab: str = ""
    award: str = ""
    organism: str = ""
    organ: str = ""
    biosample_type: str = ""
    life_stage: str = ""
    replication_type: str = ""
    bio_replicate_count: int = 0
    tech_replicate_count: int = 0
    possible_controls: list[str] = Field(default_factory=list)
    related_series: list[str] = Field(default_factory=list)
    documents: list[str] = Field(default_factory=list)
    url: str = ""
    files: list[FileSummary] = Field(default_factory=list)

    # Quality/audit info
    audit_error_count: int = 0
    audit_warning_count: int = 0

    @classmethod
    def from_api(cls, data: dict, files: list[dict] | None = None) -> ExperimentDetail:
        """Parse from ENCODE API experiment object (frame=embedded preferred)."""
        # Extract target
        target = ""
        if data.get("target"):
            t = data["target"]
            if isinstance(t, str):
                target = t.strip("/").split("/")[-1]
            elif isinstance(t, dict):
                target = t.get("label", "")

        # Extract lab
        lab = ""
        if data.get("lab"):
            lab_raw = data["lab"]
            if isinstance(lab_raw, str):
                lab = lab_raw.strip("/").split("/")[-1]
            elif isinstance(lab_raw, dict):
                lab = lab_raw.get("title", lab_raw.get("name", ""))

        # Extract award/project
        award = ""
        if data.get("award"):
            a = data["award"]
            if isinstance(a, str):
                award = a.strip("/").split("/")[-1]
            elif isinstance(a, dict):
                award = a.get("project", a.get("name", ""))

        # Extract biosample details
        biosample_type = ""
        organ = ""
        if data.get("biosample_ontology"):
            ont = data["biosample_ontology"]
            if isinstance(ont, dict):
                biosample_type = ont.get("classification", "")
                organ_slims = ont.get("organ_slims", [])
                organ = ", ".join(organ_slims) if organ_slims else ""

        # Controls
        controls = []
        for ctrl in data.get("possible_controls", []):
            if isinstance(ctrl, str):
                controls.append(ctrl.strip("/").split("/")[-1])
            elif isinstance(ctrl, dict):
                controls.append(ctrl.get("accession", ""))

        # Audit counts
        audit = data.get("audit", {})
        error_count = len(audit.get("ERROR", [])) if isinstance(audit, dict) else 0
        warning_count = len(audit.get("WARNING", [])) if isinstance(audit, dict) else 0

        # Parse files
        file_summaries = []
        if files:
            file_summaries = [FileSummary.from_api(f) for f in files]

        return cls(
            accession=data.get("accession", ""),
            assay_title=data.get("assay_title", ""),
            assay_term_name=data.get("assay_term_name", ""),
            target=target,
            biosample_summary=data.get("biosample_summary", ""),
            description=data.get("description", ""),
            status=data.get("status", ""),
            date_released=data.get("date_released", ""),
            lab=lab,
            award=award,
            organism=_extract_organism(data),
            organ=organ,
            biosample_type=biosample_type,
            life_stage=data.get("life_stage_age", ""),
            replication_type=data.get("replication_type", ""),
            bio_replicate_count=data.get("bio_replicate_count", 0) or 0,
            tech_replicate_count=data.get("tech_replicate_count", 0) or 0,
            possible_controls=controls,
            related_series=[
                s if isinstance(s, str) else s.get("accession", "") for s in data.get("related_series", [])
            ],
            documents=[d if isinstance(d, str) else d.get("@id", "") for d in data.get("documents", [])],
            url=f"https://www.encodeproject.org/experiments/{data.get('accession', '')}/",
            files=file_summaries,
            audit_error_count=error_count,
            audit_warning_count=warning_count,
        )


class DownloadResult(BaseModel):
    """Result of a file download operation."""

    accession: str
    file_path: str = ""
    file_size: int = 0
    file_size_human: str = ""
    success: bool = False
    error: str = ""
    md5_verified: bool = False


def _human_size(size_bytes: int) -> str:
    """Convert bytes to human-readable string."""
    if size_bytes == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
    return f"{size:.1f} {units[i]}"
