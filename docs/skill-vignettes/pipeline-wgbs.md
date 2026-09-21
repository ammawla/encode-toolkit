# Pipeline WGBS -- Running the ENCODE Methylation Pipeline

> **Category:** Pipeline Execution | **Tools Used:** `encode_search_experiments`, `encode_list_files`, `encode_download_files`, `encode_log_derived_file`

## What This Skill Does

Executes the ENCODE WGBS pipeline from raw FASTQ files to per-CpG methylation calls in bedMethyl format. The pipeline runs Trim Galore (bisulfite-aware trimming), Bismark (alignment), Picard (deduplication), and MethylDackel (extraction). Outputs are strand-merged CpG beta values with coverage annotations, ready for DMR analysis or aggregation.

## When to Use This

- You have WGBS FASTQ files (from ENCODE or your own lab) and need per-CpG methylation calls.
- You want ENCODE-standard processing with auditable provenance for every step.
- You need to validate bisulfite conversion using lambda spike-in controls before trusting the data.

## Example Session

### Scientist's Request

> "Run the ENCODE WGBS pipeline on two human pancreas samples I downloaded. Check bisulfite conversion quality and make sure coverage is sufficient for DMR calling."

### Step 1: Download FASTQ Files

```
encode_search_experiments(
    assay_title="WGBS", organ="pancreas",
    biosample_type="tissue", organism="Homo sapiens", limit=10
)
```

Two experiments found. Download paired-end FASTQs for both.

```
encode_download_files(
    file_accessions=["ENCFF901ABC", "ENCFF902DEF", "ENCFF903GHI", "ENCFF904JKL"],
    download_dir="/data/pancreas_wgbs", organize_by="experiment"
)
```

### Step 2: Execute the Pipeline

```bash
nextflow run skills/pipeline-wgbs/scripts/main.nf \
    -profile local \
    --reads '/data/pancreas_wgbs/*_R{1,2}.fastq.gz' \
    --genome_dir '/ref/bismark_index' \
    --min_coverage 5 \
    --outdir results/ \
    -resume
```

ENCODE FASTQs are named by accession, so link each pair to `<sample>_R1.fastq.gz` / `<sample>_R2.fastq.gz` names before the run. `--genome_dir` is the folder made by `bismark_genome_preparation` (it also holds the FASTA). The workflow has no bisulfite conversion-rate stage: it does not align to lambda, so conversion QC is a separate, manual check (next step).

### Step 3: Check Bisulfite Conversion (Manual; Lambda Spike-in)

This is not computed by the workflow. If the library carries a lambda spike-in, align the reads to a Bismark index of the lambda genome yourself and extract methylation there: since lambda DNA is unmethylated, all methylation calls on lambda represent conversion failures.

| Sample | Lambda CpG Methylation | Conversion Rate | Status |
|--------|----------------------|-----------------|--------|
| Pancreas Donor 1 | 0.3% | 99.7% | Pass |
| Pancreas Donor 2 | 1.4% | 98.6% | Fail |

Donor 1 passes at 99.7% -- well above the 98% threshold. Donor 2 at 98.6% fails. At 1.4% false positive rate across ~28 million CpGs, that contaminates hundreds of thousands of sites. Donor 2 must be excluded or re-prepared.

If no lambda spike-in is available, check CHH context methylation as a proxy: the workflow writes it to `bismark/methylation/<sample>.CHH.bedMethyl.gz`. Somatic tissues should show CHH below 1%. Values above that indicate conversion problems (exception: neurons and ESCs have genuine non-CpG methylation at 2--5%).

### Step 4: Evaluate CpG Coverage for DMR Calling

DMR analysis requires reliable per-CpG estimates, which demands sufficient read depth. The coverage figures come from `coverage/<sample>.coverage_stats.txt`, the mapping rate from the Bismark report in `bismark/alignments/`, and the duplication rate from `bismark/dedup_reports/`.

| Metric | Donor 1 | ENCODE Threshold |
|--------|---------|-----------------|
| Mean CpG coverage | 18.4x | >=10x for DMRs |
| CpGs at >=5x | 89.2% | >=80% |
| CpGs at >=10x | 74.6% | >=60% |
| Mapping rate | 76.1% | >=70% |
| Duplication rate | 22.3% | <30% |

Donor 1 meets all ENCODE thresholds. The 18.4x mean coverage exceeds the 10x minimum for quantitative DMR analysis (Foox et al. 2021). Below 10x, beta values are too noisy for detecting small methylation differences.

### Step 5: Review M-bias and Trim if Needed
MethylDackel generates M-bias plots showing methylation by read position (`bismark/mbias/`, with the suggested bounds in `<sample>_mbias_report.txt`). End-repair artifacts inflate methylation at the 5' end of read 2. The workflow extracts without trimming, so if the plot shows a spike at positions 1--10, re-run the extraction by hand on the published BAM:

```bash
MethylDackel extract --mergeContext --nOT 0,0,10,0 --nOB 0,0,10,0 \
    /ref/genome.fa results/bismark/alignments/donor1.sorted.bam
```

`--nOT` and `--nOB` take four numbers: bases to ignore at the start of read 1, the end of read 1, the start of read 2 and the end of read 2, for the original top and bottom strands. `0,0,10,0` on both ignores the first 10 bp of read 2.

### Step 6: Log Provenance
```
encode_log_derived_file(
    file_path="/results/bismark/methylation/donor1.CpG.bedMethyl.gz",
    source_accessions=["ENCSR491HHV", "ENCFF901ABC", "ENCFF902DEF"],
    description="CpG methylation calls, bisulfite conversion 99.7%, mean 18.4x coverage",
    file_type="bedMethyl",
    tool_used="Bismark 0.24.2 + MethylDackel 0.6.1",
    parameters="--merge_context true, --min_coverage 5; lambda conversion 99.7% from a separate alignment"
)
```

## Key Pitfalls

- **Never skip conversion QC.** A library at 98% conversion introduces ~560,000 false methylation calls across the human genome. Always use lambda spike-in or CHH proxy.
- **Do not mix RRBS and WGBS.** RRBS covers ~10% of CpGs near MspI sites. Use `--skip_dedup true` for RRBS since fragments share cut sites by design.
- **Always merge CpG strands.** Forward and reverse reads at a CpG dinucleotide measure the same site. Keep the workflow's default `--merge_context true` (MethylDackel `--mergeContext`) to avoid double-counting and halving apparent coverage.
- **Coverage thresholds depend on the question.** 5x is adequate for binary calls (methylated vs. unmethylated). 10x is the minimum for quantitative DMR detection. 30x is needed for allele-specific methylation.

## Related Skills

- **methylation-aggregation** -- Combine bedMethyl outputs across donors into tissue-level maps.
- **quality-assessment** -- Evaluate pipeline outputs against ENCODE audit standards.
- **pipeline-guide** -- Parent skill for compute resource planning and cloud deployment.
- **data-provenance** -- Full lineage tracking from FASTQ accessions to final bedMethyl.
- **epigenome-profiling** -- Layer methylation with histone marks and accessibility for chromatin state classification.

---

*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 47 skills for genomics research*
