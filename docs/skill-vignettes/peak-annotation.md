# Peak Annotation -- From Peaks to Genes, cCREs, and Enhancer-Gene Links

> **Category:** Analysis | **Tools Used:** `encode_search_experiments`, `encode_list_files`, `encode_download_files`, `encode_search_files`, `encode_log_derived_file`

## What This Skill Does

Annotates ENCODE peak calls with genomic features (promoter, intron, intergenic), links distal peaks to target genes using GREAT and the ABC model, and overlaps peaks with ENCODE SCREEN cCREs. Turns a BED file of coordinates into a biologically interpretable catalog.

## When to Use This

- You have ATAC-seq or ChIP-seq peaks and need to know what genes they regulate and where they sit in the genome.
- You want to link distal enhancer peaks to target genes using the Activity-by-Contact model rather than nearest-gene assignment.
- You need to anchor your peaks against the ENCODE cCRE registry to classify known regulatory elements.

## Example Session

A scientist annotates ATAC-seq peaks from human pancreatic islets using three complementary strategies: GREAT for functional enrichment, the ABC model for enhancer-gene linking, and SCREEN cCRE overlap.

### Step 1: Download ATAC-seq Peaks

```
encode_search_experiments(
    assay_title="ATAC-seq", organ="pancreas",
    biosample_term_name="islet of Langerhans", status="released"
)
encode_list_files(
    experiment_accession="ENCSR162FMV", file_format="bed",
    output_type="IDR thresholded peaks", assembly="GRCh38", preferred_default=True
)
encode_download_files(
    file_accessions=["ENCFF441ZFQ"], download_dir="/data/islet_atac/peaks"
)
```

Remove blacklisted regions before any annotation (Amemiya et al. 2019):

```bash
bedtools intersect -a ENCFF441ZFQ.bed -b hg38-blacklist.v2.bed -v > islet_atac_clean.bed
# 84,219 peaks remain
```

### Step 2: GREAT Functional Enrichment

GREAT (McLean et al. 2010) assigns biological meaning to non-coding regions using a basal-plus-extension rule that accounts for gene density:

```r
library(rGREAT)
peaks <- rtracklayer::import("islet_atac_clean.bed")
great_job <- submitGreatJob(peaks, species = "hg38", version = "4.0.4")
go_bp <- getEnrichmentTables(great_job, ontology = "GO Biological Process")
```

Top terms: regulation of insulin secretion (4.8x, FDR 1.2e-18), glucose homeostasis (3.9x, FDR 8.7e-14), pancreas development (5.1x, FDR 2.3e-11). GREAT confirms peaks are enriched near islet-relevant genes -- a sanity check that the data reflects expected biology.

### Step 3: ABC Model for Enhancer-Gene Linking

For distal peaks (>3 kb from any TSS), nearest-gene assignment is unreliable. The ABC model (Fulco et al. 2019) predicts enhancer-gene links by combining accessibility signal with Hi-C contact frequency:

```
encode_search_files(
    output_type="element gene regulatory interaction predictions",
    organ="pancreas", assembly="GRCh38", preferred_default=True
)
```

```bash
bedtools intersect -a islet_atac_clean.bed -b abc_predictions.tsv -wa -wb \
    > atac_abc_links.tsv
awk '$NF >= 0.015' atac_abc_links.tsv > atac_abc_high_conf.tsv
# 12,847 high-confidence peak-gene links (ABC score >= 0.015)
```

Roughly 40% of ABC links skip the nearest gene entirely (Fulco et al. 2019) -- this is the key advantage over proximity-based methods.

### Step 4: SCREEN cCRE Overlap

ENCODE SCREEN catalogs 926,535 human cCREs classified by biochemical signature. Overlapping ATAC peaks with cCREs reveals which are known regulatory elements:

```bash
bedtools intersect -a islet_atac_clean.bed -b GRCh38-cCREs.bed -wa -wb > atac_ccre_overlap.tsv
```

| cCRE Type | Peaks | Fraction |
|---|---|---|
| dELS (distal enhancer-like) | 31,402 | 37.3% |
| pELS (proximal enhancer-like) | 18,944 | 22.5% |
| PLS (promoter-like) | 14,738 | 17.5% |
| CTCF-only | 6,329 | 7.5% |
| No cCRE overlap | 12,806 | 15.2% |

The 15% without cCRE overlap may represent islet-specific regulatory elements absent from the pan-tissue SCREEN catalog -- flag these for follow-up rather than discarding them.

### Step 5: Log Provenance

```
encode_log_derived_file(
    file_path="/data/islet_atac/atac_abc_high_conf.tsv",
    source_accessions=["ENCSR162FMV"],
    description="Islet ATAC peaks with ABC enhancer-gene links and SCREEN cCRE overlap",
    tool_used="bedtools v2.31.0, rGREAT v2.0.0, SCREEN v3 cCREs",
    parameters="blacklist=hg38-blacklist.v2.bed; GREAT v4.0.4; ABC>=0.015"
)
```

## Key Principles

- **Use all three layers together.** GREAT tells you WHAT pathways the peaks regulate, ABC tells you WHICH gene each distal peak contacts, and cCRE overlap tells you WHETHER a peak is a known regulatory element.
- **ABC beats nearest-gene for distal peaks.** Nearest-gene annotation is acceptable for promoter peaks but misleading for enhancers where the target gene is often not the closest one.
- **Report the cCRE gap.** Peaks without cCRE overlap are biologically interesting -- they may be tissue-specific elements absent from the pan-tissue catalog.

## Related Skills

- **regulatory-elements** -- Identify cCREs using ENCODE biochemical signals before overlapping with your peaks.
- **motif-analysis** -- Discover TF motifs within annotated peak categories (promoter vs enhancer peaks yield different motif vocabularies).
- **histone-aggregation** -- Build union peak catalogs to annotate across multiple donors.
- **visualization-workflow** -- Publication-quality annotation plots and TSS distance histograms.
- **integrative-analysis** -- Combine annotation results with expression data to validate enhancer-gene predictions.

---

*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 43 skills for genomics research*
