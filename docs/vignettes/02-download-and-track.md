# Downloading Data and Building Your Research Library

> This vignette demonstrates downloading ENCODE files, tracking experiments locally,
> managing citations, and maintaining data provenance -- all through natural conversation with Claude.

**Prerequisites:** You have the ENCODE MCP plugin installed and have identified an experiment
of interest. If you need help finding experiments, see [Searching ENCODE Data](01-search-and-explore.md).

**Skills demonstrated:** `download-encode`, `track-experiments`, `cite-encode`, `data-provenance`

---

## Scenario

You have identified experiment **ENCSR133RZO** -- H3K27me3 ChIP-seq on human pancreas tissue
(female, 16 years), from the Bernstein lab at the Broad Institute. You now want to download
its processed data, add it to your local research library, and prepare citations.

## Step 1: List Available Files

**You ask Claude:** "What files are available for experiment ENCSR133RZO?"

**Claude calls:** `encode_list_files(experiment_accession="ENCSR133RZO")`

```json
[
  {"accession": "ENCFF635JIA", "format": "bed",    "output_type": "pseudoreplicated peaks",  "size": "39.5 KB",  "preferred_default": true},
  {"accession": "ENCFF199LSM", "format": "bigBed", "output_type": "pseudoreplicated peaks",  "size": "179.0 KB", "preferred_default": true},
  {"accession": "ENCFF387ALH", "format": "bigWig", "output_type": "signal p-value",          "size": "1.2 GB",   "preferred_default": true},
  {"accession": "ENCFF186PZN", "format": "bigWig", "output_type": "fold change over control", "size": "1.2 GB",   "preferred_default": false},
  {"accession": "ENCFF977UZL", "format": "bam",    "output_type": "alignments",              "size": "3.3 GB",   "preferred_default": false},
  {"accession": "ENCFF763GUV", "format": "bam",    "output_type": "unfiltered alignments",   "size": "3.9 GB",   "preferred_default": false}
]
```

*Plus 7 FASTQ files (~500 MB each). All processed files are GRCh38.*

**Interpretation:** Three files are flagged `preferred_default: true` -- the ENCODE pipeline's
recommended outputs. For most analyses, start with **ENCFF635JIA** (BED peaks for overlap
and enrichment) and **ENCFF186PZN** (fold-change bigWig for heatmaps and signal quantification).
BAM and FASTQ files are only needed if you plan to re-align or re-call peaks.

## Step 2: Download Peak Files

**You ask Claude:** "Download the preferred default BED file to /data/encode"

**Claude calls:** `encode_download_files(file_accessions=["ENCFF635JIA"], download_dir="/data/encode")`

```json
{"file": "ENCFF635JIA.bed.gz", "size": 40482, "path": "/data/encode/ENCFF635JIA.bed.gz", "md5_verified": true}
```

**Interpretation:** The file downloaded and its MD5 checksum matches the ENCODE registry,
confirming data integrity. For batch downloads, use `encode_batch_download` with search
filters -- Claude previews the download list before proceeding.

## Step 3: Track the Experiment

Tracking stores metadata, publications, and pipeline information in a local SQLite database.

**You ask Claude:** "Track experiment ENCSR133RZO in my local library"

**Claude calls:** `encode_track_experiment(accession="ENCSR133RZO")`

```json
{
  "status": "tracked",
  "accession": "ENCSR133RZO",
  "metadata_stored": {"assay_title": "Histone ChIP-seq", "target": "H3K27me3",
    "biosample_summary": "Homo sapiens pancreas tissue female child (16 years)",
    "lab": "Bradley Bernstein, Broad", "date_released": "2021-06-24"},
  "publications_found": 0,
  "pipelines_found": 1
}
```

**Interpretation:** The experiment is now in your local library. Zero publications were
found -- common for tissue samples from large-scale mapping efforts. The pipeline record
captures the ENCODE ChIP-seq processing pipeline version used.

## Step 4: Get Citations

**You ask Claude:** "Get BibTeX citations for my tracked experiments"

**Claude calls:** `encode_get_citations(export_format="bibtex")`

