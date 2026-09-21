# Pipeline: ChIP-seq -- ENCODE-Standard Processing from FASTQ to Peaks

> **Category:** Pipeline Execution | **Tools Used:** `encode_search_experiments`, `encode_list_files`, `encode_download_files`, `encode_log_derived_file`

## What This Skill Does

Runs an ENCODE-standard ChIP-seq pipeline via Nextflow DSL2: FASTQ quality control, BWA-MEM alignment, filtering and deduplication, MACS2 peak calling, an IDR comparison for every pair of replicates, FRiP calculation, and signal track generation. Outputs narrowPeak or broadPeak files, fold-change and p-value bigWig tracks, and a MultiQC report.

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
    file_accessions=["ENCFF123ABC", "ENCFF456DEF", "ENCFF789GHI", "ENCFF012JKL", "ENCFF345MNO", "ENCFF678PQR"],
    download_dir="/data/chipseq/fastq", organize_by="flat"
)
```

Six FASTQ files downloaded: two paired-end ChIP replicates and the matched input control, all MD5-verified.

ENCODE names every FASTQ after its accession (`ENCFF123ABC.fastq.gz`), with no `_R1`/`_R2` in the name, so the `--reads` glob cannot pair them. Take each file's mate from its page on encodeproject.org (`paired_end` is 1 or 2, `paired_with` names the other accession), then link them into the shape the globs expect:

```bash
cd /data/chipseq/fastq
ln -s ENCFF123ABC.fastq.gz chip_rep1_R1.fq.gz
ln -s ENCFF456DEF.fastq.gz chip_rep1_R2.fq.gz
ln -s ENCFF789GHI.fastq.gz chip_rep2_R1.fq.gz
ln -s ENCFF012JKL.fastq.gz chip_rep2_R2.fq.gz
ln -s ENCFF345MNO.fastq.gz input_rep1_R1.fq.gz
ln -s ENCFF678PQR.fastq.gz input_rep1_R2.fq.gz
```

The `chip_`/`input_` prefixes keep the `--reads` and `--control` globs from matching the same files -- overlapping globs would peak-call the input library and feed those peaks to IDR.

### Step 2: Build the Container Image

```bash
docker build -t encode-toolkit/pipeline-chipseq:1.0.0 skills/pipeline-chipseq/scripts/
```

The `nextflow.config` ships with four profiles (local, slurm, gcp, aws). Process resources are the same in every profile: 8 CPUs / 32 GB for BWA-MEM, 4 CPUs / 16 GB for deduplication, 2 CPUs / 8 GB for MACS2, and a 4-CPU / 16 GB default for everything else. Machines under 32 GB RAM never schedule the alignment task locally and should use the SLURM profile.

### Step 3: Run the Pipeline

```bash
nextflow run skills/pipeline-chipseq/scripts/main.nf \
  -profile local \
  --reads '/data/chipseq/fastq/chip_*_R{1,2}.fq.gz' \
  --control '/data/chipseq/fastq/input_*_R{1,2}.fq.gz' \
  --genome GRCh38 \
  --peak_type narrow \
  --bwa_index /data/reference/GRCh38_index \
  --chrom_sizes /data/reference/GRCh38.chrom.sizes \
  --outdir /data/chipseq/results
```

H3K27ac is a narrow active mark, so `--peak_type narrow` invokes `macs2 callpeak --call-summits` at q-value 0.05. For broad marks (H3K27me3, H3K36me3, H3K9me3), use `--peak_type broad`, which adds `--broad --broad-cutoff 0.1` and skips IDR. `--chrom_sizes` is required (`bedGraphToBigWig` needs it) and the BWA index directory must already hold `GRCh38.fa` plus its index files -- the workflow builds neither. Only the ENCODE blacklist v2 is downloaded on first run, when `--blacklist` is omitted.

### Step 4: Interpret QC Output

Open `results/qc/multiqc/multiqc_report.html`. Key metrics for a passing H3K27ac experiment:

```
Metric                      Rep1       Rep2       Threshold      Verdict
------------------------------------------------------------------------
Total reads                 48.2M      51.7M      >=20M          PASS
Mapping rate                96.3%      95.8%      >80%           PASS
Duplication rate            18.4%      21.1%      <30%           PASS
FRiP                        0.082      0.075      >=0.01         PASS
MACS2 peaks (q<0.05)       68,412     71,088      --             --
IDR peaks (0.05 threshold)  42,316     --         >20,000        PASS
```

**FRiP** at 0.075-0.082 indicates strong enrichment -- active histone marks typically sit at 0.05-0.15, while most TF experiments fall at 0.01-0.05. It is written as a fraction to `results/qc/<sample>.frip_mqc.tsv`, one row per peak set, and MultiQC picks that table up. **42,316 IDR peaks** shows excellent replicate reproducibility. Red flags: FRiP below 0.01 (weak enrichment or antibody failure) or a duplication rate above 30% (PCR bottleneck).

NRF/PBC1/PBC2 and the NSC/RSC strand-correlation metrics are ENCODE standards this workflow does not compute -- phantompeakqualtools is not in the image. Run them yourself against `filtered/<sample>.final.bam` if you need them, and say so when reporting.

### Step 5: Key Output Files

Use IDR peaks as your primary peak set, and fold-change bigWig for browser visualization.

```
results/peaks/idr/chip_rep1_vs_chip_rep2.idr_peaks.txt  # 42,316 reproducible peaks (use these)
results/peaks/narrow/                                    # Per-replicate narrowPeak, summits, bedGraphs
results/signal/chip_rep1.fc.bw                           # Fold-change-over-control bigWig
results/signal/chip_rep1.pval.bw                         # Signal p-value bigWig
results/qc/chip_rep1.frip_mqc.tsv                        # FRiP per peak set
results/qc/multiqc/multiqc_report.html                   # Aggregated QC report
```

IDR writes one file per pair of replicates, so two replicates give one file and three would give three. The control library passes through `aligned/`, `filtered/` and `fastqc/` under a `CONTROL_` prefix; it is never peak-called.

### Step 6: Log Provenance

```
encode_log_derived_file(
    file_path="/data/chipseq/results/peaks/idr/chip_rep1_vs_chip_rep2.idr_peaks.txt",
    source_accessions=["ENCFF123ABC", "ENCFF456DEF", "ENCFF789GHI", "ENCFF012JKL", "ENCFF345MNO", "ENCFF678PQR"],
    description="IDR peaks from 2 H3K27ac replicates with a matched input control",
    file_type="idr_peaks",
    tool_used="pipeline-chipseq 1.0.0 (BWA 0.7.18, MACS2 2.2.9.1, IDR 2.0.4.2)",
    parameters="--genome GRCh38 --peak_type narrow; macs2 qvalue=0.05; idr threshold=0.05"
)
```

The source accessions are the ENCODE FASTQs the run consumed, which is what the peaks were derived from.

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
*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 47 skills for genomics research*
