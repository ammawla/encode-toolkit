# Setup — Getting Started with ENCODE MCP

> **Category:** Core | **Tools Used:** `encode_get_metadata`, `encode_get_facets`

## What This Skill Does

The setup skill helps new users install the ENCODE MCP server, verify their connection, and orient themselves within ENCODE's data hierarchy. It turns the question "what data does ENCODE have for my tissue?" into a concrete inventory of assays, biosample types, and file formats available for any organ or cell type.

## When to Use This

- First time connecting to ENCODE through Claude
- Exploring what data exists before designing an analysis
- Troubleshooting connection issues or empty search results

## Example Session

### Scientist's Request

> I just installed the ENCODE connector and I want to study pancreatic gene regulation. What kinds of experiments does ENCODE have for pancreas? I'm not sure where to start.

### Step 1: Discover Available Assay Types

**Claude calls:** `encode_get_metadata(metadata_type="assays")`

**Response:**
```json
{
  "metadata_type": "assays",
  "values": [
    "Histone ChIP-seq",
    "TF ChIP-seq",
    "ATAC-seq",
    "DNase-seq",
    "total RNA-seq",
    "polyA plus RNA-seq",
    "WGBS",
    "intact Hi-C",
    "CUT&RUN",
    "CUT&Tag",
    "CRISPR screen",
    "..."
  ],
  "count": 79
}
```

**What this means:** ENCODE hosts 79 distinct assay types spanning chromatin profiling, transcription, DNA methylation, 3D genome structure, and functional screens. Note how specific the names are: there is no plain `"RNA-seq"` -- you filter on `"total RNA-seq"`, `"polyA plus RNA-seq"`, `"small RNA-seq"` and so on.

### Step 2: See What Pancreas Data Exists

**Claude calls:** `encode_get_facets(organ="pancreas")`

**Response:**
```json
{
  "assay_title": [
    {"term": "Histone ChIP-seq", "count": 48},
    {"term": "total RNA-seq", "count": 35},
    {"term": "TF ChIP-seq", "count": 15},
    {"term": "ATAC-seq", "count": 12},
    {"term": "WGBS", "count": 6}
  ],
  "biosample_ontology.classification": [
    {"term": "tissue", "count": 72},
    {"term": "cell line", "count": 18},
    {"term": "in vitro differentiated cells", "count": 14},
    {"term": "primary cell", "count": 9}
  ],
  "target.label": [
    {"term": "H3K27ac", "count": 12},
    {"term": "H3K4me3", "count": 10},
    {"term": "H3K27me3", "count": 8},
    {"term": "H3K4me1", "count": 7},
    {"term": "CTCF", "count": 5}
  ]
}
```

**What this means:** ENCODE has over 100 pancreas experiments. The top-level keys are ENCODE's facet field names, and each one lists its terms with live counts. Histone ChIP-seq and total RNA-seq dominate, with active (H3K27ac, H3K4me3) and repressive (H3K27me3) marks well represented. Most data comes from bulk tissue, but cell line and in vitro differentiated samples are also available. CTCF ChIP-seq provides insulator and 3D genome boundary data.

### Step 3: Check Biosample Type Options

**Claude calls:** `encode_get_metadata(metadata_type="biosample_types")`

**Response:**
```json
{
  "metadata_type": "biosample_types",
  "values": [
    "cell line",
    "tissue",
    "primary cell",
    "whole organisms",
    "in vitro differentiated cells",
    "cell-free sample",
    "organoid",
    "technical sample"
  ],
  "count": 8
}
```

**What this means:** ENCODE classifies biosamples into 8 categories. For pancreas research, "tissue" provides in vivo context, "primary cell" captures sorted islet populations, and "in vitro differentiated cells" includes stem-cell-derived beta cells.

## Key Concepts

- **ENCODE's data hierarchy:** Organism > Organ > Biosample type > Assay > Target > File format. The setup skill walks you through each layer.
- **Facets vs. metadata:** `encode_get_metadata` returns the full list of valid filter values (static). `encode_get_facets` returns live counts of how many experiments match each filter (dynamic). Use metadata to learn vocabulary, facets to scope your project.
- **No authentication needed:** All released ENCODE data is public. Credentials are only required for unreleased or embargoed datasets.
- **Assembly matters:** Human data uses GRCh38 (current) or hg19 (legacy). Never mix assemblies in a single analysis. Use `encode_get_metadata(metadata_type="assemblies")` to see all options.

## Related Skills

- [search-encode](search-encode.md) — find specific experiments after orienting with setup
- [download-encode](download-encode.md) — retrieve files once you know what data exists
- [quality-assessment](quality-assessment.md) — evaluate experiment quality before using data

---
*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) — 43 skills for genomics research*
