# Pipeline DNase-seq -- ENCODE DNase-seq Processing with Hotspot2

> **Category:** Pipeline Execution | **Tools Used:** `encode_search_experiments`, `encode_list_files`, `encode_download_files`, `encode_log_derived_file`

## What This Skill Does

Runs the ENCODE DNase-seq pipeline end-to-end: BWA-MEM alignment, Hotspot2 peak calling for DNase hypersensitive sites (DHSs), and optional HINT (RGT) footprinting in DNase-seq mode. Implemented as a Nextflow DSL2 workflow with Docker, SLURM, GCP, and AWS profiles. Hotspot2 is the ENCODE-standard peak caller for DNase-seq -- it is not MACS2.

## When to Use This

- You have paired-end DNase-seq FASTQ files (from ENCODE or your own lab) and need DHS peaks.
- You need footprinting analysis to identify bound transcription factors from accessibility signal.
- You want a SPOT score and hotspot counts computed the way ENCODE computes them.

## Example Session

> "Run the ENCODE DNase-seq pipeline on human pancreas tissue DNase-seq, call DHSs, and perform footprinting."

### Step 1: Find and Download DNase-seq Data

```
encode_search_experiments(
    assay_title="DNase-seq", organ="pancreas",
    biosample_type="tissue", status="released", limit=25
)
```

```
DNase-seq (3):  ENCSR891VQR (M,34y,PE), ENCSR244ISL (F,30y,PE), ENCSR003BFZ (M,54y,SE)
```

Note the third experiment is single-end -- older ENCODE DNase-seq libraries were often sequenced SE. This workflow pairs reads with `fromFilePairs` and trims and aligns them as pairs, so it processes paired-end libraries only; for the single-end experiment use ENCODE's processed peaks instead. Download the paired-end FASTQs:

```
encode_list_files(experiment_accession="ENCSR891VQR", file_format="fastq", assembly="GRCh38")
encode_download_files(
    file_accessions=["ENCFF123ABC", "ENCFF456DEF"],
    download_dir="/data/pancreas_dnase/fastq", organize_by="experiment"
)
```

### Step 2: Run the Pipeline

ENCODE names FASTQs by accession (`ENCFF123ABC.fastq.gz`), so link each pair to the
`<sample>_R1` / `<sample>_R2` names that the `--reads` pattern matches (the file's
`paired_end` value on the portal says which mate is which):

```bash
cd /data/pancreas_dnase/fastq/ENCSR891VQR
ln -s ENCFF123ABC.fastq.gz ENCSR891VQR_R1.fastq.gz
ln -s ENCFF456DEF.fastq.gz ENCSR891VQR_R2.fastq.gz
```

Hotspot2 needs a center-sites file, made once per genome and read length with
`extractCenterSites.sh` (in the image), and footprinting needs an RGT data directory:

```bash
# With footprinting
nextflow run skills/pipeline-dnaseseq/scripts/main.nf -profile local \
    --reads '/data/pancreas_dnase/fastq/ENCSR891VQR/*_R{1,2}.fastq.gz' \
    --bwa_index '/ref/bwa_index/genome.fa' --chrom_sizes '/ref/hg38.chrom.sizes' \
    --hotspot_center_sites '/ref/hotspot2/hg38.center_sites.n100.starch' \
    --hotspot_mappable '/ref/hotspot2/hg38.mappable_only.bed' \
    --blacklist '/ref/hg38-blacklist.v2.bed' \
    --rgt_data '/ref/rgtdata' --organism hg38 --outdir results_pe/ -resume

# Hotspots and signal only
nextflow run skills/pipeline-dnaseseq/scripts/main.nf -profile local \
    --reads '/data/pancreas_dnase/fastq/ENCSR244ISL/*_R{1,2}.fastq.gz' \
    --bwa_index '/ref/bwa_index/genome.fa' --chrom_sizes '/ref/hg38.chrom.sizes' \
    --hotspot_center_sites '/ref/hotspot2/hg38.center_sites.n100.starch' \
    --blacklist '/ref/hg38-blacklist.v2.bed' \
    --skip_footprint --outdir results_noftp/ -resume
```

Single-end reads also cannot resolve the TF protection patterns that footprinting needs (Vierstra et al. 2020), so paired-end data is strongly preferred whenever footprinting is planned.

