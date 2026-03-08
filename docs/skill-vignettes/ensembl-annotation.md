# Ensembl Annotation -- VEP, Regulatory Build, and Liftover for ENCODE Data

> **Category:** External Databases | **Tools Used:** `encode_search_experiments`, `encode_list_files`, `encode_download_files`, Ensembl REST API

## What This Skill Does

Queries the Ensembl REST API to annotate variants with VEP (consequence, CADD, REVEL, SpliceAI), classify ENCODE regions against the Ensembl Regulatory Build, convert coordinates between GRCh37 and GRCh38, and resolve gene identifiers across databases. The Ensembl Regulatory Build incorporates ENCODE, Roadmap Epigenomics, and Blueprint data into a unified regulatory annotation -- querying it provides an independent, aggregated view of your ENCODE regions (Zerbino et al. 2015).

## When to Use This

- You have GWAS variants falling in ENCODE peaks and need consequence predictions with pathogenicity scores.
- You want to compare ENCODE cCRE classifications against the Ensembl Regulatory Build for independent validation.
- You have older data on hg19/GRCh37 that needs liftover before intersecting with ENCODE GRCh38 files.

## Example Session

A scientist has GWAS hits for type 2 diabetes that overlap ENCODE ATAC-seq peaks in human pancreas. She wants to annotate these variants with VEP, cross-check against the Ensembl Regulatory Build, and liftover legacy coordinates from a collaborator's hg19 dataset.

### Step 1: Run VEP on Variants in ENCODE Peaks

First, retrieve ATAC-seq peaks from pancreas to define the regulatory landscape:

```
encode_search_experiments(assay_title="ATAC-seq", organ="pancreas", biosample_type="tissue")
encode_list_files(experiment_accession="ENCSR...", file_format="bed",
    output_type="IDR thresholded peaks", assembly="GRCh38", preferred_default=True)
```

After intersecting GWAS variants with downloaded peaks using `bedtools intersect`, annotate each overlapping variant with VEP. For a single variant:

```bash
curl -H "Content-type: application/json" \
  "https://rest.ensembl.org/vep/human/id/rs7903146?CADD=1;REVEL=1;SpliceAI=1;regulatory=1"
```

For a batch of variants in ENCODE peaks (up to 200 per request):

```bash
curl -X POST -H "Content-type: application/json" \
  "https://rest.ensembl.org/vep/human/region" \
  -d '{"variants": ["10 114758349 . C T . . .", "11 72433098 . G A . . ."]}'
```

Most variants in ATAC-seq peaks will return `regulatory_region_variant` with MODIFIER impact. This does not mean low importance -- VEP cannot assess regulatory disruption from sequence alone. The CADD score, combined with the ENCODE cCRE class and tissue-specific chromatin state, gives a far more complete picture.

### Step 2: Classify ENCODE Regions Against the Ensembl Regulatory Build

For each ENCODE peak region of interest, query the Ensembl Regulatory Build for its independent classification:

```bash
curl -H "Content-type: application/json" \
  "https://rest.ensembl.org/overlap/region/human/10:114756000-114760000?feature=regulatory;feature=motif"
```

Compare the returned feature types against ENCODE cCRE labels:

| Ensembl Regulatory Build | ENCODE cCRE Equivalent |
|--------------------------|------------------------|
| Promoter                 | PLS (promoter-like)    |
| Enhancer                 | pELS / dELS            |
| Open chromatin           | DNase-only             |
| CTCF binding site        | CTCF-only              |

Agreement between the two catalogs strengthens confidence. Discrepancies often arise because the Regulatory Build includes Blueprint and Roadmap data from tissues not in ENCODE, or because ENCODE's cCRE pipeline uses different thresholds. Report both classifications and note the Ensembl version (currently 114).

### Step 3: Liftover Legacy Coordinates (hg19 to GRCh38)

A collaborator provides ChIP-seq peaks called on hg19. Before intersecting with ENCODE GRCh38 data, convert coordinates:

```bash
# Single region
curl -H "Content-type: application/json" \
  "https://rest.ensembl.org/map/human/GRCh37/10:114756000..114760000:1/GRCh38"

# For many regions, loop through a BED file
while read chr start end; do
  curl -s -H "Content-type: application/json" \
    "https://rest.ensembl.org/map/human/GRCh37/${chr}:${start}..${end}:1/GRCh38"
  sleep 0.2  # respect rate limits
done < legacy_peaks.bed > lifted_results.json
```

For genome-wide liftover (thousands of regions), the REST API is too slow. Use UCSC `liftOver` or CrossMap locally instead. The REST API is best suited for targeted queries of tens to low hundreds of regions.

After liftover, always verify that lifted coordinates still overlap the expected gene or regulatory feature -- structural rearrangements between assemblies can shift regions to unexpected locations.

## Key Principles

- **VEP MODIFIER does not mean unimportant.** Non-coding regulatory variants are classified as MODIFIER by default. Combine the VEP consequence with ENCODE cCRE class, CADD score, and tissue activity to assess functional significance.
- **Two catalogs are better than one.** The Ensembl Regulatory Build and ENCODE cCREs use different input data and algorithms. Agreement between them increases confidence; disagreement flags regions worth investigating further.
- **Always match assemblies.** ENCODE data is on GRCh38. Older GWAS catalogs and collaborator datasets may be on GRCh37. Liftover before intersecting, never after.
- **Batch limits matter.** VEP REST accepts 200 variants per POST. Overlap queries are capped at ~5Mb. For larger analyses, install the standalone VEP tool or download Ensembl GFF files.

## Related Skills

- **variant-annotation** -- Full ENCODE-based post-GWAS workflow with cCRE intersection and TF disruption analysis.
- **regulatory-elements** -- Build tissue-specific cCRE catalogs from ENCODE histone marks and accessibility data.
- **gnomad-variants** -- Add population allele frequencies and gene constraint scores to your variant annotations.
- **ucsc-browser** -- Retrieve UCSC-hosted ENCODE tracks and cCRE annotations via REST API.
- **disease-research** -- Connect annotated regulatory variants to disease mechanisms.

---
*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 43 skills for genomics research*
