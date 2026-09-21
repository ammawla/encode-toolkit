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
  - [encode_summarize_collection](#encode_summarize_collection)
  - [encode_export_data](#encode_export_data)
- [Citations & Publications](#citations--publications)
  - [encode_get_citations](#encode_get_citations)
  - [encode_link_reference](#encode_link_reference)
  - [encode_get_references](#encode_get_references)
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
| `limit` | int | 25 | Max results to return (clamped to 1-1000) |
| `offset` | int | 0 | Skip first N results for pagination |

#### Returns

```json
{
  "results": [
    {
      "accession": "ENCSR133RZO",
      "assay_title": "Histone ChIP-seq",
      "target": "H3K27me3",
      "biosample_summary": "pancreas tissue male adult (54 years)",
      "organism": "Homo sapiens",
      "organ": "pancreas",
      "biosample_type": "tissue",
      "status": "released",
      "date_released": "2023-05-15",
      "description": "H3K27me3 ChIP-seq on human pancreas",
      "lab": "Bing Ren, UCSD",
      "file_count": 24,
      "replication_type": "isogenic",
      "life_stage": "adult",
      "assembly": ["GRCh38"],
      "audit_error_count": 0,
      "audit_not_compliant_count": 1,
      "audit_warning_count": 3,
      "audit_internal_action_count": 2,
      "dbxrefs": ["GEO:GSE123456"],
      "url": "https://www.encodeproject.org/experiments/ENCSR133RZO/"
    }
  ],
  "total": 66,
  "limit": 25,
  "offset": 0,
  "has_more": true,
  "next_offset": 25
}
```

Notes on the shape:

- Audits are four flat integers (`audit_error_count`, `audit_not_compliant_count`, `audit_warning_count`, `audit_internal_action_count`), not a nested object.
- `assembly` is a list of the assemblies seen on the experiment's files.
- `organ` is a comma-joined string when a biosample maps to several organ slims.
- `next_offset` is `null` once the result set is exhausted; the key is always present.
- `filter_warnings` (array of strings) is added when `assay_title`, `organ`, or `biosample_type` is not one of the known ENCODE values.
- `suggestion` (string) is added when `results` is empty.

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
    {"term": "Histone ChIP-seq", "count": 412},
    {"term": "TF ChIP-seq", "count": 188},
    {"term": "ATAC-seq", "count": 96}
  ],
  "target.label": [
    {"term": "H3K27me3", "count": 12},
    {"term": "H3K4me3", "count": 11}
  ],
  "biosample_ontology.classification": [
    {"term": "tissue", "count": 45},
    {"term": "cell line", "count": 21}
  ]
}
```

Notes on the shape:

- The top-level keys are ENCODE facet field names taken verbatim from the portal (`assay_title`, `status`, `target.label`, `biosample_ontology.classification`, `biosample_ontology.organ_slims`, `lab.title`, ...). Which ones appear depends on `search_type` and the filters — there is no fixed set and no `"facets"` wrapper.
- Every facet value is an array of `{"term": ..., "count": ...}` objects. Terms with a zero count are dropped, facets with more than 200 terms are omitted entirely, and surviving facets are capped at their first 50 terms.
- `filter_warnings` (array of strings) is added when a pre-filter value is not a known ENCODE value.

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

List all valid values for a given filter parameter. Useful for discovering the correct names to use in searches. The lists are static (no API call) and come from the server's own catalog of ENCODE values.

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
    "total RNA-seq",
    "..."
  ],
  "count": 79
}
```

`count` is simply `len(values)`:

| metadata_type | Values |
|---------------|--------|
| assays | 79 |
| organisms | 5 |
| organs | 66 |
| biosample_types | 8 |
| file_formats | 38 |
| output_types | 88 |
| output_categories | 6 |
| assemblies | 17 |
| life_stages | 7 |
| replication_types | 3 |
| statuses | 8 |
| file_statuses | 7 |

---

## Experiment Details

### `encode_get_experiment`

Get complete metadata for a single experiment, including all associated files, controls, replicate counts, and audit counts.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `accession` | string | *required* | ENCODE experiment accession (e.g., `"ENCSR133RZO"`) |

#### Returns

```json
{
  "accession": "ENCSR133RZO",
  "assay_title": "Histone ChIP-seq",
  "assay_term_name": "ChIP-seq",
  "target": "H3K27me3",
  "biosample_summary": "pancreas tissue male adult (54 years)",
  "description": "H3K27me3 ChIP-seq on human pancreas",
  "status": "released",
  "date_released": "2023-05-15",
  "lab": "Bing Ren, UCSD",
  "award": "ENCODE",
  "organism": "Homo sapiens",
  "organ": "pancreas",
  "biosample_type": "tissue",
  "life_stage": "adult",
  "replication_type": "isogenic",
  "assembly": ["GRCh38"],
  "bio_replicate_count": 2,
  "tech_replicate_count": 2,
  "possible_controls": ["ENCSR000AKS"],
  "related_series": [],
  "documents": [],
  "url": "https://www.encodeproject.org/experiments/ENCSR133RZO/",
  "files": [
    {
      "accession": "ENCFF635JIA",
      "file_format": "bed",
      "file_type": "bed narrowPeak",
      "output_type": "IDR thresholded peaks",
      "output_category": "annotation",
      "file_size": 1258291,
      "file_size_human": "1.2 MB",
      "assembly": "GRCh38",
      "biological_replicates": [1, 2],
      "technical_replicates": ["1_1", "2_1"],
      "status": "released",
      "download_url": "https://www.encodeproject.org/files/ENCFF635JIA/@@download/ENCFF635JIA.bed.gz",
      "s3_uri": "s3://encode-public/2023/05/15/ENCFF635JIA.bed.gz",
      "md5sum": "5d41402abc4b2a76b9719d911017c592",
      "experiment_accession": "ENCSR133RZO",
      "experiment_assay": "Histone ChIP-seq",
      "biosample_summary": "pancreas tissue male adult (54 years)",
      "preferred_default": true,
      "date_created": "2023-05-15T10:23:45.123456+00:00"
    }
  ],
  "audit_error_count": 0,
  "audit_not_compliant_count": 1,
  "audit_warning_count": 3,
  "audit_internal_action_count": 2
}
```

Notes on the shape:

- Controls are under `possible_controls` (a list of accessions), not `controls`.
- Audit levels are the four `audit_*_count` integers; there is no nested `audit` object and no per-file audit information.
- `files` holds complete file records — the same 19 fields `encode_get_file_info` returns.
- An unknown or malformed accession raises a tool error rather than returning an `error` field.

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
| `output_category` | string \| null | null | `"raw data"`, `"alignment"`, `"signal"`, `"annotation"`, `"quantification"`, `"reference"` |
| `assembly` | string \| null | null | `"GRCh38"`, `"hg19"`, `"mm10"` |
| `status` | string \| null | null | `"released"`, `"archived"`, `"in progress"` |
| `preferred_default` | bool \| null | null | `true` returns only recommended files |
| `limit` | int | 200 | Max files to return (clamped to 1-1000) |

#### Returns

A bare JSON array of file records — there is no `results` wrapper, no `total`, and no pagination keys.

```json
[
  {
    "accession": "ENCFF635JIA",
    "file_format": "bed",
    "file_type": "bed narrowPeak",
    "output_type": "IDR thresholded peaks",
    "output_category": "annotation",
    "file_size": 1258291,
    "file_size_human": "1.2 MB",
    "assembly": "GRCh38",
    "biological_replicates": [1, 2],
    "technical_replicates": ["1_1", "2_1"],
    "status": "released",
    "download_url": "https://www.encodeproject.org/files/ENCFF635JIA/@@download/ENCFF635JIA.bed.gz",
    "s3_uri": "s3://encode-public/2023/05/15/ENCFF635JIA.bed.gz",
    "md5sum": "5d41402abc4b2a76b9719d911017c592",
    "experiment_accession": "ENCSR133RZO",
    "experiment_assay": "Histone ChIP-seq",
    "biosample_summary": "pancreas tissue male adult (54 years)",
    "preferred_default": true,
    "date_created": "2023-05-15T10:23:45.123456+00:00"
  }
]
```

`file_size` is in bytes; `file_size_human` is the formatted version (`"1.2 MB"`). The absolute download link is `download_url` (there is no `href` or `path` field).

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
| `limit` | int | 25 | Max results (clamped to 1-1000) |
| `offset` | int | 0 | Pagination offset |

#### Returns

```json
{
  "results": [
    {
      "accession": "ENCFF388RZD",
      "file_format": "bigWig",
      "file_type": "bigWig",
      "output_type": "fold change over control",
      "output_category": "signal",
      "file_size": 419430400,
      "file_size_human": "400.0 MB",
      "assembly": "GRCh38",
      "biological_replicates": [1, 2],
      "technical_replicates": ["1_1", "2_1"],
      "status": "released",
      "download_url": "https://www.encodeproject.org/files/ENCFF388RZD/@@download/ENCFF388RZD.bigWig",
      "s3_uri": "s3://encode-public/2023/05/15/ENCFF388RZD.bigWig",
      "md5sum": "098f6bcd4621d373cade4e832627b4f6",
      "experiment_accession": "ENCSR133RZO",
      "experiment_assay": "Histone ChIP-seq",
      "biosample_summary": "pancreas tissue male adult (54 years)",
      "preferred_default": false,
      "date_created": "2023-05-15T10:25:11.987654+00:00"
    }
  ],
  "total": 142,
  "limit": 25,
  "offset": 0,
  "has_more": true,
  "next_offset": 25
}
```

Notes on the shape:

- The parent experiment is `experiment_accession` (with `experiment_assay` alongside it); this tool does not emit a `dataset` field.
- Sizes are per file only — nothing here aggregates them. Use `encode_batch_download` with `dry_run=True` for a total.
- `filter_warnings` and `suggestion` behave as in `encode_search_experiments`.
- Setting `organism` switches the search to a two-step walk (experiments first, then their files). On that path `total` counts only the files collected so far, and a `total_note` string is added saying so.

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

```json
{
  "accession": "ENCFF635JIA",
  "file_format": "bed",
  "file_type": "bed narrowPeak",
  "output_type": "IDR thresholded peaks",
  "output_category": "annotation",
  "file_size": 1258291,
  "file_size_human": "1.2 MB",
  "assembly": "GRCh38",
  "biological_replicates": [1, 2],
  "technical_replicates": ["1_1", "2_1"],
  "status": "released",
  "download_url": "https://www.encodeproject.org/files/ENCFF635JIA/@@download/ENCFF635JIA.bed.gz",
  "s3_uri": "s3://encode-public/2023/05/15/ENCFF635JIA.bed.gz",
  "md5sum": "5d41402abc4b2a76b9719d911017c592",
  "experiment_accession": "ENCSR133RZO",
  "experiment_assay": "Histone ChIP-seq",
  "biosample_summary": "pancreas tissue male adult (54 years)",
  "preferred_default": true,
  "date_created": "2023-05-15T10:23:45.123456+00:00"
}
```

These 19 fields are the complete record. Sequencing details such as run type, read length, or paired-end partner are not included, and quality metrics are not returned by this tool — query the ENCODE portal directly if you need them.

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
      "file_size": 1258291,
      "file_size_human": "1.2 MB",
      "success": true,
      "error": "",
      "md5_verified": true
    }
  ],
  "errors": [
    {
      "accession": "ENCFF000XXX",
      "error": "Client error '404 Not Found' for url 'https://www.encodeproject.org/files/ENCFF000XXX/'"
    }
  ],
  "summary": {
    "total_requested": 2,
    "successful": 1,
    "failed": 1,
    "total_size": 1258291,
    "total_size_human": "1.2 MB"
  }
}
```

`errors` holds only accessions whose metadata could not be fetched. A download that fails stays in `downloaded` with `"success": false` and a non-empty `error`. `summary.failed` counts both.

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
| `limit` | int | 100 | Max files (safety cap, clamped to 1-1000) |
| `dry_run` | bool | `true` | **Preview only.** Set `false` to download. |
| `offset` | int | 0 | Skip the first N matching files. Pass the previous reply's `next_offset` to continue |

#### Returns (dry_run=true)

```json
{
  "file_count": 100,
  "total_size": 209715200,
  "total_size_human": "200.0 MB",
  "files": [
    {
      "accession": "ENCFF635JIA",
      "file_format": "bed",
      "output_type": "IDR thresholded peaks",
      "file_size": 1258291,
      "file_size_human": "1.2 MB",
      "target_path": "/data/encode/ENCSR133RZO/ENCFF635JIA.bed.gz",
      "already_exists": false
    }
  ],
  "message": "Found 100 files (200.0 MB). Set dry_run=False to download.",
  "search_total": 142,
  "has_more": true,
  "next_offset": 100,
  "total_note": "Lower bound: files collected so far from matching experiments, not the full count"
}
```

Each entry in `files` is an object with those seven keys — `target_path` is where the file would land and `already_exists` says whether it is there already. `search_total` is how many files the underlying walk collected, a lower bound rather than a portal match count; `file_count` is how many of them this call would download (at most `limit`).

#### Returns (dry_run=false)

```json
{
  "downloaded": [
    {
      "accession": "ENCFF635JIA",
      "file_path": "/data/encode/ENCSR133RZO/ENCFF635JIA.bed.gz",
      "file_size": 1258291,
      "file_size_human": "1.2 MB",
      "success": true,
      "error": "",
      "md5_verified": true
    }
  ],
  "summary": {
    "total_found": 142,
    "total_downloaded": 100,
    "successful": 100,
    "failed": 0,
    "total_size": 209715200,
    "total_size_human": "200.0 MB"
  },
  "has_more": true,
  "next_offset": 100,
  "total_note": "Lower bound: files collected so far from matching experiments, not the full count"
}
```

The summary differs from `encode_download_files`: it reports `total_found` (the same lower bound as `search_total`) and `total_downloaded`, and there is no separate `errors` list — a failed download appears in `downloaded` with `"success": false`.

#### Returns (no matches)

```json
{
  "message": "No files found matching the search criteria.",
  "total": 0,
  "has_more": false,
  "next_offset": null,
  "suggestion": "Try broadening your search filters. Use encode_get_facets to see what data is available for your criteria.",
  "total_note": "Lower bound: files collected so far from matching experiments, not the full count"
}
```

`total_note` is present in all three shapes: `organism` always has a value here (it defaults to `"Homo sapiens"` and cannot be null), so the file search always takes its two-step walk over matching experiments. All three shapes also gain `filter_warnings` when a filter value is not a known ENCODE value. When `has_more` is true, call the tool again with `offset` set to `next_offset` to reach the rest.

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
    "action": "tracked"
  },
  "auto_linked_references": [
    {"type": "geo_accession", "id": "GSE123456"}
  ],
  "publications_found": 1,
  "publications": [
    {
      "pmid": "32728249",
      "doi": "10.1038/s41586-020-2493-4",
      "title": "An atlas of gene regulatory elements in adult mouse cerebrum",
      "authors": "Li YE, Preissl S, Hou X",
      "journal": "Nature",
      "year": "2020",
      "abstract": ""
    }
  ],
  "pipelines_found": 1,
  "pipelines": [
    {
      "title": "Histone ChIP-seq 2 (unreplicated)",
      "version": "1.7.1",
      "software": [
        {"name": "bowtie2", "version": "2.3.4.3"}
      ],
      "status": "released"
    }
  ]
}
```

Notes on the shape:

- `tracking.action` is `"tracked"` for a new row or `"updated"` when the experiment was already in the library.
- `auto_linked_references` appears only when a `GEO:` or `PMID:` cross-reference was newly linked from the experiment's `dbxrefs`.
- `publications_found` / `publications` are present only with `fetch_publications=true`, `pipelines_found` / `pipelines` only with `fetch_pipelines=true`.
- `notes` is stored but not echoed back; read it with `encode_list_tracked`.

#### Storage

Data is stored in a local SQLite database at `~/.encode_connector/tracker.db`. The database uses WAL mode for concurrent read access and includes tables for experiments, publications, pipeline info, quality metrics, derived files, and external references.

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
      "biosample_summary": "pancreas tissue male adult (54 years)",
      "organism": "Homo sapiens",
      "organ": "pancreas",
      "biosample_type": "tissue",
      "status": "released",
      "date_released": "2023-05-15",
      "description": "H3K27me3 ChIP-seq on human pancreas",
      "lab": "Bing Ren, UCSD",
      "award": "ENCODE",
      "assembly": "GRCh38",
      "replication_type": "isogenic",
      "life_stage": "adult",
      "url": "https://www.encodeproject.org/experiments/ENCSR133RZO/",
      "tracked_at": 1739452800.123456,
      "updated_at": 1739452800.123456,
      "notes": "Pancreas H3K27me3 for enhancer analysis",
      "publication_count": 1,
      "derived_file_count": 2
    }
  ],
  "count": 3,
  "stats": {
    "tracked_experiments": 3,
    "publications": 6,
    "pipeline_records": 3,
    "quality_metrics": 0,
    "derived_files": 2,
    "external_references": 4,
    "db_path": "/Users/you/.encode_connector/tracker.db"
  }
}
```

Notes on the shape:

- `tracked_at` and `updated_at` are epoch seconds (floats), not ISO strings.
- `assembly` is the stored text for the experiment; when its files span several assemblies the names are joined into one comma-separated string.
- `count` is the number of rows returned; `stats.tracked_experiments` counts the whole database.
- The raw ENCODE metadata kept in the database is stripped from this output.

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
  "experiment_1": {
    "accession": "ENCSR133RZO",
    "assay": "Histone ChIP-seq",
    "biosample": "pancreas tissue male adult (54 years)"
  },
  "experiment_2": {
    "accession": "ENCSR000AKS",
    "assay": "Histone ChIP-seq",
    "biosample": "liver tissue female adult (53 years)"
  },
  "verdict": "COMPATIBLE_WITH_CAVEATS",
  "recommendation": "These experiments can be compared, but the warnings should be addressed in your analysis.",
  "compatible_aspects": [
    "Same organism: Homo sapiens",
    "Same assembly: GRCh38",
    "Same assay: Histone ChIP-seq"
  ],
  "issues": [],
  "warnings": [
    "Different organs/tissues: pancreas vs liver.",
    "Different targets: H3K27me3 vs H3K4me3."
  ]
}
```

