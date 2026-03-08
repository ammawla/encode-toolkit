# 3D Genome Organization and DNA Methylation

> This vignette demonstrates how to explore chromatin looping (Hi-C) and DNA methylation
> (WGBS) data from ENCODE for understanding genome organization and epigenetic regulation.

**Prerequisites:** Familiarity with ENCODE search. See [Searching ENCODE Data](01-discovery-and-search.md).

**Skills demonstrated:** `search-encode`, `hic-aggregation`, `methylation-aggregation`, `integrative-analysis`

---

## Scenario

You are investigating how 3D genome organization and DNA methylation patterns contribute
to gene regulation in human pancreatic tissue -- specifically, whether chromatin loops
connect hypomethylated regulatory elements to their target genes.

---

## Step 1: Survey 3D Genome Data

**You ask Claude:** "What 3D genome data exists for human pancreas?"

**Claude calls:** `encode_get_facets(organ="pancreas")`

| Assay | Experiments |
|-------|-------------|
| intact Hi-C | 5 |
| in situ Hi-C | 1 |
| ChIA-PET | 2 |

**Interpretation:** Five intact Hi-C experiments are the primary source for loop detection.
Two ChIA-PET experiments capture protein-mediated contacts (CTCF or RNAPII) and serve as
orthogonal validation.

---

## Step 2: Survey DNA Methylation Data

**You ask Claude:** "What about whole-genome bisulfite sequencing for pancreas?"

**Claude calls:** `encode_search_experiments(assay_title="WGBS", organ="pancreas")`

**Result:** 5 WGBS experiments from pancreas tissue -- enough to compute reliable
weighted-average methylation profiles and identify hypomethylated regions (HMRs).

**Caution:** ENCODE also has 5 RRBS experiments for pancreas. RRBS covers only CpG-rich
regions (~10% of CpGs) and must NOT be mixed with WGBS in per-CpG averaging.

---

## Step 3: Aggregate Hi-C Loops

**You ask Claude:** "How do I build a comprehensive loop catalog from these experiments?"

**Claude uses the `hic-aggregation` skill** to guide the workflow:

1. **Download BEDPE loop files** from each experiment (GRCh38 assembly only)
2. **Quality-gate**: Verify 400M+ valid read pairs, >60% cis contacts, no ERROR audit flags
3. **Harmonize resolution**: Loop anchors are binned regions (5kb, 10kb, or 25kb).
   All loops must share a common resolution before merging (Loop Catalog method, Reyna 2025)
4. **Filter per sample**: Remove blocklist regions (Amemiya 2019), apply score filtering,
   discard self-ligation artifacts (<20kb anchor separation)
5. **Union merge**: Concatenate filtered loops, merge by binned anchor identity, and count
   supporting experiments per loop
6. **Annotate confidence**: >=50% support = constitutive; 2+ = supported; 1 = singleton

### Key Context

- **Loop caller concordance is low**: Wolff et al. 2022 found HICCUPS, Mustache, Fit-Hi-C,
  and HiCExplorer intersect by approximately 50% at most -- a strong argument for the
  union approach over reliance on any single caller.
- **Union captures more biology**: The Loop Catalog (Reyna 2025) recovered 4.19M unique
  loops across 1,089 datasets, roughly 3x more than any individual experiment.
- **Mustache** (Roayaei Ardakany 2020, 165 citations) recovers more validated loops than
  HICCUPS and works on both Hi-C and Micro-C data.

---

## Step 4: Aggregate Methylation Data

**You ask Claude:** "How do I combine methylation data across these WGBS samples?"

**Claude uses the `methylation-aggregation` skill** to guide the analysis:

1. **Download bedMethyl files** for CpG methylation state (GRCh38)
2. **Quality-gate**: Bisulfite conversion >=98% (even 1% incomplete conversion creates
   false methylation), mean CpG coverage >=10x, no ERROR flags
