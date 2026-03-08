# Variant Annotation -- T2D Risk Variant rs7903146 in Pancreatic Islet Enhancers

> **Category:** Workflow | **Tools Used:** `encode_search_experiments`, `encode_get_facets`, `encode_list_files`, `encode_download_files`, `encode_track_experiment`, `encode_log_derived_file`, `encode_link_reference`

## What This Skill Does

Annotates genetic variants with ENCODE functional data to determine whether they disrupt regulatory elements in disease-relevant tissues. Layers chromatin accessibility, histone marks, TF binding, and 3D chromatin contacts to distinguish causal regulatory variants from bystander SNPs in linkage disequilibrium. Covers the full post-GWAS workflow: variant set definition, tissue mapping, multi-layer annotation, variant-to-gene linking, and evidence-based prioritization.

## When to Use This

- You have GWAS hits, fine-mapped credible sets, or eQTL variants and need to determine which ones disrupt functional regulatory elements.
- You want to overlay ENCODE enhancer, accessibility, and Hi-C data onto non-coding variants to prioritize candidates for experimental validation.
- You need to link a variant in an intergenic enhancer to its target gene using 3D chromatin contact data.

## Example Session

A researcher investigates rs7903146 (chr10:112998590, C>T), the strongest common variant association for type 2 diabetes, located in intron 3 of TCF7L2. Despite being inside a gene body, the variant sits in a non-coding regulatory region -- not in an exon. The goal is to determine whether it falls in an islet-active enhancer and identify its regulatory target.

### Step 1: Survey Pancreas Functional Data in ENCODE

```
encode_get_facets(organ="pancreas")
```

Pancreas has ATAC-seq (4 experiments), Histone ChIP-seq (18 across H3K27ac, H3K4me3, H3K4me1, H3K27me3), Hi-C (2), and RNA-seq (6). Sufficient for multi-layer annotation.

### Step 2: Gather Islet Chromatin Accessibility

```
encode_search_experiments(assay_title="ATAC-seq", organ="pancreas", biosample_type="tissue", limit=10)
```

Four ATAC-seq experiments on pancreas tissue returned. Select experiments with no ERROR audits. Download IDR thresholded peaks on GRCh38:

```
encode_list_files(experiment_accession="ENCSR...", file_format="bed",
    output_type="IDR thresholded peaks", assembly="GRCh38", preferred_default=True)
```

**Result**: rs7903146 overlaps an ATAC-seq peak in all four pancreas samples. The region is accessible in islet chromatin.

### Step 3: Check Active Enhancer Marks

```
encode_search_experiments(assay_title="Histone ChIP-seq", target="H3K27ac", organ="pancreas", biosample_type="tissue")
encode_search_experiments(assay_title="Histone ChIP-seq", target="H3K4me1", organ="pancreas", biosample_type="tissue")
encode_search_experiments(assay_title="Histone ChIP-seq", target="H3K4me3", organ="pancreas", biosample_type="tissue")
```

Download peaks and intersect with the variant position (chr10:112998590):

- **H3K27ac**: Overlaps peak -- active regulatory mark present
- **H3K4me1**: Overlaps peak -- enhancer mark present
- **H3K4me3**: No overlap -- not a promoter

This combination (ATAC+ H3K27ac+ H3K4me1+ H3K4me3-) classifies the region as an **active enhancer** in pancreas tissue, consistent with ENCODE cCRE class dELS (distal enhancer-like signature).

### Step 4: Query Hi-C for Enhancer-Gene Contacts

```
encode_search_experiments(assay_title="Hi-C", organ="pancreas", biosample_type="tissue")
```

Download contact matrices and extract loops overlapping the rs7903146 locus. The enhancer harboring rs7903146 forms a chromatin loop contacting the TCF7L2 promoter approximately 400 kb downstream, confirming enhancer-to-promoter physical proximity. Critically, no loop is detected to intervening genes, supporting TCF7L2 as the direct regulatory target rather than a nearer gene.

### Step 5: Score and Prioritize

Applying the variant annotation evidence framework:

| Evidence Layer | Result | Score |
|---|---|---|
| Overlaps tissue-specific ATAC peak | Yes (4/4 pancreas samples) | +2 |
| Overlaps H3K27ac peak (pancreas) | Yes | +2 |
| Overlaps H3K4me1, not H3K4me3 | Active enhancer | +2 |
| Hi-C loop to TCF7L2 promoter | Yes | +1 |
| Known T2D GWAS lead SNP | rs7903146 OR=1.4 | +3 |

**Total: 10** -- High-priority causal candidate (threshold >= 8). Multiple independent lines of evidence converge: the variant sits in a pancreas-specific active enhancer that physically contacts TCF7L2.

### Step 6: Log Provenance

```
encode_track_experiment(accession="ENCSR...", notes="variant annotation - T2D rs7903146")
encode_log_derived_file(
    file_path="/data/t2d_variants/rs7903146_annotation.tsv",
    source_accessions=["ENCSR...", "ENCSR...", "ENCSR...", "ENCSR..."],
    description="Functional annotation of rs7903146 using pancreas ATAC-seq, H3K27ac, H3K4me1, H3K4me3, Hi-C",
    file_type="variant_annotation",
    tool_used="bedtools intersect v2.31.0",
    parameters="GRCh38; IDR thresholded peaks; blacklist=hg38-blacklist.v2.bed"
)
encode_link_reference(
    experiment_accession="ENCSR...",
    reference_type="doi",
    reference_id="10.1038/ng.2383",
    description="Mahajan et al. 2014 T2D GWAS identifying rs7903146"
)
```

## Key Principles

- **LD awareness is non-negotiable.** rs7903146 is a known causal variant, but most GWAS loci contain dozens of candidates in LD. Always expand lead SNPs to LD proxies (r2 >= 0.8) or use fine-mapped credible sets before annotation.
- **The nearest gene is wrong half the time.** Enhancers skip intervening genes. Hi-C and ABC model data are essential for correct variant-to-gene assignment. Without 3D chromatin data, a variant in a TCF7L2 intron could be misattributed to that gene based on proximity alone -- here the evidence supports it, but that must be demonstrated, not assumed.
- **Tissue specificity determines relevance.** The same variant may sit in quiescent chromatin in liver but an active enhancer in islets. Always annotate in disease-relevant tissue. Document when the ideal tissue is unavailable.
- **Overlap is not causality.** Overlapping an enhancer is necessary but not sufficient. Confirming that the T allele disrupts a specific TF binding motif (e.g., TCF/LEF) requires motif analysis or MPRA validation.

## Related Skills

- **regulatory-elements** -- Classify the enhancer harboring the variant into promoter/enhancer/insulator categories.
- **histone-aggregation** -- Merge H3K27ac peaks across donors to build a comprehensive enhancer catalog before variant intersection.
- **accessibility-aggregation** -- Union ATAC-seq peaks across samples to maximize detection of the variant-overlapping accessible region.
- **hic-aggregation** -- Aggregate Hi-C loops across replicates to strengthen the enhancer-promoter contact evidence.
- **gwas-catalog** -- Retrieve all known GWAS associations for the variant locus and related traits.
- **ensembl-annotation** -- Get VEP consequences and CADD scores for the variant.
- **jaspar-motifs** -- Check whether the risk allele disrupts a TCF/LEF or other TF binding motif.
- **gtex-expression** -- Verify TCF7L2 expression in pancreas relative to other tissues.

---

*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 43 skills for genomics research*
