# ClinVar Annotation -- Clinical Variants in ENCODE Regulatory Elements

> **Category:** External Databases | **Tools Used:** `encode_search_experiments`, `encode_list_files`, `encode_download_files`, `encode_log_derived_file`, `encode_link_reference`

## What This Skill Does

Annotates variants in ENCODE-defined regulatory elements with ClinVar clinical significance (ACMG five-tier: Pathogenic, Likely pathogenic, VUS, Likely benign, Benign). Queries ClinVar via NCBI E-utilities, then intersects with ENCODE peak files to find clinically relevant variants disrupting enhancers, promoters, and insulators.

## When to Use This

- You have ENCODE peaks and want to know if clinically significant variants fall inside them.
- You have ClinVar pathogenic variants and need ENCODE functional context to explain their mechanism.
- You want to prioritize VUS overlapping tissue-specific enhancers for reclassification.

## Example Session

A scientist studying neonatal diabetes annotates ENCODE pancreas enhancers with ClinVar variants to find pathogenic mutations in regulatory regions near insulin pathway genes.

### Step 1: Find and Download Pancreas Enhancer Peaks

```
encode_search_experiments(
    assay_title="Histone ChIP-seq", target="H3K27ac",
    organ="pancreas", biosample_type="tissue", status="released"
)

encode_list_files(
    experiment_accession="ENCSR831YAX",
    file_format="bed", output_type="IDR thresholded peaks", assembly="GRCh38"
)

encode_download_files(
    file_accessions=["ENCFF635JIA"],
    download_dir="/data/clinvar_annotation/peaks", organize_by="flat"
)
```

The scientist selects ENCSR831YAX (best audit, no ERROR flags). One narrowPeak file: ENCFF635JIA (142,318 peaks). The ClinVar VCF is fetched separately:

```bash
wget https://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38/clinvar.vcf.gz
wget https://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38/clinvar.vcf.gz.tbi
```

Both files must be GRCh38. Mixing assemblies produces silently incorrect intersections.

### Step 2: Filter ClinVar to Pathogenic and VUS Variants

```bash
# Extract pathogenic and likely pathogenic variants to BED
bcftools view -i 'INFO/CLNSIG~"Pathogenic" || INFO/CLNSIG~"Likely_pathogenic"' \
    clinvar.vcf.gz | \
    bcftools query -f '%CHROM\t%POS0\t%END\t%ID\t%INFO/CLNSIG\t%INFO/CLNDN\n' \
    > clinvar_pathogenic.bed

# Separately extract VUS for reclassification candidates
bcftools view -i 'INFO/CLNSIG="Uncertain_significance"' \
    clinvar.vcf.gz | \
    bcftools query -f '%CHROM\t%POS0\t%END\t%ID\t%INFO/CLNSIG\t%INFO/CLNDN\n' \
    > clinvar_vus.bed
```

`%POS0` outputs 0-based coordinates matching BED format. Using `%POS` (1-based VCF convention) without adjustment causes off-by-one errors in every intersection.

### Step 3: Intersect with ENCODE Enhancer Peaks

```bash
bedtools intersect -a clinvar_pathogenic.bed -b ENCFF635JIA.bed -wa -wb \
    > pathogenic_in_enhancers.bed

bedtools intersect -a clinvar_vus.bed -b ENCFF635JIA.bed -wa -wb \
    > vus_in_enhancers.bed
```

### Step 4: Results

```
Pathogenic/Likely pathogenic in enhancers:  47 variants
  Neonatal diabetes-associated:              3
  Type 2 diabetes-associated:                8
  Other endocrine conditions:               36

VUS in pancreas enhancers:                 214 variants
  Near insulin pathway genes (INS, PDX1):   12  -- priority for reclassification
```

The 12 VUS variants overlapping active enhancers near insulin pathway genes are candidates for functional follow-up. Under ACMG guidelines, ENCODE evidence that a variant disrupts a tissue-specific enhancer supports the PS3 criterion (functional studies). A VUS with PS3 evidence may be upgraded to likely pathogenic. Always report star ratings -- a 0-star pathogenic call carries far less weight than a 3-star expert panel review.

### Step 5: Log Provenance

```
encode_log_derived_file(
    file_path="/data/clinvar_annotation/pathogenic_in_enhancers.bed",
    source_accessions=["ENCSR831YAX"],
    description="ClinVar pathogenic variants in H3K27ac pancreas enhancers",
    file_type="variant_annotation",
    tool_used="bedtools intersect v2.31.0 + ClinVar VCF 2026-03 release",
    parameters="GRCh38; pathogenic+likely_pathogenic; IDR thresholded peaks"
)
```

## Key Principles

- **Assembly match is non-negotiable.** ENCODE peaks are GRCh38. The ClinVar VCF must also be GRCh38. No warning when mismatched -- results will simply be wrong.
- **VUS is not benign.** Uncertain significance means insufficient evidence, not absence of pathogenicity. A VUS in an active enhancer is a reclassification candidate.
- **Star ratings gate confidence.** Filter to 2+ stars for high-confidence analyses. Report ratings in every output table.
- **ClinVar updates monthly.** Record the release date in provenance. Classifications change as new evidence is submitted.

## Related Skills

| Skill | Use for |
|-------|---------|
| `variant-annotation` | Full ENCODE regulatory variant prioritization with scoring |
| `gwas-catalog` | Population-level GWAS associations in ENCODE regulatory regions |
| `gnomad-variants` | Population allele frequencies to complement ClinVar pathogenicity |
| `regulatory-elements` | Characterize enhancers and promoters disrupted by variants |
| `disease-research` | Disease-focused ENCODE analysis for clinical phenotypes |

---
*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 43 skills for genomics research*