`compatible_aspects`, `issues`, and `warnings` are plain prose strings, not field maps. If either accession is not tracked, the whole response is `{"error": "Experiment ENCSR000AKS not tracked. Track it first."}`.

#### Verdicts

| Verdict | Meaning |
|---------|---------|
| `"FULLY_COMPATIBLE"` | No issues and no warnings |
| `"COMPATIBLE_WITH_CAVEATS"` | Combinable but review the warnings |
| `"NOT_COMPATIBLE"` | A blocking issue: different organisms, or no shared genome assembly |

---

### `encode_summarize_collection`

Summarize your tracked collection with counts grouped by assay, target, organism, organ, biosample type, and lab.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `assay_title` | string \| null | null | Filter by assay type (partial match) |
| `organism` | string \| null | null | Filter by organism (partial match) |
| `organ` | string \| null | null | Filter by organ (partial match) |

#### Returns

```json
{
  "total_experiments": 3,
  "total_publications": 2,
  "total_derived_files": 4,
  "total_external_references": 5,
  "by_assay": {"Histone ChIP-seq": 2, "ATAC-seq": 1},
  "by_target": {"H3K27me3": 2, "none": 1},
  "by_organism": {"Homo sapiens": 3},
  "by_organ": {"pancreas": 2, "liver": 1},
  "by_biosample_type": {"tissue": 3},
  "by_lab": {"Bing Ren, UCSD": 3}
}
```

