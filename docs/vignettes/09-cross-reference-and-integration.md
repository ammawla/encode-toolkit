# Cross-Database Integration and Multi-Omics Analysis

> This vignette demonstrates connecting ENCODE data to external databases and performing
> multi-omics integration for comprehensive biological insights. All tool outputs shown
> are from real ENCODE API queries.

**Prerequisites:** You have tracked experiments locally ([Download & Track](02-download-and-track.md)).

**Skills demonstrated:** `cross-reference`, `data-provenance`, `cite-encode`,
`integrative-analysis`, `regulatory-elements`

## Scenario

You have accumulated ENCODE experiments across histone ChIP-seq, ATAC-seq, and RNA-seq
for human pancreas. Now you need to connect them to GEO, PubMed, and genome browsers
while maintaining a complete provenance chain for publication.

## Step 1: Link to GEO

**You ask Claude:** "This ENCODE experiment ENCSR133RZO has GEO data. Link it."

**Claude calls:** `encode_link_reference(experiment_accession="ENCSR133RZO", reference_type="geo_accession", reference_id="GSE187091", description="Original GEO submission for H3K27me3 pancreas ChIP-seq")`

```json
{"status": "linked", "experiment_accession": "ENCSR133RZO",
 "reference_type": "geo_accession", "reference_id": "GSE187091"}
```

**Interpretation:** GEO may contain supplementary metadata not in ENCODE (donor clinical
annotations, custom processing). Reviewers may also require the GEO accession alongside
the ENCODE accession.

## Step 2: Link to PubMed

**You ask Claude:** "Link the ENCODE Phase 3 paper to my tracked experiment."

**Claude calls:** `encode_link_reference(experiment_accession="ENCSR133RZO", reference_type="pmid", reference_id="32728249", description="ENCODE Phase 3 integrative analysis (Moore et al., Nature 2020)")`

```json
{"status": "linked", "experiment_accession": "ENCSR133RZO",
 "reference_type": "pmid", "reference_id": "32728249"}
```

**Interpretation:** PMID 32728249 is now attached to ENCSR133RZO. When you export
citations with `encode_get_citations`, this paper appears automatically. The PMID can
also be passed to PubMed MCP tools for abstract retrieval or related articles.

## Step 3: Retrieve All External References

**You ask Claude:** "Show me all external references I've linked."

**Claude calls:** `encode_get_references()`

```json
{"references": [
   {"experiment_accession": "ENCSR133RZO", "reference_type": "geo_accession",
    "reference_id": "GSE187091"},
   {"experiment_accession": "ENCSR133RZO", "reference_type": "pmid",
    "reference_id": "32728249"}
 ], "total": 2}
```

**Interpretation:** Your library now bridges ENCODE, GEO, and PubMed. Filter by type
with `encode_get_references(reference_type="pmid")`. Supported types: `pmid`, `doi`,
`geo_accession`, `nct_id` (ClinicalTrials.gov), `preprint_doi`, and `other`.

## Step 4: Annotate with Ensembl Gene Models

**You ask Claude:** "What Ensembl annotations are relevant for my pancreas peaks?"

Claude recommends:

- **Gene models:** GENCODE v44 (GRCh38) -- the annotation set used by ENCODE pipelines.
  Select the APPRIS principal isoform or MANE Select transcript for TSS consistency.
- **Regulatory build:** Ensembl Regulatory Build provides pancreas-relevant promoter,
  enhancer, CTCF, and open chromatin annotations.
- **TSS window:** Use +/- 2 kb from canonical TSS for promoter-proximal classification.

Reference: Frankish et al., Nucleic Acids Research (2021). doi: 10.1093/nar/gkaa1087

## Step 5: Visualize in the UCSC Genome Browser

**You ask Claude:** "How do I visualize my ENCODE data in UCSC Browser?"

Claude recommends three approaches: (1) load ENCODE bigWig files directly as custom
tracks via their stable download URLs (e.g., ENCFF387ALH.bigWig for your H3K27me3
signal); (2) register the ENCODE track hub at `encodeproject.org/batch_hub/` for
automatic metadata labels; (3) layer with ENCODE/SCREEN CREs, PhyloP 100-way
conservation, and RepeatMasker for genomic context.

