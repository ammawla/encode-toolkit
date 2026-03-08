# Transcription Factor Binding and Regulatory Element Analysis

> This vignette demonstrates how to characterize regulatory elements using ENCODE
> TF ChIP-seq data, chromatin state classification, and motif analysis tools. All
> ENCODE output shown is from real API queries against encodeproject.org.

## Scenario

You are studying transcription factor binding in human pancreas and want to identify
active regulatory elements, determine which TFs bind them, and connect binding to
candidate target genes.

## Step 1: Survey TF ChIP-seq Coverage

**You ask Claude:**
> "What TF ChIP-seq experiments exist for human pancreas?"

**Claude calls:** `encode_get_facets(assay_title="TF ChIP-seq", organ="pancreas")`

**Result (target facet):**
```json
{
  "target.label": [
    { "term": "CTCF", "count": 16 },
    { "term": "POLR2A", "count": 5 },
    { "term": "REST", "count": 3 },
    { "term": "POLR2AphosphoS5", "count": 1 },
    { "term": "SIN3A", "count": 1 },
    { "term": "TCF7L2", "count": 1 }
  ]
}
```

**What this tells you:** Pancreas has 25 TF ChIP-seq experiments across 6 targets.
CTCF dominates (16) as a ubiquitous insulator profiled across ENCODE tissues. POLR2A
marks active transcription. REST represses neuronal genes. TCF7L2 is the standout: a
Wnt effector and top type 2 diabetes GWAS hit (Grant et al. 2006, Nat Genet).

Lineage-defining pancreatic TFs (PDX1, NKX6.1, MAFB, FOXA2, HNF1A) are absent from
ENCODE pancreas. Supplement with the Parker lab islet regulome (Pasquali et al. 2014,
Nat Genet) or HPAP for these factors.

## Step 2: Classify Regulatory Elements by Chromatin State

**You ask Claude:**
> "How do I identify active regulatory elements in pancreas using histone marks?"

**Claude uses the regulatory-elements skill** to guide chromatin state classification
based on combinatorial histone patterns (Kundaje et al. 2015, Nature; Ernst and
Kellis 2012, Nat Methods):

| Element class | Histone signature | Biological interpretation |
|---|---|---|
| Active promoter | H3K4me3 + H3K27ac | Transcription initiation site, open chromatin |
| Active enhancer | H3K4me1 + H3K27ac | Distal regulatory element driving expression |
| Poised enhancer | H3K4me1 only | Primed for activation, silent in current state |
| Primed promoter | H3K4me3 only | Promoter without active transcription |
| Polycomb-repressed | H3K27me3 | Silenced by PRC2, may be bivalent with H3K4me3 |
| Heterochromatin | H3K9me3 | Constitutive silencing, repeats, pericentromeric |
| Transcribed body | H3K36me3 | Gene body of actively transcribed genes |

**ENCODE pancreas coverage for these marks:**
- H3K4me3 (16), H3K27ac (15), H3K4me1 (13) -- full enhancer/promoter classification
- H3K27me3 (14), H3K9me3 (14) -- both repressive compartments
- H3K36me3 (12) -- transcribed gene bodies

This constitutes a complete six-mark reference epigenome. Retrieve preferred default
BED files for each mark and run ChromHMM, or use histone-aggregation to merge peaks
across donors before segmentation.

**Accessibility confirmation.** Overlay ATAC-seq (10) or DNase-seq (31) peaks on
chromatin states. Active elements should coincide with accessible chromatin. Regions
with active marks but no accessibility may reflect antibody artifacts or cell-type
heterogeneity in bulk tissue.

## Step 3: Motif Enrichment in Regulatory Elements

**You ask Claude:**
> "What TF motifs are enriched in pancreatic active enhancers?"

**Claude uses the regulatory-elements skill** to outline the motif workflow. After
defining active enhancers (H3K4me1 + H3K27ac intersected with ATAC-seq), perform
motif enrichment:

**De novo discovery:** HOMER `findMotifsGenome.pl` (Heinz et al. 2010, Mol Cell)
finds enriched motifs against GC-matched background. MEME-ChIP (Machanick and Bailey
2011, Bioinformatics) combines de novo discovery with CentriMo central enrichment.

**Known motif scanning:** Score against JASPAR 2024 PWMs (Rauluseviciute et al. 2024,
Nucleic Acids Res) or HOCOMOCO v12 using AME.

