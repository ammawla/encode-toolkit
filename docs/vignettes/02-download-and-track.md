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

The tool returns a JSON array of file records. Each record carries 19 fields; the ones
that drive file choice are shown here:

```json
[
  {"accession": "ENCFF635JIA", "file_format": "bed",    "output_type": "pseudoreplicated peaks",   "file_size": 40482,      "file_size_human": "39.5 KB",  "assembly": "GRCh38", "preferred_default": true},
  {"accession": "ENCFF199LSM", "file_format": "bigBed", "output_type": "pseudoreplicated peaks",   "file_size": 183334,     "file_size_human": "179.0 KB", "assembly": "GRCh38", "preferred_default": true},
  {"accession": "ENCFF387ALH", "file_format": "bigWig", "output_type": "signal p-value",           "file_size": 1239311158, "file_size_human": "1.2 GB",   "assembly": "GRCh38", "preferred_default": true},
  {"accession": "ENCFF186PZN", "file_format": "bigWig", "output_type": "fold change over control", "file_size": 1325853979, "file_size_human": "1.2 GB",   "assembly": "GRCh38", "preferred_default": false},
  {"accession": "ENCFF977UZL", "file_format": "bam",    "output_type": "alignments",               "file_size": 3546672634, "file_size_human": "3.3 GB",   "assembly": "GRCh38", "preferred_default": false},
  {"accession": "ENCFF763GUV", "file_format": "bam",    "output_type": "unfiltered alignments",    "file_size": 4221319561, "file_size_human": "3.9 GB",   "assembly": "GRCh38", "preferred_default": false}
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
{
  "downloaded": [
    {
      "accession": "ENCFF635JIA",
      "file_path": "/data/encode/ENCFF635JIA.bed.gz",
      "file_size": 40482,
      "file_size_human": "39.5 KB",
      "success": true,
      "error": "",
      "md5_verified": true
    }
  ],
  "errors": [],
  "summary": {
    "total_requested": 1,
    "successful": 1,
    "failed": 0,
    "total_size": 40482,
    "total_size_human": "39.5 KB"
  }
}
```

**Interpretation:** The file downloaded and its MD5 checksum matches the ENCODE registry,
confirming data integrity (`md5_verified: true`). Files land directly in `download_dir`
because `organize_by` defaults to `"flat"`; pass `"experiment"` to get one subdirectory per
experiment. For batch downloads, use `encode_batch_download` with search filters -- Claude
previews the download list before proceeding.

## Step 3: Track the Experiment

Tracking stores metadata, publications, and pipeline information in a local SQLite database.

**You ask Claude:** "Track experiment ENCSR133RZO in my local library"

**Claude calls:** `encode_track_experiment(accession="ENCSR133RZO")`

```json
{
  "tracking": {
    "accession": "ENCSR133RZO",
    "action": "tracked"
  },
  "auto_linked_references": [
    {"type": "geo_accession", "id": "GSE187091"}
  ],
  "publications_found": 0,
  "publications": [],
  "pipelines_found": 1,
  "pipelines": [
    {
      "title": "Histone ChIP-seq 2 (unreplicated)",
      "version": "1.7.1",
      "software": [{"name": "bowtie2", "version": "2.3.4.3"}],
      "status": "released"
    }
  ]
}
```

**Interpretation:** The experiment is now in your local library -- `tracking.action` is
`"tracked"` on first insert and `"updated"` when you track it again. The GEO cross-reference
in the ENCODE record was linked automatically. Zero publications were found -- common for
tissue samples from large-scale mapping efforts. The pipeline record captures the ENCODE
ChIP-seq processing pipeline version used. The stored metadata is not echoed back here; read
it with `encode_list_tracked`.

## Step 4: Get Citations

**You ask Claude:** "Get BibTeX citations for my tracked experiments"

**Claude calls:** `encode_get_citations(export_format="bibtex")`

```text
No publications found.
```

