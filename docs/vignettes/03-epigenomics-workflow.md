# Epigenomic Profiling with ENCODE Data

> This vignette demonstrates building a comprehensive chromatin landscape for a tissue
> of interest, from initial data survey through aggregation and visualization guidance.
> Tools handle data discovery; skills guide downstream analysis.

## Scenario

You are characterizing the chromatin state of human pancreatic tissue by collecting
multiple histone modifications and accessibility data from ENCODE. Your goal is to
build union peak catalogs, assess experiment compatibility, and prepare data for
chromatin state segmentation.

## Step 1: Survey Available Histone Marks

**You ask Claude:** "What histone marks are available for human pancreas in ENCODE?"

**Claude calls:** `encode_get_facets(organ="pancreas", assay_title="Histone ChIP-seq")`

**Result:**
| Mark | Role | Experiments |
|------|------|-------------|
| H3K4me3 | Active/poised promoters (sharp peaks at TSSs) | 16 |
| H3K27ac | Active enhancers and promoters (distinguishes active from poised) | 15 |
| H3K27me3 | Polycomb repression (broad domains over silent genes) | 14 |
| H3K9me3 | Constitutive heterochromatin (repeats, pericentromeric) | 14 |
| H3K4me1 | Enhancers -- primed, poised, and active | 13 |
| H3K36me3 | Actively transcribed gene bodies | 12 |
| CTCF | Insulator and TAD boundary factor | 16 |

This covers the Roadmap Epigenomics 5-mark core (Kundaje et al. 2015) plus H3K27ac,
enabling the 18-state ChromHMM model that resolves active enhancers, bivalent
promoters, Polycomb-repressed domains, and heterochromatin.

## Step 2: Search for Active Enhancer Mark (H3K27ac)

**You ask Claude:** "Find H3K27ac ChIP-seq on human pancreas tissue."

**Claude calls:** `encode_search_experiments(assay_title="Histone ChIP-seq", organ="pancreas", target="H3K27ac")`

**Result (3 of 15 experiments):**
```
ENCSR927WRI  H3K27ac  pancreas tissue male adult (54y)    bernstein  14 files
ENCSR817FFF  H3K27ac  pancreas tissue female adult (53y)  bernstein  14 files
ENCSR329VQG  H3K27ac  body of pancreas female child (5y)  bernstein  18 files
```

Fifteen H3K27ac experiments cover multiple donors across ages and sexes, all from the
Bernstein lab (Broad Institute). Individual experiments are unreplicated, but 15
donors provides strong biological replication across the collection. H3K27ac is
essential here because it distinguishes active enhancers (H3K4me1 + H3K27ac) from
primed enhancers (H3K4me1 alone) -- without it, you cannot classify enhancer state.

## Step 3: Search for Accessibility Data

**You ask Claude:** "Also find ATAC-seq experiments for pancreas."

**Claude calls:** `encode_search_experiments(assay_title="ATAC-seq", organ="pancreas")`

**Result (2 of 10 experiments):**
```
ENCSR832UMM  ATAC-seq  pancreas tissue male adult (37y)    snyder  isogenic
ENCSR605AVQ  ATAC-seq  pancreas tissue female adult (51y)  snyder  isogenic
```

Pancreas has 10 ATAC-seq plus 31 DNase-seq experiments. Intersecting accessibility
peaks with histone marks is the standard approach for regulatory element
classification: accessible + H3K27ac = active enhancer; accessible + H3K4me3 = active
promoter.

## Step 4: Compare Experiments for Compatibility

**You ask Claude:** "Are ENCSR133RZO and ENCSR511LIV compatible for combined analysis?"

**Claude calls:** `encode_compare_experiments(accession1="ENCSR133RZO", accession2="ENCSR511LIV")`

**Result:**
```
Verdict: COMPATIBLE
Matching: assay (Histone ChIP-seq), target (H3K27me3), organ (pancreas),
          assembly (GRCh38), lab (Bernstein)
Differences: donor age (16y vs 61y)
Warnings: both unreplicated, 45-year age gap
Recommendation: compatible for union aggregation -- age difference is
                biological variation, not a batch effect
```

Use `encode_compare_experiments` for every pair before merging. Key incompatibilities
to watch for: mixed assemblies (GRCh38 vs. hg19), different targets, or mismatched
biosample types (tissue vs. cell line).

## Step 5: Aggregate Histone Peaks (Skill Guidance)

**You ask Claude:** "How do I merge H3K27ac peaks across all these pancreas samples?"

**Claude activates the histone-aggregation skill**, which guides a literature-backed
union merge workflow. The rationale: chromatin mark detection is binary once noise is
filtered -- if a mark is detected in one donor but not another, the binding site is
real. We want the **union of all detections, not a consensus**.

The skill walks you through five stages:

**1. Download peak files** using `encode_list_files` for each experiment, selecting
IDR thresholded peaks > replicated peaks > pseudoreplicated peaks. Prefer
`preferred_default=True`.

