# Pipeline Guide -- Choosing and Running ENCODE Pipelines

> **Category:** Workflow | **Tools Used:** `encode_search_experiments`, `encode_list_files`, `encode_download_files`

## What This Skill Does

Helps scientists select the correct pipeline for their data, assess compute requirements, and connect to the assay-specific child pipeline skills that ship executable Nextflow workflows. This is the entry point for all pipeline execution tasks.

## When to Use This

- You have raw FASTQ files from a sequencing core and need to know which pipeline to run.
- You want to understand the compute resources (CPU, RAM, disk) required before committing to a run.
- You need to decide between running locally, on an HPC cluster, or in the cloud.
- You are unsure which output files a pipeline produces or which ones to use for downstream analysis.

## Two Things Called "the ENCODE Pipeline"

The **official ENCODE uniform pipelines** are WDL workflows executed with Caper/Cromwell:
[chip-seq-pipeline2](https://github.com/ENCODE-DCC/chip-seq-pipeline2),
[atac-seq-pipeline](https://github.com/ENCODE-DCC/atac-seq-pipeline),
[rna-seq-pipeline](https://github.com/ENCODE-DCC/rna-seq-pipeline),
[dnase-seq-pipeline](https://github.com/ENCODE-DCC/dnase-seq-pipeline),
[dna-me-pipeline](https://github.com/ENCODE-DCC/dna-me-pipeline) and
[hic-pipeline](https://github.com/ENCODE-DCC/hic-pipeline). ENCODE publishes none for CUT&RUN.

What this toolkit runs are its **own Nextflow DSL2 implementations** of the same standards, written by the ENCODE Toolkit author. Each `pipeline-*` skill ships `scripts/main.nf`, `scripts/nextflow.config` and `scripts/Dockerfile`, and builds its own image tagged `encode-toolkit/pipeline-<name>:1.0.0`. They need Nextflow and Docker (or Singularity on a cluster), and nothing from the WDL side.

## Example Session

### Scientist's Request

> "I have ChIP-seq FASTQs from our sequencing core -- H3K27ac on human pancreatic islets, paired-end 150bp. How do I process them to get peak calls?"

### Step 1: Identify the Right Pipeline

Claude recognizes this as a histone ChIP-seq experiment and routes it to the child skill.

**Toolkit skill:** `pipeline-chipseq` -- BWA-MEM, samtools/Picard filtering, MACS2, IDR
**Standard followed:** `ENCODE-DCC/chip-seq-pipeline2` (WDL) -- the reference implementation, not what runs here
**Image:** `encode-toolkit/pipeline-chipseq:1.0.0`, built from the skill's `scripts/Dockerfile`
**Key outputs:** MACS2 peaks, per-pair IDR results, fold-change and p-value bigWigs, filtered BAM

For H3K27ac, MACS2 runs in narrow mode (`--peak_type narrow`, the default). Broad marks like H3K27me3 or H3K36me3 need `--peak_type broad`, which swaps `--call-summits` for `--broad --broad-cutoff 0.1` and skips IDR. One run uses one peak type for every sample, so mixed targets mean two runs with different `--outdir` values.

### Step 2: Assess Compute Resources

Claude checks the scientist's system against what the workflow requests.

| Requirement | What the workflow asks for | Scientist's System |
|---|---|---|
| CPU | 8 cores for `BWA_MEM`, 4 by default, 2 for MACS2 and signal tracks | 8 cores |
| RAM | 32 GB for `BWA_MEM` per attempt, 16 GB elsewhere | 32 GB |
| Disk | 50 GB free (the skill's stated minimum) | 200 GB free |
| Container | Docker, or Singularity for `-profile slurm` | Docker installed |

The system covers those requests. `process.resourceLimits` caps every request at `--max_cpus`, `--max_memory` and `--max_time` (defaults `16`, `64.GB`, `24.h`), so on a smaller host lower the cap instead of editing processes. The BWA index for GRCh38 needs roughly 8 GB of disk, far less than the ~30 GB STAR index that `pipeline-rnaseq` requires.

### Step 3: Run the Child Pipeline Skill

Claude invokes the **pipeline-chipseq** skill, whose workflow has five processing stages: adapter trimming and QC, BWA-MEM alignment, duplicate marking and filtering, MACS2 peak calling with IDR, and signal tracks with FRiP. Build the image once, then run it:

```bash
docker build -t encode-toolkit/pipeline-chipseq:1.0.0 skills/pipeline-chipseq/scripts/

nextflow run skills/pipeline-chipseq/scripts/main.nf \
    -profile local \
    --reads 'fastq/chip_*_R{1,2}.fq.gz' \
    --control 'fastq/input_*_R{1,2}.fq.gz' \
    --genome GRCh38 \
    --peak_type narrow \
    --bwa_index GRCh38_index \
    --chrom_sizes GRCh38.chrom.sizes \
    --outdir results/h3k27ac \
    -resume
```

`--reads` and `--chrom_sizes` are required and the run stops before the first task without them. `--bwa_index` is a directory holding `GRCh38.fa` and its BWA index files; the workflow never builds or downloads one. Keep the `--reads` and `--control` globs on different prefixes, or the control is processed twice -- once as a control and once as a ChIP sample.

The `-resume` flag is critical. If any step fails, rerunning the command picks up from the last successful step rather than starting over.

### Step 4: Understand Pipeline Outputs

After the run completes, the key output files are:

| File | Format | Use For |
|---|---|---|
| `peaks/narrow/<sample>_peaks.narrowPeak` | bed narrowPeak | Enhancer identification, overlap analysis |
| `peaks/idr/<sampleA>_vs_<sampleB>.idr_peaks.txt` | IDR table (+ `.png`) | Reproducibility between one pair of replicates |
| `signal/<sample>.fc.bw` and `.pval.bw` | bigWig | Genome browser visualization, heatmaps |
| `filtered/<sample>.final.bam` | BAM | Custom reprocessing, coverage plots |
| `qc/<sample>.frip_mqc.tsv`, `qc/multiqc/multiqc_report.html` | TSV / HTML | FRiP and the aggregated QC report |

IDR runs once for every pair of samples at threshold 0.05 -- two samples give one comparison, three give three -- and only in narrow runs. This is not the full ENCODE IDR protocol: there is no pooled or pseudoreplicate analysis and no rescue or self-consistency ratio. NSC, RSC, NRF and PBC are not computed either; the **quality-assessment** skill covers those manual steps.

## Child Pipeline Skills

When Claude identifies the assay type, it delegates to the appropriate child skill.

| Your Data | Claude Uses | Aligner | Peak/Quant Caller |
|---|---|---|---|
| Histone or TF ChIP-seq | `pipeline-chipseq` | BWA-MEM | MACS2 + IDR |
| ATAC-seq | `pipeline-atacseq` | Bowtie2 | MACS2 on Tn5-shifted, nucleosome-free fragments + IDR |
| RNA-seq | `pipeline-rnaseq` | STAR 2-pass | RSEM, plus kallisto unless skipped |
| Whole-genome bisulfite | `pipeline-wgbs` | Bismark | MethylDackel |
| Hi-C | `pipeline-hic` | BWA | pairtools, Juicer `.hic` / cooler `.mcool`, HiCCUPS loops |
| DNase-seq | `pipeline-dnaseseq` | BWA | hotspot2, optional `rgt-hint` footprinting |
| CUT&RUN / CUT&Tag | `pipeline-cutandrun` | Bowtie2 | SEACR and/or MACS2, spike-in scaled |

Each child skill ships a Nextflow workflow, a `nextflow.config` with the `local`, `slurm`, `gcp` and `aws` profiles, a Dockerfile, and five stage-specific reference files. Required parameters differ per pipeline -- Hi-C, DNase-seq and CUT&RUN each need their index, `--chrom_sizes` and more -- so read the child skill before the first run.

## Execution Environments

| Environment | Best For | Setup |
|---|---|---|
| Local (Docker) | 1-10 samples, fast turnaround | `docker build -t encode-toolkit/pipeline-chipseq:1.0.0 skills/pipeline-chipseq/scripts/`, then `-profile local` |
| HPC (SLURM + Singularity) | 10-100 samples, shared cluster | `singularity build pipeline-chipseq.sif docker-daemon://encode-toolkit/pipeline-chipseq:1.0.0`, then `-profile slurm --container /path/to/pipeline-chipseq.sif` |
| Google Cloud Batch | No local compute, pay-per-use | `-profile gcp` with `--gcp_project`, `--gcp_workdir gs://<bucket>/work` and a registry image; spot VMs are on by default (rough estimate: $2-5 per ChIP-seq sample) |
| AWS Batch | Large-scale production | `-profile aws` with `--aws_queue`, `--aws_workdir s3://<bucket>/work` and a registry image |
| Terra / DNAnexus | Running the official WDL pipelines | WDL platforms; the toolkit's Nextflow workflows do not run there |

## Related Skills

- **pipeline-chipseq** through **pipeline-cutandrun** -- The seven child skills with executable Nextflow pipelines.
- **download-encode** -- Retrieve the ENCODE FASTQ files that feed these pipelines.
- **quality-assessment** -- Evaluate pipeline QC outputs, and run the metrics the workflows do not compute.
- **data-provenance** -- Log every pipeline run with inputs, versions, parameters, and checksums.

---

*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 47 skills for genomics research*
