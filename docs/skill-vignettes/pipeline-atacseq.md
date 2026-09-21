# Pipeline ATAC-seq -- ENCODE-Standard Processing from FASTQ to Peaks

> **Category:** Pipeline Execution | **Tools Used:** `encode_search_experiments`, `encode_download_files`, `encode_log_derived_file`

## What This Skill Does

Runs the ENCODE ATAC-seq pipeline end-to-end: Bowtie2 alignment, Tn5 transposase offset correction (+4/-5 bp), mitochondrial read removal, nucleosome-free fragment selection, MACS2 peak calling without input control, an IDR comparison for every pair of replicates, and FRiP calculation. Delivered as a Nextflow DSL2 pipeline with Docker containers and cloud deployment profiles. TSS enrichment is a manual post-processing step -- the workflow does not compute it.

## When to Use This

- You have raw ATAC-seq FASTQ files and need ENCODE-compliant peaks and signal tracks.
- You want to compare your ATAC-seq data against ENCODE reference experiments on equal footing.
- You need publication-ready processing with full provenance (tool versions, parameters, QC metrics).

## Example Session

> "Process paired-end ATAC-seq from human pancreatic islets through the ENCODE pipeline."

### Step 1: Run the Pipeline

```bash
nextflow run skills/pipeline-atacseq/scripts/main.nf \
  -profile local \
  --reads 'fastq/islet_*_R{1,2}.fq.gz' \
  --genome GRCh38 \
  --bowtie2_index /data/reference/GRCh38_bowtie2_index \
  --outdir results/
```

The Bowtie2 index must already exist -- the workflow neither builds nor downloads it, and stops before the first task if the directory is missing. `--blacklist` is optional: without it the workflow downloads the ENCODE Blacklist v2 for `--genome`. The glob must match at least two replicates for IDR to run.

The pipeline executes five stages automatically:

| Stage | Tool | What Happens |
|-------|------|-------------|
| QC & Trimming | FastQC, Trim Galore `--nextera` | Adapter removal, quality filtering |
| Alignment | Bowtie2 `--very-sensitive` | Short-fragment-optimized mapping |
| Tn5 Shift & Filtering | samtools, Picard, deeptools `alignmentSieve`, bedtools | Mito removal, dedup, offset correction, blacklist, size selection |
| Peak Calling | MACS2, IDR | NFR-only peaks, one IDR comparison per replicate pair |
| Signal & QC | deeptools `bamCoverage`, bedtools, MultiQC | bigWig tracks, FRiP table, QC report |

### Step 2: Tn5 Offset Correction (Key ATAC-seq Step)

The Tn5 transposase creates a 9-bp target site duplication when inserting adapters. To locate the true cut site, the pipeline shifts every aligned read with `alignmentSieve --ATACshift`, after duplicate removal and before blacklist filtering:

- **Forward strand (+):** shift +4 bp
- **Reverse strand (-):** shift -5 bp

This correction is essential for footprinting and motif analysis. Without it, cut-site positions are offset by ~4.5 bp, blurring TF binding signatures (Buenrostro et al. 2013).

### Step 3: Mitochondrial Read Removal

Mitochondrial DNA is nucleosome-free and highly accessible, acting as a sponge for Tn5. A typical ATAC-seq library captures 30-80% mitochondrial reads. The pipeline filters all `--mito_name` reads (default `chrM`) after alignment, before any downstream analysis, and publishes the per-contig counts it used as `qc/<sample>.idxstats.txt`. Divide the mapped count on the `chrM` row by the sum of the mapped column to get the fraction, or read it from the samtools section of the MultiQC report.

If mitochondrial fraction exceeds 50%, the cell lysis step likely needs optimization -- the data is still processable but read depth after filtering may be insufficient.

### Step 4: Nucleosome-Free Fragment Selection

ATAC-seq produces a characteristic nucleosomal ladder:

| Fragment Class | Size Range | Used For |
|---------------|-----------|----------|
| Nucleosome-free (NFR) | <150 bp | Peak calling, TF footprinting |
| Mono-nucleosome | 150-300 bp | Nucleosome positioning |
| Di-nucleosome | 300-500 bp | Chromatin compaction analysis |

The pipeline writes an NFR BAM (below `--nfr_max`, default 150 bp) and a mono-nucleosome BAM (`--nfr_max` to 300 bp) to `filtered/nfr/`, and calls peaks only on the NFR BAM. Mixing nucleosomal fragments into peak calling conflates TF binding signal with nucleosome occupancy. The workflow does not plot the fragment size distribution.

### Step 5: Evaluate QC Output

After the pipeline finishes, open `results/qc/multiqc/multiqc_report.html`. The critical metrics:

| Metric | Threshold | Your Result | Read it from |
|--------|-----------|-------------|--------------|
| Mitochondrial fraction | <20% | 12% | `qc/<sample>.idxstats.txt` |
| FRiP | >=0.3 | 0.38 | `qc/<sample>.frip_mqc.tsv` |
| IDR peaks at 0.05 | >50,000 | 74,218 | `peaks/idr/islet_rep1_vs_islet_rep2.idr_peaks.txt` |
| TSS enrichment | >=5 (GRCh38) | 8.4 | manual -- not computed here |
| NRF | >=0.8 | 0.87 | manual -- not computed here |

**TSS enrichment is the single most informative metric**, and this workflow does not produce it: there is no TSS BED input and no `computeMatrix`/`plotProfile` step. Run it yourself against `signal/<sample>.signal.bw` before judging a library. A score below 3 indicates a failed experiment regardless of what other metrics show; scores above 7 are excellent (Yan et al. 2020). Fragment-size plots, NRF/PBC and ataqv are manual in the same way.

IDR runs once per pair of replicates, so two replicates give one file; a third would add `islet_rep1_vs_islet_rep3` and `islet_rep2_vs_islet_rep3`. There is no pooled, optimal or conservative peak set.

### Step 6: Compare Against ENCODE Reference

```
encode_search_experiments(assay_title="ATAC-seq", organ="pancreas", biosample_type="tissue")
encode_download_files(
    file_accessions=["ENCFF635JIA"],
    download_dir="/data/encode_reference/", organize_by="flat")
```

Intersect your peaks with the ENCODE reference peaks to quantify concordance:

```bash
bedtools intersect -u \
  -a results/peaks/idr/islet_rep1_vs_islet_rep2.idr_peaks.txt \
  -b /data/encode_reference/ENCFF635JIA.bed \
  > results/comparison/islet_idr_vs_ENCFF635JIA.overlap.tsv
```

### Step 7: Log Provenance

The IDR peaks came from local FASTQs, so they have no ENCODE source accession to record --
`encode_log_derived_file` accepts ENCODE accessions only, and a file derived purely from local
data belongs outside the provenance chain. The overlap table is the file that really consumes
ENCODE data, so log that one and describe the local inputs in the description:

```
encode_log_derived_file(
    file_path="results/comparison/islet_idr_vs_ENCFF635JIA.overlap.tsv",
    source_accessions=["ENCFF635JIA"],
    description="Overlap of IDR thresholded ATAC-seq peaks from local islet FASTQs (2 bio reps, Bowtie2 2.5.4 / MACS2 2.2.9.1 / IDR 2.0.4.2) with the ENCODE reference peak set",
    file_type="peak_overlap",
    tool_used="bedtools intersect (bedtools 2.31.0)",
    parameters="bedtools intersect -u -a islet_rep1_vs_islet_rep2.idr_peaks.txt -b ENCFF635JIA.bed")
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
*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 47 skills for genomics research*