The keys inside each `by_*` object are values observed in your own tracked rows, sorted by count. Missing values are bucketed as `"unknown"` (as `"none"` for `by_target`), and `by_target`, `by_organ`, and `by_lab` are truncated to their top 20 entries. When nothing matches the filters the response is just `{"total_experiments": 0, "message": "No tracked experiments found matching filters."}`.

---

### `encode_export_data`

Export tracked experiments as a table for Excel, R, or pandas.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `format` | string | `"csv"` | `"csv"`, `"tsv"`, or `"json"` |
| `assay_title` | string \| null | null | Filter by assay type (partial match) |
| `organism` | string \| null | null | Filter by organism (partial match) |
| `organ` | string \| null | null | Filter by organ (partial match) |

#### Returns (json)

A bare JSON array of rows — the `encode_list_tracked` row fields plus `pmids` and `external_reference_count`.

```json
[
  {
    "accession": "ENCSR133RZO",
    "assay_title": "Histone ChIP-seq",
    "target": "H3K27me3",
    "biosample_summary": "pancreas tissue male adult (54 years)",
    "organism": "Homo sapiens",
    "organ": "pancreas",
    "biosample_type": "tissue",
    "status": "released",
    "date_released": "2023-05-15",
    "description": "H3K27me3 ChIP-seq on human pancreas",
    "lab": "Bing Ren, UCSD",
    "award": "ENCODE",
    "assembly": "GRCh38",
    "replication_type": "isogenic",
    "life_stage": "adult",
    "url": "https://www.encodeproject.org/experiments/ENCSR133RZO/",
    "tracked_at": 1739452800.123456,
    "updated_at": 1739452800.123456,
    "notes": "Pancreas H3K27me3 for enhancer analysis",
    "publication_count": 1,
    "derived_file_count": 2,
    "pmids": "32728249",
    "external_reference_count": 3
  }
]
```

