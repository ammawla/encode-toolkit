# Pipeline CUT&RUN -- From FASTQ to Spike-in Normalized Peaks

> **Category:** Pipeline Execution | **Tools Used:** `encode_search_experiments`, `encode_download_files`, `encode_log_derived_file`

## What This Skill Does

Generates and runs a Nextflow DSL2 pipeline for CUT&RUN and CUT&Tag data: Bowtie2 alignment to both the target genome and E. coli spike-in reference, SEACR peak calling optimized for low-background chromatin profiling, and spike-in calibrated signal tracks for quantitative cross-sample comparison.

## When to Use This

- You have CUT&RUN or CUT&Tag FASTQs and need peak calls and normalized signal tracks.
- You need spike-in normalization to compare enrichment across samples or conditions.
- You want to use SEACR (the CUT&RUN-specific peak caller) rather than MACS2.
- You are processing Henikoff-style targeted chromatin profiling data from pA-MNase or pA-Tn5.

## How CUT&RUN Differs from ChIP-seq

Three properties of CUT&RUN data require a fundamentally different pipeline.

**Low background.** CUT&RUN cleaves DNA only at antibody-bound sites, producing far less non-specific signal than ChIP-seq sonication. MACS2's dynamic Poisson background model, designed for the high noise floor of ChIP-seq, tends to overcall peaks in CUT&RUN data. SEACR (Meers et al. 2019) uses a sparse enrichment model built for this signal profile.

**Spike-in calibration.** E. coli DNA carried over from pA-MNase (CUT&RUN) or pA-Tn5 (CUT&Tag) production serves as an internal calibration standard. Samples with stronger target enrichment consume more enzyme, leaving proportionally fewer spike-in reads. The pipeline aligns to both the target genome and E. coli, then computes per-sample scale factors from spike-in read counts. Without this step, quantitative comparisons between samples are unreliable.

**CUT&RUN suspect list.** Beyond the ENCODE blacklist (Amemiya et al. 2019), CUT&RUN data contains protocol-specific artifacts in regions where pA-MNase cleaves preferentially regardless of antibody. Nordin et al. 2023 cataloged these regions into a suspect list that must be applied in addition to the standard blacklist.

## Example Session

### Scientist's Request

> "I have CUT&RUN data for H3K4me3 in human pancreatic islets -- four biological replicates, paired-end 150bp. Process them with spike-in normalization."

### Step 1: Run the Pipeline

Claude generates and executes the Nextflow pipeline with spike-in enabled.

```bash
nextflow run main.nf \
    -profile local \
    --reads '/data/cutandrun/H3K4me3_islets_*_R{1,2}.fastq.gz' \
    --bowtie2_index '/ref/bowtie2_index/genome' \
    --spikein_index '/ref/bowtie2_ecoli/ecoli' \
    --chrom_sizes '/ref/hg38.chrom.sizes' \
    --blacklist '/ref/hg38-blacklist.v2.bed' \
    --seacr_mode stringent \
    --peak_caller seacr \
    --outdir results/h3k4me3_islets \
    -resume
```

The `--spikein_index` points to a Bowtie2 index of the E. coli K12 MG1655 genome. Omitting this flag (or passing `--skip_spikein true`) disables spike-in normalization entirely -- only acceptable for single-sample visualization, never for cross-sample comparison.

### Step 2: Spike-in Scale Factor Calculation

The pipeline reports spike-in read counts and computed scale factors per sample.

| Sample | Total Reads | Genome Mapped | Spike-in Reads | Spike-in % | Scale Factor |
|---|---|---|---|---|---|
| Rep1 | 28.4M | 24.1M | 312K | 1.1% | 1.00 |
| Rep2 | 31.2M | 26.8M | 485K | 1.6% | 0.64 |
| Rep3 | 25.7M | 21.9M | 298K | 1.2% | 1.05 |
| Rep4 | 29.8M | 25.3M | 620K | 2.1% | 0.50 |

Spike-in percentages between 1-10% indicate a successful experiment. Below 0.1% suggests insufficient carry-over; above 30% suggests failed enrichment.

### Step 3: Filter Against Blacklist AND Suspect List

Both region lists are applied to the SEACR peak calls.

```bash
bedtools intersect \
    -a results/peaks/Rep1.seacr.stringent.bed \
    -b hg38-blacklist.v2.bed CUTandRUN.suspectlist.hg38.bed \
    -v \
    > results/peaks/Rep1.seacr.filtered.bed
```

The suspect list (Nordin et al. 2023) removes regions where pA-MNase cleaves DNA irrespective of antibody binding. These regions pass standard blacklist filtering but produce artifactual CUT&RUN signal. Skipping this filter inflates peak counts by 5-15% with false positives.

### Step 4: QC Assessment

Claude evaluates the output against CUT&RUN-specific thresholds.

| Metric | Rep1 | Rep2 | Rep3 | Rep4 | Threshold |
|---|---|---|---|---|---|
| Mapping rate | 84.9% | 85.9% | 85.2% | 84.9% | >80% pass |
| Duplication rate | 12.3% | 14.1% | 11.8% | 15.7% | <20% pass |
| FRiP | 18.4% | 22.1% | 16.9% | 24.5% | >10% pass |
| Peak count | 21,432 | 24,871 | 19,845 | 26,103 | >5,000 pass |

Fragment size distributions show the expected nucleosomal ladder: a sub-nucleosomal peak below 120 bp (TF footprints) and a dominant mononucleosomal peak at approximately 150 bp (histone mark signal). The presence of this ladder confirms successful CUT&RUN digestion.

### Step 5: Log Provenance

```python
encode_log_derived_file(
    file_path="/results/h3k4me3_islets/peaks/Rep1.seacr.filtered.bed",
    source_accessions=["ENCSR...", "ENCFF..."],
    description="CUT&RUN H3K4me3 peaks, spike-in normalized, blacklist + suspect list filtered",
    file_type="CUT&RUN_peaks",
    tool_used="Bowtie2 2.5.3 + SEACR 1.3",
    parameters="stringent mode; spikein=ecoli_K12; blacklist=v2; suspectlist=Nordin2023"
)
```

## SEACR vs MACS2 Decision

Use SEACR as the primary peak caller for CUT&RUN. It handles the sparse, low-background signal profile correctly and works with or without an IgG control. MACS2 remains useful as a secondary caller when comparing CUT&RUN results to existing ChIP-seq peak sets, since both callers produce narrowPeak format. Run both with `--peak_caller both` when cross-assay consistency matters.

## Related Skills

- **pipeline-guide** -- Parent skill for compute assessment and environment selection.
- **pipeline-chipseq** -- ChIP-seq pipeline; use when comparing CUT&RUN to ChIP-seq for the same target.
- **histone-aggregation** -- Merge CUT&RUN peaks across samples into a union catalog.
- **quality-assessment** -- Evaluate pipeline outputs against ENCODE QC standards.
- **data-provenance** -- Full provenance chain from FASTQ to filtered peaks.

---

*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 43 skills for genomics research*
