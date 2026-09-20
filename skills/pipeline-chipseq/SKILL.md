---
name: pipeline-chipseq
description: "Execute ENCODE ChIP-seq processing pipeline from FASTQ to peaks and signal tracks. Child of pipeline-guide. Provides stage-by-stage Nextflow execution with Docker containers and cloud deployment. Use when users need to process ChIP-seq data following ENCODE standards, run peak calling with MACS2, perform IDR analysis, or generate signal tracks. Trigger on: ChIP-seq pipeline, run ChIP-seq, process ChIP-seq, MACS2 peak calling, IDR analysis, ChIP-seq FASTQ processing."
---

# ENCODE ChIP-seq Pipeline

## When to Use

- User wants to run a ChIP-seq processing pipeline from FASTQ to peaks and signal tracks
- User asks about "ChIP-seq pipeline", "MACS2", "peak calling", "BWA alignment for ChIP", or "IDR"
- User needs to process histone or TF ChIP-seq data following ENCODE standards
- Example queries: "process my ChIP-seq FASTQs", "run the ENCODE ChIP-seq pipeline", "call peaks from ChIP-seq with MACS2 and IDR"

Execute the ENCODE ChIP-seq processing pipeline from raw FASTQ files through peak calling,
IDR analysis, and signal track generation. This skill provides a Nextflow DSL2
implementation following ENCODE uniform analysis standards.

## Overview

The pipeline processes chromatin immunoprecipitation sequencing data through
quality control, adapter trimming, alignment to a reference genome, filtering and
duplicate removal, blacklist filtering, peak calling with MACS2, a single IDR comparison
between two replicates, and signal track generation.

The same workflow handles transcription factor (TF) ChIP-seq and histone modification
ChIP-seq. The peak mode is chosen once per run with `--peak_type narrow|broad`; it applies
to every sample in that run. To process narrow and broad targets together, run the
workflow twice with different `--peak_type` and `--outdir` values.

## Key Literature

| Reference | Journal | Year | DOI | Relevance |
|-----------|---------|------|-----|-----------|
| Landt et al. "ChIP-seq guidelines and practices" | Genome Research | 2012 | 10.1101/gr.136184.111 | ENCODE ChIP-seq standards (~4,000 citations) |
| ENCODE Project Consortium "Expanded encyclopaedias" | Nature | 2020 | 10.1038/s41586-020-2493-4 | ENCODE Phase 3 standards |
| Zhang et al. "Model-based Analysis of ChIP-Seq (MACS)" | Genome Biology | 2008 | 10.1186/gb-2008-9-9-r137 | Peak caller (~7,000 citations) |
| Li et al. "Measuring reproducibility (IDR)" | Annals of Applied Statistics | 2011 | 10.1214/11-AOAS466 | Replicate consistency (~1,500 citations) |
| Amemiya et al. "ENCODE Blacklist" | Scientific Reports | 2019 | 10.1038/s41598-019-45839-z | Artifact regions (~1,372 citations) |
| Ramachandran et al. "phantompeakqualtools" | — | 2013 | — | NSC/RSC strand correlation metrics (manual step, see below) |

## Pipeline Stages

```
FASTQ ──> FastQC / Trim Galore ──> BWA-MEM ──> Samtools Filter ──> Picard MarkDuplicates
  │                                            (-F 1804/-F 1028, -q 30)   (duplicates REMOVED)
  │                                                                       │
  │           ┌───────────────────────────────────────────────────────────┘
  │           v
  │     Blacklist Filter ──> MACS2 Peak Calling ──> IDR (narrow runs only)
  │       (applied to BAM)          │
  │                                 v
  │                    Signal Tracks (bdgcmp + bedGraphToBigWig)
  v
 QC reports ──────────────────────────────────> MultiQC
```

Control libraries, when `--control` is given, travel through stages 1-3 alongside the ChIP
samples with a `CONTROL_` prefix and are split off before peak calling; MACS2 pools them
with `-c`.

### Stage Summary