#### Returns (csv / tsv)

Raw delimited text, not JSON, with these 17 columns in this order:

```
accession, assay_title, target, organism, organ, biosample_type,
biosample_summary, lab, assembly, status, date_released,
replication_type, life_stage, publication_count, pmids,
derived_file_count, external_reference_count
```

The JSON rows are wider: they also carry `description`, `award`, `url`, `tracked_at`, `updated_at`, and `notes`. Values containing the separator or a quote are double-quoted with `""` escaping.

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
      "id": 1,
      "experiment_accession": "ENCSR133RZO",
      "pmid": "32728249",
      "doi": "10.1038/s41586-020-2493-4",
      "title": "An atlas of gene regulatory elements in adult mouse cerebrum",
      "authors": "Li YE, Preissl S, Hou X",
      "journal": "Nature",
      "year": "2020",
      "abstract": ""
    }
  ],
  "count": 2
}
```

These are stored database rows, so they carry `id` and `experiment_accession` in addition to the seven fields `encode_track_experiment` reports.

#### Returns (bibtex)

Raw BibTeX text (or the plain string `No publications found.`). The citation key is the PMID, falling back to the DOI or the experiment accession, with `.` and `/` replaced by `_`:

```bibtex
@article{32728249,
  title = {An atlas of gene regulatory elements in adult mouse cerebrum},
  author = {Li YE and Preissl S and Hou X},
  journal = {Nature},
  year = {2020},
  doi = {10.1038/s41586-020-2493-4},
  pmid = {32728249},
  note = {ENCODE experiment: ENCSR133RZO},
}
```

#### Returns (ris)

Raw RIS text (or `No publications found.`), one `AU` line per author:

```
TY  - JOUR
TI  - An atlas of gene regulatory elements in adult mouse cerebrum
AU  - Li YE
AU  - Preissl S
AU  - Hou X
JO  - Nature
PY  - 2020
DO  - 10.1038/s41586-020-2493-4
AN  - PMID:32728249
N1  - ENCODE experiment: ENCSR133RZO
ER  -
```

Neither export format is JSON — do not try to parse them.

---

### `encode_link_reference`

Link an external identifier (PubMed, bioRxiv, ClinicalTrials.gov, GEO) to a tracked experiment.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `experiment_accession` | string | *required* | Tracked experiment accession |
| `reference_type` | string | *required* | `"pmid"`, `"doi"`, `"nct_id"`, `"preprint_doi"`, `"geo_accession"`, or `"other"` |
| `reference_id` | string | *required* | The identifier value |
| `description` | string | `""` | Why this reference is linked |

#### Returns

```json
{
  "action": "linked",
  "experiment_accession": "ENCSR133RZO",
  "reference_type": "pmid",
  "reference_id": "32728249"
}
```

`action` is `"linked"` for a new link or `"already_linked"` when the same triple exists. `description` is stored but not echoed. If the experiment is not tracked the response is `{"error": "Experiment ENCSR133RZO not tracked. Track it first."}`.

---

### `encode_get_references`

Get external references linked to tracked experiments, ready to hand to PubMed, bioRxiv, or ClinicalTrials.gov tools.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `experiment_accession` | string \| null | null | Filter by experiment |
| `reference_type` | string \| null | null | Filter by type: `"pmid"`, `"doi"`, `"nct_id"`, `"preprint_doi"`, `"geo_accession"`, `"other"` |

#### Returns

```json
{
  "references": [
    {
      "id": 3,
      "experiment_accession": "ENCSR133RZO",
      "reference_type": "geo_accession",
      "reference_id": "GSE123456",
      "description": "Auto-extracted from ENCODE dbxrefs",
      "linked_at": 1739452800.223456
    }
  ],
  "count": 1
}
```

References are ordered newest first; `linked_at` is epoch seconds.

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

`description`, `file_type`, `tool_used`, and `parameters` are stored but not echoed here — read them back with `encode_get_provenance`.

---

### `encode_get_provenance`

View provenance chains from derived files back to original ENCODE source data.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `file_path` | string \| null | null | Get provenance for a specific derived file |
| `source_accession` | string \| null | null | List all files derived from a specific accession |

Provide one or the other. If `file_path` is null, the tool lists derived files; if `source_accession` is null too, it lists all of them.

#### Returns (file_path)

A single record with its resolved sources:

```json
{
  "id": 1,
  "file_path": "~/analysis/filtered_peaks.bed",
  "source_accessions": ["ENCSR133RZO", "ENCFF635JIA"],
  "description": "H3K27me3 peaks filtered to promoter regions",
  "created_at": 1739452900.654321,
  "file_type": "filtered_peaks",
  "tool_used": "bedtools intersect",
  "parameters": "bedtools intersect -a ENCFF635JIA.bed -b promoters.bed -u",
  "notes": "",
  "source_experiments": [
    {
      "accession": "ENCSR133RZO",
      "assay_title": "Histone ChIP-seq",
      "biosample_summary": "pancreas tissue male adult (54 years)",
      "organism": "Homo sapiens"
    },
    {
      "accession": "ENCFF635JIA",
      "tracked": false
    }
  ]
}
```

A source that is not in your tracker appears as `{"accession": ..., "tracked": false}`. If no record exists for the path, the response is `{"error": "No provenance record for ~/analysis/filtered_peaks.bed"}`.

#### Returns (source_accession)

```json
{
  "derived_files": [
    {
      "id": 1,
      "file_path": "~/analysis/filtered_peaks.bed",
      "source_accessions": ["ENCSR133RZO", "ENCFF635JIA"],
      "description": "H3K27me3 peaks filtered to promoter regions",
      "created_at": 1739452900.654321,
      "file_type": "filtered_peaks",
      "tool_used": "bedtools intersect",
      "parameters": "bedtools intersect -a ENCFF635JIA.bed -b promoters.bed -u",
      "notes": ""
    }
  ],
  "count": 1
}
```

`created_at` is epoch seconds, and the list entries carry no `source_experiments` — ask for a single `file_path` to resolve those.

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
  "message": "No credentials configured. You can still access all public ENCODE data. Use action='store' with your ENCODE access key pair to access restricted data."
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

Calling `"store"` without both keys returns `{"error": ..., "help": ...}` instead.

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

The most commonly used assay types (`encode_get_metadata("assays")` returns all 79):

| Category | Assay Titles |
|----------|-------------|
| **Histone/Chromatin** | `"Histone ChIP-seq"`, `"TF ChIP-seq"`, `"ATAC-seq"`, `"DNase-seq"`, `"CUT&RUN"`, `"CUT&Tag"`, `"MNase-seq"` |
| **Transcription** | `"total RNA-seq"`, `"polyA plus RNA-seq"`, `"small RNA-seq"`, `"long read RNA-seq"`, `"CAGE"`, `"RAMPAGE"`, `"PRO-seq"`, `"GRO-seq"` |
| **3D Genome** | `"Hi-C"`, `"intact Hi-C"`, `"Micro-C"`, `"ChIA-PET"`, `"HiChIP"`, `"PLAC-seq"`, `"5C"` |
| **DNA Methylation** | `"WGBS"`, `"RRBS"`, `"MeDIP-seq"`, `"MRE-seq"` |
| **Functional** | `"STARR-seq"`, `"MPRA"`, `"CRISPR screen"`, `"eCLIP"`, `"iCLIP"` |
| **Single Cell** | `"scRNA-seq"`, `"snATAC-seq"`, `"snRNA-seq"`, `"long read scRNA-seq"` |
| **Perturbation** | `"CRISPRi RNA-seq"`, `"shRNA RNA-seq"`, `"siRNA RNA-seq"`, `"CRISPR RNA-seq"` |

`"RNA-seq"` on its own is not an ENCODE assay title — use `"total RNA-seq"` or `"polyA plus RNA-seq"`.

### Organs

```
adipose tissue, adrenal gland, arterial blood vessel, blood, blood vessel,
bodily fluid, bone element, bone marrow, brain, breast, bronchus, colon,
connective tissue, ear, embryo, endocrine gland, epithelium, esophagus,
exocrine gland, extraembryonic component, eye, gallbladder, gonad,
hair follicle, heart, immune organ, intestine, kidney, large intestine,
limb, liver, lung, lymph node, lymphatic vessel, lymphoid tissue,
major salivary gland, mammary gland, mouth, musculature of body, nerve,
nose, ovary, pancreas, pericardium, penis, placenta, prostate gland,
skeleton, skin of body, skin of prepuce of penis, small intestine,
spinal cord, spleen, stomach, testis, thymus, thyroid gland, tongue,
tonsil, trachea, ureter, urinary bladder, uterus, vagina, vasculature, vein
```

### File Formats

```
fastq, bam, bed, bigWig, bigBed, tsv, csv, tar, hic, tagAlign, bedpe,
pairs, fasta, gff, gtf, idat, CEL, rcc, sra, csfasta, csqual, 2bit,
database, vcf, bigInteract, idx, txt, h5ad, hdf5, sam, wig, starch,
chain, PWM, btr, cndb, nucle3d, yaml
```

### Output Types

The most commonly used output types (`encode_get_metadata("output_types")` returns all 88):

| Category | Output Types |
|----------|-------------|
| **Raw** | `"reads"`, `"index reads"`, `"filtered reads"` |
| **Alignment** | `"alignments"`, `"unfiltered alignments"`, `"transcriptome alignments"` |
| **Signal** | `"signal of unique reads"`, `"signal of all reads"`, `"signal p-value"`, `"fold change over control"` |
| **Peaks** | `"peaks"`, `"IDR thresholded peaks"`, `"pseudoreplicated peaks"`, `"replicated peaks"`, `"conservative IDR thresholded peaks"`, `"optimal IDR thresholded peaks"`, `"candidate Cis-Regulatory Elements"` |
| **Quantification** | `"gene quantifications"`, `"transcript quantifications"`, `"exon quantifications"` |
| **3D Genome** | `"contact matrix"`, `"mapping quality thresholded contact matrix"`, `"contact domains"`, `"loops"`, `"genome compartments"` |
| **Methylation** | `"methylation state at CpG"`, `"methylation state at CHG"`, `"methylation state at CHH"` |

Chromatin loops are `"loops"` and TADs are `"contact domains"` — ENCODE has no `"chromatin interactions"` or `"topologically associated domains"` output type.

### Genome Assemblies

| Assembly | Organism |
|----------|----------|
| `GRCh38` | Human (current) |
| `hg19` | Human (legacy) |
| `T2T-CHM13` | Human (telomere-to-telomere) |
| `mm10` | Mouse (current) |
| `mm9` | Mouse (legacy) |
| `GRCm39` | Mouse (newest) |
| `dm6` | Fly |
| `ce11` | Worm |

`encode_get_metadata("assemblies")` returns all 17, including the legacy `dm3` and `ce10` builds and the `-minimal` variants.

---

## Rate Limits & Performance

- ENCODE API rate limit: **10 requests per second** (automatically handled)
- Download concurrency: **3 parallel downloads**
- Search results: capped at **1000** per query (use pagination for larger sets)
- Download timeout: **5 minutes** per file
- Metadata and facet responses are cached for **1 hour**
- All downloads verified with **MD5 checksums** by default

## Local Storage

| Path | Contents |
|------|----------|
| `~/.encode_connector/tracker.db` | SQLite database with tracked experiments, publications, pipelines, provenance |
| `~/.encode_connector/credentials.enc` | Fernet-encrypted credentials, used only when no OS keyring is available |
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
