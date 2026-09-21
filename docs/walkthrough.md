# ENCODE MCP Walkthrough

*Author: Dr. Alex M. Mawla, PhD*

A hands-on guide to querying, downloading, and managing ENCODE genomics data using Claude. This walkthrough covers real research scenarios from simple lookups to full analysis workflows.

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Discovering What Data Exists](#2-discovering-what-data-exists)
3. [Searching for Experiments](#3-searching-for-experiments)
4. [Exploring Experiment Details](#4-exploring-experiment-details)
5. [Finding and Inspecting Files](#5-finding-and-inspecting-files)
6. [Downloading Data](#6-downloading-data)
7. [Building a Research Library](#7-building-a-research-library)
8. [Managing Citations](#8-managing-citations)
9. [Comparing Experiments](#9-comparing-experiments)
10. [Tracking Data Provenance](#10-tracking-data-provenance)
11. [Complete Workflows](#11-complete-workflows)
12. [Tips and Best Practices](#12-tips-and-best-practices)

---

## 1. Getting Started

### Installation

Add the ENCODE MCP server to your Claude configuration. No separate install step is needed when using `uvx`:

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "encode": {
      "command": "uvx",
      "args": ["encode-toolkit"]
    }
  }
}
```

**Claude Code (CLI)**:

```bash
claude mcp add encode -- uvx encode-toolkit
```

Restart Claude after adding the config. You should see "ENCODE Project" listed in your available tools.

### Authentication

Most ENCODE data is public. No credentials are needed for the examples in this walkthrough. If you need access to unreleased or restricted datasets, see the [Authentication](#authentication-optional) section at the end.

---

## 2. Discovering What Data Exists

Before searching, it helps to know what's available. ENCODE has thousands of experiments across dozens of assay types, organisms, and tissues. Two tools help you explore the landscape.

### List valid filter values

> **You:** What assay types are available on ENCODE?

Claude calls `encode_get_metadata(metadata_type="assays")`. The reply is
`{"metadata_type": "assays", "values": [...], "count": 79}`; the 79 `values` read:

```
Histone ChIP-seq, TF ChIP-seq, ATAC-seq, DNase-seq, total RNA-seq,
polyA plus RNA-seq, Hi-C, intact Hi-C, Micro-C, CUT&RUN, CUT&Tag,
STARR-seq, MPRA, CRISPR screen, eCLIP, WGBS, RRBS, ...
```

These are ENCODE's own assay titles, so they are exactly what the search filters
accept. Note there is no bare `"RNA-seq"` title -- use `"total RNA-seq"` or
`"polyA plus RNA-seq"`.

You can do this for any filter dimension:

> **You:** What organs have data on ENCODE?

`encode_get_metadata(metadata_type="organs")` returns 66 values:
`blood, brain, liver, lung, heart, kidney, pancreas, intestine, spleen, thymus, ...`

> **You:** What genome assemblies are available?

`encode_get_metadata(metadata_type="assemblies")` returns 17 values:
`GRCh38, hg19, mm10, mm9, GRCm39, dm6, ce11, ...`

### Get live counts with facets

Facets show you how much data exists for a given filter combination. This is the fastest way to scope a project before committing to a search.

> **You:** What histone marks have ChIP-seq data for human pancreas?

Claude calls `encode_get_facets(assay_title="Histone ChIP-seq", organ="pancreas")`.
Each key of the reply is an ENCODE facet field and each value is a list of
`{"term": ..., "count": ...}` objects -- there is no `facets` wrapper:

```
"target.label":
  { "term": "H3K27me3", "count": 12 }
  { "term": "H3K4me3",  "count": 11 }
  { "term": "H3K27ac",  "count": 10 }
  { "term": "H3K4me1",  "count":  9 }
  { "term": "H3K36me3", "count":  8 }
  { "term": "H3K9me3",  "count":  7 }
  ...
```

Which facet fields come back depends on `search_type` and the filters --
`assay_title`, `status`, `target.label`, `biosample_ontology.classification`,
`biosample_ontology.organ_slims`, `lab.title` and `files.file_type` are the usual
ones for experiments.

More facet examples:

> **You:** What assays are available for mouse brain?

> **You:** How many experiments does ENCODE have for each organism?

> **You:** What biosample types are available for liver data?

---

## 3. Searching for Experiments

The main search tool lets you combine 20+ filters to find exactly the experiments you need.

### Basic searches

> **You:** Find all histone ChIP-seq experiments for human pancreas tissue.

Claude calls `encode_search_experiments` with:
- `assay_title="Histone ChIP-seq"`
- `organ="pancreas"`
- `biosample_type="tissue"`

Returns a structured table:

```
Found 66 experiments (showing 25):

Accession     Assay              Target     Biosample         Status
ENCSR133RZO   Histone ChIP-seq   H3K27me3   pancreas tissue   released
ENCSR456ABC   Histone ChIP-seq   H3K4me3    pancreas tissue   released
ENCSR789DEF   Histone ChIP-seq   H3K27ac    pancreas tissue   released
...
```

### Narrowing results with additional filters

> **You:** Find H3K27me3 ChIP-seq on adult human pancreas tissue.

```
assay_title="Histone ChIP-seq"
target="H3K27me3"
organ="pancreas"
biosample_type="tissue"
life_stage="adult"
```

### Searching by cell line

> **You:** Find all RNA-seq experiments on GM12878 cells.

```
assay_title="total RNA-seq"
biosample_term_name="GM12878"
```

### Searching by organism

> **You:** Find ATAC-seq experiments on mouse brain.

```
assay_title="ATAC-seq"
organism="Mus musculus"
organ="brain"
```

### Free-text search

When you're not sure which filters to use, free-text search works across all fields:

> **You:** Search ENCODE for CRISPR screen experiments in pancreatic cells.

```
search_term="CRISPR screen pancreatic"
```

### Date-filtered search

> **You:** Find experiments released in the last year.

```
date_released_from="2025-01-01"
date_released_to="2026-03-06"
```

### Pagination

Large result sets return 25 results by default. Ask for more or paginate:

> **You:** Show me all 66 pancreas ChIP-seq experiments, not just the first 25.

```
limit=100
```

> **You:** Show me results 26 through 50.

```
offset=25, limit=25
```

---

## 4. Exploring Experiment Details

Once you find an experiment of interest, get its full details.

> **You:** Show me the full details for experiment ENCSR133RZO.

Claude calls `encode_get_experiment` with `accession="ENCSR133RZO"` and returns:

```
Experiment: ENCSR133RZO
  Assay:       Histone ChIP-seq
  Target:      H3K27me3
  Organism:    Homo sapiens
  Biosample:   pancreas, tissue, adult
  Assembly:    GRCh38
  Status:      released
  Lab:         Bernstein (Broad Institute)
  Replicates:  2 (isogenic)

Files: 24 total
  6 fastq (raw reads)
  4 bam (alignments)
  8 bed (peaks)
  6 bigWig (signal tracks)

Audit:
  2 warnings, 0 errors
```

This gives you everything: metadata, file inventory, quality audit status, and control experiments.

---

## 5. Finding and Inspecting Files

### List files for a specific experiment

> **You:** What BED files are available for ENCSR133RZO?

Claude calls `encode_list_files` with `experiment_accession="ENCSR133RZO"` and `file_format="bed"`:

```
8 BED files found:

Accession     Type              Output Type                 Assembly   Size
ENCFF635JIA   bed narrowPeak    IDR thresholded peaks       GRCh38     1.2 MB
ENCFF388RZD   bed narrowPeak    pseudoreplicated peaks      GRCh38     2.8 MB
ENCFF901XYZ   bed narrowPeak    replicated peaks            GRCh38     1.5 MB
ENCFF234ABC   bed broadPeak     IDR thresholded peaks       GRCh38     3.1 MB
...
```

### Get the recommended files

ENCODE marks certain files as "preferred default" -- these are the recommended analysis files:

> **You:** Show me just the recommended files for ENCSR133RZO.

```
preferred_default=True
```

### Search files across all experiments

This is powerful when you need a specific file type from many experiments at once:

> **You:** Find all IDR thresholded peak files for H3K27me3 in GRCh38.

Claude calls `encode_search_files` with:
- `output_type="IDR thresholded peaks"`
- `target="H3K27me3"`
- `assembly="GRCh38"`

Returns files from every matching experiment in one table.

### Inspect a single file

> **You:** Give me the full metadata for file ENCFF635JIA.

Claude calls `encode_get_file_info` and returns the file record: `file_format`, `file_type`, `output_type`, `output_category`, `file_size` (bytes) with `file_size_human`, `assembly`, `biological_replicates`, `technical_replicates`, `status`, `download_url`, `s3_uri`, `md5sum`, `experiment_accession`, `experiment_assay`, `biosample_summary`, `preferred_default` and `date_created`.

Sequencing details such as read length, run type or paired-end mate are not part of this record -- query the ENCODE portal directly if you need them.

---

## 6. Downloading Data

### Download specific files

> **You:** Download ENCFF635JIA and ENCFF388RZD to ~/data/encode.

Claude calls `encode_download_files` with:
- `file_accessions=["ENCFF635JIA", "ENCFF388RZD"]`
- `download_dir="~/data/encode"`

```
Downloaded 2 files:
  ~/data/encode/ENCFF635JIA.bed.gz   1.2 MB   MD5 verified
  ~/data/encode/ENCFF388RZD.bed.gz   2.8 MB   MD5 verified

Total: 4.0 MB
```

### Organize downloads by experiment

> **You:** Download those files organized by experiment.

```
organize_by="experiment"
```

Creates:
```
~/data/encode/
  ENCSR133RZO/
    ENCFF635JIA.bed.gz
    ENCFF388RZD.bed.gz
```

Other organization modes:
- `"flat"` -- all files in one directory (default)
- `"format"` -- grouped by file format (`bed/`, `bigWig/`, `fastq/`)
- `"experiment_format"` -- nested (`ENCSR133RZO/bed/`, `ENCSR133RZO/bigWig/`)

### Batch download with search

The most powerful download workflow combines search and download in one step. It uses **dry-run mode by default** so you can preview before committing.

**Step 1: Preview**

> **You:** Download all BED files from human pancreas ChIP-seq to ~/data/encode.

Claude calls `encode_batch_download` with `dry_run=True` (default):

```
Preview: Found 142 files (387 MB total)

  42 bed narrowPeak files
  38 bed broadPeak files
  62 bed other files

Set dry_run=False to download. Files will be organized by experiment.
```

**Step 2: Confirm**

> **You:** Looks good, go ahead and download.

Claude calls again with `dry_run=False` and the download begins.

### Filtered batch downloads

> **You:** Download only the IDR thresholded peaks for H3K27me3 in GRCh38 assembly to ~/data/peaks.

```
output_type="IDR thresholded peaks"
target="H3K27me3"
assembly="GRCh38"
download_dir="~/data/peaks"
dry_run=False
```

> **You:** Download ATAC-seq signal tracks from mouse brain.

```
file_format="bigWig"
assay_title="ATAC-seq"
organ="brain"
organism="Mus musculus"
```

---

## 7. Building a Research Library

The experiment tracker lets you build a local library of ENCODE experiments, like a reference manager for genomics data. Everything is stored in a local SQLite database.

### Track an experiment

> **You:** Track experiment ENCSR133RZO.

Claude calls `encode_track_experiment` with `accession="ENCSR133RZO"`:

```
tracking: ENCSR133RZO -> tracked
  Auto-linked references: 1 (geo_accession GSE187091)
  Publications found: 2
  Pipelines found: 1 (Histone ChIP-seq 2 (unreplicated), v1.7.1)
```

The reply carries `tracking` (`accession` plus an `action` of `"tracked"` or
`"updated"`), the publications and pipelines it found, and any references it
auto-linked. The experiment metadata itself goes into the database, not the reply.

This fetches and stores:
- Full experiment metadata
- Associated publications (PMIDs, DOIs, authors, journal)
- Pipeline and analysis information (software versions, methods)

### Add notes

> **You:** Track ENCSR456ABC and add a note: "Use as positive control for pancreas analysis."

```
accession="ENCSR456ABC"
notes="Use as positive control for pancreas analysis."
```

### Browse your library

> **You:** Show me all my tracked experiments.

Claude calls `encode_list_tracked`:

```
3 tracked experiments:

Accession     Assay              Target     Organ      Publications   Notes
ENCSR133RZO   Histone ChIP-seq   H3K27me3   pancreas   2              --
ENCSR456ABC   Histone ChIP-seq   H3K4me3    pancreas   1              Use as positive control
ENCSR789DEF   ATAC-seq           --         brain      3              --
```

### Filter your library

> **You:** Show me just the ChIP-seq experiments I'm tracking.

```
assay_title="ChIP-seq"
```

> **You:** Which of my tracked experiments are from pancreas?

```
organ="pancreas"
```

---

## 8. Managing Citations

Export publications from your tracked experiments in standard citation formats for use with reference managers.

### View publications

> **You:** What publications are associated with ENCSR133RZO?

Claude calls `encode_get_citations` with `accession="ENCSR133RZO"`:

```
2 publications:

1. Smith et al. (2023) "Chromatin landscape of the human pancreas"
   Nature Genetics, DOI: 10.1038/ng.xxxx, PMID: 12345678

2. ENCODE Consortium (2020) "Expanded encyclopaedias of DNA elements..."
   Nature, DOI: 10.1038/s41586-020-2493-4, PMID: 32728249
```

In JSON mode the tool returns `{"publications": [...], "count": 2}`, where each
publication carries `id`, `experiment_accession`, `pmid`, `doi`, `title`, `authors`,
`journal`, `year` and `abstract`.

### Export as BibTeX

> **You:** Export all my citations as BibTeX.

Claude calls `encode_get_citations` with `export_format="bibtex"`:

The reply is raw BibTeX text (not JSON), one entry per stored publication, keyed by PMID:

```bibtex
@article{12345678,
  title = {Chromatin landscape of the human pancreas},
  author = {Smith J and Jones A and Lee B},
  journal = {Nature Genetics},
  year = {2023},
  doi = {10.1038/ng.xxxx},
  pmid = {12345678},
  note = {ENCODE experiment: ENCSR133RZO},
}

@article{32728249,
  title = {Expanded encyclopaedias of DNA elements in the human and mouse genomes},
  author = {ENCODE Project Consortium and Moore JE and Purcaro MJ},
  journal = {Nature},
  year = {2020},
  doi = {10.1038/s41586-020-2493-4},
  pmid = {32728249},
  note = {ENCODE experiment: ENCSR133RZO},
}
```

### Export as RIS (for Endnote, Zotero, Mendeley)

> **You:** Export citations in RIS format so I can import them into Zotero.

```
export_format="ris"
```

```
TY  - JOUR
TI  - Chromatin landscape of the human pancreas
AU  - Smith J
AU  - Jones A
AU  - Lee B
JO  - Nature Genetics
PY  - 2023
DO  - 10.1038/ng.xxxx
AN  - PMID:12345678
N1  - ENCODE experiment: ENCSR133RZO
ER  -
```

---

## 9. Comparing Experiments

Before combining data from two experiments in a joint analysis, check whether they're compatible.

> **You:** Are ENCSR133RZO and ENCSR456ABC compatible for combined analysis?

Both experiments must be tracked first. Claude calls
`encode_compare_experiments(accession1="ENCSR133RZO", accession2="ENCSR456ABC")`:

```json
{
  "experiment_1": {
    "accession": "ENCSR133RZO",
    "assay": "Histone ChIP-seq",
    "biosample": "pancreas tissue female child (16 years)"
  },
  "experiment_2": {
    "accession": "ENCSR456ABC",
    "assay": "Histone ChIP-seq",
    "biosample": "pancreas tissue male adult (37 years)"
  },
  "verdict": "COMPATIBLE_WITH_CAVEATS",
  "recommendation": "These experiments can be compared, but the warnings should be addressed in your analysis.",
  "compatible_aspects": [
    "Same organism: Homo sapiens",
    "Same assembly: GRCh38",
    "Same assay: Histone ChIP-seq",
    "Same biosample type: tissue",
    "Same organ: pancreas"
  ],
  "issues": [],
  "warnings": [
    "Different targets: H3K27me3 vs H3K4me3.",
    "Different labs: Bradley Bernstein, Broad vs Bing Ren, UCSD. Batch effects possible."
  ]
}
```

`verdict` is one of `FULLY_COMPATIBLE`, `COMPATIBLE_WITH_CAVEATS` (warnings only) or
`NOT_COMPATIBLE` (at least one blocking issue).

### Incompatible experiments

> **You:** Can I combine ENCSR133RZO (human pancreas) with ENCSR789DEF (mouse brain)?

```json
{
  "experiment_1": { "accession": "ENCSR133RZO", "assay": "Histone ChIP-seq", "biosample": "pancreas tissue female child (16 years)" },
  "experiment_2": { "accession": "ENCSR789DEF", "assay": "ATAC-seq", "biosample": "brain tissue male adult (8 weeks)" },
  "verdict": "NOT_COMPATIBLE",
  "recommendation": "These experiments have fundamental incompatibilities that must be resolved before combined analysis.",
  "compatible_aspects": [
    "Same biosample type: tissue"
  ],
  "issues": [
    "Different organisms: Homo sapiens vs Mus musculus. Cross-species comparison requires ortholog mapping.",
    "Different genome assemblies: GRCh38 vs mm10. Coordinate liftover needed before comparison."
  ],
  "warnings": [
    "Different assay types: Histone ChIP-seq vs ATAC-seq. Multi-omic integration may be needed.",
    "Different organs/tissues: pancreas vs brain."
  ]
}
```

If either accession has not been tracked, the reply is a single key:
`{"error": "Experiment ENCSR789DEF not tracked. Track it first."}`

---

## 10. Tracking Data Provenance

When you create derived files from ENCODE data (filtered peaks, merged signals, differential analyses), log them for reproducibility.

### Log a derived file

> **You:** I ran bedtools intersect to filter the peaks from ENCSR133RZO. Log this file.

Claude calls `encode_log_derived_file`:

```python
file_path = "~/analysis/pancreas_h3k27me3_filtered.bed"
source_accessions = ["ENCSR133RZO", "ENCFF635JIA"]
description = "H3K27me3 peaks filtered to promoter regions"
file_type = "filtered_peaks"
tool_used = "bedtools intersect"
parameters = "bedtools intersect -a ENCFF635JIA.bed -b promoters.bed -u"
```

```json
{
  "success": true,
  "record_id": 1,
  "file_path": "~/analysis/pancreas_h3k27me3_filtered.bed",
  "source_accessions": ["ENCSR133RZO", "ENCFF635JIA"],
  "message": "Provenance logged. Use encode_get_provenance to view the full chain."
}
```

The `description`, `file_type`, `tool_used` and `parameters` you passed are stored but
not echoed back -- `encode_get_provenance` reads them out again.

### View the provenance chain

> **You:** Show me the provenance for my filtered peaks file.

Claude calls `encode_get_provenance(file_path="~/analysis/pancreas_h3k27me3_filtered.bed")`:

```json
{
  "id": 1,
  "file_path": "~/analysis/pancreas_h3k27me3_filtered.bed",
  "source_accessions": ["ENCSR133RZO", "ENCFF635JIA"],
  "description": "H3K27me3 peaks filtered to promoter regions",
  "created_at": 1772807400.512345,
  "file_type": "filtered_peaks",
  "tool_used": "bedtools intersect",
  "parameters": "bedtools intersect -a ENCFF635JIA.bed -b promoters.bed -u",
  "notes": "",
  "source_experiments": [
    {
      "accession": "ENCSR133RZO",
      "assay_title": "Histone ChIP-seq",
      "biosample_summary": "pancreas tissue female child (16 years)",
      "organism": "Homo sapiens"
    },
    {
      "accession": "ENCFF635JIA",
      "tracked": false
    }
  ]
}
```

`created_at` is epoch seconds. A source that is not a tracked experiment -- a file
accession such as ENCFF635JIA, for instance -- comes back as `{"accession": ..., "tracked": false}`.

### List all files derived from an experiment

> **You:** What files have I derived from ENCSR133RZO?

```
source_accession="ENCSR133RZO"
```

```
2 derived files:
  ~/analysis/pancreas_h3k27me3_filtered.bed   (bedtools intersect)
  ~/analysis/pancreas_h3k27me3_heatmap.png     (deepTools plotHeatmap)
```

---

## 11. Complete Workflows

Here are end-to-end workflows showing how the tools chain together for real research tasks.

### Workflow A: Histone Mark Survey

**Goal:** Survey all histone ChIP-seq marks available for human pancreas and download the IDR peak files.

```
Step 1: "What histone marks have ChIP-seq data for human pancreas tissue?"
         -> encode_get_facets shows 8 marks with experiment counts

Step 2: "Find all the histone ChIP-seq experiments for pancreas tissue."
         -> encode_search_experiments returns 66 experiments

Step 3: "Download all the IDR thresholded peaks in GRCh38 to ~/data/pancreas_peaks."
         -> encode_batch_download (dry_run) shows 58 files, 120 MB
         -> "Go ahead" -> downloads with MD5 verification

Step 4: "Track all these experiments."
         -> encode_track_experiment for each, fetches publications + pipelines

Step 5: "Export all my citations as BibTeX."
         -> encode_get_citations with export_format="bibtex"
```

### Workflow B: Cross-Tissue Comparison

**Goal:** Compare ATAC-seq chromatin accessibility between liver and pancreas.

```
Step 1: "Find ATAC-seq experiments on human liver tissue."
         -> encode_search_experiments returns 12 experiments

Step 2: "And for pancreas?"
         -> another search returns 8 experiments

Step 3: "Track ENCSR111AAA (liver) and ENCSR222BBB (pancreas)."
         -> both tracked with publications

Step 4: "Are these two experiments compatible for combined analysis?"
         -> encode_compare_experiments confirms same organism, assembly, assay

Step 5: "Download the preferred default bigWig signal tracks for both."
         -> encode_list_files with preferred_default=True for each
         -> encode_download_files for the signal tracks

Step 6: "Log my differential accessibility results."
         -> encode_log_derived_file records the source experiments and tool used
```

### Workflow C: Multi-Omics Integration

**Goal:** Collect ChIP-seq, ATAC-seq, and total RNA-seq data for GM12878 to build an integrative model.

```
Step 1: "What assay types have data for GM12878 on ENCODE?"
         -> encode_search_experiments with biosample_term_name="GM12878"
            (encode_get_facets narrows by assay_title, organism, organ or
             biosample_type -- not by an individual cell line)
         -> One search per assay gives the breakdown:
            TF ChIP-seq (200+), ATAC-seq (15), total RNA-seq (30), Hi-C (8)...

Step 2: "Find H3K27ac ChIP-seq for GM12878."
         -> 6 experiments found

Step 3: "Find ATAC-seq for GM12878."
         -> 15 experiments found

Step 4: "Find total RNA-seq for GM12878."
         -> 30 experiments found

Step 5: "Download the recommended peak files and signal tracks for these
          experiments, organized by experiment."
         -> Batch downloads with organize_by="experiment"

Step 6: "Track these experiments and export citations for my methods section."
         -> Tracked, BibTeX exported
```

---

## 12. Tips and Best Practices

### Start broad, then narrow

Don't start with every filter at once. Use facets first, then progressively add filters:

```
1. encode_get_facets(organ="pancreas")          -- see what's available
2. encode_search_experiments(organ="pancreas",
     assay_title="Histone ChIP-seq")            -- narrow to assay
3. encode_search_experiments(..., target="H3K27me3",
     biosample_type="tissue")                   -- narrow to mark + type
```

### Use dry_run before downloading

Batch downloads default to `dry_run=True`. Always preview first:

```
1. encode_batch_download(dry_run=True, ...)     -- see file count + size
2. "Looks good, download."                      -- dry_run=False
```

### Use preferred_default for clean results

ENCODE experiments often have many files (raw, intermediate, final). Setting `preferred_default=True` returns only the recommended analysis-ready files.

### Track everything you use

Tracking is lightweight and saves you from having to re-search later. It also captures publications and pipeline info automatically. Get in the habit of tracking experiments as you find them.

### Log derived files for reproducibility

Every time you create a new file from ENCODE data, log it. Your future self will thank you when a reviewer asks "where did this peak set come from?"

### Use organize_by for large downloads

When downloading files from many experiments, use `organize_by="experiment"` or `organize_by="experiment_format"` to keep things tidy. Flat directories become unmanageable past ~50 files.

### Check compatibility before combining

Before running a joint analysis on two experiments, use `encode_compare_experiments` to catch mismatches in organism, assembly, or assay type. It's much faster than debugging halfway through a pipeline.

---

## Authentication (optional)

Most ENCODE data is public. You only need credentials for unreleased or embargoed datasets.

### Check if you have credentials

> **You:** Do I have ENCODE credentials configured?

### Store credentials

> **You:** Store my ENCODE credentials. My access key is ABCD1234 and my secret key is EFGH5678.

Credentials are stored in your OS keyring (macOS Keychain, Linux Secret Service, Windows Credential Locker) and encrypted at rest. They are never stored in plaintext.

Get your access keys from your [ENCODE profile](https://www.encodeproject.org/).

### Remove credentials

> **You:** Clear my ENCODE credentials.

---

## Quick Reference

| Task | What to ask Claude |
|------|-------------------|
| List assay types | "What assay types are on ENCODE?" |
| Count data by organ | "What organs have ChIP-seq data?" |
| Search experiments | "Find ATAC-seq on human liver tissue" |
| Experiment details | "Show me details for ENCSR133RZO" |
| List files | "What BED files does ENCSR133RZO have?" |
| Search files globally | "Find all IDR peaks for H3K27me3 in GRCh38" |
| Download files | "Download ENCFF635JIA to ~/data" |
| Batch download | "Download all BED files from pancreas ChIP-seq" |
| Track experiment | "Track ENCSR133RZO with publications" |
| View tracked | "Show my tracked experiments" |
| Export citations | "Export all citations as BibTeX" |
| Compare experiments | "Are these two experiments compatible?" |
| Log derived file | "Log that I created filtered_peaks.bed from ENCSR133RZO" |
| View provenance | "Show provenance for my filtered peaks file" |
