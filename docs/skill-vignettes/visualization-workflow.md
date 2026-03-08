# Visualization Workflow -- Publication-Quality Figures from ENCODE Data

> **Category:** Analysis | **Tools Used:** `encode_search_files`, `encode_download_files`, `encode_log_derived_file`

## What This Skill Does

Guides creation of publication-quality visualizations from ENCODE data -- deepTools heatmaps, IGV locus screenshots, UCSC track hubs, and static plots. Visualization is an analytical step: it reveals patterns invisible in summary statistics and validates computational findings at individual loci.

## Example Session

A scientist visualizes H3K27ac, ATAC-seq, and RNA-seq signal at active enhancers in human pancreas to show that enhancer accessibility corresponds with nearby gene expression.

### Step 1: Find and Download Signal Files

```
encode_search_files(
    file_format="bigWig", output_type="fold change over control",
    assay_title="Histone ChIP-seq", target="H3K27ac",
    organ="pancreas", biosample_type="tissue", assembly="GRCh38"
)
```

Repeat for ATAC-seq and RNA-seq. All files must be GRCh38 fold-change-over-control so they are directly comparable.

```
encode_download_files(
    file_accessions=["ENCFF735QAP", "ENCFF291DHB", "ENCFF803KQJ"],
    download_dir="/data/viz_pancreas", organize_by="flat"
)
```

### Step 2: Build the deepTools Signal Matrix at H3K27ac Peak Summits

```bash
computeMatrix reference-point \
    -S H3K27ac_fc.bigWig ATAC_fc.bigWig RNA_fc.bigWig \
    -R h3k27ac_idr_peaks.bed \
    --referencePoint center -b 3000 -a 3000 --binSize 50 \
    --missingDataAsZero --sortRegions descend --sortUsing mean \
    --blackListFileName hg38-blacklist.v2.bed \
    -o matrix_enhancers.gz -p 8
```

Using `reference-point` mode because enhancer peaks are point features. The `--blackListFileName` flag removes artifact regions (Amemiya et al. 2019).

### Step 3: Render the Heatmap
```bash
plotHeatmap -m matrix_enhancers.gz \
    -o enhancer_heatmap.pdf \
    --colorList "white,#FF8000" "white,#00B400" "white,#9B59B6" \
    --whatToShow "heatmap and colorbar" \
    --heatmapHeight 15 --heatmapWidth 4 \
    --zMin 0 0 0 --zMax 12 8 5 \
    --samplesLabel "H3K27ac" "ATAC-seq" "RNA-seq" \
    --regionsLabel "Active Enhancers" \
    --kmeans 3 --outFileSortedRegions enhancer_clusters.bed \
    --dpi 300
```

Three clusters emerge: (1) high H3K27ac + high ATAC -- canonical active enhancers; (2) high H3K27ac + low ATAC -- primed enhancers; (3) moderate signal across all marks -- weaker elements. The `--zMax` values differ per track to match each signal's dynamic range.

### Step 4: Set Up UCSC Track Hub

Three files are needed: `hub.txt`, `genomes.txt`, and `hg38/trackDb.txt`. **hub.txt:**
```
hub pancreas_enhancers
shortLabel Pancreas Enhancers
longLabel H3K27ac + ATAC + RNA-seq at pancreatic islet enhancers
genomesFile genomes.txt
email researcher@institution.edu
```

**hg38/trackDb.txt** (one child track shown; repeat for ATAC and RNA-seq):
```
track enhancerSignals
compositeTrack on
shortLabel Enhancer Signals
type bigWig
visibility full
autoScale off

    track H3K27ac_signal
    parent enhancerSignals
    bigDataUrl H3K27ac_fc.bigWig
    shortLabel H3K27ac
    type bigWig
    color 255,128,0
    viewLimits 0:12
```

Setting `viewLimits` manually is critical -- without it UCSC auto-scales each track independently and real differences disappear. Use the same values as `--zMax` from deepTools. Host on any HTTPS server and load via `genome.ucsc.edu/cgi-bin/hgTracks?db=hg38&hubUrl=https://yourserver.edu/hub.txt`.

### Step 5: Log Provenance
```
encode_log_derived_file(
    file_path="/data/viz_pancreas/enhancer_heatmap.pdf",
    source_accessions=["ENCFF735QAP", "ENCFF291DHB", "ENCFF803KQJ"],
    description="3-mark heatmap at H3K27ac peaks, k-means=3, pancreas",
    file_type="publication_figure", tool_used="deepTools 3.5.4",
    parameters="reference-point; -b 3000 -a 3000; binSize=50; kmeans=3; blacklist=v2"
)
```

## Key Principles

- **Always use fold-change-over-control bigWigs.** Raw coverage is not comparable across experiments with different sequencing depths. Mixing normalization types produces misleading patterns.
- **Set color scales manually and per-track.** Auto-scaling hides real differences. Lock the scale across all panels after inspecting each signal distribution.
- **Filter regions before visualization.** A heatmap of 200,000 unfiltered MACS2 peaks is dominated by noise. Use IDR thresholded peaks or filter by signalValue first.

## Related Skills

- **histone-aggregation** -- Build the union peak set used as input regions for heatmaps.
- **epigenome-profiling** -- Assemble the multi-mark dataset that feeds into track hubs.
- **quality-assessment** -- Verify experiment quality before visualization.
- **download-encode** -- Retrieve the bigWig and BED files required by deepTools and UCSC.

---

*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 43 skills for genomics research*
