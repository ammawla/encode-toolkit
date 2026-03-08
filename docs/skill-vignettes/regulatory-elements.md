# Regulatory Elements -- Classifying cCREs in Human Brain

> **Category:** Analysis | **Tools Used:** `encode_search_experiments`, `encode_get_facets`, `encode_list_files`, `encode_download_files`, `encode_log_derived_file`

## What This Skill Does

Classifies candidate cis-regulatory elements (cCREs) using layered functional genomics data -- chromatin accessibility, histone marks, and CTCF binding. Distinguishes promoters, active enhancers, poised enhancers, insulators, and quiescent regions using the same combinatorial logic underlying ENCODE's 926,535-element cCRE registry (ENCODE Project Consortium 2020).

## When to Use This

- You need to build a tissue-specific regulatory element catalog that separates promoters from enhancers from insulators.
- You want to classify open chromatin peaks by overlaying ChromHMM states or histone mark combinations.
- You are interpreting non-coding variants and need to know what class of regulatory element they fall in.

## Example Session

A scientist classifies cCREs in human brain tissue, distinguishing four element classes: active promoters (H3K4me3+), active enhancers (H3K27ac+ H3K4me1+), CTCF-bound insulators, and quiescent regions.

### Step 1: Survey Available Brain Data

```
encode_get_facets(organ="brain", assay_title="Histone ChIP-seq")
```

Brain has broad coverage: H3K27ac (12 experiments), H3K4me3 (14), H3K4me1 (9), H3K27me3 (11), plus ATAC-seq (7) and CTCF ChIP-seq (5). Sufficient for full classification.

### Step 2: Collect the Four Core Layers

```
encode_search_experiments(assay_title="Histone ChIP-seq", target="H3K4me3", organ="brain", biosample_type="tissue", limit=25)
encode_search_experiments(assay_title="Histone ChIP-seq", target="H3K27ac", organ="brain", biosample_type="tissue", limit=25)
encode_search_experiments(assay_title="Histone ChIP-seq", target="H3K4me1", organ="brain", biosample_type="tissue", limit=25)
encode_search_experiments(assay_title="ATAC-seq", organ="brain", biosample_type="tissue", limit=25)
encode_search_experiments(assay_title="TF ChIP-seq", target="CTCF", organ="brain", biosample_type="tissue", limit=25)
```

Select one high-quality experiment per mark from the same donor where possible to avoid batch effects. Reject any experiment with ERROR-level audits.

### Step 3: Download IDR Peaks and Signal Tracks

```
encode_list_files(experiment_accession="ENCSR...", file_format="bed",
    output_type="IDR thresholded peaks", assembly="GRCh38", preferred_default=True)
```

For H3K4me1 (broad mark), use `output_type="replicated peaks"` instead. Download all files, then apply blacklist filtering (Amemiya et al. 2019):

```bash
bedtools intersect -v -a peaks.bed -b hg38-blacklist.v2.bed > peaks.filtered.bed
```

### Step 4: Classify Elements by Mark Overlap

Starting from ATAC-seq open chromatin peaks as the universe of candidate elements, overlay each mark:

```bash
# Promoters: accessible + H3K4me3
bedtools intersect -a atac.filtered.bed -b h3k4me3.filtered.bed -u > promoters.bed

# Active enhancers: accessible + H3K27ac + H3K4me1, NOT H3K4me3
bedtools intersect -a atac.filtered.bed -b h3k27ac.filtered.bed -u \
  | bedtools intersect -a - -b h3k4me1.filtered.bed -u \
  | bedtools intersect -a - -b h3k4me3.filtered.bed -v > enhancers.bed

# CTCF-bound insulators: accessible + CTCF, NOT H3K4me3, NOT H3K27ac
bedtools intersect -a atac.filtered.bed -b ctcf.filtered.bed -u \
  | bedtools intersect -a - -b h3k4me3.filtered.bed -v \
  | bedtools intersect -a - -b h3k27ac.filtered.bed -v > insulators.bed

# Quiescent: accessible but no marks (open chromatin with no classification)
bedtools intersect -a atac.filtered.bed -b h3k4me3.filtered.bed -v \
  | bedtools intersect -a - -b h3k27ac.filtered.bed -v \
  | bedtools intersect -a - -b ctcf.filtered.bed -v > quiescent.bed
```

### Step 5: Results

```
Total accessible regions:  148,207
Promoters (H3K4me3+):      21,384  (14.4%)
Active enhancers:           43,921  (29.6%)
CTCF-bound insulators:      8,716  ( 5.9%)
Quiescent/unclassified:    74,186  (50.1%)
```

The large quiescent fraction is expected -- many accessible regions lack the core marks in this tissue. These may be primed elements, tissue-specific elements active in brain subregions not captured by bulk tissue, or false positives from the accessibility assay.

### Step 6: Log Provenance

```
encode_log_derived_file(
    file_path="/data/brain_cCREs/brain_regulatory_catalog.bed",
    source_accessions=["ENCSR...", "ENCSR...", "ENCSR...", "ENCSR...", "ENCSR..."],
    description="Brain cCRE catalog: 21,384 promoters, 43,921 enhancers, 8,716 insulators",
    file_type="regulatory_elements",
    tool_used="bedtools intersect v2.31.0",
    parameters="blacklist=hg38-blacklist.v2.bed; mark overlap classification; GRCh38"
)
```

## Key Principles

- **Accessibility first, marks second.** Use ATAC-seq or DNase-seq peaks as the candidate universe, then overlay marks to classify. A region without accessibility is unlikely to be an active regulatory element regardless of histone marks.
- **H3K4me3 separates promoters from enhancers.** This is the foundational distinction (Heintzman et al. 2007). Enhancers carry H3K4me1 but not H3K4me3; promoters carry H3K4me3.
- **Biochemical classification is not functional validation.** An H3K27ac+ region is a candidate enhancer. Confirming it regulates a target gene requires perturbation data (CRISPRi) or reporter assays (MPRA, STARR-seq). Always state the evidence level.
- **Check Roadmap Epigenomics first.** Pre-computed ChromHMM states exist for 111 reference epigenomes (Kundaje et al. 2015). If your tissue is covered, use those states rather than re-deriving classifications from individual marks.

## Related Skills

- **histone-aggregation** -- Merge peaks across multiple donors before classification to maximize sensitivity.
- **epigenome-profiling** -- Build comprehensive chromatin profiles with extended mark panels and ChromHMM.
- **variant-annotation** -- Map non-coding variants to classified regulatory elements for functional interpretation.
- **peak-annotation** -- Annotate classified elements with nearest genes and genomic feature context.
- **quality-assessment** -- Verify ChIP-seq quality (FRiP, NSC, RSC) before trusting mark classifications.

---

*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 43 skills for genomics research*
