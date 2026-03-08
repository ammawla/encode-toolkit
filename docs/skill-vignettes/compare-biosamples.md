# Compare Biosamples -- Finding Tissue-Specific Enhancers Across Organs

> **Category:** Analysis | **Tools Used:** `encode_get_facets`, `encode_search_experiments`, `encode_track_experiment`, `encode_compare_experiments`, `encode_list_files`, `encode_download_files`, `encode_log_derived_file`

## What This Skill Does

Guides systematic comparison of ENCODE experiments across different biosamples to identify tissue-specific regulatory elements and cross-tissue differences. Handles availability mapping, compatibility checking, batch effect detection, and file selection.

## When to Use This

- You want to find enhancers active in one tissue but not another.
- You need to verify that two experiments from different organs are technically comparable.
- You are designing a multi-tissue comparison and need to map data availability.

## Example Session

A scientist compares H3K27ac ChIP-seq between pancreas and liver tissue to identify pancreas-specific enhancers -- regulatory elements that drive tissue identity (Heintzman et al. 2009).

### Step 1: Map Data Availability

Before committing to a comparison, check what exists for each tissue.

```
encode_get_facets(organ="pancreas", assay_title="Histone ChIP-seq")
encode_get_facets(organ="liver", assay_title="Histone ChIP-seq")
```

Both organs have H3K27ac experiments on primary tissue with GRCh38 assembly. Pancreas has 3 released experiments; liver has 5. Sufficient for a cross-tissue comparison.

### Step 2: Search for Matched Experiments

```
encode_search_experiments(
    assay_title="Histone ChIP-seq", target="H3K27ac",
    organ="pancreas", biosample_type="tissue", limit=10
)
encode_search_experiments(
    assay_title="Histone ChIP-seq", target="H3K27ac",
    organ="liver", biosample_type="tissue", limit=10
)
```

Select one experiment per tissue, matching on biosample type, life stage, and assembly:

| Accession | Organ | Biosample | Life Stage | Lab | Audit |
|---|---|---|---|---|---|
| ENCSR831YAX | pancreas | pancreas tissue | adult | Ren, UCSD | WARNING: 1 |
| ENCSR653DFZ | liver | liver tissue | adult | Snyder, Stanford | Clean |

Both are adult primary tissue, same assay and target. The lab difference is a known batch effect risk (Leek et al. 2010), but unavoidable here -- document it.

### Step 3: Track and Check Compatibility

```
encode_track_experiment(accession="ENCSR831YAX", notes="Cross-tissue H3K27ac - pancreas")
encode_track_experiment(accession="ENCSR653DFZ", notes="Cross-tissue H3K27ac - liver")

encode_compare_experiments(accession1="ENCSR831YAX", accession2="ENCSR653DFZ")
```

The compatibility report returns verdict **COMPATIBLE (with warnings)**: organism, assembly, assay, target, and replication all match. Two mismatches are flagged -- biosample (pancreas vs liver) and lab (Ren vs Snyder). The biosample mismatch is the variable of interest, so that is expected. The lab mismatch is the real concern: for publication-grade analysis, include a second pair from matching labs, or verify via PCA that signal clusters by tissue rather than by lab.

### Step 4: Select Files, Download, and Compare

Select IDR thresholded peaks (narrowPeak) from both experiments -- never mix IDR peaks from one tissue with pseudoreplicated peaks from another, as the stringency difference confounds biology.

```
encode_download_files(
    file_accessions=["ENCFF635JIA", "ENCFF912QLP"],
    download_dir="/data/cross_tissue/h3k27ac", organize_by="experiment"
)
```

After blacklist filtering (Amemiya et al. 2019), find tissue-specific peaks:

```bash
# Pancreas-specific enhancers: present in pancreas, absent in liver
bedtools intersect -a pancreas_h3k27ac.narrowPeak -b liver_h3k27ac.narrowPeak -v \
    > pancreas_specific_h3k27ac.bed

# Constitutive elements: shared between both tissues
bedtools intersect -a pancreas_h3k27ac.narrowPeak -b liver_h3k27ac.narrowPeak -u \
    > shared_h3k27ac.bed
```

Expected: enhancer peaks are predominantly tissue-specific (~95% not shared across all tissues per Andersson et al. 2014), while promoter-proximal H3K27ac is largely constitutive.

### Step 5: Log Provenance

```
encode_log_derived_file(
    file_path="/data/cross_tissue/h3k27ac/pancreas_specific_h3k27ac.bed",
    source_accessions=["ENCSR831YAX", "ENCSR653DFZ"],
    description="Pancreas-specific H3K27ac peaks absent in liver",
    file_type="differential_peaks",
    tool_used="bedtools intersect v2.31.0",
    parameters="bedtools intersect -a pancreas.bed -b liver.bed -v; blacklist=hg38-blacklist.v2.bed"
)
```

## Key Principles

- **H3K27ac at enhancers is the best tissue discriminator.** If you can only compare one mark, start here (Heintzman et al. 2009, Roadmap 2015).
- **Biosample mismatch is the signal, not a problem.** In cross-tissue comparisons, the compatibility tool will flag biosample differences -- that is expected and correct.
- **Lab mismatch is the noise.** When experiments come from different labs, verify that signal clusters by tissue (biology) not by lab (batch). Use CTCF or housekeeping promoters as batch-effect controls.
- **Same file type across all tissues.** Never mix IDR thresholded peaks with pseudoreplicated peaks or different assemblies in a single comparison.

## Related Skills

- **histone-aggregation** -- Merge peaks across multiple experiments for the SAME tissue before cross-tissue comparison.
- **quality-assessment** -- Evaluate each experiment's quality before including it in a comparison.
- **integrative-analysis** -- Layer RNA-seq, ATAC-seq, and ChIP-seq for deeper cross-tissue characterization.
- **regulatory-elements** -- Annotate tissue-specific peaks as enhancers, promoters, or insulators.
- **data-provenance** -- Record comparison parameters and derived files for reproducibility.

---

*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 43 skills for genomics research*