**2. Blocklist filter** (Amemiya et al. 2019, 1372 citations): remove artifact-prone
regions (centromeres, telomeres, satellite repeats):
```bash
bedtools intersect -a sample.narrowPeak -b hg38-blacklist.v2.bed -v > sample.filtered.narrowPeak
```

**3. SignalValue filter** (Perna et al. 2024): remove bottom 25% of peaks per sample
by signalValue (column 7). This is a per-sample quantile, not a universal threshold.

**4. Tag and merge**: label each peak with its sample ID, concatenate, then union
merge counting unique samples:
```bash
awk -v sid="sample1" 'BEGIN{OFS="\t"} {$4=sid; print}' sample1.narrowPeak > sample1.tagged.bed
cat *.tagged.bed | bedtools sort -i - | \
    bedtools merge -c 4,7,9 -o count_distinct,max,max > union_H3K27ac.bed
```

**5. Confidence annotation**: HIGH (>=50% of samples), SUPPORTED (2+ samples),
SINGLETON (1 sample). The skill emphasizes: do NOT discard singletons -- a peak in
1 of 15 donors is a real binding event in that individual.

## Step 6: Aggregate Accessibility Peaks (Skill Guidance)

**You ask Claude:** "Now merge the ATAC-seq peaks the same way."

**Claude activates the accessibility-aggregation skill**, which follows the same
union logic with accessibility-specific additions:

- Optional minimum peak width filter (>=50bp) to remove Tn5 insertion artifacts
- If combining ATAC-seq and DNase-seq: both detect open chromatin through different
  enzymatic mechanisms (Corces et al. 2017 showed ~75% overlap), so a union is
  scientifically justified
- Peaks tagged by assay source (ATAC vs. DNase) to track platform contribution

The output is a union accessible regions catalog ready for intersection with histone
marks to classify regulatory elements.

## Step 7: Visualization Guidance (Skill)

**You ask Claude:** "How should I visualize these chromatin profiles together?"

**Claude activates the visualization-workflow skill** and recommends three approaches:

**deepTools heatmaps** (Ramirez et al. 2016) -- compare multiple marks at the same
genomic regions with k-means clustering to reveal sub-patterns:
```bash
computeMatrix reference-point \
    -S H3K27ac_fc.bigWig H3K4me3_fc.bigWig H3K27me3_fc.bigWig ATAC_fc.bigWig \
    -R union_H3K27ac.bed --referencePoint center -b 3000 -a 3000 -o matrix.gz
plotHeatmap -m matrix.gz -o heatmap.png --kmeans 4 \
    --colorMap YlOrRd Reds Blues Greens --dpi 300
```

Clustering reveals: active promoters (H3K4me3 + H3K27ac + ATAC), active enhancers
(H3K27ac + ATAC, no H3K4me3), poised elements (H3K27me3 only), and bivalent regions
(H3K4me3 + H3K27me3).

**IGV** -- validate findings at key pancreatic loci (INS, GCK, PDX1) by loading
ENCODE bigWig URLs directly, without downloading full files.

**UCSC track hub** -- build a composite hub with consistent color coding (H3K27ac =
orange, H3K4me3 = red, H3K27me3 = blue, ATAC = green) and share with collaborators.

## Step 8: Log Provenance

Track the complete analysis chain for reproducibility:
```
encode_log_derived_file(
    file_path="/data/pancreas/union_H3K27ac.annotated.bed",
    source_accessions=["ENCSR927WRI", "ENCSR817FFF", "ENCSR329VQG", ...],
    description="Union H3K27ac peaks across 15 pancreas donors",
    file_type="aggregated_peaks",
    tool_used="bedtools merge v2.31.0",
    parameters="blocklist filtered, signalValue >= 25th pctl, merge -d 0"
)
```

## Skills Demonstrated

| Skill | Role in This Workflow |
|-------|----------------------|
| **search-encode** | Finding experiments by assay, organ, and histone target |
| **epigenome-profiling** | Assembling the histone modification panel and assessing coverage |
| **compare-biosamples** | Verifying experiment compatibility before aggregation |
| **histone-aggregation** | Union merge of narrowPeak files with blocklist and signalValue filtering |
| **accessibility-aggregation** | Union merge of ATAC-seq/DNase-seq peaks with Tn5 artifact removal |
| **visualization-workflow** | deepTools heatmaps, IGV inspection, UCSC track hubs |
| **data-provenance** | Recording the analysis chain from ENCODE accessions to derived files |

## What's Next

- [Variant & Disease](04-variant-and-disease.md) -- Intersect union peak catalogs with
  GWAS variants to identify regulatory mechanisms underlying pancreatic disease risk
- [Pipeline Execution](08-pipeline-execution.md) -- Process raw ENCODE data through
  the full ChIP-seq or ATAC-seq pipeline when you need custom peak calls
