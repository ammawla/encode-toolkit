# Batch Analysis -- Detecting and Correcting Batch Effects Across Labs

> **Category:** Analysis | **Tools Used:** `encode_search_experiments`, `encode_track_experiment`, `encode_compare_experiments`, `encode_batch_download`, `encode_log_derived_file`

## What This Skill Does

Guides systematic batch operations across multiple ENCODE experiments: discovery, quality screening, download, pairwise comparison, batch effect detection, and correction. Essential when combining data from different labs, donors, or sequencing platforms where technical variation can mask or mimic biological signal.

## When to Use This

- You are combining 5+ experiments from multiple ENCODE production labs and need to verify that technical variation does not dominate.
- You need a structured QC-to-correction workflow before integrative analysis of cross-lab datasets.

## Example Session

A scientist combines four H3K27ac ChIP-seq experiments on human liver tissue from two ENCODE labs (Ren/UCSD and Bernstein/Broad) to build a unified active enhancer catalog. Before merging peaks, they must confirm samples cluster by biology, not by lab of origin.

### Step 1: Search and Screen Experiments

```
encode_search_experiments(
    assay_title="Histone ChIP-seq", target="H3K27ac",
    organ="liver", biosample_type="tissue", limit=50
)
```

Four experiments pass initial review:

| Accession | Biosample | Lab | Replicates | Audit |
|---|---|---|---|---|
| ENCSR241WNM | liver, adult male 37y | Ren, UCSD | 2 | Clean |
| ENCSR917GGS | liver, adult female 53y | Ren, UCSD | 2 | WARNING: 1 |
| ENCSR638LQC | liver, adult male 60y | Bernstein, Broad | 2 | Clean |
| ENCSR302RJR | liver, adult female 41y | Bernstein, Broad | 2 | WARNING: 1 |

All four are GRCh38 with 2 biological replicates and no ERROR audits -- Tier 1/2 quality. Key batch variable: two samples per lab.

### Step 2: Track and Compare Pairwise

```
encode_track_experiment(accession="ENCSR241WNM", notes="Liver H3K27ac batch -- Ren lab")
encode_track_experiment(accession="ENCSR917GGS", notes="Liver H3K27ac batch -- Ren lab")
encode_track_experiment(accession="ENCSR638LQC", notes="Liver H3K27ac batch -- Bernstein lab")
encode_track_experiment(accession="ENCSR302RJR", notes="Liver H3K27ac batch -- Bernstein lab")

encode_compare_experiments(accession1="ENCSR241WNM", accession2="ENCSR638LQC")
# Result: Warning -- different labs (Ren vs Bernstein). Check for batch effects.
```

All six pairwise checks run. Cross-lab pairs flag the lab difference; same-lab pairs return compatible.
### Step 3: Download Signal Tracks

```
encode_batch_download(
    assay_title="Histone ChIP-seq", target="H3K27ac", organ="liver",
    file_format="bigWig", output_type="fold change over control",
    assembly="GRCh38", preferred_default=True,
    download_dir="/data/liver_h3k27ac/signal/", organize_by="experiment", dry_run=True)
# Dry run: 4 files, 2.8 GB total. Proceed with dry_run=False.
```

### Step 4: Detect Batch Effects with PCA and Correlation

Build a genome-wide signal matrix with deepTools:

```bash
multiBigwigSummary bins \
    -b ENCSR241WNM.bw ENCSR917GGS.bw ENCSR638LQC.bw ENCSR302RJR.bw \
    --labels Ren_M37 Ren_F53 Broad_M60 Broad_F41 \
    --binSize 10000 -o liver_h3k27ac_matrix.npz -p 8

plotPCA -in liver_h3k27ac_matrix.npz --plotFile liver_pca.pdf
plotCorrelation -in liver_h3k27ac_matrix.npz --corMethod pearson --whatToPlot heatmap --plotFile liver_correlation.pdf
```

PC1 separates the two labs rather than donor sex or age. Pearson correlations are higher within-lab (r=0.95) than across-lab (r=0.82) -- a clear batch effect (Leek et al. 2010).

### Step 5: Correct with limma removeBatchEffect

The design is balanced (2 samples per lab, no confounding), so correction is valid:

```r
library(limma)
signal_matrix <- read.delim("liver_h3k27ac_bins.tsv", row.names=1)
batch <- factor(c("Ren", "Ren", "Broad", "Broad"))
sex   <- factor(c("M", "F", "M", "F"))

corrected <- removeBatchEffect(
    as.matrix(signal_matrix), batch=batch, design=model.matrix(~sex)
)
```

After correction, correlations converge across labs (r=0.90-0.93) and PCA shows no lab-driven separation. The MA plot mean shifts from log2FC=0.4 to near zero.

### Step 6: Log Provenance

```
encode_log_derived_file(
    file_path="/data/liver_h3k27ac/liver_h3k27ac_corrected_matrix.tsv",
    source_accessions=["ENCSR241WNM", "ENCSR917GGS", "ENCSR638LQC", "ENCSR302RJR"],
    description="Batch-corrected H3K27ac signal matrix, 4 liver samples, 2 labs",
    tool_used="limma::removeBatchEffect v3.56.2; deepTools v3.5.4",
    parameters="binSize=10000; batch=lab; design=~sex; post-correction r=0.90-0.93")
```

## Key Principles

- **Detect before you correct.** Always run PCA and correlation first. If samples already cluster by biology, correction is unnecessary and can remove real signal.
- **Balanced designs are correctable; confounded designs are not.** If all samples of condition A come from Lab 1 and all of condition B from Lab 2, no algorithm can disentangle lab from biology (Leek et al. 2010).
- **Preserve biology in the model matrix.** Include biological variables of interest in the `design` argument of `removeBatchEffect` so they are protected from removal.

## Related Skills

- **integrative-analysis** -- Next step after batch correction; combines corrected data into unified peak catalogs.
- **quality-assessment** -- Deep QC on individual experiments flagged during batch screening.
- **visualization-workflow** -- Publication-ready PCA plots, MA plots, and correlation heatmaps.

---

*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 43 skills for genomics research*
