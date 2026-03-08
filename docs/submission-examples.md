# ENCODE MCP Plugin -- Submission Examples

> These examples demonstrate core functionality of the ENCODE MCP plugin.
> All output shown is from real ENCODE API queries run on March 8, 2026.
> ENCODE accessions are permanent identifiers -- these results remain valid indefinitely.

---

## Example 1: Discovering Available Data

**Scientist asks Claude:**
> "What ENCODE data exists for human pancreas?"

**Claude calls:** `encode_get_facets(organ="pancreas")`

**Response (trimmed to key facets):**
```json
{
  "assay_title": [
    { "term": "Histone ChIP-seq", "count": 73 },
    { "term": "DNase-seq", "count": 31 },
    { "term": "TF ChIP-seq", "count": 25 },
    { "term": "snATAC-seq", "count": 17 },
    { "term": "ATAC-seq", "count": 10 },
    { "term": "total RNA-seq", "count": 11 }
  ],
  "target.label": [
    { "term": "H3K4me3", "count": 16 },
    { "term": "H3K27ac", "count": 15 },
    { "term": "H3K27me3", "count": 14 },
    { "term": "H3K4me1", "count": 13 }
  ],
  "biosample_ontology.term_name": [
    { "term": "pancreas", "count": 108 },
    { "term": "body of pancreas", "count": 72 },
    { "term": "Panc1", "count": 47 }
  ]
}
```

**What the scientist learns:**
- 288 total pancreas experiments span 30 assay types
- Histone ChIP-seq dominates (73 experiments) with all six major marks profiled
- Most data comes from tissue (200) rather than cell lines (51) or organoids (5)
- The scientist can now narrow down to a specific mark, assay, or biosample

---

## Example 2: Searching for Experiments

**Scientist asks Claude:**
> "Find me H3K27me3 ChIP-seq experiments on human pancreas tissue."

**Claude calls:** `encode_search_experiments(assay_title="Histone ChIP-seq", organ="pancreas", limit=3)`

**Response (trimmed to first 2 of 73 results):**
```json
{
  "results": [
    {
      "accession": "ENCSR133RZO",
      "target": "H3K27me3-human",
      "biosample_summary": "Homo sapiens pancreas tissue female child (16 years)",
      "lab": "bradley-bernstein",
      "file_count": 14,
      "audit_error_count": 0,
      "dbxrefs": ["GEO:GSE187091"],
      "url": "https://www.encodeproject.org/experiments/ENCSR133RZO/"
    },
    {
      "accession": "ENCSR511LIV",
      "target": "H3K27me3-human",
      "biosample_summary": "Homo sapiens pancreas tissue female adult (61 years)",
      "lab": "bradley-bernstein",
      "file_count": 14,
      "dbxrefs": ["GEO:GSE187520"],
      "url": "https://www.encodeproject.org/experiments/ENCSR511LIV/"
    }
  ],
  "total": 73,
  "offset": 0
}
```

**What the scientist learns:**
- 73 histone ChIP-seq experiments match, spanning multiple marks and donors
- Each result includes donor demographics, GEO cross-references, and audit status
- The `total: 73` field tells them how many more results exist beyond the preview
- Zero audit errors on these experiments indicates high data quality

---

## Example 3: Getting Experiment Details and Files

**Scientist asks Claude:**
> "Show me the details and available files for experiment ENCSR133RZO."

**Claude calls:** `encode_get_experiment(accession="ENCSR133RZO")`

**Response (trimmed -- 14 files total, 3 shown):**
```json
{
  "accession": "ENCSR133RZO",
  "assay_title": "Histone ChIP-seq",
  "target": "H3K27me3",
  "biosample_summary": "Homo sapiens pancreas tissue female child (16 years)",
  "lab": "Bradley Bernstein, Broad",
  "organ": "pancreas",
  "biosample_type": "tissue",
  "possible_controls": ["ENCSR618UQQ"],
  "files": [
    {
      "accession": "ENCFF635JIA",
      "file_format": "bed",
      "output_type": "pseudoreplicated peaks",
      "file_size_human": "39.5 KB",
      "assembly": "GRCh38",
      "preferred_default": true
    },
    {
      "accession": "ENCFF186PZN",
      "file_format": "bigWig",
      "output_type": "fold change over control",
      "file_size_human": "1.2 GB",
      "assembly": "GRCh38"
    },
    {
      "accession": "ENCFF977UZL",
      "file_format": "bam",
      "output_type": "alignments",
      "file_size_human": "3.3 GB",
      "assembly": "GRCh38"
    }
  ],
  "url": "https://www.encodeproject.org/experiments/ENCSR133RZO/"
}
```

**Then the scientist asks:**
> "Just show me the BED peak files."

