# Pipeline RNA-seq -- STAR Alignment to Gene Quantification

> **Category:** Pipeline Execution | **Tools Used:** `encode_search_experiments`, `encode_batch_download`, `encode_search_files`

## What This Skill Does

Executes the ENCODE RNA-seq pipeline from raw FASTQ files through STAR 2-pass alignment, RSEM gene/transcript quantification, optional Kallisto pseudoalignment, and strand-specific signal track generation. Deployed via Nextflow DSL2 with Docker, SLURM, GCP, and AWS profiles.

## When to Use This

- You have RNA-seq FASTQ files and need gene expression quantification following ENCODE standards.
- You need strand-specific signal tracks (bigWig) for genome browser visualization.
- You want transcript-level quantification with RSEM or fast pseudocounts with Kallisto.

## Example Session

A researcher has paired-end RNA-seq from human pancreatic islets and needs gene-level TPM values aligned to GRCh38 with GENCODE annotation.

### Step 1: Detect Library Strandedness

The sample sheet does not specify strandedness. Before running the full pipeline, confirm the library protocol. If unknown, the pipeline auto-detects using RSeQC `infer_experiment.py`:

```
nextflow run scripts/main.nf \
  -profile local \
  --reads 'fastq/*_R{1,2}.fq.gz' \
  --genome GRCh38 \
  --outdir results/
```

The QC stage reports strandedness from `infer_experiment.py`:

| Metric | Value | Interpretation |
|---|---|---|
| "1++,1--,2+-,2-+" (sense) | 3.2% | Reads matching sense strand |
| "1+-,1-+,2++,2--" (antisense) | 96.1% | Reads matching antisense strand |
| Undetermined | 0.7% | Ambiguous |

Antisense fraction above 90% confirms **reverse stranded** (dUTP protocol), the ENCODE standard. The pipeline proceeds with `--strandedness reverse` automatically. If this fraction were near 50/50, the library would be unstranded (e.g., SMART-Seq2), requiring `--strandedness unstranded`.

### Step 2: Select GENCODE Annotation

The `--genome GRCh38` flag defaults to GENCODE v38 for human (`--genome mm10` uses vM27 for mouse). To override with a specific annotation:

```
nextflow run scripts/main.nf \
  -profile local \
  --reads 'fastq/*_R{1,2}.fq.gz' \
  --genome GRCh38 \
  --gtf /refs/gencode.v44.annotation.gtf \
  --outdir results/
```

GENCODE comprehensive annotation includes all gene biotypes. For protein-coding-only analysis, filter the GTF before indexing. Never mix annotation versions across samples in the same study.

### Step 3: Evaluate Alignment QC

After the pipeline completes, inspect `results/star/logs/Log.final.out` for each sample:

| Metric | Sample 1 | Sample 2 | Threshold |
|---|---|---|---|
| Total reads | 42.1M | 38.7M | >=30M PE |
| Uniquely mapped | 85.3% | 83.9% | >=70% |
| Multi-mapped | 6.8% | 7.2% | <10% |
| Unmapped (too short) | 5.1% | 5.8% | -- |
| Splice junctions (novel) | 48,219 | 45,103 | -- |

Both samples exceed the 70% uniquely mapped threshold. The ENCODE standard also requires mapping rate above 80% (unique + multi-mapped combined): Sample 1 at 92.1% and Sample 2 at 91.1% both pass. Multi-mapped rates under 10% confirm clean libraries without excessive repetitive element contamination.

### Step 4: Check Expression-Level QC

From the RSeQC and RSEM output:

| Metric | Sample 1 | Sample 2 | Threshold |
|---|---|---|---|
| rRNA rate | 2.3% | 3.1% | <10% |
| Exonic rate | 71.2% | 69.8% | >60% |
| Detected genes (TPM>1) | 14,821 | 14,503 | >12,000 |
| Duplication rate | 31.4% | 28.7% | <60% |
| Gene body coverage (5'/3' bias) | 1.18 | 1.22 | <1.5 |

All metrics pass. Low rRNA confirms successful depletion. Gene body coverage near 1.0 indicates intact RNA. Now validate against ENCODE pancreas RNA-seq:

```
encode_search_experiments(
    assay_title="total RNA-seq",
    organ="pancreas",
    biosample_type="tissue"
)

encode_batch_download(
    download_dir="/data/encode_ref/",
    output_type="gene quantifications",
    assay_title="total RNA-seq",
    organ="pancreas",
    assembly="GRCh38"
)
```

Compare your TPM distributions against the ENCODE reference. Concordance of housekeeping genes (ACTB, GAPDH, RPL13A) provides a sanity check that the pipeline ran correctly.

## Key Principles

- **STAR 2-pass mode is non-negotiable for novel junction discovery.** Pass 1 identifies splice junctions across all samples; pass 2 re-aligns using the combined junction set. This recovers tissue-specific splicing events missed by annotation alone (Dobin et al. 2013).
- **STAR requires 32GB RAM for human.** The genome index loads entirely into shared memory. Machines below this threshold will fail silently or crash at the alignment step.
- **Use TPM, not FPKM, for cross-sample comparison.** FPKM depends on total library composition and is not comparable between samples. TPM normalizes to a fixed sum per sample (Li & Dewey 2011).
- **Do not pre-filter multi-mapped reads before RSEM.** RSEM uses expectation-maximization to probabilistically assign multi-mappers. Removing them first discards signal from gene families and repetitive elements.
- **Wrong strandedness produces near-zero counts.** This is the most common user error. If gene counts are uniformly low, verify strandedness with `infer_experiment.py` before re-running.

## Related Skills

- **pipeline-guide** -- Parent skill for pipeline selection and compute resource estimation.
- **quality-assessment** -- Deep-dive QC beyond the metrics checked here.
- **integrative-analysis** -- Combine RNA-seq with ChIP-seq or ATAC-seq for regulatory inference.
- **compare-biosamples** -- Differential expression across cell types using quantification output.
- **single-cell-encode** -- For scRNA-seq (STARsolo or Cell Ranger, different pipeline).

---

*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 43 skills for genomics research*
