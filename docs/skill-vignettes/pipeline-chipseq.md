# Pipeline: ChIP-seq -- ENCODE-Standard Processing from FASTQ to Peaks

> **Category:** Pipeline Execution | **Tools Used:** `encode_search_experiments`, `encode_list_files`, `encode_download_files`, `encode_log_derived_file`

## What This Skill Does

Runs a complete ENCODE-standard ChIP-seq pipeline via Nextflow DSL2: FASTQ quality control, BWA-MEM alignment, filtering and deduplication, MACS2 peak calling, IDR reproducibility analysis, and signal track generation. Outputs narrowPeak/broadPeak files, fold-change bigWig tracks, and a comprehensive QC report.

## When to Use This

- You have raw ChIP-seq FASTQs and need ENCODE-compliant peak calls and signal tracks.
- You want to process your own data with the same pipeline used by the ENCODE DCC, then compare against ENCODE reference data.

## Example Session

A scientist processes paired-end H3K27ac ChIP-seq from two biological replicates of human pancreatic islets with a matched input control.

### Step 1: Download FASTQs from ENCODE

```
encode_list_files(
    experiment_accession="ENCSR831YAX",
    file_format="fastq", status="released"
)
```

```
encode_download_files(
    file_accessions=["ENCFF123ABC", "ENCFF456DEF", "ENCFF789GHI", "ENCFF012JKL"],
    download_dir="/data/chipseq/fastq", organize_by="flat"
)
```

Four FASTQ files downloaded: paired-end ChIP reads (R1/R2) and matched input control (R1/R2), all MD5-verified.

### Step 2: Set Up Local Docker Execution

```bash
docker pull encodedcc/chip-seq-pipeline:v2.2.1
```

The `nextflow.config` ships with four profiles (local, slurm, gcp, aws). The local profile allocates 8 CPUs / 32 GB to BWA-MEM, 16 GB to deduplication, and 8 GB to MACS2. Machines under 32 GB RAM should use the SLURM profile.

### Step 3: Run the Pipeline

```bash
nextflow run skills/pipeline-chipseq/scripts/main.nf \
  -profile local \
  --reads '/data/chipseq/fastq/chip_R{1,2}.fq.gz' \
  --control '/data/chipseq/fastq/input_R{1,2}.fq.gz' \
  --genome GRCh38 \
  --peak_type narrow \
  --outdir /data/chipseq/results
```

H3K27ac is a narrow active mark, so `--peak_type narrow` invokes `macs2 callpeak --call-summits` at q-value 0.05. For broad marks (H3K27me3, H3K36me3, H3K9me3), use `--peak_type broad` which adds `--broad --broad-cutoff 0.1`. The GRCh38 reference and ENCODE blacklist v2 auto-download on first run.

### Step 4: Interpret QC Output

Open `results/qc/multiqc/multiqc_report.html`. Key metrics for a passing H3K27ac experiment:

```
Metric                      Rep1       Rep2       Threshold      Verdict
------------------------------------------------------------------------
Total reads                 48.2M      51.7M      >=20M          PASS
Mapping rate                96.3%      95.8%      >80%           PASS
Duplication rate            18.4%      21.1%      <30%           PASS
NRF                         0.87       0.84       >=0.8          PASS
NSC                         1.14       1.11       >1.05          PASS
RSC                         1.02       0.97       >0.8           PASS
FRiP                        8.2%       7.5%       >=1%           PASS
MACS2 peaks (q<0.05)       68,412     71,088      --             --
IDR peaks (0.05 threshold)  42,316     --         >20,000        PASS
```

**FRiP** at 7-8% indicates strong enrichment -- active histone marks typically range 5-15%, while most TF experiments fall at 1-5%. **NSC/RSC** above thresholds confirm real strand-shift signal. **42,316 IDR peaks** shows excellent replicate reproducibility. Red flags: NRF below 0.8 (PCR bottleneck) or FRiP below 1% (weak enrichment or antibody failure).

### Step 5: Key Output Files

Use IDR peaks as your primary peak set, and fold-change bigWig for browser visualization.

```
results/peaks/idr/idr_peaks.txt        # 42,316 reproducible peaks (use these)
results/peaks/narrow/                   # Per-replicate narrowPeak files
results/signal/fold_change/*.fc.bw      # Fold-change-over-control bigWig
results/signal/pvalue/*.pval.bw         # Signal p-value bigWig
results/qc/multiqc/multiqc_report.html  # Aggregated QC report
```

### Step 6: Log Provenance

```
encode_log_derived_file(
    file_path="/data/chipseq/results/peaks/idr/idr_peaks.txt",
    source_accessions=["ENCSR831YAX"],
    description="IDR-filtered H3K27ac peaks from 2 replicates, ENCODE pipeline",
    file_type="idr_peaks",
    tool_used="ENCODE ChIP-seq pipeline v2.2.1 (BWA-MEM + MACS2 + IDR)",
    parameters="genome=GRCh38; peak_type=narrow; macs2 qvalue=0.05; idr threshold=0.05"
)
```

## Cloud Cost Estimates

| Platform | Instance | Cost/Sample | Wall Time | Notes |
|----------|----------|-------------|-----------|-------|
| Local | 8 cores, 32 GB | $0 | 3-6 hours | Docker required |
| GCP | n1-standard-8 (preemptible) | ~$2-5 | 2-4 hours | Preemptible saves 60-80% |
| AWS | m5.2xlarge (spot) | ~$2-5 | 2-4 hours | Spot instances recommended |
| SLURM | 8 cores, 32 GB | Varies | 2-4 hours | Singularity auto-mounted |

A 2-replicate experiment (~50M reads each, ~40 GB total) stays under $10 on preemptible/spot.

## Related Skills

- **pipeline-guide** (parent) -- Pipeline selection and resource planning.
- **quality-assessment** -- Deep-dive QC beyond the traffic-light summary.
- **histone-aggregation** -- Merge peaks across experiments after peak calling.

---
*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 43 skills for genomics research*
