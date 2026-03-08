# Pipeline Guide -- Choosing and Running ENCODE Pipelines

> **Category:** Workflow | **Tools Used:** `encode_search_experiments`, `encode_list_files`, `encode_download_files`

## What This Skill Does

Helps scientists select the correct ENCODE uniform analysis pipeline for their data, assess compute requirements, and connect to the assay-specific child pipeline skills that generate executable Nextflow workflows. This is the entry point for all pipeline execution tasks.

## When to Use This

- You have raw FASTQ files from a sequencing core and need to know which pipeline to run.
- You want to understand the compute resources (CPU, RAM, disk) required before committing to a run.
- You need to decide between running locally, on an HPC cluster, or in the cloud.
- You are unsure which output files a pipeline produces or which ones to use for downstream analysis.

## Example Session

### Scientist's Request

> "I have ChIP-seq FASTQs from our sequencing core -- H3K27ac on human pancreatic islets, paired-end 150bp. How do I process them to get peak calls?"

### Step 1: Identify the Right Pipeline

Claude recognizes this as a histone ChIP-seq experiment and identifies the pipeline.

**Pipeline:** `ENCODE-DCC/chip-seq-pipeline2` (BWA-MEM + MACS2 + IDR)
**Container:** `encodedcc/chip-seq-pipeline:v2.2.1`
**Key outputs:** IDR thresholded peaks (narrowPeak), fold change over control (bigWig), filtered alignments (BAM)

For H3K27ac, MACS2 runs in narrow peak mode. Broad marks like H3K27me3 or H3K36me3 require `--broad` mode with different parameters. Claude selects the correct mode based on the target.

### Step 2: Assess Compute Resources

Claude checks the scientist's system to match pipeline requirements.

| Requirement | ChIP-seq Minimum | Scientist's System |
|---|---|---|
| CPU | 4 cores | 8 cores |
| RAM | 16 GB | 32 GB |
| Disk | 50 GB free | 200 GB free |
| Container | Docker or Singularity | Docker installed |

The system exceeds minimums. With 8 cores, alignment time drops from roughly 4 hours to 2 hours per sample. The BWA index for GRCh38 requires approximately 8 GB of disk, far less than the STAR index (30 GB) needed for RNA-seq.

### Step 3: Connect to the Child Pipeline Skill

Claude invokes the **pipeline-chipseq** skill, which generates a complete Nextflow DSL2 workflow tailored to the scientist's system. The child skill includes five processing stages: adapter trimming and QC, BWA-MEM alignment, duplicate marking and filtering, MACS2 peak calling, and IDR reproducibility analysis.

```
nextflow run chipseq_pipeline.nf \
    -profile local \
    --reads '/data/islets/H3K27ac_*.fastq.gz' \
    --genome GRCh38 \
    --outdir results/h3k27ac \
    -resume
```

The `-resume` flag is critical. If any step fails, rerunning the command picks up from the last successful step rather than starting over.

### Step 4: Understand Pipeline Outputs

After the run completes, the key output files are:

| File | Format | Use For |
|---|---|---|
| IDR thresholded peaks | bed narrowPeak | Enhancer identification, overlap analysis |
| Fold change over control | bigWig | Genome browser visualization, heatmaps |
| Filtered alignments | BAM | Custom reprocessing, coverage plots |
| QC metrics | JSON/TSV | Quality assessment (FRiP, NSC, RSC, NRF) |

Prioritize the IDR thresholded peaks for downstream work -- these are the reproducible peaks passing the 0.05 IDR threshold across biological replicates.

## Child Pipeline Skills

When Claude identifies the assay type, it delegates to the appropriate child skill.

| Your Data | Claude Uses | Aligner | Peak/Quant Caller |
|---|---|---|---|
| Histone or TF ChIP-seq | `pipeline-chipseq` | BWA-MEM | MACS2 + IDR |
| ATAC-seq | `pipeline-atacseq` | Bowtie2 | MACS2 (Tn5-adjusted) |
| RNA-seq | `pipeline-rnaseq` | STAR 2-pass | RSEM + Kallisto |
| Whole-genome bisulfite | `pipeline-wgbs` | Bismark | MethylDackel |
| Hi-C | `pipeline-hic` | BWA | Juicer + HiCCUPS |
| DNase-seq | `pipeline-dnaseseq` | BWA | Hotspot2 + HINT-ATAC |
| CUT&RUN / CUT&Tag | `pipeline-cutandrun` | Bowtie2 | SEACR + spike-in |

Each child skill includes a full Nextflow pipeline, Dockerfile, cloud deployment configs (local, SLURM, GCP, AWS), and five stage-specific reference files.

## Execution Environments

| Environment | Best For | Setup |
|---|---|---|
| Local (Docker) | 1-10 samples, fast turnaround | `docker pull encodedcc/chip-seq-pipeline:v2.2.1` |
| HPC (SLURM + Singularity) | 10-100 samples, shared cluster | `-profile slurm` in Nextflow config |
| Google Cloud | No local compute, pay-per-use | `-profile gcloud`, ~$2-5 per ChIP-seq sample |
| AWS Batch | Large-scale production | `-profile awsbatch`, spot instances for 60-80% savings |
| Terra (Broad) | WDL-native, ENCODE pipelines pre-installed | Upload FASTQs, select pipeline |

## Related Skills

- **pipeline-chipseq** through **pipeline-cutandrun** -- The seven child skills with executable Nextflow pipelines.
- **download-encode** -- Retrieve ENCODE reference files and genome indices needed by pipelines.
- **quality-assessment** -- Evaluate pipeline QC outputs against ENCODE standards.
- **data-provenance** -- Log every pipeline run with inputs, versions, parameters, and checksums.

---

*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 43 skills for genomics research*