| Stage | Tool | Input | Output | Reference |
|-------|------|-------|--------|-----------|
| 1. QC & Trimming | FastQC, Trim Galore | Raw FASTQ | Trimmed FASTQ, FastQC reports | references/01-qc-trimming.md |
| 2. Alignment | BWA-MEM, samtools | Trimmed FASTQ | Sorted BAM, flagstat | references/02-alignment.md |
| 3. Filtering | samtools, Picard, bedtools | Sorted BAM | Deduplicated, blacklist-filtered BAM | references/03-filtering.md |
| 4. Peak Calling & IDR | MACS2, IDR | Filtered BAM | narrowPeak/broadPeak, idr_peaks.txt | references/04-analysis.md |
| 5. Signal & QC report | MACS2 bdgcmp, bedGraphToBigWig, MultiQC | MACS2 bedGraphs, QC logs | bigWig, multiqc_report.html | references/05-qc-metrics.md |

## Input Requirements

### Required
- **Treatment FASTQ** (`--reads`): ChIP sample reads, gzipped. A Nextflow file-pair glob,
  e.g. `'fastq/chip_*_R{1,2}.fq.gz'`. Paired-end by default; add `--single_end` for SE data.
- **Chromosome sizes** (`--chrom_sizes`): two-column `<chrom>\t<size>` file used by
  `bedGraphToBigWig`. The workflow stops immediately if it is missing. Build it with
  `samtools faidx GRCh38.fa && cut -f1,2 GRCh38.fa.fai > GRCh38.chrom.sizes`.
- **BWA index directory** (`--bwa_index`): a directory holding `<genome>.fa` plus its BWA
  index files. BWA is invoked as `bwa mem ... <dir>/GRCh38.fa`, so the directory must
  contain `GRCh38.fa`, `GRCh38.fa.amb`, `GRCh38.fa.ann`, `GRCh38.fa.bwt`, `GRCh38.fa.pac`
  and `GRCh38.fa.sa`. Build it once with `bwa index GRCh38_index/GRCh38.fa`. If the flag is
  omitted, the workflow looks for `./<genome>_index` in the launch directory. The workflow
  does not build or download the index.

### Optional
- **Control FASTQ** (`--control`): input/IgG reads, same glob form. Strongly recommended
  for meaningful enrichment, but the workflow runs without one; MACS2 then uses its local
  lambda background model.
- **Blacklist** (`--blacklist`): defaults to the ENCODE Blacklist v2 URL for `--genome`.

There is no sample sheet. Inputs are globs, and every sample in a run shares one
`--peak_type` and one `--genome`.

**The `--reads` and `--control` globs must not match the same files.** A glob such as
`'fastq/*_R{1,2}.fq.gz'` also matches `fastq/input_R{1,2}.fq.gz`, so the control library
would be processed twice: once as a control and once as a ChIP sample, producing peak calls
for the input itself and possibly feeding them to IDR. Use a distinct prefix
(`'fastq/chip_*_R{1,2}.fq.gz'`) or keep controls in a separate directory.

### Narrow vs Broad Peak Mode Decision

| Peak Type | Targets | MACS2 flags used by the workflow |
|-----------|---------|----------------------------------|
| Narrow (`--peak_type narrow`) | H3K4me3, H3K4me1, H3K27ac, H3K9ac, all TFs, CTCF | `--qvalue 0.05 --call-summits` |
| Broad (`--peak_type broad`) | H3K27me3, H3K36me3, H3K9me3, H3K79me2 | `--qvalue 0.05 --broad --broad-cutoff 0.1` |

IDR runs only for `--peak_type narrow`. Broad runs produce no `peaks/idr/` output.

## Parameters

### Pipeline parameters (`main.nf`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--reads` | none (required) | Glob for the ChIP FASTQ file pairs |
| `--chrom_sizes` | none (required) | Two-column chromosome sizes file for the bigWig tracks |
| `--bwa_index` | `./<genome>_index` | Directory holding `<genome>.fa` and its BWA index files |
| `--control` | none | Glob for control/input FASTQ file pairs; optional |
| `--genome` | `GRCh38` | `GRCh38` or `mm10`; sets the MACS2 genome size, the default blacklist and the default index directory name (`<genome>_index`) |
| `--peak_type` | `narrow` | `narrow` or `broad`; one value for the whole run |
| `--blacklist` | ENCODE Blacklist v2 URL for `--genome` | BED (or `.bed.gz`) of artifact regions removed from the BAM |
| `--single_end` | `false` | Treat `--reads`/`--control` as single-end files |
| `--skip_idr` | `false` | Skip the IDR step |
| `--outdir` | `results` | Where results are published |

