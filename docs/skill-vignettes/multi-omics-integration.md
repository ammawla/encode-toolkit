# Multi-Omics Integration -- Building the Regulatory Landscape of Human Liver

> **Category:** Meta-Analysis | **Tools Used:** `encode_get_facets`, `encode_search_experiments`, `encode_list_files`, `encode_download_files`, `encode_track_experiment`, `encode_compare_experiments`, `encode_log_derived_file`

## What This Skill Does

Layers four or more ENCODE data types -- RNA-seq, ATAC-seq, Histone ChIP-seq, Hi-C, and WGBS -- into a single regulatory landscape for a tissue or cell type. Covers data inventory, quality gating, enhancer identification, enhancer-gene linkage, and chromatin state annotation. Follows the Mawla et al. 2023 framework for cross-assay integration.

## When to Use This

- You want to identify active enhancers by requiring convergent evidence from accessibility, histone marks, and expression.
- You are building an enhancer-gene regulatory network using Hi-C and expression data.
- You need to distinguish active, poised, and repressed elements in a specific tissue.

## Example Session

A scientist builds a complete regulatory landscape of human liver by layering five data types: H3K27ac ChIP-seq, H3K4me1 ChIP-seq, ATAC-seq, RNA-seq, and Hi-C. The goal is to identify active enhancers driving liver-specific gene expression and link them to target genes.

### Step 1: Inventory All Available Liver Data

```
encode_get_facets(organ="liver", organism="Homo sapiens")
```

Liver tissue has strong multi-omic coverage: Histone ChIP-seq (H3K27ac: 8, H3K4me1: 6, H3K4me3: 7, H3K27me3: 5), ATAC-seq (5), RNA-seq (12), Hi-C (3), TF ChIP-seq (14 targets). Sufficient for full integration.

### Step 2: Select Donor-Matched Experiments

Search each layer separately (`encode_search_experiments` per assay + target), then pick one high-quality experiment per assay, prioritizing donor-matched data from the same lab:

| Layer | Accession | Biosample | Lab | Audit |
|---|---|---|---|---|
| H3K27ac | ENCSR832RBL | liver, adult male 37y | Ren, UCSD | Clean |
| H3K4me1 | ENCSR537BCG | liver, adult male 37y | Ren, UCSD | Clean |
| ATAC-seq | ENCSR862GLC | liver, adult male 37y | Ren, UCSD | Clean |
| RNA-seq | ENCSR094PJT | liver, adult female 51y | Gingeras, CSHL | WARNING: 1 |
| Hi-C | ENCSR128LUB | liver, adult male 32y | Ren, UCSD | Clean |

H3K27ac, H3K4me1, and ATAC-seq are donor-matched -- ideal for peak-level intersection. RNA-seq and Hi-C come from different donors, acceptable for expression filtering and contact-based linkage but noted for provenance.

### Step 3: Track, Compare, and Download

Track all five experiments, then verify compatibility across the peak-layer trio:

```
encode_compare_experiments(accession1="ENCSR832RBL", accession2="ENCSR862GLC")
encode_download_files(
    file_accessions=["ENCFF421LMC", "ENCFF817BNA", "ENCFF739QPB", "ENCFF210TSQ", "ENCFF493HVL"],
    download_dir="/data/liver_multiomics", organize_by="experiment"
)
```

Compatibility confirmed: same organism, assembly (GRCh38), organ, and lab. All files MD5-verified.

### Step 4: Identify Active Enhancers

Blacklist-filter all peak sets (Amemiya et al. 2019), then require convergence of three signals:
```bash
# Active enhancers: H3K27ac AND H3K4me1 AND ATAC-accessible, NOT promoter
bedtools intersect -a h3k27ac.clean.bed -b atac.clean.bed -u \
  | bedtools intersect -a - -b h3k4me1.clean.bed -u \
  | bedtools intersect -a - -b h3k4me3.clean.bed -v \
  | bedtools window -a - -b tss_2kb.bed -w 0 -v > active_enhancers_liver.bed
```

### Step 5: Link Enhancers to Target Genes via Hi-C

Use the Activity-By-Contact framework (Fulco et al. 2019) to link enhancers to genes through chromatin contact frequency rather than proximity alone:
```bash
bedtools pairtobed -a hic_loops.bedpe -b active_enhancers_liver.bed -type either > enhancer_loops.bedpe
bedtools intersect -a enhancer_loops_other_anchor.bed -b liver_expressed_tss.bed -u > linked_targets.bed
```

Filter to genes with TPM >= 1 in liver RNA-seq. Enhancers without a Hi-C link fall back to nearest expressed gene within 500kb.

### Step 6: Results

```
H3K27ac peaks (post-blacklist):       62,413
ATAC-seq peaks (post-blacklist):      81,297
H3K4me1 peaks (post-blacklist):       74,510
Triple-positive enhancers:             26,148
  With Hi-C-supported gene link:       9,712  (37.1%)
  Nearest-gene fallback:              16,436  (62.9%)
Near liver-expressed genes (total):   24,803  (94.9%)
```

The 37.1% Hi-C linkage rate reflects the resolution limit of Hi-C data (5-25kb bins). Known liver-specific enhancer regions upstream of ALB, APOB, and CYP3A4 are captured with triple-positive signal and Hi-C-confirmed gene links, validating the approach. Super-enhancer clusters at SERPINA1 and HNF4A loci carry the strongest H3K27ac signal.

### Step 7: Log Provenance

```
encode_log_derived_file(
    file_path="/data/liver_multiomics/active_enhancers_liver.bed",
    source_accessions=["ENCSR832RBL", "ENCSR537BCG", "ENCSR862GLC", "ENCSR094PJT", "ENCSR128LUB"],
    description="Active liver enhancers: H3K27ac+H3K4me1+ATAC, TSS-subtracted, Hi-C-linked",
    file_type="enhancer_catalog", tool_used="bedtools v2.31.0",
    parameters="blacklist=hg38-blacklist.v2; intersect+pairtobed; ABC linkage; TPM>=1"
)
```

## Key Principles

- **No single assay is sufficient.** RNA-seq tells you what, ATAC-seq tells you where, histone marks tell you how, and Hi-C tells you which gene. Integration reveals the regulatory logic.
- **Require convergent evidence.** Triple-positive regions (accessible + H3K27ac + H3K4me1) are high-confidence enhancers. A single mark alone produces false positives.
- **Hi-C beats proximity.** Over 40% of enhancers skip their nearest gene (Fulco et al. 2019). Contact-based linkage is more accurate, but proximity is an acceptable fallback.
- **Matched donors reduce noise.** Always report which layers are donor-matched and which are cross-donor.
- **Report what is missing.** If a data layer is absent, state what it prevents. No H3K27me3 means no bivalent state calls. No Hi-C means distance-based gene links only.

## Related Skills

- **integrative-analysis** -- Two- to three-layer integration when full multi-omics coverage is not available.
- **regulatory-elements** -- Classify integrated peaks into promoters, enhancers, and insulators.
- **histone-aggregation** / **hic-aggregation** -- Merge peaks or loops across donors before overlay.
- **epigenome-profiling** -- Broader characterization including ChromHMM segmentation.
- **visualization-workflow** -- Publication-quality multi-track figures from the integrated landscape.

---

*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 43 skills for genomics research*
