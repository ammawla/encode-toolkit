# Integrative Analysis -- Multi-Omic Regulatory Element Discovery

> **Category:** Analysis | **Tools Used:** `encode_get_facets`, `encode_search_experiments`, `encode_list_files`, `encode_download_files`, `encode_compare_experiments`, `encode_track_experiment`, `encode_log_derived_file`

## What This Skill Does

Combines multiple ENCODE data types into a multi-layered analysis to answer questions no single assay can address alone. Covers compatibility checks, file matching, batch effect detection, integration strategy, validation, and provenance.

## When to Use This

- You need to overlap peaks from different assays to find active regulatory elements.
- You are linking enhancers to target genes using accessibility, histone marks, and expression.
- You need to define chromatin states from a panel of histone marks using ChromHMM.

## Example Session

A scientist wants to identify active enhancers driving tissue-specific gene expression in human liver by integrating H3K27ac ChIP-seq, ATAC-seq, and RNA-seq.

### Step 1: Explore Availability and Search Each Layer

```
encode_search_experiments(assay_title="Histone ChIP-seq", target="H3K27ac", organ="liver", biosample_type="tissue", limit=50)
encode_search_experiments(assay_title="ATAC-seq", organ="liver", biosample_type="tissue", limit=50)
encode_search_experiments(assay_title="total RNA-seq", organ="liver", biosample_type="tissue", limit=50)
```

| Layer | Accession | Biosample | Lab | Audit |
|---|---|---|---|---|
| H3K27ac | ENCSR832RBL | liver, adult male 37y | Ren, UCSD | Clean |
| ATAC-seq | ENCSR862GLC | liver, adult male 37y | Ren, UCSD | Clean |
| RNA-seq | ENCSR094PJT | liver, adult female 51y | Gingeras, CSHL | WARNING: 1 |

Donor-matched H3K27ac and ATAC-seq from the same lab minimize batch effects. The RNA-seq is from a different donor -- acceptable for expression-level filtering but noted for provenance.

### Step 2: Track and Verify Compatibility

```
encode_track_experiment(accession="ENCSR832RBL")
encode_track_experiment(accession="ENCSR862GLC")
encode_compare_experiments(accession1="ENCSR832RBL", accession2="ENCSR862GLC")
```

Compatibility confirmed: same organism, assembly (GRCh38), biosample, and lab. No batch correction needed.

### Step 3: Download Matched Files

```
encode_list_files(experiment_accession="ENCSR832RBL", file_format="bed", output_type="IDR thresholded peaks", assembly="GRCh38")
encode_list_files(experiment_accession="ENCSR862GLC", file_format="bed", output_type="IDR thresholded peaks", assembly="GRCh38")
encode_list_files(experiment_accession="ENCSR094PJT", output_type="gene quantifications", assembly="GRCh38")

encode_download_files(
    file_accessions=["ENCFF421LMC", "ENCFF739QPB", "ENCFF210TSQ"],
    download_dir="/data/liver_integration", organize_by="experiment"
)
```

All files GRCh38, MD5-verified. Both peak files are narrowPeak from the same ENCODE uniform pipeline.

### Step 4: Integrate -- Peak Overlap to Find Active Enhancers

Blacklist-filter both peak sets, then intersect H3K27ac with ATAC-seq open chromatin:
```bash
# Blacklist filter (Amemiya et al. 2019)
bedtools intersect -a h3k27ac_liver.narrowPeak -b hg38-blacklist.v2.bed -v > h3k27ac.clean.bed
bedtools intersect -a atac_liver.narrowPeak -b hg38-blacklist.v2.bed -v > atac.clean.bed

# Active enhancers: H3K27ac peaks overlapping open chromatin
bedtools intersect -a h3k27ac.clean.bed -b atac.clean.bed -wa -u > active_enhancers_liver.bed
```

### Step 5: Filter by Expression (TPM >= 1, within 500kb of TSS)

```bash
awk -F'\t' '$6 >= 1 {print $1, $2, $3, $4}' OFS='\t' liver_genes.tsv > liver_expressed_tss.bed
bedtools window -a active_enhancers_liver.bed -b liver_expressed_tss.bed -w 500000 \
    > enhancers_near_expressed_genes.bed
```

### Step 6: Results

```
H3K27ac peaks (after QC):          62,413
ATAC-seq peaks (after QC):         81,297
H3K27ac overlapping ATAC-seq:      38,921  (62.4% of H3K27ac)
ATAC-seq overlapping H3K27ac:      34,108  (42.0% of ATAC-seq)
Near liver-expressed genes:         31,455  (80.8% of active enhancers)
```

The asymmetric overlap is expected: ATAC-seq detects all open chromatin (promoters, insulators, poised elements), while H3K27ac marks only active regions. Validation against known biology confirms ALB, APOB, and CYP3A4 enhancer regions all carry dual signal.

### Step 7: Log Provenance

```
encode_log_derived_file(
    file_path="/data/liver_integration/enhancers_near_expressed_genes.bed",
    source_accessions=["ENCSR832RBL", "ENCSR862GLC", "ENCSR094PJT"],
    description="Active liver enhancers: H3K27ac + ATAC-seq overlap, near liver-expressed genes",
    file_type="integrative_peaks", tool_used="bedtools v2.31.0",
    parameters="blacklist=hg38-blacklist.v2.bed; intersect -wa -u; window -w 500000; TPM>=1"
)
```

## Key Principles

- **Same assembly is non-negotiable.** Never mix GRCh38 and hg19 without explicit liftOver.
- **Match file types across layers.** Use the same output type and pipeline version across all experiments.
- **Report overlap in both directions.** Asymmetric overlap is biologically meaningful -- it reveals what fraction of each assay's features participate in the joint signal.
- **Validate with independent data.** Cross-layer confirmation (peaks + expression) is the minimum standard.

## Related Skills

- **regulatory-elements** -- Classify the integrated peak set into promoters, enhancers, and insulators.
- **epigenome-profiling** -- Build a full epigenomic profile for a biosample before integration.
- **histone-aggregation** / **accessibility-aggregation** -- Build union catalogs across donors before integrating.
- **data-provenance** -- Generate a publication-ready methods section from the provenance chain.

---

*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 43 skills for genomics research*
