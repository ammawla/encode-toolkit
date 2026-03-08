# Search ENCODE -- Finding the Right Experiments

> **Category:** Core | **Tools Used:** `encode_search_experiments`, `encode_get_facets`, `encode_get_metadata`

## What This Skill Does

Searches and explores the ENCODE Project catalog of functional genomic elements. Finds experiments by assay type, organ, biosample, target, and organism, then presents results with quality audit flags and suggested next steps.

## When to Use This

- You need to find all available ChIP-seq, ATAC-seq, or RNA-seq experiments for a specific tissue or cell line.
- You want to survey what ENCODE data exists before designing an analysis -- e.g., checking whether CUT&RUN data is available alongside ChIP-seq for your organ of interest.
- You are building a multi-experiment comparison and need to identify matching datasets across biosamples, targets, or labs.

## Example Session

### Scientist's Request

> "Find all H3K27ac ChIP-seq experiments on human pancreatic islets. I want released data only."

### Step 1: Explore Available Data

Before searching, check what pancreas data exists to set expectations.

```
encode_get_facets(organ="pancreas", assay_title="Histone ChIP-seq")
```

```json
{
  "total_experiments": 38,
  "facets": {
    "target": {"H3K27ac": 6, "H3K4me3": 8, "H3K27me3": 7, "H3K4me1": 5, "H3K36me3": 4},
    "biosample_type": {"tissue": 22, "cell line": 10, "in vitro differentiated cells": 6},
    "biosample_term_name": {"pancreas": 14, "islet of Langerhans": 8, "PANC-1": 6}
  }
}
```

Six H3K27ac experiments exist in pancreas, with 8 islet-specific datasets across all marks.

### Step 2: Search for Matching Experiments

```
encode_search_experiments(
  assay_title="Histone ChIP-seq", organ="pancreas",
  biosample_term_name="islet of Langerhans", target="H3K27ac",
  status="released", limit=25
)
```

```json
{
  "total": 4,
  "results": [
    {"accession": "ENCSR831YAX", "biosample_summary": "islet of Langerhans, adult male 54y",
     "target": "H3K27ac-human", "lab": "Bing Ren, UCSD",
     "audit": {"WARNING": 1, "NOT_COMPLIANT": 0, "ERROR": 0}},
    {"accession": "ENCSR976DGM", "biosample_summary": "islet of Langerhans, adult female 47y",
     "target": "H3K27ac-human", "lab": "Bing Ren, UCSD",
     "audit": {"WARNING": 0, "NOT_COMPLIANT": 0, "ERROR": 0}},
    {"accession": "ENCSR149DGJ", "biosample_summary": "islet of Langerhans, adult male 38y",
     "target": "H3K27ac-human", "lab": "Bradley Bernstein, Broad",
     "audit": {"WARNING": 2, "NOT_COMPLIANT": 0, "ERROR": 0}},
    {"accession": "ENCSR440KDQ", "biosample_summary": "islet of Langerhans, adult female 62y",
     "target": "H3K27ac-human", "lab": "Bradley Bernstein, Broad",
     "audit": {"WARNING": 1, "NOT_COMPLIANT": 1, "ERROR": 0}}
  ],
  "has_more": false
}
```

### Step 3: Interpret Results

Four experiments from two labs across both sexes and a range of donor ages.

- **ENCSR976DGM** has a clean audit (no warnings) -- prioritize this for analysis.
- **ENCSR440KDQ** has a NOT_COMPLIANT flag -- use `encode_get_experiment` to inspect the specific audit before including it.
- Two labs (Ren and Bernstein) provide biological diversity but may require batch-aware analysis.
- All four are from adult donors; embryonic islet H3K27ac data is not available.

Next steps: use `encode_list_files` on these accessions to retrieve IDR thresholded peaks in GRCh38, or track them locally with `encode_track_experiment`.

## Key Search Parameters

| Parameter | Description | Example Values |
|---|---|---|
| `assay_title` | Assay type (must match ENCODE vocabulary) | `"Histone ChIP-seq"`, `"ATAC-seq"`, `"RNA-seq"` |
| `organ` | Broad anatomical system | `"pancreas"`, `"brain"`, `"liver"`, `"heart"` |
| `biosample_term_name` | Specific cell or tissue name | `"islet of Langerhans"`, `"GM12878"`, `"K562"` |
| `biosample_type` | Sample classification | `"tissue"`, `"cell line"`, `"primary cell"`, `"organoid"` |
| `target` | ChIP-seq or CUT&RUN target | `"H3K27ac"`, `"H3K4me3"`, `"CTCF"`, `"p300"` |
| `organism` | Species (default: Homo sapiens) | `"Homo sapiens"`, `"Mus musculus"` |
| `life_stage` | Developmental stage | `"adult"`, `"embryonic"`, `"child"` |
| `status` | Data release status (default: released) | `"released"`, `"archived"` |

**Tip:** Run `encode_get_metadata(metadata_type="assays")` to see all valid assay names before searching. Wrong values return empty results silently.

## Related Skills

- **download-encode** -- Download files after finding experiments.
- **quality-assessment** -- Evaluate ChIP-seq QC metrics (FRiP, NSC, RSC) for flagged experiments.
- **track-experiments** -- Save found experiments to a local collection for provenance tracking.
- **compare-biosamples** -- Compare data across tissues or cell lines found in search results.
- **epigenome-profiling** -- Build comprehensive chromatin profiles from multiple search results.

---

*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 43 skills for genomics research*
