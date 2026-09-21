# Pipeline CUT&RUN -- From FASTQ to Spike-in Normalized Peaks

> **Category:** Pipeline Execution | **Tools Used:** `encode_search_experiments`, `encode_download_files`, `encode_log_derived_file`

## What This Skill Does

Runs the Nextflow DSL2 pipeline that ships with the skill for CUT&RUN and CUT&Tag data: Bowtie2 alignment to the target genome, realignment of the unmapped pairs to an E. coli spike-in reference, SEACR peak calling optimized for low-background chromatin profiling, and spike-in calibrated signal tracks for quantitative cross-sample comparison.

## When to Use This

- You have CUT&RUN or CUT&Tag FASTQs and need peak calls and normalized signal tracks.
- You need spike-in normalization to compare enrichment across samples or conditions.
- You want to use SEACR (the CUT&RUN-specific peak caller) rather than MACS2.
- You are processing Henikoff-style targeted chromatin profiling data from pA-MNase or pA-Tn5.

## How CUT&RUN Differs from ChIP-seq

Three properties of CUT&RUN data require a fundamentally different pipeline.

**Low background.** CUT&RUN cleaves DNA only at antibody-bound sites, producing far less non-specific signal than ChIP-seq sonication. MACS2's dynamic Poisson background model, designed for the high noise floor of ChIP-seq, tends to overcall peaks in CUT&RUN data. SEACR (Meers et al. 2019) uses a sparse enrichment model built for this signal profile.

**Spike-in calibration.** E. coli DNA carried over from pA-MNase (CUT&RUN) or pA-Tn5 (CUT&Tag) production serves as an internal calibration standard. Samples with stronger target enrichment consume more enzyme, leaving proportionally fewer spike-in reads. The pipeline aligns to the target genome, realigns the read pairs that did not map there to the E. coli index, and computes per-sample scale factors from those counts. Without this step, quantitative comparisons between samples are unreliable.

**CUT&RUN suspect list.** Beyond the ENCODE blacklist (Amemiya et al. 2019), CUT&RUN data contains protocol-specific artifacts in regions where pA-MNase cleaves preferentially regardless of antibody. Nordin et al. 2023 cataloged these regions into a suspect list. The workflow takes one `--blacklist` BED and applies it to the BAM, so the suspect list is either merged into that BED up front or applied to the peak files afterwards by hand.

## Example Session

### Scientist's Request

> "I have CUT&RUN data for H3K4me3 in human pancreatic islets -- four biological replicates, paired-end 150bp. Process them with spike-in normalization."

### Step 1: Run the Pipeline

Claude runs the pipeline that ships with the skill, with spike-in calibration enabled.

```bash
nextflow run skills/pipeline-cutandrun/scripts/main.nf \
    -profile local \
    --reads '/data/cutandrun/fastq/Rep*_R{1,2}.fastq.gz' \
    --bowtie2_index '/ref/bowtie2_index/genome' \
    --spikein_index '/ref/bowtie2_ecoli/ecoli' \
    --chrom_sizes '/ref/hg38.chrom.sizes' \
    --blacklist '/ref/hg38-blacklist.v2.bed' \
    --seacr_mode stringent \
    --peak_caller seacr \
    --outdir results/h3k4me3_islets \
    -resume
```

The `--spikein_index` points to a Bowtie2 index of the E. coli K12 MG1655 genome. Omitting this flag (or passing `--skip_spikein true`) drops the calibration and the bigWigs fall back to RPKM -- acceptable for single-sample visualization, never for cross-sample comparison. The scale factor is applied only to the bigWig; the fragment bedGraph SEACR reads is always unscaled.

### Step 2: Spike-in Scale Factor Calculation

The pipeline writes each sample's count to `spikein/<sample>.spikein_counts.txt` and one run-wide `spikein/scale_factors.txt` (sample, spike-in count, scale factor). The factor is the smallest non-zero spike-in count in the run divided by the sample's own count, so the sample with the fewest spike-in reads gets 1.00 and everything else scales down.

| Sample | Total Reads | Genome Mapped | Spike-in Reads | Spike-in % | Scale Factor |
|---|---|---|---|---|---|
| Rep1 | 28.4M | 24.1M | 312K | 1.1% | 0.96 |
| Rep2 | 31.2M | 26.8M | 485K | 1.6% | 0.61 |
| Rep3 | 25.7M | 21.9M | 298K | 1.2% | 1.00 |
| Rep4 | 29.8M | 25.3M | 620K | 2.1% | 0.48 |