### Infrastructure parameters (`nextflow.config`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--container` | `encode-toolkit/pipeline-chipseq:1.0.0` | Image built from `scripts/Dockerfile`. Pass a registry image for `gcp`/`aws`, or a `.sif` file for `slurm` |
| `--max_cpus`, `--max_memory`, `--max_time` | `16`, `64.GB`, `24.h` | Upper bounds applied to every process |
| `--slurm_queue`, `--slurm_account` | `normal`, none | SLURM partition and account |
| `--gcp_project`, `--gcp_workdir` | none (both required for `-profile gcp`) | Google Cloud project and `gs://` work directory |
| `--gcp_location`, `--gcp_disk` | `us-central1`, `200.GB` | Google Batch region and per-task disk |
| `--aws_queue`, `--aws_workdir` | none (both required for `-profile aws`) | AWS Batch job queue and `s3://` work directory |
| `--aws_region`, `--aws_cli_path` | `us-east-1`, `/home/ec2-user/miniconda/bin/aws` | AWS region, and the AWS CLI path inside the Batch AMI |

Profiles are `local`, `slurm`, `gcp` and `aws`.

## QC Thresholds

These thresholds follow ENCODE standards established by Landt et al. 2012 and the
ENCODE DCC quality metrics documentation. **The workflow itself computes only the
metrics marked "workflow" below**; the rest are community thresholds you evaluate from
manual steps documented in `references/05-qc-metrics.md`.

| Metric | Threshold | Computed by | Source |
|--------|-----------|-------------|--------|
| Total sequenced reads | >=20M (TF), >=45M (histone) | workflow (FastQC, flagstat) | Landt 2012 |
| Mapping rate | >80% | workflow (`samtools flagstat`) | ENCODE |
| Duplication rate | <30% | workflow (Picard `dup_metrics.txt`) | ENCODE |
| IDR peaks at 0.05 | >20,000 (TF) | workflow (`peaks/idr/idr_peaks.txt`) | ENCODE |
| NRF (non-redundant fraction) | >=0.8 | manual | ENCODE |
| PBC1 (PCR bottleneck coeff 1) | >=0.8 | manual | ENCODE |
| PBC2 (PCR bottleneck coeff 2) | >=3 | manual | ENCODE |
| NSC (normalized strand coeff) | >1.05 | manual (phantompeakqualtools) | phantompeakqualtools |
| RSC (relative strand corr) | >0.8 | manual (phantompeakqualtools) | phantompeakqualtools |
| FRiP (fraction reads in peaks) | >=1% | manual (bedtools + samtools) | Landt 2012 |
| Mitochondrial fraction | <5% | manual (`samtools idxstats`) | ENCODE |

### Interpreting QC: Traffic Light System

| Color | Meaning | Action |
|-------|---------|--------|
| Green | All metrics pass | Proceed to analysis |
| Yellow | 1-2 metrics marginal | Review library prep, may be usable |
| Red | Multiple failures | Do not use; re-do experiment |

**Important**: No single metric is sufficient. Interpret QC collectively. A sample with
borderline NRF but excellent FRiP may still be usable.

## Execution

### Quick Start (Local Docker)
```bash
nextflow run scripts/main.nf \
  -profile local \
  --reads 'fastq/chip_*_R{1,2}.fq.gz' \
  --control 'fastq/input_*_R{1,2}.fq.gz' \
  --genome GRCh38 \
  --peak_type narrow \
  --bwa_index GRCh38_index \
  --chrom_sizes GRCh38.chrom.sizes \
  --blacklist hg38-blacklist.v2.bed.gz \
  --outdir results/
```

The `--reads` and `--control` globs use different prefixes so no FASTQ is picked up twice.
`--blacklist` is optional; without it the workflow downloads the ENCODE Blacklist v2 for
`--genome`.

### SLURM HPC

The `slurm` profile runs through Singularity, so pass a local image file rather than the
default Docker image name:

```bash
singularity build pipeline-chipseq.sif docker-daemon://encode-toolkit/pipeline-chipseq:1.0.0

nextflow run scripts/main.nf \
  -profile slurm \
  --container /path/to/pipeline-chipseq.sif \
  --slurm_queue normal \
  --reads 'fastq/chip_*_R{1,2}.fq.gz' \
  --control 'fastq/input_*_R{1,2}.fq.gz' \
  --genome GRCh38 \
  --peak_type narrow \
  --bwa_index GRCh38_index \
  --chrom_sizes GRCh38.chrom.sizes \
  --outdir results/
```

