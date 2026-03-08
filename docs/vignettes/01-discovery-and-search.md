# Finding ENCODE Data for Your Research

> This vignette demonstrates how scientists use the ENCODE MCP plugin through Claude
> to discover and search genomic data. All output shown is from real ENCODE API queries.

## Scenario

You are studying chromatin regulation in human pancreatic tissue and need to find
what ENCODE data is available before designing experiments.

## Step 1: Explore What's Available

**You ask Claude:**
> "What ENCODE data exists for human pancreas?"

**Claude calls:** `encode_get_facets(organ="pancreas")`

**Result:**
```json
{
  "assay_title": [
    { "term": "Histone ChIP-seq", "count": 73 },
    { "term": "DNase-seq", "count": 31 },
    { "term": "TF ChIP-seq", "count": 25 },
    { "term": "snATAC-seq", "count": 17 },
    { "term": "ATAC-seq", "count": 10 },
    { "term": "total RNA-seq", "count": 11 },
    { "term": "WGBS", "count": 5 },
    { "term": "intact Hi-C", "count": 5 }
  ],
  "target.label": [
    { "term": "H3K4me3", "count": 16 },
    { "term": "H3K27ac", "count": 15 },
    { "term": "H3K27me3", "count": 14 },
    { "term": "H3K4me1", "count": 13 },
    { "term": "H3K36me3", "count": 12 },
    { "term": "CTCF", "count": 16 }
  ],
  "biosample_ontology.term_name": [
    { "term": "pancreas", "count": 108 },
    { "term": "body of pancreas", "count": 72 },
    { "term": "Panc1", "count": 47 },
    { "term": "islet of Langerhans", "count": 3 }
  ]
}
```

**What this tells you:** Pancreas has strong histone modification coverage (73 ChIP-seq
experiments) across all six core marks plus CTCF. Chromatin accessibility is well
represented with DNase-seq (31) and ATAC-seq/snATAC-seq (27 combined).

Note the biosample breakdown: Panc1 (47 experiments) is a cancer line -- use caution
for normal physiology studies. Islet of Langerhans has only 3 experiments, so
islet-specific work may need supplementary external data.

## Step 2: Search for Specific Experiments

**You ask Claude:**
> "Show me the H3K27me3 ChIP-seq experiments on pancreas tissue."

**Claude calls:** `encode_search_experiments(assay_title="Histone ChIP-seq", organ="pancreas", target="H3K27me3")`

**Result:**
```json
{
  "results": [
    {
      "accession": "ENCSR133RZO",
      "target": "H3K27me3-human",
      "biosample_summary": "Homo sapiens pancreas tissue female child (16 years)",
      "lab": "bradley-bernstein",
      "replication_type": "unreplicated",
      "audit_warning_count": 8,
      "dbxrefs": ["GEO:GSE187091"]
    },
    {
      "accession": "ENCSR511LIV",
      "target": "H3K27me3-human",
      "biosample_summary": "Homo sapiens pancreas tissue female adult (61 years)",
      "lab": "bradley-bernstein",
      "replication_type": "unreplicated",
      "audit_warning_count": 8,
      "dbxrefs": ["GEO:GSE187520"]
    }
  ],
  "total": 73
}
```

**What this tells you:** Two H3K27me3 experiments from the Bernstein lab cover different
donor ages (16 and 61 years). Both are unreplicated -- common for primary tissue where
donor material is limited. GEO cross-references let you find these in NCBI GEO for raw
data or supplementary metadata.

## Step 3: Refine with Metadata

**You ask Claude:**
> "What assay types does ENCODE support?"

**Claude calls:** `encode_get_metadata(metadata_type="assays")`

**Result:**
```json
{
  "metadata_type": "assays",
  "values": [
    "Histone ChIP-seq", "TF ChIP-seq", "ATAC-seq", "DNase-seq",
    "RNA-seq", "WGBS", "Hi-C", "CUT&RUN", "CUT&Tag",
    "STARR-seq", "MPRA", "CRISPR screen", "eCLIP"
  ],
  "count": 59
}
```

**What this tells you:** The metadata tool returns canonical assay names that the search
tools expect, preventing typos. This is especially useful for newer methods like CUT&RUN
or STARR-seq where naming varies across the literature.

**You follow up:**
> "Find CUT&RUN experiments on pancreas."

**Claude calls:** `encode_search_experiments(assay_title="CUT&RUN", organ="pancreas")`

Claude reports whether CUT&RUN data exists for pancreas. If none are found, you can
pivot to CUT&Tag or a related tissue.

## Step 4: Quality-Aware Selection

ENCODE assigns audit flags at four severity levels: ERROR, NOT_COMPLIANT, WARNING,
and INTERNAL_ACTION. Always check before downloading.

**You ask Claude:**
> "Check the quality of ENCSR133RZO before I use it."

**Claude calls:** `encode_get_experiment(accession="ENCSR133RZO")`

**Result (key fields):**
```json
{
  "accession": "ENCSR133RZO",
  "status": "released",
  "replication_type": "unreplicated",
  "audit": {
    "ERROR": 0,
    "NOT_COMPLIANT": 0,
    "WARNING": 8,
    "INTERNAL_ACTION": 0
  },
  "files_count": 14
}
```

**What this tells you:** Zero errors and zero compliance failures mean this experiment
passed ENCODE's core quality standards. The 8 warnings are typical for primary tissue
and often flag unreplicated design or suboptimal library complexity.

Key considerations:

- **Unreplicated design.** Pair ENCSR133RZO with ENCSR511LIV (the 61-year-old
  donor) as a cross-donor replicate.
- **Bernstein lab.** A leading chromatin lab in the Consortium, adding confidence
  in wet-lab quality.
- **Broad mark.** H3K27me3 should use broadPeak format, not narrowPeak. The same
  applies to H3K9me3 and H3K36me3.
- **File selection.** Filter for preferred default files or IDR thresholded peaks
  to get the highest-confidence calls.

## Skills Demonstrated

- **search-encode** -- Finding experiments by assay, organ, target, and browsing
  available data with faceted counts
- **quality-assessment** -- Evaluating audit status, replication, and lab provenance
- **setup** -- Understanding ENCODE's biosample hierarchy and assay naming conventions

## What's Next

- [Download & Track](02-download-and-track.md) -- Download your selected files and
  track experiments locally for provenance
- [Epigenomics Workflow](03-epigenomics-workflow.md) -- Build a full chromatin
  landscape from histone marks, accessibility, and methylation data
