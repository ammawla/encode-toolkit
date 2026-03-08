# GEO Connector: Finding Complementary Datasets in NCBI GEO

> Search the Gene Expression Omnibus for datasets that complement your ENCODE
> experiments, link GEO accessions for provenance, and build cross-study
> collections for meta-analysis.

**Skill:** `geo-connector` | **Tools used:** `encode_search_experiments`, `encode_get_experiment`, `encode_link_reference`, `encode_track_experiment`, `encode_log_derived_file`

---

## Scenario

You are profiling chromatin accessibility in human liver and have identified
ENCODE ATAC-seq experiments on liver tissue. You want to find complementary
GEO datasets -- disease cohorts, perturbation experiments, or additional
donors -- that expand your analysis beyond ENCODE's reference samples.

## Step 1: Find ENCODE Experiments and Check for GEO Cross-References

**You ask Claude:** "Find ATAC-seq experiments on human liver tissue in ENCODE."

**Claude calls:** `encode_search_experiments(assay_title="ATAC-seq", organ="liver", biosample_type="tissue")`

| Accession | Biosample | Status | Lab |
|-----------|-----------|--------|-----|
| ENCSR604VJZ | liver tissue male adult (32 years) | released | Michael Snyder, Stanford |
| ENCSR692FUV | liver tissue female adult (53 years) | released | Michael Snyder, Stanford |

**You ask Claude:** "Check if ENCSR604VJZ has a GEO accession."

**Claude calls:** `encode_get_experiment(accession="ENCSR604VJZ")`

Claude inspects the `dbxrefs` field and finds `GEO:GSEuploadpending` or a real
accession like `GEO:GSE 133098`. Not all ENCODE experiments have GEO deposits --
the ENCODE Portal is the canonical source, and GEO is the secondary archive.

## Step 2: Search GEO for Complementary Liver Datasets

**You ask Claude:** "Search GEO for human liver ATAC-seq datasets that are not from ENCODE."

Claude queries E-utilities to find non-ENCODE liver accessibility data:

```bash
# Human liver ATAC-seq series with BED supplementary files
esearch -db gds \
  -query 'liver AND ATAC-seq AND "Homo sapiens"[ORGN] AND gse[ETYP] AND bed[suppFile]'
```

Claude retrieves summaries and presents results:

| GEO Accession | Title | Samples | Year |
|---------------|-------|:-------:|------|
| GSE118683 | Chromatin accessibility in human liver development | 18 | 2019 |
| GSE149038 | ATAC-seq of NAFLD and healthy liver biopsies | 24 | 2021 |
| GSE215930 | Liver zonation chromatin landscape | 12 | 2023 |

These datasets provide developmental stages (GSE118683), disease context
(GSE149038), and spatial resolution (GSE215930) -- none of which exist in
ENCODE's reference collection.

## Step 3: Link GEO Accessions to Tracked ENCODE Experiments

**You ask Claude:** "Track ENCSR604VJZ and link it to GSE149038 for our NAFLD comparison."

**Claude calls:**
1. `encode_track_experiment(accession="ENCSR604VJZ", notes="Liver ATAC-seq, healthy reference for NAFLD comparison")`
2. `encode_link_reference(experiment_accession="ENCSR604VJZ", reference_type="geo_accession", reference_id="GSE149038", description="NAFLD vs healthy liver ATAC-seq (24 samples)")`

```json
{"status": "linked", "experiment_accession": "ENCSR604VJZ",
 "reference_type": "geo_accession", "reference_id": "GSE149038"}
```

The GEO accession is now permanently attached to the ENCODE experiment. You can
retrieve it later with `encode_get_references(experiment_accession="ENCSR604VJZ")`.

## Step 4: Build a Cross-Study Collection for Meta-Analysis

**You ask Claude:** "Also link GSE118683 for the developmental comparison, then show me all references."

**Claude calls:**
1. `encode_link_reference(experiment_accession="ENCSR604VJZ", reference_type="geo_accession", reference_id="GSE118683", description="Liver developmental ATAC-seq (18 samples, fetal to adult)")`
2. `encode_get_references(experiment_accession="ENCSR604VJZ")`

```json
{
  "references": [
    {"reference_type": "geo_accession", "reference_id": "GSE149038",
     "description": "NAFLD vs healthy liver ATAC-seq (24 samples)"},
    {"reference_type": "geo_accession", "reference_id": "GSE118683",
     "description": "Liver developmental ATAC-seq (18 samples, fetal to adult)"}
  ],
  "total": 2
}
```

After running your combined analysis, log the output for provenance:

**Claude calls:** `encode_log_derived_file(file_path="/data/liver_meta/encode_geo_union_peaks.bed", source_accessions=["ENCSR604VJZ", "GSE149038", "GSE118683"], description="Union peak set from ENCODE + GEO liver ATAC-seq (3 studies, 44 samples)", tool_used="bedtools merge v2.31.0", parameters="bedtools merge -d 200 -c 5 -o max")`

This creates a full provenance chain from your derived file back to both ENCODE
and GEO source data.

## Tips

- **GEO UIDs are not accessions.** E-utilities search returns numeric UIDs. Call
  ESummary to convert them to GSE/GSM accession numbers.
- **Use series matrix for expression data.** It downloads 10-100x faster than
  SOFT format and loads directly into R or Python.
- **Filter with `suppFile`.** Adding `bed[suppFile]` or `bw[suppFile]` to your
  GEO query restricts results to series that provide processed peak or signal files.
- **Rate limits apply.** Without an NCBI API key, you are limited to 3 requests
  per second. Always include `tool=encode_mcp` and `email=` parameters.
- **ENCODE Portal is canonical.** If a dataset exists in both ENCODE and GEO,
  always download from ENCODE -- the Portal applies standardized processing
  pipelines and quality audits that GEO submissions may lack.

## Related Skills

| Skill | Use for |
|-------|---------|
| `cross-reference` | Linking PubMed, DOI, NCT, and other external identifiers |
| `data-provenance` | Logging derived files from ENCODE + GEO combined analyses |
| `search-encode` | Finding ENCODE experiments before cross-referencing |
| `track-experiments` | Building your local experiment library |
| `ensembl-annotation` | Annotating genomic coordinates from merged peak sets |

---
*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 43 skills for genomics research*
