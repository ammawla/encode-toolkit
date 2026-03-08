# Quality Assessment -- Evaluating ENCODE Experiments Before Analysis

> **Category:** Analysis | **Tools Used:** `encode_search_experiments`, `encode_get_experiment`, `encode_list_files`

## What This Skill Does

Evaluates whether ENCODE experiments meet quality standards for your analysis by combining ENCODE audit flags with assay-specific QC metrics (FRiP, NSC, RSC, NRF for ChIP-seq; TSS enrichment for ATAC-seq; mapping rate for RNA-seq). No single metric is sufficient -- quality is assessed collectively, in context.

## When to Use This

- You found several experiments and need to decide which ones to include in your analysis.
- ENCODE audit flags say WARNING or NOT_COMPLIANT and you need to know if the data is still usable.
- You are combining data from multiple labs or donors and need comparable quality across all inputs.

## Example Session

A scientist wants to study H3K4me3 at promoters in human liver tissue and needs to select only high-quality experiments.

### Step 1: Find Candidate Experiments

```
encode_search_experiments(
    assay_title="Histone ChIP-seq", target="H3K4me3",
    organ="liver", biosample_type="tissue", status="released", limit=25
)
```

Four experiments returned:

| Accession | Biosample | Lab | Audit Summary |
|---|---|---|---|
| ENCSR576MKN | liver, adult male 32y | Bernstein, Broad | Clean |
| ENCSR831WFJ | liver, adult female 51y | Ren, UCSD | WARNING: 1 |
| ENCSR265PLT | liver, adult male 60y | Bernstein, Broad | NOT_COMPLIANT: 1, WARNING: 1 |
| ENCSR709QWB | liver, adult female 44y | Ren, UCSD | ERROR: 1 |

### Step 2: Inspect Each Experiment

```
encode_get_experiment(accession="ENCSR576MKN")
```

Repeat for all four. The full metadata reveals audit details, replicate structure, and pipeline version. Here is the quality summary across all candidates:

| Accession | Replicates | FRiP | NSC | RSC | NRF | Read Depth | IDR Peaks |
|---|---|---|---|---|---|---|---|
| ENCSR576MKN | 2 bio (isogenic) | 8.2% | 1.32 | 1.14 | 0.91 | 28M, 31M | 24,817 |
| ENCSR831WFJ | 2 bio (anisogenic) | 5.6% | 1.18 | 0.93 | 0.84 | 22M, 19M | 18,403 |
| ENCSR265PLT | 2 bio (anisogenic) | 1.8% | 1.07 | 0.72 | 0.76 | 15M, 12M | 6,291 |
| ENCSR709QWB | 1 bio | 0.6% | 1.02 | 0.48 | 0.62 | 9M | None |

### Step 3: Interpret the Audit Flags

**ENCSR576MKN** -- Clean. No audit flags. All metrics well above Landt et al. 2012 thresholds.

**ENCSR831WFJ** -- WARNING: "insufficient read depth for one replicate." Replicate 2 has 19M reads, slightly below the 20M recommendation for histone marks. The other metrics are solid and IDR peaks were called successfully.

**ENCSR265PLT** -- NOT_COMPLIANT: "low library complexity." NRF = 0.76 falls below the 0.8 threshold, meaning excessive PCR duplication. The WARNING flags low read depth on replicate 2 (12M). RSC = 0.72 also fails the 0.8 threshold. Two metrics below standard is a pattern, not a fluke.

**ENCSR709QWB** -- ERROR: "missing biological replicate." Only one replicate was submitted. FRiP = 0.6% is below the 1% minimum for any ChIP-seq. NSC near 1.0 indicates negligible enrichment. NRF = 0.62 shows severe library complexity exhaustion. No IDR peaks could be called. This experiment failed at multiple levels.

### Step 4: Check File Availability for Passing Experiments

```
encode_list_files(
    experiment_accession="ENCSR576MKN",
    output_type="IDR thresholded peaks", assembly="GRCh38"
)
```

Confirm IDR thresholded peaks exist for each experiment you plan to use. Also verify files were processed with the same pipeline version for consistency.

### Step 5: Assign Quality Tiers

| Accession | Tier | Verdict | Rationale |
|---|---|---|---|
| ENCSR576MKN | High quality | Include | All metrics pass. Two replicates. IDR peaks available. |
| ENCSR831WFJ | Usable with caveats | Include | One replicate slightly under depth. All other metrics pass. Document the WARNING. |
| ENCSR265PLT | Use with caution | Exclude | NRF and RSC both below threshold. Low depth compounds the complexity issue. Only use if no alternative exists. |
| ENCSR709QWB | Not recommended | Exclude | Single replicate, ERROR audit, FRiP and NRF both failing, no IDR peaks. Discard. |

### Final Selection

Two experiments (ENCSR576MKN, ENCSR831WFJ) pass quality gating from two donors and two labs. This provides biological replication across individuals while maintaining comparable data quality.

For the excluded experiments: ENCSR265PLT could be rescued only if re-sequenced to address the complexity bottleneck. ENCSR709QWB is not salvageable -- the underlying library failed.

## Key Principles

- **No single metric decides quality.** FRiP alone can mislead -- focal transcription factor binding legitimately produces low FRiP. Evaluate FRiP, NSC, RSC, and NRF together.
- **Read depth cannot fix a bad library.** If NRF is below 0.8, the library complexity is exhausted. Sequencing deeper yields only more PCR duplicates, not more unique fragments (Landt et al. 2012).
- **Audit severity matters.** WARNING flags are usually safe to proceed with after documenting. NOT_COMPLIANT requires investigation. ERROR means stop and look for alternatives.
- **Assay thresholds are not interchangeable.** ChIP-seq FRiP of 5% is acceptable; ATAC-seq FRiP of 5% is a red flag. CUT&RUN FRiP of 5% is also a red flag. Always apply assay-appropriate thresholds.
- **Always apply the ENCODE Blacklist.** Quality metrics computed before blacklist filtering (Amemiya et al. 2019) can be inflated by artifact regions. Confirm blacklist was applied in the pipeline.

## Related Skills

- **batch-analysis** -- Screen QC metrics across dozens of experiments systematically before filtering.
- **histone-aggregation** -- Quality filtering is a prerequisite before merging peaks into union catalogs.
- **data-provenance** -- Log which experiments were kept, which were excluded, and why.
- **compare-biosamples** -- Ensure comparable quality across the samples being compared.

---

*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 43 skills for genomics research*
