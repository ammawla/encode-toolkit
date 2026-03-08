# scRNA Meta-Analysis -- Cross-Study Single-Cell Integration

> **Category:** Meta-Analysis | **Tools Used:** `encode_search_experiments`, `encode_get_experiment`, `encode_list_files`, `encode_download_files`, `encode_track_experiment`, `encode_log_derived_file`

## What This Skill Does

Guides cross-study single-cell RNA-seq meta-analysis -- combining datasets from multiple labs and platforms into a unified cell atlas with batch correction, label transfer, and reproducibility assessment. Follows the Mawla et al. 2019 framework for detection-limit-aware interpretation and cross-study marker validation.

## When to Use This

- You need to answer "what cell types exist in my tissue and what genes define them?" using data from multiple studies.
- You are building a tissue-level cell atlas by integrating scRNA-seq across donors, labs, and platforms.
- You want to assess which marker genes are reproducible across independent datasets versus study-specific artifacts.

## Example Session

A researcher integrates three human pancreatic islet scRNA-seq studies to build a reproducible cell type atlas and identify high-confidence marker genes.

### Step 1: Find and Quality-Gate scRNA-seq Experiments

```
encode_search_experiments(assay_title="scRNA-seq", organ="pancreas", limit=100)
```

| Study | Accession | Platform | Cells | Lab | Genes/cell | Mito % |
|---|---|---|---|---|---|---|
| A | ENCSR241VNQ | 10x Chromium v3 | 8,412 | Ren, UCSD | 3,200 | 6.2% |
| B | ENCSR579GTO | 10x Chromium v2 | 5,837 | Snyder, Stanford | 2,100 | 8.1% |
| C | ENCSR918KLF | Smart-seq2 | 1,204 | Gingeras, CSHL | 6,400 | 4.3% |

Three labs, three platforms, fourteen donors. All pass QC: no ERROR audits, genes/cell above threshold (>1,000 droplet / >3,000 plate), mito% < 20%, mapping rate > 80%. Smart-seq2 (Study C) has higher genes/cell but lower throughput -- integration must correct for platform-specific detection rates.

```
encode_track_experiment(accession="ENCSR241VNQ", notes="scRNA meta-analysis, pancreas")
encode_track_experiment(accession="ENCSR579GTO", notes="scRNA meta-analysis, pancreas")
encode_track_experiment(accession="ENCSR918KLF", notes="scRNA meta-analysis, pancreas")
```

### Step 2: Download Gene Quantifications

```
encode_list_files(experiment_accession="ENCSR241VNQ", file_format="h5ad", assembly="GRCh38", preferred_default=True)
encode_download_files(
    file_accessions=["ENCFF312ABQ", "ENCFF847RTN", "ENCFF503LKW"],
    download_dir="/data/islet_scrna_meta/", organize_by="experiment"
)
```

All files GRCh38, MD5-verified. For Study C (Smart-seq2), fall back to TSV gene quantifications if h5ad is unavailable.

### Step 3: Integrate with Harmony

Mixed platforms require explicit batch correction. Following Tran et al. 2020, Harmony is the recommended first choice -- fast, robust across platform types. Alternatives: scVI (best unsupervised per Luecken et al. 2022 benchmark), scANVI (semi-supervised when partial labels exist), Seurat CCA/rPCA.

Pre-integration per dataset: filter cells (nGene > 200, mito% < 20%), remove ambient RNA with CellBender, remove doublets with Scrublet, normalize with scran pooling, select 3,000 HVGs.

```python
import scanpy as sc, scanpy.external as sce

adata = sc.concat([study_a, study_b, study_c], label="study", keys=["A", "B", "C"])
sc.pp.highly_variable_genes(adata, n_top_genes=3000, batch_key="study")
sc.tl.pca(adata)
sce.pp.harmony_integrate(adata, key="study")
sc.pp.neighbors(adata, use_rep="X_pca_harmony")
sc.tl.leiden(adata, resolution=0.6)
```

Verify clusters reflect biology, not batch. Known islet cell types -- beta (INS), alpha (GCG), delta (SST), ductal (KRT19) -- should each form single clusters containing cells from all three studies.

### Step 4: Reproducibility Assessment (Mawla et al. 2019)

Identify marker genes per cell type within each study independently, then intersect:

```
Beta-cell markers across studies:
  Study A only:       312 genes
  Study B only:       287 genes
  Study C only:       198 genes
  All three studies:   41 genes  (high-confidence markers)
  Any two studies:    124 genes  (supported markers)
```

The 41 genes in all three studies are high-confidence beta-cell markers -- INS, IAPP, HADH, NPTX2 among them. Study-specific markers likely reflect detection-limit artifacts, not true biology.

Cross-contamination check: GCG detection in beta-cell clusters at 1.8% of reads falls within the 0.26-2.44% ambient RNA range (Macosko et al. 2015) and cannot be taken as evidence of bihormonal cells.

### Step 5: Pseudobulk Differential Expression

For condition comparisons, aggregate cells per donor and use DESeq2, edgeR, or limma-voom (Squair et al. 2021). Single-cell-level tests (Wilcoxon, MAST) inflate p-values by treating cells as independent observations. Require a minimum of 10 cells per cell type per donor for each pseudobulk sample.

### Step 6: Log Provenance

```
encode_log_derived_file(
    file_path="/data/islet_scrna_meta/integrated_islet_atlas.h5ad",
    source_accessions=["ENCSR241VNQ", "ENCSR579GTO", "ENCSR918KLF"],
    description="Integrated pancreatic islet scRNA-seq atlas, 3 studies, 14 donors, 15,453 cells post-QC",
    file_type="integrated_atlas",
    tool_used="Scanpy 1.10 + Harmony 0.1.0",
    parameters="HVGs=3000, harmony_key=study, leiden_resolution=0.6, CellBender ambient removal"
)
```

## Key Principles

- **Reproducibility over novelty.** A gene found in one study is a hypothesis. A gene found in all studies is a marker. Cross-study intersection is the minimum standard for claiming cell type identity genes.
- **Detection is not expression.** Most genes in scRNA-seq operate at or below the detection limit. Zero values are ambiguous -- dropout or true absence. Never interpret zeros as biological negatives without TIN or abundance context.
- **Pseudobulk for DE, always.** Aggregate to donor level and use DESeq2, edgeR, or limma-voom. Never treat individual cells as independent observations.
- **Ambient RNA contaminates.** Highly abundant transcripts (INS, GCG, ALB) leak into other cell types at 0.26-2.44% of reads. Cross-detection below this threshold is not evidence of co-expression.

## Related Skills

- **single-cell-encode** -- Finding and downloading ENCODE single-cell datasets before integration.
- **multi-omics-integration** -- Combine the scRNA-seq atlas with ENCODE epigenomic layers (ATAC-seq, histone marks).
- **cellxgene-context** -- Validate the integrated atlas against CellxGene Census expression data.
- **quality-assessment** -- Evaluate ENCODE experiment quality metrics during the QC-gating step.
- **data-provenance** -- Generate a publication-ready methods section from the logged provenance chain.

---

*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 43 skills for genomics research*