### Cloud

```bash
# Google Cloud Batch
nextflow run scripts/main.nf -profile gcp \
    --container us-docker.pkg.dev/<project>/<repo>/pipeline-chipseq:1.0.0 \
    --gcp_project <project> \
    --gcp_workdir gs://<bucket>/work \
    --reads 'gs://<bucket>/fastq/chip_*_R{1,2}.fq.gz' \
    --control 'gs://<bucket>/fastq/input_*_R{1,2}.fq.gz' \
    --genome GRCh38 \
    --peak_type narrow \
    --bwa_index gs://<bucket>/reference/GRCh38_index \
    --chrom_sizes gs://<bucket>/reference/GRCh38.chrom.sizes \
    --outdir gs://<bucket>/results

# AWS Batch
nextflow run scripts/main.nf -profile aws \
    --container <account>.dkr.ecr.<region>.amazonaws.com/pipeline-chipseq:1.0.0 \
    --aws_queue <job-queue> \
    --aws_workdir s3://<bucket>/work \
    --reads 's3://<bucket>/fastq/chip_*_R{1,2}.fq.gz' \
    --control 's3://<bucket>/fastq/input_*_R{1,2}.fq.gz' \
    --genome GRCh38 \
    --peak_type narrow \
    --bwa_index s3://<bucket>/reference/GRCh38_index \
    --chrom_sizes s3://<bucket>/reference/GRCh38.chrom.sizes \
    --outdir s3://<bucket>/results
```

`--outdir` only sets where results are published; Google Batch and AWS Batch stage every
task through the work directory, and the workflow stops with an error if it or the
project/queue is missing.

## Cloud Cost Estimates

| Platform | Instance | Cost/Sample | Time/Sample | Notes |
|----------|----------|-------------|-------------|-------|
| GCP | n1-standard-8 | ~$2-5 | 2-4 hours | Spot VMs enabled in the `gcp` profile |
| AWS | m5.2xlarge | ~$2-5 | 2-4 hours | Spot instances recommended |
| Local | 8 cores, 32GB | $0 | 3-6 hours | Docker required |
| SLURM | 8 cores, 32GB | Varies | 2-4 hours | Singularity image required |

## Output Directory Structure

```
results/
  fastqc/                       # FastQC reports for raw and trimmed reads (.html, .zip)
  trimmed/                      # Trimmed FASTQ (*_val_1.fq.gz / *_val_2.fq.gz) + trimming reports
  aligned/                      # <sample>.bam, .bam.bai, <sample>.flagstat.txt
  filtered/                     # <sample>.dup_metrics.txt, <sample>.final.bam(.bai),
                                #   <sample>.final.flagstat.txt
  peaks/
    narrow/                     # --peak_type narrow: <sample>_peaks.narrowPeak, _summits.bed,
                                #   _peaks.xls, _treat_pileup.bdg, _control_lambda.bdg
    broad/                      # --peak_type broad: _peaks.broadPeak, _peaks.gappedPeak,
                                #   _peaks.xls, the same bedGraphs
    idr/                        # idr_peaks.txt (+ idr_peaks.txt.png); narrow runs only
  signal/                       # <sample>.fc.bw, <sample>.pval.bw
  qc/
    multiqc/                    # multiqc_report.html, multiqc_data/
  pipeline_info/                # timeline.html, report.html, trace.txt
```

Only one of `peaks/narrow/` and `peaks/broad/` exists per run, matching `--peak_type`.
When `--control` is given, the control libraries also appear in `aligned/`, `filtered/` and
`fastqc/` under a `CONTROL_<name>` prefix.

## Common Pitfalls

### 1. Overlapping `--reads` and `--control` globs
The most common silent failure. If both globs match the same FASTQ, the control is also
treated as a ChIP sample: MACS2 calls peaks on the input library and IDR may pair those
peaks with a real replicate. Nothing errors. Use non-overlapping globs.

### 2. Missing Input Control
ChIP-seq is far more interpretable with a matched input (or IgG) control. Without one,
MACS2 falls back to its local lambda background model and false positive rates rise.
The workflow does not require `--control`, so check that you passed it.

