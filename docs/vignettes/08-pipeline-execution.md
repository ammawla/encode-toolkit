# Running ENCODE-Standard Pipelines

> This vignette demonstrates how the ENCODE MCP plugin guides you through setting up
> and running official ENCODE analysis pipelines for processing raw sequencing data.

**Prerequisites:** You have downloaded raw FASTQ files from ENCODE and have Docker or
Singularity installed. See [Download & Track](02-download-and-track.md) if needed.

**Skills demonstrated:** `pipeline-guide`, `quality-assessment`, `download-encode`

---

## Scenario

You have raw FASTQ files from three ENCODE assays -- ChIP-seq, ATAC-seq, and RNA-seq --
on human pancreas tissue. You need to process them through ENCODE-standard pipelines to
generate peak calls, signal tracks, and QC metrics comparable to ENCODE portal outputs.

---

## Step 1: Choose the Right Pipeline

**You ask Claude:** "I have ChIP-seq FASTQs from ENCODE. What pipeline should I use?"

**Claude uses the pipeline-guide skill** to match assay type to the correct pipeline:

| Assay | Container | Workflow Manager |
|-------|-----------|-----------------|
| ChIP-seq | `encodedcc/chip-seq-pipeline:v2.2.1` | Cromwell / Nextflow DSL2 |
| ATAC-seq | `encodedcc/atac-seq-pipeline:v2.2.0` | Cromwell / Nextflow DSL2 |
| RNA-seq | `encodedcc/rna-seq-pipeline:v1.2.0` | Cromwell / Nextflow DSL2 |
| WGBS | `encodedcc/wgbs-pipeline:v2.0.0` | Cromwell |
| Hi-C | `encodedcc/hic-pipeline:v2.0.0` | Cromwell |
| DNase-seq | `encodedcc/dnase-seq-pipeline:v1.1.0` | Cromwell |
| CUT&RUN | `encodedcc/cutandrun-pipeline:v1.0.0` | Cromwell |

All pipelines support local Docker, SLURM + Singularity, Google Cloud, and AWS Batch.

---

## Step 2: ChIP-seq Pipeline Setup

**You ask Claude:** "Walk me through setting up the ChIP-seq pipeline for H3K27me3"

**Claude uses the pipeline-guide skill** to walk through seven stages:

1. **Read QC** -- FastQC assessment, adapter trimming with cutadapt (discard < 20 bp)
2. **Alignment** -- BWA-MEM to GRCh38 (index files bundled in container)
3. **Filtering** -- Picard deduplication, MAPQ >= 30, blacklist removal (`hg38-blacklist.v2.bed`)
4. **Peak calling** -- MACS2: narrowPeak for H3K4me3/H3K27ac/H3K4me1, broadPeak for H3K27me3/H3K9me3/H3K36me3
5. **Replicate analysis** -- IDR for replicated experiments, pseudoreplication for single-donor tissue
6. **Signal tracks** -- BigWig generation (fold-change over control, signal p-value)
7. **QC metrics** -- FRiP, NSC, RSC, NRF, PBC1/PBC2 written to QC report JSON

**Nextflow configuration:**

```nextflow
profiles {
  local { process.executor = 'local';  docker.enabled = true;  process.memory = '16 GB' }
  slurm { process.executor = 'slurm';  singularity.enabled = true; process.time = '24h' }
  gcp   { process.executor = 'google-lifesciences'; google.project = 'my-project-id' }
  aws   { process.executor = 'awsbatch'; process.queue = 'my-batch-queue' }
}
```

**Running the pipeline:**

```bash
nextflow run ENCODE-DCC/chip-seq-pipeline2 \
  -profile local \
  --input input.json \
  --genome GRCh38 \
  --pipeline_type histone \
  --broad_peak true
```

The input JSON specifies FASTQ paths for experiment and control replicates, the genome
reference TSV (hosted at `storage.googleapis.com/encode-pipeline-genome-data`), and
pipeline parameters such as `pipeline_type: histone` and `always_use_pooled_ctl: true`.

---

## Step 3: ATAC-seq Pipeline

**You ask Claude:** "I also have ATAC-seq data. How is that pipeline different?"

**Claude uses the pipeline-guide skill** to highlight key differences:

| Parameter | ChIP-seq | ATAC-seq |
|-----------|----------|----------|
| Aligner | BWA-MEM | Bowtie2 |
| Tn5 shift | N/A | +4 bp / -5 bp offset applied |
| Mitochondrial reads | Kept | Removed (often 30-60% of raw reads) |
| Peak caller | MACS2 default | MACS2 `--shift -75 --extsize 150` |
| Control sample | Input or IgG required | No control needed |

