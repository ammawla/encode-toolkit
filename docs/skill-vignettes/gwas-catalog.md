# GWAS Catalog -- Linking Disease Variants to ENCODE Regulatory Elements

> **Category:** External Databases | **Tools Used:** `encode_search_experiments`, `encode_list_files`, `encode_get_facets`, `encode_track_experiment`, `encode_log_derived_file`, `encode_link_reference` | **External API:** EBI GWAS Catalog REST API

## What This Skill Does

Queries the NHGRI-EBI GWAS Catalog to retrieve disease-associated variants, overlaps them with ENCODE regulatory elements in disease-relevant tissues, and links regulatory variants to target genes using Hi-C and chromatin accessibility data.

## When to Use This

- You have GWAS hits for a disease and need to know which fall in functional regulatory elements.
- You need to connect GWAS loci to target genes through enhancer-gene links (ABC model, Hi-C).

## Example Session

### Scientist's Request

> "I'm studying type 2 diabetes genetics. Can you find the top GWAS associations for T2D and show me which ones fall in ENCODE regulatory elements in pancreatic islets?"

### Step 1: Survey ENCODE Data for the Disease-Relevant Tissue

```
encode_get_facets(organ="pancreas", assay_title="Histone ChIP-seq")
```

The facets confirm 6 H3K27ac and 8 H3K4me3 experiments in islets, plus ATAC-seq for accessibility -- sufficient annotation layers for variant overlap.

### Step 2: Query the GWAS Catalog for Type 2 Diabetes Loci

```python
import requests
efo_id = "EFO_0001360"  # Type II diabetes mellitus
url = f"https://www.ebi.ac.uk/gwas/rest/api/efoTraits/{efo_id}/associations"
response = requests.get(url, params={"size": 500})
associations = response.json()["_embedded"]["associations"]
```

Three well-established T2D loci serve as test cases:

| Locus | Lead SNP | Gene | Chromosome | p-value | Risk Allele |
|---|---|---|---|---|---|
| 10q25.2 | rs7903146 | TCF7L2 | chr10:112,998,590 | 2e-120 | T |
| 11p15.1 | rs5219 | KCNJ11 | chr11:17,388,025 | 4e-14 | T |
| 8q24.11 | rs13266634 | SLC30A8 | chr8:117,172,544 | 5e-18 | C |

### Step 3: Retrieve ENCODE Peak Files for Islet Regulatory Elements

Pull H3K27ac (enhancers) and ATAC-seq (accessibility) peak files in GRCh38.

```
encode_search_experiments(
  assay_title="Histone ChIP-seq", organ="pancreas",
  biosample_term_name="islet of Langerhans", target="H3K27ac", status="released"
)
encode_list_files(
  experiment_accession="ENCSR976DGM", file_format="bed",
  output_type="IDR thresholded peaks", assembly="GRCh38", preferred_default=True
)
```

Repeat for ATAC-seq to get the accessibility layer.

### Step 4: Intersect GWAS Variants with ENCODE Peaks

Overlap T2D variant coordinates with islet regulatory elements:

```bash
bedtools intersect -a t2d_gwas_variants.bed -b islet_h3k27ac_peaks.bed -wa -wb > t2d_in_enhancers.bed
bedtools intersect -a t2d_gwas_variants.bed -b islet_atac_peaks.bed -wa -wb > t2d_in_accessible.bed
```

### Step 5: Interpret the Overlap Results

| Lead SNP | Gene | In Islet H3K27ac Peak | In Islet ATAC Peak | Regulatory Classification | Priority |
|---|---|---|---|---|---|
| rs7903146 | TCF7L2 | Yes -- islet-specific enhancer | Yes | Active enhancer in islets; variant disrupts TCF/LEF binding motif | Highest |
| rs5219 | KCNJ11 | No | No | Missense coding variant (E23K); not a regulatory mechanism | Low (coding) |
| rs13266634 | SLC30A8 | No | No | Missense coding variant (R325W); zinc transporter loss-of-function | Low (coding) |

The rs7903146 variant at TCF7L2 falls within an islet-specific H3K27ac enhancer and an open chromatin peak -- a regulatory mechanism. The KCNJ11 and SLC30A8 variants are coding missense changes that would not overlap regulatory elements, illustrating why ENCODE overlay is most informative for non-coding GWAS hits.

### Step 6: Link the Regulatory Variant to Its Target Gene

For rs7903146, the nearest gene (TCF7L2) happens to be the correct target, but this is not always the case. Confirm with ENCODE Hi-C and the ABC model (Nasser et al. 2021):

```
encode_search_experiments(assay_title="Hi-C", organ="pancreas")
```

ABC confirms the rs7903146-containing enhancer contacts the TCF7L2 promoter. Cross-reference with GTEx pancreas eQTLs via `gtex-expression` for additional support.

### Step 7: Log Provenance

```
encode_track_experiment(accession="ENCSR976DGM", notes="H3K27ac peaks used for T2D GWAS overlay")
encode_log_derived_file(
  file_path="/data/t2d_gwas_encode_overlay.tsv",
  source_accessions=["ENCSR976DGM"],
  description="T2D GWAS variants (EFO_0001360) overlapped with islet H3K27ac peaks",
  tool_used="bedtools intersect + GWAS Catalog REST API",
  parameters="GRCh38, p<5e-8, IDR thresholded peaks"
)
encode_link_reference(
  experiment_accession="ENCSR976DGM", reference_type="other",
  reference_id="EFO_0001360", description="GWAS Catalog T2D trait used for variant overlay"
)
```

## Related Skills

- **variant-annotation** -- Full variant prioritization with ENCODE regulatory annotations.
- **clinvar-annotation** -- Clinical significance of GWAS variants in ENCODE peaks.
- **gtex-expression** -- eQTL colocalization to validate variant-to-gene assignments.
- **regulatory-elements** -- Characterize enhancers/promoters/insulators at GWAS loci.
- **disease-research** -- Broader disease-focused ENCODE analysis beyond GWAS.
- **publication-trust** -- Verify literature claims backing the analytical framework.

---

*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 43 skills for genomics research*