```bibtex
@article{ENCODE_Consortium_2012,
  title   = {An integrated encyclopedia of {DNA} elements in the human genome},
  author  = {{The ENCODE Project Consortium}},
  journal = {Nature},
  volume  = {489},
  pages   = {57--74},
  year    = {2012},
  doi     = {10.1038/nature11247},
  note    = {Primary ENCODE reference for experiment ENCSR133RZO}
}
```

**Interpretation:** Since ENCSR133RZO has no experiment-specific publications, the tool returns
the primary Consortium reference. For experiments with linked publications, those specific
citations appear instead. RIS format (Endnote, Zotero, Mendeley) is also available.

## Step 5: Log a Derived File

After analysis, log derived files to maintain a provenance chain back to ENCODE source data.

**You ask Claude:** "I filtered the peaks to remove blacklist regions -- log this derived file"

**Claude calls:**
```python
encode_log_derived_file(
    file_path="/data/encode/ENCSR133RZO_H3K27me3_filtered.bed",
    source_accessions=["ENCFF635JIA"],
    description="Blacklist-filtered H3K27me3 peaks from pancreas tissue",
    tool_used="bedtools subtract",
    parameters="bedtools subtract -a ENCFF635JIA.bed.gz -b hg38-blacklist.v2.bed"
)
```

```json
{
  "status": "logged",
  "provenance_id": "prov_001",
  "file_path": "/data/encode/ENCSR133RZO_H3K27me3_filtered.bed",
  "source_accessions": ["ENCFF635JIA"],
  "tool_used": "bedtools subtract",
  "logged_at": "2026-03-07T14:32:00Z"
}
```

**Interpretation:** The provenance record links your filtered file back to ENCFF635JIA with
the exact tool and parameters. You or a reviewer can trace any result to its ENCODE source.

## Step 6: Export Your Library

**You ask Claude:** "Export my tracked experiments as CSV"

**Claude calls:** `encode_export_data(format="csv")`

```csv
accession,assay_title,target,biosample_summary,lab,date_released,publications,derived_files
ENCSR133RZO,Histone ChIP-seq,H3K27me3,"pancreas tissue female child (16 years)","Bradley Bernstein, Broad",2021-06-24,0,1
ENCSR511LIV,Histone ChIP-seq,H3K27me3,"pancreas tissue female adult (61 years)","Bradley Bernstein, Broad",2021-06-24,0,0
ENCSR368EPJ,Histone ChIP-seq,H3K9me3,"pancreas tissue female adult (59 years)","Bradley Bernstein, Broad",2021-06-24,0,0
```

**Interpretation:** Each row is one tracked experiment. The `derived_files` column tracks
analysis progress -- ENCSR133RZO shows one derived file logged, while the others await
processing. TSV and JSON formats are also available.

---

## Summary of Tools Used

| Step | Tool | Purpose |
|------|------|---------|
| List files | `encode_list_files` | See all files for an experiment with sizes and formats |
| Download | `encode_download_files` | Download specific files with MD5 verification |
| Track | `encode_track_experiment` | Store experiment metadata and publications locally |
| Cite | `encode_get_citations` | Export BibTeX or RIS citations for manuscripts |
| Provenance | `encode_log_derived_file` | Record derived file lineage back to ENCODE sources |
| Export | `encode_export_data` | Export your library as CSV, TSV, or JSON |

## Best Practices

- **Start with `preferred_default` files** unless you have a specific reason to use
  alternative outputs. These represent the ENCODE pipeline's best-quality processed data.
- **Track before you analyze.** Adding experiments to your library first ensures a complete
  record of data sources.
- **Log every derived file.** It costs seconds now and saves hours of forensic reconstruction
  later. Always include the full command or parameters used.
- **Always filter against the blacklist.** Remove artifact regions with `hg38-blacklist.v2.bed`
  (Amemiya et al., 2019) before any downstream analysis.

## What's Next

- [Epigenomics Workflow](03-epigenomics-workflow.md) -- combine multiple histone marks, ATAC-seq,
  and RNA-seq from pancreas to build a regulatory landscape.
