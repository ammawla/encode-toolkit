# Data Provenance -- From Download to Publication-Ready Methods

> **Category:** Workflow | **Tools Used:** `encode_download_files`, `encode_log_derived_file`, `encode_get_provenance`, `encode_get_citations`

## What This Skill Does

Tracks every operation on ENCODE data with exact tool versions, reference files, parameters, and timestamps. The payoff: when you say "generate methods section," Claude reads the provenance chain and writes a fully-cited, version-specific methods paragraph ready for submission. No digging through shell history. No guessing which bedtools version you used three months ago.

## Example Session

A scientist downloads ATAC-seq peaks, applies blacklist filtering, lifts coordinates from hg19 to GRCh38, merges with a second dataset, and asks Claude to write the methods.

### Step 1: Download ENCODE Peaks

```
encode_download_files(
    file_accessions=["ENCFF491SIG"],
    download_dir="/data/atac_islets/peaks",
    organize_by="flat", verify_md5=True
)
```

Claude logs: file accession ENCFF491SIG, 2.1 MB, MD5 verified, bed narrowPeak format, GRCh38, from experiment ENCSR831YAX (ATAC-seq on human pancreatic islets, Ren lab, UCSD).

### Step 2: Blacklist Filter -- Log the Operation

**You ask Claude:** "Remove blacklisted regions from these peaks using bedtools"

Claude runs the filter and immediately logs provenance:

```
encode_log_derived_file(
    file_path="/data/atac_islets/derived/ENCFF491SIG.bl_filtered.bed",
    source_accessions=["ENCFF491SIG"],
    description="ATAC-seq peaks, blacklist-filtered",
    file_type="filtered_peaks",
    tool_used="bedtools intersect v2.31.0",
    parameters="bedtools intersect -a ENCFF491SIG.bed -b hg38-blacklist.v2.bed -v; blacklist=Amemiya et al. 2019 (DOI:10.1038/s41598-019-45839-z)"
)
```

Logged: 128,433 input regions, 127,891 passed (99.6%), 542 blacklisted regions removed. Tool version, blacklist source, citation, and exact command all recorded.

### Step 3: Liftover hg19 to GRCh38 -- Log with Chain File

A collaborator's dataset is in hg19. You need it in GRCh38 before merging.

**You ask Claude:** "Lift these peaks from hg19 to GRCh38"

```
encode_log_derived_file(
    file_path="/data/atac_islets/derived/collab_peaks.GRCh38.bed",
    source_accessions=["ENCFF491SIG"],
    description="Collaborator ATAC-seq peaks lifted from hg19 to GRCh38",
    file_type="liftover_peaks",
    tool_used="UCSC liftOver v377 (Kent et al. 2002, PMID:12045153)",
    parameters="liftOver collab_peaks.hg19.bed hg19ToHg38.over.chain.gz collab_peaks.GRCh38.bed unmapped.bed -minMatch=0.95; chain_source=https://hgdownload.soe.ucsc.edu/goldenPath/hg19/liftOver/ accessed 2024-01-15"
)
```

Logged: 45,231 input regions, 44,892 converted (99.25%), 339 unmapped (0.75%) saved to unmapped.bed. Chain file URL, access date, and minMatch parameter all captured.

### Step 4: Merge Datasets -- Log with Parameters

**You ask Claude:** "Merge these two peak sets into a union catalog"

```
encode_log_derived_file(
    file_path="/data/atac_islets/derived/atac_islets_union.bed",
    source_accessions=["ENCSR831YAX", "ENCFF491SIG"],
    description="Union ATAC-seq peaks from ENCODE islets + collaborator dataset",
    file_type="merged_peaks",
    tool_used="bedtools merge v2.31.0 (Quinlan & Hall 2010, DOI:10.1093/bioinformatics/btq033)",
    parameters="cat encode_filtered.bed collab_lifted.bed | bedtools sort | bedtools merge -d 0 -c 4 -o count_distinct"
)
```

Logged: 172,783 input regions from two sources, 134,207 union peaks after merge. Merge distance, count method, and both source accessions recorded.

### Step 5: Generate Methods Section

**You ask Claude:** "Write me a methods section for this analysis"

Claude reads the entire provenance chain via `encode_get_provenance` and produces:

> **Chromatin Accessibility Analysis**
>
> ATAC-seq data for human pancreatic islets were obtained from the ENCODE Project (ENCODE Project Consortium 2020) via the ENCODE portal (https://www.encodeproject.org), experiment accession ENCSR831YAX. IDR thresholded peaks (Li et al. 2011) aligned to GRCh38 were selected (file accession ENCFF491SIG; MD5-verified). Artifact-prone regions were removed using the ENCODE Blacklist v2 (Amemiya et al. 2019) with bedtools intersect v2.31.0 (Quinlan & Hall 2010), retaining 127,891 of 128,433 regions (99.6%). A collaborator dataset (45,231 peaks, GRCh37/hg19) was lifted to GRCh38 using UCSC liftOver v377 (Kent et al. 2002) with chain file hg19ToHg38.over.chain.gz (UCSC Genome Browser, accessed 2024-01-15; minMatch=0.95); 44,892 regions (99.25%) converted successfully and 339 unmapped regions were excluded. The two peak sets were merged into a union catalog using bedtools merge v2.31.0 (merge distance=0 bp, count_distinct sample tagging), yielding 134,207 non-redundant accessible regions. All source data are available from ENCODE under accession ENCSR831YAX. Analysis scripts and the complete provenance log are available at [repository URL].

Every version number, every citation, every accession, every statistic -- pulled directly from the provenance log. No reconstruction from memory. No "we used bedtools" without a version.

## Why This Matters

The difference between a reproducible methods section and a vague one is not effort at writing time -- it is effort at logging time. This skill shifts the cost to the moment of execution, when the information is available and accurate, rather than months later when you are writing the manuscript and guessing.

## Related Skills

- **cite-encode** -- Generate BibTeX/RIS citations for all ENCODE experiments used.
- **pipeline-guide** -- ENCODE pipeline execution that feeds into the provenance chain.
- **quality-assessment** -- QC metrics recorded alongside provenance for audit flags.
- **publication-trust** -- Verify that literature citations in your methods are accurate.

---

*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 43 skills for genomics research*