```bash
nextflow run ENCODE-DCC/atac-seq-pipeline2 \
  -profile local \
  --input input.json \
  --genome GRCh38
```

The Tn5 transposase shift is critical: without the +4/-5 bp offset correction, insertion
sites will be systematically displaced. The ENCODE pipeline applies this automatically --
do not apply the shift manually before running.

---

## Step 4: RNA-seq Pipeline

**You ask Claude:** "And for RNA-seq quantification?"

**Claude uses the pipeline-guide skill** to describe the workflow:

- **Alignment:** STAR two-pass to GRCh38 with GENCODE v29 annotations
- **Quantification:** RSEM (gene + transcript TPM/FPKM) and Kallisto in parallel
- **Signal:** Strand-specific bigWig tracks (plus and minus strand separately)

```bash
nextflow run ENCODE-DCC/rna-seq-pipeline \
  -profile local \
  --input input.json \
  --genome GRCh38 \
  --endedness paired
```

Check strandedness carefully: most ENCODE RNA-seq libraries are reverse-stranded (dUTP
method), but older experiments may be unstranded. The experiment metadata on the portal
specifies this under library details.

---

## Step 5: Cloud Cost Estimates

**You ask Claude:** "How much will this cost to run on Google Cloud?"

| Assay | Instance | Time | Cost (preemptible) |
|-------|----------|------|--------------------|
| ChIP-seq (histone) | n1-highmem-8 | 4-6 hr | $2-5 |
| ChIP-seq (TF) | n1-highmem-8 | 6-10 hr | $5-10 |
| ATAC-seq | n1-highmem-8 | 3-5 hr | $2-4 |
| RNA-seq | n1-highmem-16 | 2-4 hr | $3-8 |
| WGBS | n1-highmem-16 | 12-24 hr | $15-30 |
| Hi-C | n1-highmem-32 | 8-16 hr | $10-25 |

Storage per experiment: 10-50 GB (FASTQs 2-10 GB, BAMs 3-15 GB, signal tracks 0.5-2 GB,
peaks 10 KB-5 MB). Non-preemptible instances cost 3-5x more. Institutional HPC with
SLURM avoids cloud costs entirely.

---

## Step 6: QC Thresholds

**You ask Claude:** "What QC metrics should I check after the pipeline finishes?"

**Claude uses the quality-assessment skill:**

**ChIP-seq:** FRiP >= 1%, NSC > 1.05, RSC > 0.8, NRF >= 0.8, PBC1 >= 0.8

**ATAC-seq:** TSS enrichment >= 5, FRiP >= 20%, mitochondrial fraction < 5% after
filtering, clear nucleosomal banding in fragment size distribution

**RNA-seq:** Uniquely mapped > 70%, rRNA < 10%, exonic fraction > 60% (polyA libraries),
gene detection > 15,000 genes at TPM > 0.1

**ENCODE audit levels:** ERROR > NOT_COMPLIANT > WARNING > INTERNAL_ACTION. Experiments
with ERROR or NOT_COMPLIANT flags should be used with caution or excluded.

---

## Other Pipeline Skills Available

- **pipeline-wgbs** -- Bismark alignment, methylation extraction, PMD/HMR/UMR segmentation
- **pipeline-hic** -- BWA-MEM alignment, pairtools filtering, cooler matrices, loop calling
- **pipeline-dnaseseq** -- hotspot2 peak calling, signal generation, FRiP/spot score QC
- **pipeline-cutandrun** -- Bowtie2 with spike-in calibration, SEACR peaks, IgG normalization

Ask Claude about any of these by name for detailed setup instructions.

---

## Best Practices

- **Pin container versions.** Different versions produce subtly different results.
- **Never mix assemblies.** Use GRCh38 for all human samples, mm10 for all mouse samples.
- **Run end-to-end.** Partial runs with custom intermediate steps break comparability
  with ENCODE portal data.
- **Check QC before downstream analysis.** Samples failing NSC/RSC produce unreliable peaks.
- **Log every run.** Use `encode_log_derived_file` to record pipeline version, parameters,
  and output paths for provenance.

---

## What's Next

- [Epigenomics Workflow](03-epigenomics-workflow.md) -- Integrate processed ChIP-seq,
  ATAC-seq, and RNA-seq into a regulatory landscape
- [Quality Assessment](04-quality-assessment.md) -- Deep dive into interpreting QC metrics