**Expected pancreatic TF motifs in active enhancers:**

| TF | Motif class | Role in pancreas |
|---|---|---|
| PDX1 | Homeodomain | Master regulator of pancreas development and beta cell identity |
| NKX6.1 | Homeodomain | Beta cell maturation and maintenance |
| FOXA2 | Forkhead | Pioneer factor, opens chromatin at pancreatic enhancers |
| MAFB | bZIP | Alpha and beta cell differentiation |
| HNF1A | Homeodomain | Hepatocyte nuclear factor, MODY3 gene |
| TCF7L2 | HMG box | Wnt signaling effector, type 2 diabetes GWAS locus |
| NEUROD1 | bHLH | Endocrine cell differentiation |
| CTCF | Zinc finger | Insulator, topological domain boundaries |

FOXA2 is particularly informative: as a pioneer factor it binds nucleosomal DNA
directly, and enrichment at poised enhancers (H3K4me1 only) suggests elements
primed for activation by lineage signals.

## Step 4: Annotate Peaks to Candidate Target Genes

**You ask Claude:**
> "Which genes are regulated by these pancreatic enhancers?"

**Claude uses the regulatory-elements skill** for peak-to-gene assignment. Enhancers
act over long distances (up to 1 Mb), so nearest-gene assignment is insufficient.
Approaches in order of confidence:

1. **ENCODE cCRE-gene links** -- SCREEN provides cCREs with gene links from Hi-C,
   CRISPRi, and eQTL data (screen.encodeproject.org).
2. **3D chromatin contact** -- intact Hi-C loop calls (5 pancreas experiments) connect
   enhancers to promoters. Use hic-aggregation to merge loops across donors.
3. **GREAT** (McLean et al. 2010, Nat Biotechnol) -- regulatory domain assignment.
4. **ABC model** (Fulco et al. 2019, Nat Genet) -- combines H3K27ac signal with Hi-C
   contact frequency to predict enhancer-gene pairs.

Expect ~5% promoter, ~30% intronic, ~40% intergenic -- confirming distal identity.

## Step 5: Integrate TF Binding with Regulatory Elements

**You ask Claude:**
> "Overlay CTCF binding on the regulatory element map."

**Claude calls:** `encode_search_experiments(assay_title="TF ChIP-seq", organ="pancreas", target="CTCF")`

With 16 CTCF experiments across donors, build a consensus binding map. CTCF
delineates TAD boundaries and constrains enhancer-promoter interactions:

- **CTCF at active promoters** -- boundary elements at TSSs, common at housekeeping genes.
- **CTCF between enhancer-promoter clusters** -- insulator function blocking spread.
- **CTCF at poised enhancers** -- elements potentially awaiting domain reorganization.

For the single TCF7L2 experiment, intersect peaks with active enhancers to find
diabetes-associated regulatory elements. TCF7L2 at H3K27ac-marked, accessible
enhancers represents high-confidence sites for variant analysis.

## Quality Considerations

- **Replication.** Most pancreas TF ChIP-seq is unreplicated. Cross-donor overlap
  serves as a biological replicate proxy.
- **Peak format.** TF ChIP-seq uses narrowPeak (point-source). Never use broadPeak.
- **Background model.** Motif enrichment needs GC-matched background or ATAC-seq
  peaks lacking the histone mark of interest.
- **Cell-type heterogeneity.** Bulk pancreas is >95% exocrine -- motif results
  reflect exocrine dominance. Use snATAC-seq (17 experiments) for cell-type resolution.

## Skills Demonstrated

- **search-encode** -- Surveying TF ChIP-seq coverage and available targets
- **regulatory-elements** -- Chromatin state classification, motif analysis workflow,
  and peak-to-gene assignment strategies
- **histone-aggregation** -- Merging peaks across donors for consensus mark maps
- **hic-aggregation** -- Using chromatin contacts for enhancer-gene linking

## What's Next

- [Variant & Disease](04-variant-and-disease.md) -- Overlay GWAS variants on the
  regulatory elements and TF binding sites identified here
- [Cross-Reference & Integration](09-cross-reference-and-integration.md) -- Link
  ENCODE experiments to PubMed, GEO, and external regulome datasets
- [Epigenomics Workflow](03-epigenomics-workflow.md) -- Build the full chromatin
  landscape that feeds into this regulatory element classification