### Step 3: Check QC -- SPOT Score and DHS Counts

The SPOT score (Signal Portion of Tags) is the DNase-seq equivalent of FRiP. It measures the fraction of reads in hotspots.

| Sample | SPOT | DHS Count | Mapping Rate | Dup Rate | Verdict |
|---|---|---|---|---|---|
| ENCSR891VQR | 0.52 | 112,340 | 91% | 18% | Pass |
| ENCSR244ISL | 0.38 | 87,210 | 88% | 22% | Pass |

SPOT > 0.4 is ideal; 0.2-0.4 is acceptable with documentation. The workflow writes the score to `hotspots/<sample>.SPOT.txt`; older single-end libraries typically show higher duplication and fewer DHSs.

### Step 4: DNase-seq vs ATAC-seq -- Why Hotspot2 Matters

Hotspot2 differs from MACS2 (used for ATAC-seq) in a critical way: it incorporates a mappability correction. DNase I cuts accessible chromatin regardless of whether the underlying sequence is uniquely mappable, so without mappability adjustment, repetitive open regions produce false negatives. The mappable-regions file behind `--hotspot_center_sites` must match your read length -- center sites built for 36 bp reads give incorrect calls on 150 bp reads.

Fragment size distributions also differ. DNase-seq peaks at 50-100 bp (sub-nucleosomal cuts at DHSs) with a secondary peak at 150-200 bp (mononucleosomal). ATAC-seq instead shows a nucleosomal ladder from Tn5 insertion. An abnormal DNase-seq size distribution points to a library preparation problem, not a computational one.

### Step 5: Inspect Footprinting Output

Where footprinting was run, the output is `results_pe/footprints/ENCSR891VQR.footprints.bed` (34,218 footprints in this example). The workflow stops there: it does not match footprints to motifs or write per-motif scores, so motif analysis is a separate step (see **motif-analysis**).

Footprints are depressions in the DNase signal where a bound TF shields DNA from cleavage. Reliable footprinting requires deep sequencing (100M+ reads). Pioneer factors like FOXA2 produce shallow footprints that are harder to detect than zinc-finger TFs with strong protection signatures.

### Step 6: Log Provenance

```
encode_log_derived_file(
    file_path="/data/pancreas_dnase/results_pe/hotspots/ENCSR891VQR.hotspots.fdr0.05.bed",
    source_accessions=["ENCSR891VQR", "ENCFF123ABC", "ENCFF456DEF"],
    description="DNase hypersensitive sites from ENCODE DNase-seq pipeline, human pancreas",
    file_type="DHS_peaks",
    tool_used="BWA 0.7.18 + Hotspot2 2.1.2 + RGT-HINT 1.0.2",
    parameters="FDR 0.05, hg38 center sites (n100), blacklist v2"
)
```

## Key Principles

- **Hotspot2, not MACS2.** ENCODE uses Hotspot2 for DNase-seq because it models mappability. Running MACS2 on DNase-seq data will produce peaks, but they will not match ENCODE standards and will miss regions in low-mappability accessible chromatin.
- **Match your mappability index to read length.** A mismatched index silently corrupts peak calls. Check that the center sites passed to `--hotspot_center_sites` were built for your FASTQ read length before running.
- **Paired-end only.** This workflow does not process single-end libraries, and single-end data cannot support footprinting anyway. For single-end ENCODE experiments, use the portal's processed peaks and merge at the peak level.
- **Always apply the ENCODE Blacklist.** Amemiya et al. 2019 is non-negotiable for accessibility data. Blacklist regions produce artifactual signal that inflates DHS counts and SPOT scores.

## Related Skills

- **pipeline-atacseq** -- The ATAC-seq counterpart using Bowtie2 and MACS2 instead of BWA and Hotspot2.
- **accessibility-aggregation** -- Merge DHS peaks across samples into a union catalog, combining DNase-seq and ATAC-seq.
- **quality-assessment** -- Evaluate SPOT, NRF, and PBC metrics against ENCODE thresholds before downstream analysis.
- **pipeline-guide** -- Parent skill for compute resource planning and cloud deployment configuration.

---
*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 47 skills for genomics research*
