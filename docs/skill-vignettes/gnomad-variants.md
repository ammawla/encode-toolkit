# gnomAD Variants -- Population Frequency Context for ENCODE Regulatory Variants

> **Category:** External Databases | **Tools Used:** `encode_search_files`, `encode_download_files`, `encode_log_derived_file`, gnomAD GraphQL API

## What This Skill Does

Queries gnomAD (v4.1: 807,162 individuals) for population allele frequencies and gene constraint metrics (LOEUF, pLI) to interpret variants overlapping ENCODE regulatory elements. Distinguishes common regulatory variants (GWAS candidates) from rare variants in constrained genes (potential pathogenic regulatory mutations).

## When to Use This

- You found variants in ENCODE regulatory peaks and need to know how common they are in the population.
- You identified TF ChIP-seq target genes and want to check whether those genes are loss-of-function intolerant.
- You are filtering GWAS or eQTL variants by frequency before intersecting with ENCODE cCREs.

## Example Session

A scientist studies non-coding variants in pancreatic islet enhancers. She has ENCODE H3K27ac peaks from pancreas tissue and a set of type 2 diabetes GWAS variants. She wants to prioritize rare variants in enhancers near constrained genes.

### Step 1: Get ENCODE Enhancer Peaks

```
encode_search_files(
    assay_title="Histone ChIP-seq", target="H3K27ac", organ="pancreas",
    biosample_type="tissue", output_type="IDR thresholded peaks",
    assembly="GRCh38", file_format="bed"
)
```

Download the peaks, apply blacklist filtering (Amemiya et al. 2019), then intersect with GWAS variants:

```bash
bedtools intersect -v -a h3k27ac_pancreas.bed -b hg38-blacklist.v2.bed > enhancers.filtered.bed
bedtools intersect -a t2d_gwas_variants.bed -b enhancers.filtered.bed -u > variants_in_enhancers.bed
```

This yields 47 T2D-associated variants falling within pancreatic H3K27ac peaks.

### Step 3: Look Up Allele Frequencies in gnomAD

Query each variant against the gnomAD v4.1 GraphQL API:

```bash
curl -X POST https://gnomad.broadinstitute.org/api \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query { variant(variantId: \"11-72751181-C-T\", dataset: gnomad_r4) { rsid joint { ac an af } genome { af populations { id ac an af } } } }"
  }'
```

Results for three representative variants:

| Variant | rsID | Global AF | NFE AF | EAS AF | Category |
|---------|------|-----------|--------|--------|----------|
| 11-72751181-C-T | rs7928810 | 0.22 | 0.26 | 0.08 | Common |
| 7-15064309-G-A | rs540118 | 0.003 | 0.004 | 0.001 | Rare |
| 10-114758349-A-G | -- | absent | absent | absent | Ultra-rare/novel |

The common variant (AF > 0.05) is a GWAS candidate with modest effect. The rare variant (AF < 0.01) and the absent variant warrant closer investigation.

### Step 4: Check Gene Constraint for Target Genes

For each variant-to-gene link (from ENCODE enhancer-gene maps or ABC model), query gene constraint:

```bash
curl -X POST https://gnomad.broadinstitute.org/api \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query { gene(gene_symbol: \"ABCC8\", reference_genome: GRCh38) { gnomad_constraint { pLI oe_lof oe_lof_upper } } }"
  }'
```

| Target Gene | LOEUF | pLI | Interpretation |
|-------------|-------|-----|----------------|
| ABCC8 | 0.28 | 0.99 | Highly constrained -- regulatory disruption likely deleterious |
| TCF7L2 | 0.41 | 0.87 | Moderately constrained |
| KCNJ11 | 0.72 | 0.12 | Tolerant of LoF |

### Step 5: Prioritize Variants

Combine frequency and constraint into a prioritization matrix:

| Variant | Enhancer | AF | Target Gene | LOEUF | Priority |
|---------|----------|----|-------------|-------|----------|
| 10-114758349-A-G | H3K27ac+ | absent | ABCC8 | 0.28 | HIGH -- absent variant near constrained gene |
| 7-15064309-G-A | H3K27ac+ | 0.003 | TCF7L2 | 0.41 | MEDIUM -- rare variant, moderate constraint |
| 11-72751181-C-T | H3K27ac+ | 0.22 | KCNJ11 | 0.72 | LOW -- common variant, tolerant gene |

### Step 6: Log Provenance

```
encode_log_derived_file(
    file_path="/data/pancreas_t2d/prioritized_regulatory_variants.tsv",
    source_accessions=["ENCSR...", "gnomAD_v4.1"],
    description="47 T2D GWAS variants in pancreas H3K27ac peaks, annotated with gnomAD AF and gene constraint",
    tool_used="bedtools intersect v2.31.0 + gnomAD GraphQL API",
    parameters="AF filter: absent/rare (<0.01); constraint: LOEUF<0.35; assembly=GRCh38"
)
```

## Key Principles

- **Use gnomAD genome data for non-coding variants.** gnomAD exome data covers only protein-coding regions. Regulatory variants in enhancers and insulators require the genome dataset specifically.
- **LOEUF over pLI for new analyses.** LOEUF is continuous and better calibrated (Karczewski et al. 2020). pLI is binary (>0.9 or not) and retained only for backward compatibility.
- **Check population-specific frequencies.** A variant "rare" globally (AF = 0.002) may be common in one ancestry group (AF = 0.03 in East Asian). Always report population-specific AFs when interpreting disease relevance.
- **Absent from gnomAD does not mean de novo.** gnomAD excludes severe pediatric disease cohorts. A pathogenic variant may simply be absent from their ascertainment. Conversely, presence in gnomAD at low frequency does not rule out pathogenicity for regulatory variants.
- **Never mix assemblies.** gnomAD v4.1 and ENCODE both use GRCh38. If using gnomAD v2.1.1 (GRCh37), liftOver coordinates before intersecting with ENCODE data.

## Related Skills

- **variant-annotation** -- Full post-GWAS annotation workflow with ENCODE cCREs, RegulomeDB, and CADD scores.
- **regulatory-elements** -- Classify what type of regulatory element a variant falls in before querying gnomAD.
- **clinvar-annotation** -- Add clinical significance to gnomAD-annotated variants.
- **gwas-catalog** -- Pull GWAS associations for the variants being annotated with population frequencies.
- **ensembl-annotation** -- VEP annotation and regulatory feature overlap as a complement to gnomAD frequency data.

---

*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 43 skills for genomics research*
