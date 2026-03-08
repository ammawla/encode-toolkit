# Pipeline ATAC-seq -- ENCODE-Standard Processing from FASTQ to Peaks

> **Category:** Pipeline Execution | **Tools Used:** `encode_search_experiments`, `encode_download_files`, `encode_log_derived_file`

## What This Skill Does

Runs the ENCODE ATAC-seq pipeline end-to-end: Bowtie2 alignment, Tn5 transposase offset correction (+4/-5 bp), mitochondrial read removal, nucleosome-free fragment selection, MACS2 peak calling without input control, IDR reproducibility analysis, and TSS enrichment scoring. Delivered as a Nextflow DSL2 pipeline with Docker containers and cloud deployment profiles.

## When to Use This

- You have raw ATAC-seq FASTQ files and need ENCODE-compliant peaks and signal tracks.
- You want to compare your ATAC-seq data against ENCODE reference experiments on equal footing.
- You need publication-ready processing with full provenance (tool versions, parameters, QC metrics).

## Example Session

> "Process paired-end ATAC-seq from human pancreatic islets through the ENCODE pipeline."

### Step 1: Run the Pipeline

```bash
nextflow run scripts/main.nf \
  -profile local \
  --reads 'fastq/islet_*_R{1,2}.fq.gz' \
  --genome GRCh38 \
  --outdir results/
```

The pipeline executes five stages automatically:

| Stage | Tool | What Happens |
|-------|------|-------------|
| QC & Trimming | FastQC, Trim Galore | Adapter removal, quality filtering |
| Alignment | Bowtie2 `--very-sensitive` | Short-fragment-optimized mapping |
| Tn5 Shift & Filtering | samtools, bedtools, Picard | Offset correction, mito removal, dedup |
| Peak Calling | MACS2, IDR | NFR-only peaks, replicate consistency |
| QC & Signal | deeptools, ataqv, MultiQC | bigWig tracks, TSS enrichment, QC report |

### Step 2: Tn5 Offset Correction (Key ATAC-seq Step)

The Tn5 transposase creates a 9-bp target site duplication when inserting adapters. To locate the true cut site, the pipeline shifts every aligned read:

- **Forward strand (+):** shift +4 bp
- **Reverse strand (-):** shift -5 bp

This correction is essential for footprinting and motif analysis. Without it, cut-site positions are offset by ~4.5 bp, blurring TF binding signatures (Buenrostro et al. 2013).

### Step 3: Mitochondrial Read Removal

Mitochondrial DNA is nucleosome-free and highly accessible, acting as a sponge for Tn5. A typical ATAC-seq library captures 30-80% mitochondrial reads. The pipeline filters all chrM reads after alignment, before any downstream analysis.

If mitochondrial fraction exceeds 50%, the cell lysis step likely needs optimization -- the data is still processable but read depth after filtering may be insufficient.

### Step 4: Nucleosome-Free Fragment Selection

ATAC-seq produces a characteristic nucleosomal ladder:

| Fragment Class | Size Range | Used For |
|---------------|-----------|----------|
| Nucleosome-free (NFR) | <150 bp | Peak calling, TF footprinting |
| Mono-nucleosome | 150-300 bp | Nucleosome positioning |
| Di-nucleosome | 300-500 bp | Chromatin compaction analysis |

The pipeline separates NFR fragments (<150 bp) and calls peaks only on these. Mixing nucleosomal fragments into peak calling conflates TF binding signal with nucleosome occupancy.

### Step 5: Evaluate QC Output

After the pipeline finishes, check `results/qc/` for the aggregated MultiQC report. The critical metrics:

| Metric | Threshold | Your Result | Verdict |
|--------|-----------|-------------|---------|
| TSS enrichment | >=6 | 8.4 | Pass |
| Mitochondrial fraction | <20% | 12% | Pass |
| FRiP | >=0.3 | 0.38 | Pass |
| NRF | >=0.8 | 0.87 | Pass |
| IDR optimal peaks | >50,000 | 74,218 | Pass |

**TSS enrichment is the single most informative metric.** A score below 5 indicates a failed experiment regardless of what other metrics show. Scores above 7 are excellent (Yan et al. 2020).

### Step 6: Compare Against ENCODE Reference

```
encode_search_experiments(assay_title="ATAC-seq", organ="pancreas", biosample_type="tissue")
encode_download_files(
    file_accessions=["ENCFF635JIA"],
    download_dir="/data/encode_reference/", organize_by="flat")
```

Intersect your peaks with ENCODE reference peaks using bedtools to quantify concordance.

### Step 7: Log Provenance

```
encode_log_derived_file(
    file_path="results/peaks/idr/islet_idr_peaks.narrowPeak",
    source_accessions=["local_islet_atac_rep1", "local_islet_atac_rep2"],
    description="IDR thresholded ATAC-seq peaks, human islets, 2 bio reps",
    file_type="idr_peaks",
    tool_used="ENCODE ATAC-seq pipeline (Bowtie2 2.5.1, MACS2 2.2.9.1, IDR 2.0.4)",
    parameters="--genome GRCh38 --nfr_max 150, Tn5 shift +4/-5, blacklist v2 filtered")
```

## Common Pitfalls

- **Using BWA instead of Bowtie2.** Bowtie2 handles short NFR fragments (<150 bp) better than BWA-MEM. The pipeline uses `--very-sensitive` mode by default.
- **Skipping Tn5 shift.** Peak calling is minimally affected, but motif enrichment and footprinting analyses will be degraded. Always apply the shift.
- **Calling peaks on all fragments.** Size-select NFR (<150 bp) first. Full-fragment peak calling mixes open chromatin signal with nucleosome positions.
- **No input control needed.** Unlike ChIP-seq, ATAC-seq uses MACS2's local background model. Do not provide an input BAM.

## Related Skills

- **pipeline-guide** -- Parent skill for selecting the right pipeline for your assay type.
- **accessibility-aggregation** -- Merge your peaks with ENCODE peaks into a union catalog.
- **quality-assessment** -- Deep-dive QC when TSS enrichment or other metrics are borderline.
- **motif-analysis** -- Find enriched TF motifs in your NFR peaks (HOMER, MEME).
- **regulatory-elements** -- Classify peaks as promoters, enhancers, or insulators using histone marks.

---
*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 43 skills for genomics research*