### 3. Narrow vs Broad Peak Mode Mismatch
Using narrow peak calling for broad marks (H3K27me3, H3K36me3) fragments the signal
into many small peaks instead of capturing the broad domains. Use `--peak_type broad` for
these marks. Conversely, broad mode on TF ChIP-seq over-merges distinct binding sites.
Because `--peak_type` is one value per run, group targets of the same class into one run.

### 4. Adapter Contamination
Short insert libraries may have significant adapter read-through. Trim Galore runs
before alignment. Check the FastQC adapter content plots in `fastqc/`: >5% adapter after
trimming suggests a problem.

### 5. PCR Bottleneck
Low-input ChIP-seq libraries may have high duplication rates (>30%). The workflow removes
duplicates, so a bottlenecked library loses effective depth. Check
`filtered/<sample>.dup_metrics.txt` and the MultiQC report. NRF/PBC are manual
calculations (references/05-qc-metrics.md).

### 6. Blacklist Region Artifacts
Repetitive and high-signal artifact regions inflate peak counts and FRiP. The workflow
filters the BAM against the ENCODE blacklist (Amemiya et al. 2019) before peak calling.
The hg38-blacklist.v2.bed contains ~900 regions covering ~40 Mb.

## Pipeline Scripts

| File | Description |
|------|-------------|
| `scripts/main.nf` | Nextflow DSL2 pipeline |
| `scripts/nextflow.config` | Execution profiles (local/slurm/gcp/aws) |
| `scripts/Dockerfile` | Docker image with all pipeline tools |

The image is pinned to `linux/amd64`; on an arm64 host it runs under emulation.

Tool versions in the image: BWA 0.7.18, samtools 1.17, bedtools 2.31.0, Picard 2.27.5,
Trim Galore 0.6.7, FastQC 0.11.9, MACS2 2.2.9.1, IDR 2.0.4.2, MultiQC 1.14,
deeptools 3.5.5, UCSC `bedGraphToBigWig`. The conda environment
`bioinformatics-installer/environments/chipseq-env.yml` is an alternative route for the
manual steps and may ship different point releases of the same tools.

## ENCODE Data Integration

After running this pipeline on your own data, compare results with ENCODE:

```python
# Find matching ENCODE experiments
encode_search_experiments(
    assay_title="Histone ChIP-seq",
    target="H3K27ac",
    organ="pancreas",
    biosample_type="tissue"
)

# Download ENCODE peaks for comparison
encode_batch_download(
    download_dir="/data/encode_reference/",
    output_type="IDR thresholded peaks",
    target="H3K27ac",
    organ="pancreas",
    assembly="GRCh38"
)
```

## Pitfalls & Edge Cases

- **Input control is optional but strongly recommended**: MACS2 `-c` is only added when
  `--control` is given. Without it, enrichment is measured against the local lambda model,
  which is noisier.
- **Broad vs narrow peak mode**: H3K27me3, H3K36me3 and H3K9me3 need `--peak_type broad`.
  Narrow mode on broad marks fragments them into thousands of small peaks.
- **Duplicates are removed before peak calling**: Picard runs with `REMOVE_DUPLICATES=true`,
  and MACS2 then runs with `--keep-dup all` because the BAM is already deduplicated. There
  is no "mark only" mode.
- **Blacklist filtering happens before peak calling**: `bedtools intersect -v` is applied to
  the BAM between deduplication and MACS2, so peaks are already blacklist-clean.
- **Cross-correlation QC can mislead**: NSC/RSC values depend on fragment length
  distribution. Deeply sequenced libraries can have high NSC but poor enrichment. Check
  FRiP alongside NSC/RSC. Neither is computed by this workflow.
- **IDR here is a single two-replicate comparison**: the workflow sorts the per-sample peak
  files by name, takes the first two, and runs `idr` once. There is no pooled peak call, no
  pseudoreplicates, and no rescue or self-consistency ratio. With fewer than two peak files
  IDR is skipped silently. Extra replicates beyond the first two are dropped with a warning.

## Walkthrough: Processing ENCODE H3K27ac ChIP-seq from FASTQ to Peaks