3. **Filter per sample**: Coverage >=5x per CpG, remove blocklist regions, strand-merge
   forward/reverse CpG measurements (verify files are not already strand-merged)
4. **Per-CpG weighted averaging**: Unlike histone marks (binary, union logic), methylation
   is continuous (0-100%). Compute coverage-weighted mean at each CpG -- higher-coverage
   measurements contribute proportionally more.
5. **Identify regulatory features**:
   - **HMRs**: Runs of CpGs <30% methylation, merged within 1kb, >=3 CpGs (Schultz 2015)
   - **UMRs**: Very low methylation <10%, typically CpG island promoters
   - **PMDs**: Large (>10kb) regions at 30-70%, often marking heterochromatin

### Key Context

- **Schultz et al. 2015** (Roadmap Epigenomics, 2,900+ citations): Established per-CpG
  averaging and tissue-specific HMRs as markers of active regulatory elements.
- **Zhou et al. 2020**: ~80% of CpGs are constitutively methylated, ~10% unmethylated,
  and only ~10% are tissue-variable -- that fraction holds the regulatory information.
- **Cell-type heterogeneity**: Bulk WGBS captures all cell types. A CpG at 50% could
  mean uniform half-methylation or a mixture of fully methylated and unmethylated cells.

---

## Step 5: Integrate 3D Structure with Methylation

**You ask Claude:** "How do I connect loops to methylation patterns?"

**Claude uses the `integrative-analysis` skill** for multi-omic integration:

### Loop Anchors at Hypomethylated Regions

Anchors overlapping HMRs are likely active regulatory elements. Intersect extracted
anchor coordinates with the HMR set using `bedtools intersect` to identify loops
connecting regulatory elements to target gene promoters.

### CTCF Binding and Methylation

CTCF binding requires unmethylated DNA at its motif. Loops anchored at CTCF sites (16
CTCF ChIP-seq experiments available for pancreas) should show low methylation at both
anchors. This three-way concordance validates structural loop integrity.

### Integration Strategy

| Layer | Source | Role |
|-------|--------|------|
| 3D contacts | Hi-C union loops (5 expts) | Physical connections between distant regions |
| Methylation | WGBS weighted average (5 expts) | Regulatory state at loop anchors |
| Protein binding | CTCF ChIP-seq (16 expts) | Structural anchor validation |

This follows the ENCODE Phase 3 framework (Gorkin et al. 2020), which integrated Hi-C,
methylation, and histone data to define regulatory loops across tissues.

---

## Summary of Skills Used

| Step | Skill/Tool | Purpose |
|------|------------|---------|
| Survey 3D data | `encode_get_facets` | Assess Hi-C and 3C data availability |
| Survey methylation | `encode_search_experiments` | Find WGBS experiments |
| Aggregate loops | `hic-aggregation` | Union loop catalog with resolution-aware merging |
| Aggregate methylation | `methylation-aggregation` | Per-CpG weighted averaging and HMR calling |
| Integrate layers | `integrative-analysis` | Connect 3D structure to epigenetic state |

---

## Best Practices

- **Never mix assemblies.** Hi-C binning makes liftOver error-prone, and WGBS CpG
  positions are exact -- even a 1bp offset misaligns CpGs. Use GRCh38 throughout.
- **Keep RRBS separate from WGBS.** They measure different CpG universes.
- **Report loop caller provenance.** Given ~50% concordance between callers, document
  which algorithm produced each set and why union was chosen.
- **Log every derived file** with `encode_log_derived_file` -- both the union loop
  catalog and methylation profile depend on multiple source experiments.
- **Validate with CTCF.** CTCF loops should show unmethylated motifs at both anchors.

---

## What's Next

- [Epigenomics Workflow](03-epigenomics-workflow.md) -- Add histone marks to complete the picture
- [Pipeline Execution](08-pipeline-execution.md) -- Process raw Hi-C or WGBS data
