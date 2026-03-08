# Epigenome Profiling -- Comprehensive Chromatin State Maps from ENCODE

> **Category:** Analysis | **Tools Used:** `encode_get_facets`, `encode_search_experiments`, `encode_list_files`, `encode_download_files`, `encode_track_experiment`, `encode_summarize_collection`

## What This Skill Does

Surveys all available histone marks, chromatin accessibility, TF binding, transcription, DNA methylation, and 3D structure data for a tissue or cell type. Assembles these layers into a comprehensive epigenomic profile and interprets it using ChromHMM chromatin state segmentation (Ernst & Kellis 2012). Identifies active promoters, enhancers, poised elements, bivalent domains, and heterochromatin genome-wide.

## When to Use This

- You need a complete regulatory landscape for a tissue before downstream analysis.
- You want to know which chromatin states are present at specific loci in your biosample.
- You are planning a ChromHMM segmentation and need to confirm which marks ENCODE has profiled.

## Example Session

> "Profile the epigenome of human heart tissue. What histone marks are available? Can I build a ChromHMM state map?"

### Step 1: Survey Data Availability

```
encode_get_facets(organ="heart", biosample_type="tissue")
```

Facets reveal Histone ChIP-seq (42 experiments), ATAC-seq (6), DNase-seq (8), RNA-seq (12), TF ChIP-seq (4), WGBS (2), and Hi-C (1) across heart biosamples. Sufficient depth for a full profile.

### Step 2: Search Core Histone Marks

Query each mark in the 5-mark ChromHMM panel plus H3K27ac:

```
encode_search_experiments(assay_title="Histone ChIP-seq", target="H3K4me3", organ="heart", biosample_type="tissue", limit=20)
encode_search_experiments(assay_title="Histone ChIP-seq", target="H3K27ac", organ="heart", biosample_type="tissue", limit=20)
encode_search_experiments(assay_title="Histone ChIP-seq", target="H3K27me3", organ="heart", biosample_type="tissue", limit=20)
encode_search_experiments(assay_title="Histone ChIP-seq", target="H3K4me1", organ="heart", biosample_type="tissue", limit=20)
encode_search_experiments(assay_title="Histone ChIP-seq", target="H3K36me3", organ="heart", biosample_type="tissue", limit=20)
encode_search_experiments(assay_title="Histone ChIP-seq", target="H3K9me3", organ="heart", biosample_type="tissue", limit=20)
```

### Step 3: Assess Coverage

| Data Layer | Mark/Assay | Experiments | Donors | ChromHMM Role |
|---|---|---|---|---|
| H3K27ac | Histone ChIP | 5 | 4 | Active enhancers + promoters |
| H3K4me3 | Histone ChIP | 4 | 3 | Active/bivalent promoters |
| H3K27me3 | Histone ChIP | 4 | 3 | Polycomb repression, bivalency |
| H3K4me1 | Histone ChIP | 4 | 3 | Enhancers (primed + active) |
| H3K36me3 | Histone ChIP | 4 | 3 | Transcribed gene bodies |
| H3K9me3 | Histone ChIP | 3 | 2 | Constitutive heterochromatin |
| Accessibility | ATAC-seq | 6 | 4 | Validates regulatory elements |
| Expression | RNA-seq | 12 | 8 | Links states to function |

All six marks present. The 5-mark core (H3K4me3, H3K4me1, H3K27me3, H3K36me3, H3K9me3) enables the Roadmap 15-state ChromHMM model. Adding H3K27ac enables the 18-state extended model that separates active from poised enhancers (Creyghton et al. 2010).

### Step 4: Download Signal and Peaks

```
encode_batch_download(
    assay_title="Histone ChIP-seq", organ="heart", biosample_type="tissue",
    file_format="bigWig", output_type="fold change over control",
    assembly="GRCh38", preferred_default=True,
    download_dir="/data/heart_epigenome/signal", organize_by="experiment", dry_run=True)

encode_batch_download(
    assay_title="Histone ChIP-seq", organ="heart", biosample_type="tissue",
    file_format="bed", assembly="GRCh38", preferred_default=True,
    download_dir="/data/heart_epigenome/peaks", organize_by="experiment", dry_run=True)
```

Use IDR thresholded narrowPeak for sharp marks (H3K4me3, H3K4me1, H3K27ac). Use broadPeak for domain marks (H3K27me3, H3K9me3, H3K36me3) -- narrowPeak fragments broad domains and loses Polycomb/heterochromatin structure.

### Step 5: Build ChromHMM State Map

With all six marks binarized into 200bp bins, ChromHMM learns an 18-state model. Heart tissue shows characteristic states at cardiac loci:

| State | Name | Key Marks | Heart Interpretation |
|---|---|---|---|
| TssA | Active TSS | H3K4me3, H3K27ac | Cardiac structural genes (MYH7, TNNT2) |
| Enh | Active Enhancer | H3K4me1, H3K27ac | Heart-specific enhancers near GATA4, NKX2-5 |
| EnhBiv | Bivalent Enhancer | H3K4me1, H3K27me3 | Poised developmental enhancers |
| ReprPC | Polycomb Repressed | H3K27me3 | Silenced non-cardiac lineage genes |
| Het | Heterochromatin | H3K9me3 | Repetitive elements, pericentromeric |
| Quies | Quiescent | None | Intergenic, gene deserts |

### Step 6: Track and Document

```
encode_track_experiment(accession="ENCSR...)  # repeat for each experiment
encode_summarize_collection(organ="heart")
```

The summary confirms 24 tracked experiments across 6 histone marks, ATAC-seq, and RNA-seq -- a complete 18-state-capable epigenomic profile.

## Key Principles

- **Start with the 5-mark core.** H3K4me3, H3K4me1, H3K27me3, H3K36me3, H3K9me3 are sufficient for the 15-state model. Add H3K27ac for the 18-state model whenever available.
- **Broad marks need broadPeak.** H3K27me3 and H3K9me3 form domains spanning tens of kilobases. NarrowPeak calls miss domain-level biology.
- **Bulk tissue averages cell types.** Apparent bivalent domains (H3K4me3 + H3K27me3) may reflect mixed cell populations, not true same-cell bivalency. Confirm with sorted or single-cell data when possible.
- **Never mix assemblies.** All files in a profile must use the same genome build (GRCh38 for human).

## Related Skills

- **histone-aggregation** -- Merge peaks for a single mark across donors into a union catalog.
- **regulatory-elements** -- Classify cis-regulatory elements using the assembled profile.
- **compare-biosamples** -- Diff two tissue profiles to find tissue-specific chromatin states.
- **quality-assessment** -- Evaluate ChIP-seq QC metrics before including experiments.
- **visualization-workflow** -- Render the profile as genome browser tracks and heatmaps.
- **pipeline-chipseq** -- Process raw ChIP-seq data through the ENCODE-aligned pipeline.

---
*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 43 skills for genomics research*