**Interpretation:** ENCSR133RZO has no experiment-specific publication, and the citation
export only covers publications stored by `encode_track_experiment` -- so there is nothing
to export yet. Cite the Consortium's own reference paper yourself in that case. Once you
track an experiment whose ENCODE record does cite a paper, the same call returns one entry
per publication:

```bibtex
@article{22955616,
  title = {An integrated encyclopedia of DNA elements in the human genome},
  author = {The ENCODE Project Consortium},
  journal = {Nature},
  year = {2012},
  doi = {10.1038/nature11247},
  pmid = {22955616},
  note = {ENCODE experiment: ENCSR000AKS},
}
```

The entry key is the PMID when there is one, otherwise the DOI. Only the fields the
publication record holds are emitted -- there is no `volume` or `pages`. RIS format
(Endnote, Zotero, Mendeley) is also available with `export_format="ris"`.

## Step 5: Log a Derived File

After analysis, log derived files to maintain a provenance chain back to ENCODE source data.

**You ask Claude:** "I filtered the peaks to remove blacklist regions -- log this derived file"

**Claude calls:**
```python
encode_log_derived_file(
    file_path="/data/encode/ENCSR133RZO_H3K27me3_filtered.bed",
    source_accessions=["ENCSR133RZO", "ENCFF635JIA"],
    description="Blacklist-filtered H3K27me3 peaks from pancreas tissue",
    tool_used="bedtools subtract",
    parameters="bedtools subtract -a ENCFF635JIA.bed.gz -b hg38-blacklist.v2.bed"
)
```

```json
{
  "success": true,
  "record_id": 1,
  "file_path": "/data/encode/ENCSR133RZO_H3K27me3_filtered.bed",
  "source_accessions": ["ENCSR133RZO", "ENCFF635JIA"],
  "message": "Provenance logged. Use encode_get_provenance to view the full chain."
}
```

**Interpretation:** The provenance record links your filtered file back to ENCFF635JIA with
the exact tool and parameters. List the experiment accession among the sources as well: the
library counts a derived file against an experiment by looking for its accession in
`source_accessions`, so naming ENCSR133RZO is what makes it show up in that experiment's
`derived_file_count`. The response echoes only the identifying fields; the tool, parameters
and timestamp are stored and come back from `encode_get_provenance`. You or a reviewer can
trace any result to its ENCODE source.

## Step 6: Export Your Library

**You ask Claude:** "Export my tracked experiments as CSV"

**Claude calls:** `encode_export_data(format="csv")`

```csv
accession,assay_title,target,organism,organ,biosample_type,biosample_summary,lab,assembly,status,date_released,replication_type,life_stage,publication_count,pmids,derived_file_count,external_reference_count
ENCSR133RZO,Histone ChIP-seq,H3K27me3,Homo sapiens,pancreas,tissue,"Homo sapiens pancreas tissue female child (16 years)","Bradley Bernstein, Broad",GRCh38,released,2021-06-24,unreplicated,child 16 years,0,,1,1
ENCSR511LIV,Histone ChIP-seq,H3K27me3,Homo sapiens,pancreas,tissue,"Homo sapiens pancreas tissue female adult (61 years)","Bradley Bernstein, Broad",GRCh38,released,2021-06-24,unreplicated,adult 61 years,0,,0,1
ENCSR368EPJ,Histone ChIP-seq,H3K9me3,Homo sapiens,pancreas,tissue,"Homo sapiens pancreas tissue female adult (59 years)","Bradley Bernstein, Broad",GRCh38,released,2021-06-24,unreplicated,adult 59 years,0,,0,1
```

**Interpretation:** Each row is one tracked experiment, with the same 17 columns every
time. The `derived_file_count` column tracks analysis progress -- ENCSR133RZO shows one
derived file logged, while the others await processing. `pmids` is a semicolon-joined list
and is empty here because none of these experiments cites a paper. TSV and JSON are also
available; the JSON rows are wider, adding `description`, `award`, `url`, `tracked_at`,
`updated_at` and `notes`.

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