Spike-in percentages between 1-10% indicate a successful experiment. Below 0.1% suggests insufficient carry-over; above 30% suggests failed enrichment. A sample with no spike-in reads at all cannot be calibrated and is left unscaled at 1.00.

### Step 3: Filter the Peaks Against the Suspect List

`--blacklist` is applied to the BAM before peak calling, so the published peaks are already blacklist-clean. The workflow accepts no separate suspect list and never filters the peak files, so apply Nordin et al. 2023 by hand (or merge it into `--blacklist` before the run).

```bash
bedtools intersect \
    -a results/h3k4me3_islets/peaks/Rep1.seacr.stringent.bed \
    -b CUTandRUN.suspectlist.hg38.bed \
    -v \
    > Rep1.seacr.suspectlist_filtered.bed
```

The suspect list removes regions where pA-MNase cleaves DNA irrespective of antibody binding. These regions pass standard blacklist filtering but produce artifactual CUT&RUN signal. Skipping this filter inflates peak counts by 5-15% with false positives.

### Step 4: QC Assessment

Claude evaluates the output against CUT&RUN-specific thresholds.

| Metric | Rep1 | Rep2 | Rep3 | Rep4 | Threshold | Read it from |
|---|---|---|---|---|---|---|
| Mapping rate | 84.9% | 85.9% | 85.2% | 84.9% | >80% pass | Bowtie2 log, in `multiqc/multiqc_report.html` |
| Duplication rate | 12.3% | 14.1% | 11.8% | 15.7% | <20% pass | `alignment/<sample>.dup_metrics.txt` |
| FRiP | 0.184 | 0.221 | 0.169 | 0.245 | >0.10 pass | `qc/<sample>.frip_mqc.tsv` |
| Peak count | 21,432 | 24,871 | 19,845 | 26,103 | >5,000 pass | `peaks/<sample>.seacr.stringent.bed` |

`qc/<sample>.fragment_sizes.txt` holds the fragment length and its read count, two columns, one row per length -- the workflow draws no plot. Plotting it here shows the expected nucleosomal ladder: a sub-nucleosomal peak below 120 bp (TF footprints) and a dominant mononucleosomal peak at approximately 150 bp (histone mark signal). The presence of this ladder confirms successful CUT&RUN digestion.

### Step 5: Benchmark Against ENCODE and Log Provenance

These peaks came from local FASTQs, so they have no ENCODE source accession to record: `encode_log_derived_file` accepts ENCODE accessions only, and a file derived purely from local data belongs outside the provenance chain. Benchmark the peaks against an ENCODE H3K4me3 reference and log the comparison, which is the file that really consumes ENCODE data.

```python
encode_search_experiments(assay_title="Histone ChIP-seq", target="H3K4me3", organ="pancreas", biosample_type="tissue")
encode_download_files(file_accessions=["ENCFF..."], download_dir="/data/encode_reference", organize_by="flat")

encode_log_derived_file(
    file_path="/results/h3k4me3_islets/comparison/Rep1_vs_encode.overlap.tsv",
    source_accessions=["ENCFF..."],
    description="Overlap of local CUT&RUN H3K4me3 peaks (Rep1, SEACR stringent, spike-in calibrated signal, suspect-list filtered) with an ENCODE H3K4me3 reference peak set",
    file_type="peak_overlap",
    tool_used="bedtools intersect (bedtools 2.31.0)",
    parameters="bedtools intersect -u -a Rep1.seacr.suspectlist_filtered.bed -b <ENCODE peaks>.bed"
)
```

## SEACR vs MACS2 Decision

Use SEACR as the primary peak caller for CUT&RUN. It handles the sparse, low-background signal profile correctly and works with or without an IgG control, writing `peaks/<sample>.seacr.<mode>.bed`. MACS2 remains useful as a secondary caller when comparing CUT&RUN results to existing ChIP-seq peak sets, because it writes `peaks/<sample>.macs2_peaks.narrowPeak` in the same format as those peak calls. Run both with `--peak_caller both` when cross-assay consistency matters; FRiP is then reported for each peak set.

## Related Skills

- **pipeline-guide** -- Parent skill for compute assessment and environment selection.
- **pipeline-chipseq** -- ChIP-seq pipeline; use when comparing CUT&RUN to ChIP-seq for the same target.
- **histone-aggregation** -- Merge CUT&RUN peaks across samples into a union catalog.
- **quality-assessment** -- Evaluate pipeline outputs against ENCODE QC standards.
- **data-provenance** -- Full provenance chain from FASTQ to filtered peaks.

---

*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 47 skills for genomics research*
