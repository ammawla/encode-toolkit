# Single-Cell ENCODE -- Cell-Type-Resolved Regulatory Analysis

> **Category:** Workflow | **Tools Used:** `encode_search_experiments`, `encode_get_facets`, `encode_list_files`, `encode_search_files`, `encode_track_experiment`, `encode_log_derived_file`, `encode_link_reference`

## What This Skill Does

Finds and works with ENCODE single-cell and single-nucleus data (scRNA-seq, scATAC-seq). Covers searching for single-cell experiments, understanding ENCODE's single-cell file formats, quality assessment for sparse single-cell data, cross-study reproducibility pitfalls, and integration strategies using Harmony, scVI, and Seurat for combining datasets or linking single-cell resolution to ENCODE's deep bulk catalog.

## When to Use This

- You need to find scRNA-seq or scATAC-seq experiments for a specific tissue in ENCODE.
- You want to understand what file types ENCODE provides for single-cell data (fragment files, count matrices, h5ad).
- You are planning to integrate single-cell datasets across studies or platforms and need to account for detection-limit artifacts and batch effects.
- You want to connect cell-type-specific accessibility from scATAC-seq to bulk histone mark peaks for cell-type-resolved enhancer annotation.

## Example Session

### Scientist's Request

> "I want to find single-cell RNA-seq and ATAC-seq data for human brain in ENCODE. I need to integrate across studies and eventually overlay cell-type peaks onto bulk H3K27ac data."

### Step 1: Survey Single-Cell Availability

Check what single-cell data exists for brain before committing to a search strategy.

```
encode_get_facets(assay_title="single-cell RNA sequencing assay", organ="brain")
encode_get_facets(assay_title="single-cell ATAC-seq", organ="brain")
```

This reveals whether ENCODE has brain single-cell data, which biosample types are represented (tissue vs. organoid vs. primary cell), and which labs contributed.

### Step 2: Search for Experiments

```
encode_search_experiments(assay_title="single-cell RNA sequencing assay", organ="brain", biosample_type="tissue", status="released", limit=50)
encode_search_experiments(assay_title="single-cell ATAC-seq", organ="brain", biosample_type="tissue", status="released", limit=50)
```

If results are sparse, broaden: `encode_search_experiments(search_term="single cell RNA", organ="brain", limit=50)`. Record the platform for each experiment (10X Chromium v2/v3, Smart-seq2, Drop-seq) -- platform determines detection rates, coverage bias, and integration difficulty.

### Step 3: Understand ENCODE Single-Cell File Structure

For a scRNA-seq experiment, list the processed outputs:

```
encode_list_files(experiment_accession="ENCSR...", assembly="GRCh38", preferred_default=True)
```

ENCODE provides several file tiers for scRNA-seq: raw FASTQs with cell barcodes and UMIs, gene quantification matrices (TSV), filtered feature-barcode matrices (post-QC), and h5ad files when available. For scATAC-seq, the critical file is the **fragment file** (TSV with cell-barcode assignments) -- this is the primary input for ArchR and Signac, not per-cell peak calls.

scATAC-seq data is extremely sparse (~2-5% non-zero entries in the peak-cell matrix). This motivates gene activity scoring and pseudo-bulk aggregation rather than per-peak single-cell analysis.

### Step 4: Assess Quality and Cross-Study Comparability

Track passing experiments and note platform details:

```
encode_track_experiment(accession="ENCSR...", notes="scRNA-seq, brain cortex, 10X Chromium v3")
```

Before combining datasets, check for detection-rate mismatches. 10X Chromium detects 1,500-4,000 genes per cell; Smart-seq2 detects 4,000-8,000. If rates differ more than 2x between studies, batch effects will dominate biological signal. Cross-study scRNA-seq comparisons show that only ~1-2% of heterogeneity-driving genes replicate across independent studies of the same tissue (Mawla & Huising 2019). Clusters that align with study of origin rather than cell type indicate failed integration.

### Step 5: Integrate Across Studies

**Harmony** (recommended first-line): Fast iterative soft clustering in PCA space. Works well across platforms and scales to large atlases. Run Harmony on the PCA embedding with study/batch as the grouping variable.

**scVI** (deep generative model): Learns a latent representation that separates biological from technical variation. Preferred for large-scale atlas construction (>200k cells) or when batch effects are severe.

**Seurat CCA/RPCA**: Canonical correlation analysis identifies shared structure across datasets. Use RPCA for datasets exceeding 100k cells. Best when cell types overlap substantially between studies.

After integration, evaluate with kBET (batch mixing), iLISI (integration quality), and cLISI (cell-type separation). UMAP colored by study origin should show intermingling within clusters, not study-driven segregation.

### Step 6: Overlay onto Bulk ENCODE Epigenomics

This is where ENCODE's single-cell data becomes most powerful -- connecting cell-type resolution to the deep bulk catalog.

```
encode_search_experiments(assay_title="Histone ChIP-seq", target="H3K27ac", organ="brain", biosample_type="tissue", limit=50)
encode_search_files(output_type="candidate Cis-Regulatory Elements", assembly="GRCh38", organ="brain")
```

Aggregate scATAC-seq data into pseudo-bulk peaks per cell type (using ArchR or Signac), then intersect with bulk H3K27ac peaks. A bulk H3K27ac peak overlapping a neuron-specific scATAC-seq peak is likely a neuron-specific active enhancer. Regions accessible in astrocytes but not neurons point to glial regulatory elements invisible in bulk.

### Step 7: Log Provenance

```
encode_log_derived_file(
    file_path="/data/brain_sc/integrated_atlas.h5ad",
    source_accessions=["ENCSR...", "ENCSR...", "ENCSR..."],
    description="Integrated scRNA-seq + scATAC-seq atlas, human brain cortex, Harmony batch correction",
    file_type="integrated_atlas", tool_used="Scanpy 1.10 + Harmony + ArchR 1.0.3",
    parameters="HVGs=3000; harmony_key=study; resolution=0.8; blacklist=hg38-blacklist.v2.bed")
```

## Key Principles

- **Never treat 10X and Smart-seq2 cells as equivalent** without batch correction. Coverage patterns and detection rates are fundamentally different.
- **Validate single-cell markers against bulk.** Genes detected in bulk RNA-seq but absent in single-cell are likely dropout, not true absence. Genes appearing only in single-cell without bulk support warrant skepticism.
- **Pseudo-bulk before differential expression.** Aggregating cells into pseudo-bulk profiles per donor and cell type, then running standard bulk DE tools, outperforms single-cell-level tests for known cell types.
- **Apply ENCODE Blacklist v2** to all scATAC-seq data before analysis. Blacklist regions inflate per-cell quality metrics and create artifactual peaks.

## Related Skills

- **scrna-meta-analysis** -- Deep cross-study meta-analysis workflow with full batch correction and reproducibility assessment.
- **quality-assessment** -- Evaluate ENCODE audit flags and QC metrics for single-cell experiments.
- **integrative-analysis** -- Combine single-cell cell-type peaks with bulk histone and expression layers.
- **accessibility-aggregation** -- Build union open chromatin catalogs from pseudo-bulk scATAC-seq peaks.
- **cellxgene-context** -- Cross-reference cell type annotations with CellxGene single-cell atlases.
- **regulatory-elements** -- Classify cell-type-specific peaks into enhancers, promoters, and insulators.

---

*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 43 skills for genomics research*
