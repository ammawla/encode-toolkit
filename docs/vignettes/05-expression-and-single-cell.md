# Gene Expression Context: From Bulk to Single-Cell

> This vignette shows how to explore gene expression data in ENCODE and connect
> it to external resources like GTEx and CellxGene for comprehensive expression analysis.

## Scenario

You are investigating gene expression patterns in human pancreatic islets and want to
understand both bulk tissue and single-cell resolution data available through ENCODE.
Your goal is to build a complete picture -- from tissue-level RNA-seq through
single-nucleus profiling -- and connect ENCODE data to external expression atlases.

## Step 1: Find RNA-seq Experiments

**You ask Claude:**
> "What RNA-seq data exists for human pancreas in ENCODE?"

**Claude calls:** `encode_search_experiments(assay_title="total RNA-seq", organ="pancreas")`

**Result:** 11 total RNA-seq experiments. Claude also checks the full picture
with `encode_get_facets(organ="pancreas")` and reports the expression landscape:

| Assay | Experiments | What It Measures |
|---|---|---|
| total RNA-seq | 11 | All transcripts including non-coding |
| polyA plus RNA-seq | 7 | Mature mRNA (protein-coding biased) |
| long read RNA-seq | 3 | Full-length isoforms (PacBio/ONT) |
| microRNA-seq | 9 | Small regulatory RNAs |
| PRO-cap | 8 | Active transcription initiation |

**What this tells you:** Pancreas has solid bulk expression coverage. The 11 total
RNA-seq experiments capture both coding and non-coding transcripts. The 3 long read
RNA-seq experiments are particularly valuable for resolving pancreatic isoforms --
alternative splicing in insulin (INS) and glucagon (GCG) has functional consequences
that short reads miss.

## Step 2: Find Single-Cell Data

**You ask Claude:**
> "Are there single-cell RNA-seq experiments for pancreas?"

**Claude calls:** `encode_get_facets(organ="pancreas")`

**Result (single-cell/nucleus assays):**
```
snRNA-seq:   6 experiments
snATAC-seq: 17 experiments
```

**What this tells you:** ENCODE has single-nucleus data for pancreas, not single-cell.
The distinction matters: snRNA-seq captures nuclear transcripts and may underrepresent
cytoplasmic mRNAs like insulin, which is heavily translated and localized to the
cytoplasm in beta cells. The 17 snATAC-seq experiments provide matched chromatin
accessibility at single-cell resolution -- useful for linking regulatory elements
to cell-type-specific expression.

Note the absence of 10x multiome for pancreas. If you need joint RNA + ATAC from
the same cells, you will need to integrate snRNA-seq and snATAC-seq computationally
(tools like ArchR or Signac support this).

## Step 3: GTEx Expression Context

**You ask Claude:**
> "What does GTEx show for pancreas gene expression?"

**Claude uses the gtex-expression skill** to guide you through querying the
GTEx Portal REST API. This skill provides the endpoints, parameters, and
interpretation framework -- it does not call GTEx directly.

**What Claude explains:**

- **GTEx Portal API** (`https://gtexportal.org/api/v2/`) provides median gene
  expression (TPM) across 54 human tissues from 948 donors.
- **Pancreas-enriched genes.** Query `expression/medianGeneExpression` filtered
  to pancreas. Genes with median TPM >10 in pancreas and <1 in most other tissues
  (e.g., INS, GCG, PRSS1, CPA1) define tissue identity.
- **Cross-tissue comparison.** GTEx provides population-scale expression context
  that ENCODE lacks. ENCODE provides the regulatory context (histone marks,
  accessibility) that GTEx lacks.
- **Key reference:** GTEx Consortium. Science 369, 1318-1330 (2020).

**Practical integration:** Use GTEx to identify pancreas-enriched genes, then
search ENCODE for the regulatory elements (H3K27ac, ATAC-seq peaks) near those
genes in pancreas tissue.

## Step 4: Single-Cell Atlas Context

