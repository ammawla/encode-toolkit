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

The top-level keys are ENCODE's own facet field names, and each holds a list of
`{"term", "count"}` objects:

```json
{
  "assay_title": [
    {"term": "Histone ChIP-seq", "count": 38}
  ],
  "target.label": [
    {"term": "H3K4me3", "count": 8},
    {"term": "H3K27me3", "count": 7},
    {"term": "H3K27ac", "count": 6},
    {"term": "H3K4me1", "count": 5},
    {"term": "H3K36me3", "count": 4}
  ],
  "biosample_ontology.classification": [
    {"term": "tissue", "count": 22},
    {"term": "cell line", "count": 10},
    {"term": "in vitro differentiated cells", "count": 6}
  ],
  "biosample_ontology.term_name": [
    {"term": "pancreas", "count": 14},
    {"term": "islet of Langerhans", "count": 8},
    {"term": "PANC-1", "count": 6}
  ]
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
     "target": "H3K27ac", "lab": "Bing Ren, UCSD",
     "audit_error_count": 0, "audit_not_compliant_count": 0, "audit_warning_count": 1},
    {"accession": "ENCSR976DGM", "biosample_summary": "islet of Langerhans, adult female 47y",
     "target": "H3K27ac", "lab": "Bing Ren, UCSD",
     "audit_error_count": 0, "audit_not_compliant_count": 0, "audit_warning_count": 0},
    {"accession": "ENCSR149DGJ", "biosample_summary": "islet of Langerhans, adult male 38y",
     "target": "H3K27ac", "lab": "Bradley Bernstein, Broad",
     "audit_error_count": 0, "audit_not_compliant_count": 0, "audit_warning_count": 2},
    {"accession": "ENCSR440KDQ", "biosample_summary": "islet of Langerhans, adult female 62y",
     "target": "H3K27ac", "lab": "Bradley Bernstein, Broad",
     "audit_error_count": 0, "audit_not_compliant_count": 1, "audit_warning_count": 1}
  ],
  "limit": 25,
  "offset": 0,
  "has_more": false,
  "next_offset": null
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
| `assay_title` | Assay type (must match ENCODE vocabulary) | `"Histone ChIP-seq"`, `"ATAC-seq"`, `"total RNA-seq"` |
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