Reference: Nassar et al., Nucleic Acids Research (2023). doi: 10.1093/nar/gkac1072

## Step 6: Multi-Omics Integration Framework

**You ask Claude:** "How do I integrate RNA-seq, ChIP-seq, and ATAC-seq from pancreas?"

Claude uses the `integrative-analysis` skill to recommend:

1. **Assembly alignment.** All experiments must use GRCh38. Restrict to the same biosample
   type (tissue). Mixing tissue with cell line introduces culture-adapted confounds.
2. **Chromatin state classification.** Combine marks to define regulatory states:
   - **Active promoter:** H3K4me3+ / H3K27ac+ / ATAC+ / RNA high
   - **Active enhancer:** H3K4me1+ / H3K27ac+ / ATAC+ / H3K4me3-
   - **Poised enhancer:** H3K4me1+ / H3K27me3+ / ATAC low
   - **Repressed:** H3K27me3+ / H3K9me3+ / ATAC- / RNA low
3. **Statistical integration.** ChromHMM for state segmentation, GREAT for enhancer-gene
   association, ATAC-RNA correlation at promoters for expression prediction.
4. **Batch awareness.** Check signal distributions with MA plots before combining
   experiments from different labs.

References: Ernst & Kellis, Nature Methods (2012) doi: 10.1038/nmeth.1906;
McLean et al., Nature Biotechnology (2010) doi: 10.1038/nbt.1630

## Step 7: Generate a Methods Section with Full Provenance

**You ask Claude:** "Help me write the methods section for my paper."

Claude retrieves tracked experiments, linked references, and derived file records to
generate a structured methods block:

> **Data acquisition.** Histone ChIP-seq data for H3K27me3 in human pancreas tissue
> were obtained from ENCODE (ENCSR133RZO; GEO: GSE187091). Processed peak calls
> (ENCFF635JIA, bed narrowPeak, GRCh38) and signal tracks (ENCFF387ALH, bigWig)
> were downloaded with MD5 verification. Data processed by ENCODE ChIP-seq pipeline v2.
>
> **Post-processing.** Peaks filtered against the ENCODE blacklist v2 (Amemiya et al.,
> 2019) using bedtools subtract. Parameters recorded in provenance record prov_001.
>
> **Citation.** Data generated by the ENCODE Consortium (Moore et al., 2020;
> PMID 32728249). Experiment accessions listed in Supplementary Table 1.

**Why this matters:** Every accession, tool version, and parameter is traceable. The
`encode_get_provenance` tool retrieves the full chain from any derived file back to
its ENCODE source. A reviewer can reconstruct your analysis from identifiers alone.

## Best Practices

- **Link references early.** Add GEO, PubMed, and DOI links when you first track an
  experiment, not at submission time. Memory fades; metadata does not.
- **Use permanent identifiers.** ENCODE accessions, GEO accessions, PMIDs, and DOIs
  are stable. Avoid linking to URLs that may change.
- **One assembly, one annotation.** Never mix GRCh38 peaks with hg19 gene models.
  LiftOver first and document the chain file version.
- **Record everything.** Use `encode_log_derived_file` for every processing step.
  The cost is seconds; the value at review time is immeasurable.
- **Export for collaborators.** `encode_export_data(format="csv")` shares your tracked
  library as a spreadsheet with PMIDs ready for PubMed lookup.

## Skills Demonstrated

- **cross-reference** -- Linking ENCODE to GEO, PubMed, and external databases
- **data-provenance** -- Traceable chain from source data to derived results
- **cite-encode** -- Publication-ready citations with proper ENCODE attribution
- **integrative-analysis** -- Combining histone, accessibility, and expression data
- **regulatory-elements** -- Classifying active, poised, and repressed chromatin states

## What's Next

This vignette covers the final step in a typical ENCODE workflow. For the full path:

- [Discovery & Search](01-discovery-and-search.md) -- Finding data for your tissue
- [Download & Track](02-download-and-track.md) -- Building your local research library
- [Variant & Disease](04-variant-and-disease.md) -- Connecting regulatory elements to GWAS
- [Expression & Single Cell](05-expression-and-single-cell.md) -- Transcriptomic analysis
