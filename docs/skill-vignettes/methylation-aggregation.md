# Methylation Aggregation -- Building Tissue-Level Methylation Maps

> **Category:** Data Aggregation | **Tools Used:** `encode_search_experiments`, `encode_list_files`, `encode_download_files`, `encode_log_derived_file`

## What This Skill Does

Aggregates WGBS (Whole Genome Bisulfite Sequencing) data across multiple ENCODE experiments into a single per-CpG methylation profile using coverage-weighted averaging. Unlike histone and accessibility data where detection is binary and aggregation uses union logic, DNA methylation is a continuous signal (0--100%) at every CpG. This skill averages methylation levels, then identifies HMRs (hypomethylated regions), UMRs (unmethylated regions), and PMDs (partially methylated domains) from the averaged profile.

## When to Use This

- You want a consensus methylation map for a tissue by combining data across donors and labs.
- You need to identify regulatory regions (HMRs/UMRs) or repressed domains (PMDs) in a tissue.
- You are integrating methylation with histone marks or accessibility to classify chromatin states.

## Why Averaging, Not Union

Histone ChIP-seq peaks are binary: a region is either bound or not. If one donor shows a peak, the mark CAN bind there, so the union captures all possible binding sites. Methylation is fundamentally different -- every CpG has a value from 0% to 100%. Two samples showing 72% and 81% at the same CpG should yield a weighted average, not a union. Union logic only applies downstream to the derived HMR/UMR/PMD regions.

## Example Session

### Scientist's Request

> "I want a comprehensive methylation map of human kidney. Aggregate all available WGBS data and identify the hypomethylated regulatory regions."

### Step 1: Find WGBS Experiments on Kidney

```
encode_search_experiments(
    assay_title="WGBS",
    organ="kidney",
    biosample_type="tissue",
    organism="Homo sapiens",
    limit=50
)
```

Results: 3 released WGBS experiments from 2 labs, all on adult kidney tissue. All pass the critical thresholds -- bisulfite conversion >=98%, mean CpG coverage >=10x, no ERROR audit flags.

### Step 2: Download bedMethyl Files

For each experiment, retrieve per-CpG methylation calls (bedMethyl format) in GRCh38, then download.

```
encode_download_files(
    file_accessions=["ENCFF491OHB", "ENCFF227LKR", "ENCFF903TZQ"],
    download_dir="/data/kidney_wgbs",
    organize_by="flat"
)
```

### Step 3: Per-CpG Weighted Averaging

After filtering each sample for >=5x coverage and removing ENCODE Blacklist regions, combine all three into a single profile. The math for each CpG site:

```
weighted_mean = sum(methylation_i * coverage_i) / sum(coverage_i)
```

Concrete example at chr6:29,541,208:

| Sample | Coverage | Methylation |
|--------|----------|-------------|
| Donor 1 | 14x | 23% |
| Donor 2 | 8x | 18% |
| Donor 3 | 22x | 26% |

```
weighted_mean = (0.23*14 + 0.18*8 + 0.26*22) / (14 + 8 + 22)
             = (3.22 + 1.44 + 5.72) / 44
             = 10.38 / 44
             = 23.6%
```

The high-coverage Donor 3 contributes more to the average than the low-coverage Donor 2. This is correct -- higher coverage means a more reliable per-CpG estimate.

Output: `kidney_methylation_profile.bed` with ~26M CpGs, each annotated with sample count, total coverage, and weighted mean methylation.

### Step 4: HMR/UMR/PMD Identification

From the averaged profile, identify three classes of methylation features:

- **HMRs** (methylation <30%, >=3 CpGs within 1kb): Mark active regulatory elements -- enhancers, insulators. Found 48,219 HMRs with a median size of 680bp.
- **UMRs** (methylation <10%, >=5 CpGs within 500bp): Mark constitutively active promoters at CpG islands. Found 21,844 UMRs.
- **PMDs** (methylation 30--70%, >=20 CpGs, region >=10kb): Mark repressed or heterochromatic domains. Found 312 PMDs spanning large genomic regions.

Each HMR is annotated with sample support (e.g., "3/3 donors" = high confidence).

### Step 5: Log Provenance

Log both the per-CpG profile and the derived HMR regions back to their ENCODE sources.

```
encode_log_derived_file(
    file_path="/data/kidney_wgbs/kidney_methylation_profile.bed",
    source_accessions=["ENCSR832MFE", "ENCSR519KLJ", "ENCSR741PQW"],
    description="Per-CpG weighted-average methylation across 3 kidney WGBS experiments",
    file_type="aggregated_methylation",
    tool_used="bedtools + awk weighted averaging",
    parameters="coverage >= 5x, blacklist v2 filtered, strand-merged, shared in >= 2 samples"
)
```

## Key Pitfalls

- **Do NOT use union for per-CpG values.** Average methylation levels; reserve union logic for derived HMR/UMR/PMD regions only.
- **Coverage drives accuracy.** A CpG at 3x could plausibly be anywhere from 0% to 60%. Filter to >=5x minimum, >=10x for quantitative work.
- **Do NOT mix RRBS and WGBS.** RRBS covers only ~10% of CpGs (CpG-rich regions). Mixing inflates coverage at islands while leaving the rest of the genome single-source.
- **Cell-type heterogeneity.** Bulk WGBS from tissue averages across cell types. A CpG at 50% could mean all cells are half-methylated, or half the cells are fully methylated. This ambiguity is inherent to bulk data.

## Related Skills

- **histone-aggregation** -- Overlay HMRs with H3K27ac peaks to identify active enhancers.
- **accessibility-aggregation** -- HMRs typically overlap open chromatin; concordance validates both.
- **pipeline-wgbs** -- Process raw WGBS FASTQ files through the ENCODE-aligned Bismark pipeline.
- **epigenome-profiling** -- Combine methylation with histone and accessibility layers for chromatin state maps.

---

*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 43 skills for genomics research*
