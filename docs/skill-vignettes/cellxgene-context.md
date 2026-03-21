# CellxGene Context -- Single-Cell Resolution for Bulk ENCODE Data

> **Category:** External Databases | **Tools Used:** `encode_search_experiments`, `encode_list_files`, `encode_search_files`
> **External API:** CellxGene Census Python SDK (`cellxgene-census`)

## What This Skill Does

Connects bulk ENCODE functional genomics data to cell-type-specific expression from the CellxGene Census (50M+ single-cell observations). When you see an H3K27ac peak in bulk pancreas, CellxGene tells you whether it is driven by acinar cells, beta cells, or duct cells.

## When to Use This

- You have a bulk ENCODE peak near a gene and need to know which cell type drives the signal.
- You want to estimate cell-type composition of an ENCODE tissue sample before downstream analysis.
- You need single-cell expression references for deconvolution of bulk ENCODE RNA-seq or ChIP-seq.

## Example Session

A scientist studying pancreatic islet regulation finds active enhancers in bulk ENCODE pancreas tissue and wants to determine which cell types are responsible.

### Step 1: Find Bulk ENCODE Enhancers in Pancreas

```
encode_search_experiments(
    assay_title="Histone ChIP-seq", target="H3K27ac",
    organ="pancreas", biosample_type="tissue"
)
```

Three released experiments returned. The scientist downloads IDR thresholded peaks and identifies an H3K27ac peak overlapping the INS promoter. The question: is this peak from beta cells (which produce insulin) or background noise from the dominant acinar population?

### Step 2: Query CellxGene Census for Cell-Type Expression

```python
import cellxgene_census

with cellxgene_census.open_soma() as census:
    adata = cellxgene_census.get_anndata(
        census, organism="Homo sapiens",
        var_value_filter="feature_name == 'INS'",
        obs_value_filter="tissue_general == 'pancreas' and disease == 'normal'",
        obs_column_names=["cell_type", "tissue", "dataset_id"]
    )

    summary = adata.to_df().join(adata.obs["cell_type"]).groupby("cell_type").agg(
        mean_expr=("INS", "mean"),
        pct_expressed=("INS", lambda x: (x > 0).mean() * 100),
        n_cells=("INS", "count")
    ).sort_values("mean_expr", ascending=False)
```

Results across 76,543 pancreas cells from 8 datasets:

| Cell Type | N Cells | Mean Expression | % Expressing |
|-----------|---------|-----------------|--------------|
| type B pancreatic cell | 12,456 | 487.3 | 92% |
| acinar cell | 45,678 | 0.1 | 2% |
| ductal cell | 8,901 | 0.0 | 0% |
| alpha cell | 9,234 | 0.0 | 0% |

INS expression is exclusive to beta cells. The bulk H3K27ac peak at INS is beta-cell-driven.

### Step 3: Estimate Bulk Signal Contribution

Beta cells represent roughly 5% of total pancreas mass. Using the CellxGene expression values:

```python
cell_fraction = 0.05   # beta cells ~5% of pancreas
sc_expression = 487.3  # mean TPM in beta cells
estimated_bulk = cell_fraction * sc_expression  # ~24 TPM
```

This estimate aligns with GTEx bulk pancreas INS expression (~400 TPM when adjusted for the actual beta cell fraction of 5-10%), confirming that a small cell population can dominate bulk signal for cell-type-specific genes.

### Step 4: Extend to Multi-Gene Islet Marker Panel

```python
genes = ["INS", "GCG", "SST", "PPY", "CFTR", "CPA1"]

with cellxgene_census.open_soma() as census:
    gene_filter = " or ".join([f"feature_name == '{g}'" for g in genes])
    adata = cellxgene_census.get_anndata(
        census, organism="Homo sapiens",
        var_value_filter=gene_filter,
        obs_value_filter="tissue_general == 'pancreas' and disease == 'normal'",
        obs_column_names=["cell_type"]
    )
```

Each gene maps to a distinct cell type: INS to beta cells, GCG to alpha cells, SST to delta cells, CPA1 to acinar cells, CFTR to ductal cells. Any bulk ENCODE peak near one of these genes can now be attributed to the corresponding cell type with high confidence.

### Step 5: Cross-Validate with ENCODE Single-Cell Data

```
encode_search_experiments(assay_title="snATAC-seq", organ="pancreas")
```

If ENCODE scATAC-seq is available for pancreas, chromatin accessibility in beta cells at the INS locus should match the CellxGene expression data. Convergent evidence -- expression from CellxGene and accessibility from ENCODE scATAC-seq in the same cell type -- is the strongest form of cell-type attribution.

## Key Principles

- **Filter aggressively.** Always restrict queries by tissue and gene to avoid downloading gigabytes of data. CellxGene Census holds 50M+ cells; unfocused queries will exhaust memory.
- **Presence/absence over quantitative comparison.** Expression levels vary across datasets due to protocol differences (10x v2 vs. v3 vs. Smart-seq2). Whether a gene is detected in a cell type is robust; exact TPM values are not.
- **Exclude disease samples by default.** Use `disease == 'normal'` unless you are specifically studying disease-altered expression. Tumor samples can dramatically change cell-type proportions and gene expression.
- **Check coverage first.** Not all tissues have deep single-cell representation. Blood, brain, lung, liver, and pancreas are well covered. Adipose, adrenal, and many connective tissues are sparse.

## Related Skills

| Skill | Use for |
|-------|---------|
| `single-cell-encode` | Working with ENCODE's own scRNA-seq and scATAC-seq data |
| `gtex-expression` | Complementary bulk tissue expression from GTEx |
| `regulatory-elements` | Characterizing the ENCODE enhancers that CellxGene contextualizes |
| `compare-biosamples` | Comparing ENCODE biosamples informed by cell-type composition |
| `epigenome-profiling` | Building tissue epigenomic profiles with cell-type context |

---
*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 43 skills for genomics research*