**Goal**: Process raw H3K27ac ChIP-seq FASTQ files through this pipeline to generate peak
calls, an IDR comparison and signal tracks.
**Context**: BWA-MEM alignment, duplicate removal, blacklist filtering, MACS2 peak calling
and one IDR comparison between two replicates.

### Step 1: Find the experiment and download FASTQs

```
encode_get_experiment(accession="ENCSR000AKA")
```

Expected output:
```json
{
  "accession": "ENCSR000AKA",
  "assay_title": "Histone ChIP-seq",
  "target": "H3K27ac",
  "biosample_summary": "GM12878",
  "replicates": 2,
  "status": "released"
}
```

### Step 2: List FASTQ files

```
encode_list_files(experiment_accession="ENCSR000AKA", file_format="fastq")
```

Expected output:
```json
{
  "files": [
    {"accession": "ENCFF001FQ1", "output_type": "reads", "paired_end": "1", "biological_replicates": [1], "file_size_mb": 2400},
    {"accession": "ENCFF002FQ2", "output_type": "reads", "paired_end": "2", "biological_replicates": [1], "file_size_mb": 2500},
    {"accession": "ENCFF003FQ3", "output_type": "reads", "paired_end": "1", "biological_replicates": [2], "file_size_mb": 2200},
    {"accession": "ENCFF004FQ4", "output_type": "reads", "paired_end": "2", "biological_replicates": [2], "file_size_mb": 2300}
  ]
}
```

**Interpretation**: 2 biological replicates, each paired-end. Both replicates are needed for
the IDR step.

### Step 3: Download FASTQs

```
encode_download_files(file_accessions=["ENCFF001FQ1", "ENCFF002FQ2", "ENCFF003FQ3", "ENCFF004FQ4"], download_dir="/data/chipseq/fastq")
```

### Step 4: Name the files so a read-pair glob can find them

ENCODE accessions do not share a prefix within a pair, and the workflow matches file pairs
with a `{1,2}` glob. Link them into the shape the glob expects:

```bash
cd /data/chipseq/fastq
ln -s ENCFF001FQ1.fastq.gz chip_rep1_R1.fq.gz
ln -s ENCFF002FQ2.fastq.gz chip_rep1_R2.fq.gz
ln -s ENCFF003FQ3.fastq.gz chip_rep2_R1.fq.gz
ln -s ENCFF004FQ4.fastq.gz chip_rep2_R2.fq.gz
```

Do the same for the control library FASTQs using an `input_` prefix.

### Step 5: Run the ChIP-seq pipeline

```bash
nextflow run scripts/main.nf \
  -profile local \
  --reads '/data/chipseq/fastq/chip_*_R{1,2}.fq.gz' \
  --control '/data/chipseq/fastq/input_*_R{1,2}.fq.gz' \
  --genome GRCh38 \
  --peak_type narrow \
  --bwa_index /data/reference/GRCh38_index \
  --chrom_sizes /data/reference/GRCh38.chrom.sizes \
  --blacklist /data/reference/hg38-blacklist.v2.bed.gz \
  --outdir /data/chipseq/results
```

### Step 6: Validate output quality

From the workflow:
| Output | What to check |
|---|---|
| `qc/multiqc/multiqc_report.html` | Mapping rate (>80%), adapter content, per-base quality |
| `filtered/<sample>.dup_metrics.txt` | Duplication rate (<30%) |
| `peaks/narrow/<sample>_peaks.narrowPeak` | Peak count per replicate |
| `peaks/idr/idr_peaks.txt` | IDR peaks at 0.05 (>20,000 for TFs) |

Manual follow-ups (not run by this workflow): FRiP, NSC/RSC, NRF/PBC1/PBC2 and the
deeptools fingerprint. Commands are in `references/05-qc-metrics.md`.

### Step 7: Log provenance

```
encode_log_derived_file(
  file_path="/data/chipseq/results/peaks/idr/idr_peaks.txt",
  source_accessions=["ENCFF001FQ1", "ENCFF002FQ2", "ENCFF003FQ3", "ENCFF004FQ4"],
  description="IDR peaks from the ENCODE ChIP-seq pipeline skill, H3K27ac GM12878",
  file_type="idr_peaks",
  tool_used="pipeline-chipseq 1.0.0 (BWA 0.7.18, MACS2 2.2.9.1, IDR 2.0.4.2)",
  parameters="--genome GRCh38 --peak_type narrow"
)
```