**You ask Claude:**
> "What single-cell atlases cover pancreatic islets?"

**Claude uses the cellxgene-context skill** to guide you through the CZ CellxGene
Census, the largest standardized collection of single-cell datasets.

**What Claude explains:**

- **Pancreas datasets** in CellxGene include HPAP, Tabula Sapiens pancreas, and
  multiple islet-focused studies with standardized Cell Ontology annotations.
- **Established cell type markers** for islets:
  Beta: INS, IAPP, MAFA, NKX6-1 | Alpha: GCG, ARX, IRX2 |
  Delta: SST, HHEX | Ductal: KRT19, SOX9 | Acinar: PRSS1, CPA1
- **Key reference:** Megill et al., bioRxiv (2021).

**Practical integration:** Use CellxGene cell type proportions to deconvolve
ENCODE bulk RNA-seq, estimating how much of each cell type contributed to the
bulk signal. Bulk pancreas is ~95% exocrine -- islet transcripts are diluted.

## Step 5: Plan a Cross-Study Integration

**You ask Claude:**
> "How do I integrate scRNA-seq data across multiple studies?"

**Claude uses the scrna-meta-analysis skill** to guide you through a
multi-study integration workflow.

**What Claude explains:**

1. **Dataset QC and cell filtering.** Per-dataset thresholds: minimum 200-500
   genes per cell, maximum 5-15% mitochondrial fraction, doublet detection
   (Scrublet or DoubletFinder) applied per dataset before merging.

2. **Integration methods** for cross-study batch correction:
   - **Harmony** (Korsunsky et al., 2019) -- fast, works within a shared PCA
     space, good for moderate batch effects
   - **scVI** (Lopez et al., 2018) -- deep generative model, handles complex
     batch structures across platforms (10x v2 vs v3, Smart-seq2)
   - **Seurat v5 integration** (Hao et al., 2024) -- bridge integration and
     sketch-based workflows for large atlases

3. **Cross-study cell type annotation.** Transfer labels from a well-annotated
   reference (e.g., Tabula Sapiens) using scANVI or Seurat label transfer.
   Validate against known marker genes and report confidence scores per cell.

4. **Connecting back to ENCODE.** Once you have cell-type-resolved expression,
   use ENCODE's 17 snATAC-seq experiments for pancreas to identify cell-type-
   specific regulatory elements matched to your scRNA-seq clusters.

## Putting It Together

The complete workflow links three layers of evidence:

```
ENCODE bulk RNA-seq (11 total, 7 polyA+)
    --> Tissue-level expression baseline across donors

ENCODE snRNA-seq (6) + snATAC-seq (17)
    --> Cell-type-resolved expression and accessibility

External: GTEx (948 donors) + CellxGene (multiple atlases)
    --> Cross-tissue context + standardized cell type annotations
```

This layered approach moves from "which genes are expressed in pancreas" (GTEx +
ENCODE bulk) to "which cell types express them" (CellxGene + ENCODE snRNA-seq) to
"what regulatory elements control them" (ENCODE snATAC-seq + histone ChIP-seq).

## Skills Demonstrated

- **search-encode** -- Finding bulk and single-cell RNA-seq experiments by organ
  and assay type, using facets to survey the full expression landscape
- **single-cell-encode** -- Understanding ENCODE's single-nucleus data and its
  relationship to single-cell atlases
- **gtex-expression** -- Guidance for querying GTEx Portal API for tissue-level
  expression context
- **cellxgene-context** -- Guidance for querying CZ CellxGene Census for curated
  single-cell datasets and cell type annotations
- **scrna-meta-analysis** -- Planning cross-study integration with Harmony, scVI,
  or Seurat and annotation transfer workflows

## What's Next

- [Regulatory Element Discovery](06-regulatory-elements.md) -- Use ENCODE
  accessibility and histone data to identify enhancers and promoters
- [3D Genome & Methylation](07-3d-genome-and-methylation.md) -- Explore
  chromatin conformation and DNA methylation in pancreatic tissue