**Claude calls:** `encode_list_files(experiment_accession="ENCSR133RZO", file_format="bed")`

**Response:**
```json
[
  {
    "accession": "ENCFF635JIA",
    "file_format": "bed",
    "file_type": "bed narrowPeak",
    "output_type": "pseudoreplicated peaks",
    "file_size_human": "39.5 KB",
    "assembly": "GRCh38",
    "preferred_default": true,
    "download_url": "https://www.encodeproject.org/files/ENCFF635JIA/@@download/ENCFF635JIA.bed.gz",
    "md5sum": "2a41c04233d7ba1cac7b73b912161d50"
  }
]
```

**What the scientist learns:**
- The experiment has 14 files total: raw FASTQs, alignments, signal tracks, and peak calls
- ENCFF635JIA is the recommended peak file (`preferred_default: true`) in GRCh38
- The file includes an MD5 checksum for download verification
- The experiment used ENCSR618UQQ as its input control

---

## Example 4: Building a Research Library

**Scientist asks Claude:**
> "Track experiment ENCSR133RZO in my local library with its publications."

**Claude calls:** `encode_track_experiment(accession="ENCSR133RZO", fetch_publications=true, fetch_pipelines=true)`

**Response (representative):**
```json
{
  "status": "tracked",
  "accession": "ENCSR133RZO",
  "assay_title": "Histone ChIP-seq",
  "target": "H3K27me3",
  "organism": "Homo sapiens",
  "organ": "pancreas",
  "publications_found": 1,
  "pipelines_found": 1
}
```

**Then the scientist asks:**
> "Export the citations for my tracked experiments."

**Claude calls:** `encode_get_citations(accession="ENCSR133RZO", export_format="bibtex")`

**Response (representative BibTeX):**
```bibtex
@article{ENCSR133RZO_pub1,
  title   = {An atlas of gene regulatory elements in adult mouse cerebrum},
  author  = {Li, Yang Eric and Preissl, Sebastian and Hou, Xiaomeng and others},
  journal = {Nature},
  year    = {2021},
  doi     = {10.1038/s41586-021-03604-1},
  note    = {Associated with ENCODE experiment ENCSR133RZO}
}
```

**What the scientist learns:**
- Experiments are saved to a local SQLite database for offline access
- Publications and pipeline metadata are fetched automatically from ENCODE
- Citations can be exported in BibTeX (for LaTeX) or RIS (for Zotero/Mendeley/Endnote)
- The local library persists across sessions and can be queried later

---

## Example 5: Cross-Database Integration

**Scientist asks Claude:**
> "Link PubMed article 32728249 to my tracked experiment ENCSR133RZO -- it's from the
> Roadmap Epigenomics study that provides context for this data."

**Claude calls:** `encode_link_reference(experiment_accession="ENCSR133RZO", reference_type="pmid", reference_id="32728249", description="Roadmap Epigenomics context for pancreas H3K27me3")`

**Response:** `{"status": "linked", "experiment_accession": "ENCSR133RZO", "reference_type": "pmid", "reference_id": "32728249"}`

**Then the scientist asks:**
> "Show me all external references linked to my ENCODE experiments."

**Claude calls:** `encode_get_references()`

**Response:**
```json
{
  "references": [
    {
      "experiment_accession": "ENCSR133RZO",
      "reference_type": "pmid",
      "reference_id": "32728249",
      "description": "Roadmap Epigenomics context for pancreas H3K27me3",
      "date_linked": "2026-03-08"
    }
  ],
  "total": 1
}
```

**What the scientist learns:**
- ENCODE experiments can be linked to PubMed IDs, DOIs, bioRxiv preprints, GEO accessions, and ClinicalTrials.gov NCT IDs
- References are stored locally alongside the tracked experiment metadata
- PubMed IDs from linked references can be passed directly to a PubMed MCP tool for full article retrieval
- This creates a unified provenance chain connecting ENCODE data to the broader literature

---

## Summary of Tools Demonstrated

| Example | Tools Used | Capability |
|---------|-----------|------------|
| 1. Discovering data | `encode_get_facets` | Explore what exists before searching |
| 2. Searching experiments | `encode_search_experiments` | Find experiments by assay, organ, target |
| 3. Experiment details | `encode_get_experiment`, `encode_list_files` | Drill into metadata and files |
| 4. Research library | `encode_track_experiment`, `encode_get_citations` | Local tracking with citation export |
| 5. Cross-database | `encode_link_reference`, `encode_get_references` | Connect ENCODE to PubMed, GEO, bioRxiv |

These five examples cover the plugin's core workflow: discover, search, inspect, track, and integrate. The plugin provides 20 tools total, including batch download with MD5 verification (`encode_batch_download`), experiment compatibility comparison (`encode_compare_experiments`), and derived file provenance logging (`encode_log_derived_file`).