### Integration with downstream skills
- IDR peaks feed into -> **peak-annotation** for gene assignment
- Signal tracks (bigWig) feed into -> **visualization-workflow** for genome browser display
- Peak coordinates feed into -> **histone-aggregation** for cross-experiment union merge
- QC metrics evaluated by -> **quality-assessment** against ENCODE standards
- Pipeline provenance logged by -> **data-provenance**

## Code Examples

### 1. Find ChIP-seq data to process

```
encode_search_experiments(
  assay_title="Histone ChIP-seq",
  organ="liver",
  target="H3K4me3"
)
```

Expected output:
```json
{
  "total": 15,
  "experiments": [
    {
      "accession": "ENCSR456LIV",
      "target": "H3K4me3-human",
      "biosample_summary": "liver tissue male adult (54 years)",
      "status": "released"
    }
  ]
}
```

### 2. Download FASTQ files for pipeline input

`encode_download_files` takes *file* accessions, so list the files first:

```
encode_list_files(experiment_accession="ENCSR456LIV", file_format="fastq")

encode_download_files(
  file_accessions=["ENCFF001REP1", "ENCFF002REP1"],
  download_dir="/data/chipseq/liver_h3k4me3"
)
```

Expected output:
```json
{
  "downloaded": 2,
  "total_size_mb": 6220.5,
  "files": [
    {"accession": "ENCFF001REP1", "md5_verified": true, "paired_end": "1"},
    {"accession": "ENCFF002REP1", "md5_verified": true, "paired_end": "2"}
  ]
}
```

## Integration

| This skill produces... | Feed into... | Purpose |
|---|---|---|
| IDR peaks (`peaks/idr/idr_peaks.txt`) | **peak-annotation** | Assign peaks to nearest genes |
| MACS2 peaks (narrowPeak/broadPeak) | **histone-aggregation** | Cross-experiment union merge for histone marks |
| Signal tracks (bigWig) | **visualization-workflow** | Genome browser visualization |
| Peak coordinates (BED) | **motif-analysis** | De novo motif discovery in peak regions |
| Filtered peaks | **regulatory-elements** | Classify as enhancers, promoters, insulators |
| QC metrics | **quality-assessment** | Validate against ENCODE ChIP-seq standards |
| `pipeline_info/` reports | **data-provenance** | Record tool versions and parameters |
| Peak files | **variant-annotation** | Identify variants in ChIP-seq peaks |

## Related Skills

- **pipeline-guide** (parent): General pipeline selection and resource assessment
- **histone-aggregation**: Merge peaks across samples/replicates after peak calling
- **quality-assessment**: Deep-dive QC analysis beyond basic metrics
- **regulatory-elements**: Annotate peaks with regulatory element classifications
- **peak-annotation**: Annotate peaks with gene associations
- **compare-biosamples**: Compare ChIP-seq profiles across cell types
- **publication-trust**: Verify literature claims backing analytical decisions

## Presenting Results

When reporting ChIP-seq pipeline results:

- **Pipeline status**: Report completion status for each stage (QC, alignment, filtering,
  peak calling, IDR, signal generation) with pass/fail indicators
- **Key QC metrics from the run**: mapping rate and read counts (`samtools flagstat`,
  MultiQC), duplication rate (Picard `dup_metrics.txt`), peak counts per replicate, and
  the IDR peak count. State plainly that FRiP, NSC/RSC and NRF/PBC were not computed unless
  the user ran the manual steps
- **Peak counts**: Report the per-replicate MACS2 peak count and the IDR peak count at the
  0.05 threshold. Note the `--peak_type` used. There are no optimal/conservative/
  pseudoreplicated peak sets in this workflow
- **Signal tracks**: Provide paths to the fold-enrichment (`signal/<sample>.fc.bw`) and
  p-value (`signal/<sample>.pval.bw`) tracks
- **Traffic light summary**: Use green/yellow/red for overall sample quality, and say which
  metrics were unavailable
- **Output paths**: List the key output directories (`peaks/idr/`, `peaks/<narrow|broad>/`,
  `signal/`, `qc/multiqc/`, `pipeline_info/`)
- **Next steps**: Suggest `quality-assessment` for deeper QC evaluation, or
  `visualization-workflow` for genome browser session generation

## For the request: "$ARGUMENTS"
