# Cross-Server Integration Guide

*Author: Dr. Alex M. Mawla, PhD*

The ENCODE MCP server is designed to work seamlessly alongside other science MCP servers in your Claude ecosystem. This guide documents practical workflows combining ENCODE with PubMed, bioRxiv, ClinicalTrials.gov, and Consensus.

**Core principle:** Data interoperability through shared identifiers (PMIDs, DOIs, NCT IDs, GEO accessions), not tight coupling. ENCODE enriches its outputs with identifiers that Claude naturally passes to other servers.

---

## Table of Contents

1. [ENCODE + PubMed](#encode--pubmed)
2. [ENCODE + bioRxiv](#encode--biorxiv)
3. [ENCODE + ClinicalTrials.gov](#encode--clinicaltrialsgov)
4. [ENCODE + Consensus](#encode--consensus)
5. [Multi-Server Workflows](#multi-server-workflows)
6. [Reference Linking System](#reference-linking-system)
7. [Data Export for Cross-Referencing](#data-export-for-cross-referencing)

---

## ENCODE + PubMed

The PubMed MCP server provides access to 36M+ biomedical articles. ENCODE experiments often cite or are cited by PubMed-indexed papers.

### Workflow 1: Find Papers That Used ENCODE Data

Track an experiment, then use the auto-extracted PMIDs to search PubMed for related work.

```
User: Track ENCODE experiment ENCSR133RZO and find related PubMed articles

Claude chains:
1. encode_track_experiment("ENCSR133RZO")
   → Returns experiment metadata + auto-extracted PMIDs from publications
2. encode_get_citations("ENCSR133RZO", export_format="json")
   → Returns PMIDs: ["32728249", "29126249"]
3. get_article_metadata(pmids=["32728249", "29126249"])
   → Full PubMed metadata for each paper
4. find_related_articles(pmids=["32728249"])
   → Discover additional related papers
```

### Workflow 2: From PubMed Paper to ENCODE Data

Start from a paper, find ENCODE experiments it references.

```
User: I found PMID 32728249 about pancreatic islet chromatin. What ENCODE data exists for this?

Claude chains:
1. get_article_metadata(pmids=["32728249"])
   → Extract: pancreas, islets, ChIP-seq, histone marks
2. encode_search_experiments(assay_title="Histone ChIP-seq", organ="pancreas")
   → Find matching ENCODE experiments
3. encode_track_experiment(accession)
   → Track the most relevant experiments
4. encode_link_reference(accession, "pmid", "32728249", "Paper that motivated this analysis")
   → Link the paper to tracked experiments for provenance
```

### Workflow 3: Export Combined Bibliography

Generate a bibliography combining ENCODE tracking data with PubMed metadata.

```
User: Export my tracked ENCODE experiments with their PubMed references in BibTeX

Claude chains:
1. encode_get_citations(export_format="bibtex")
   → BibTeX entries for ENCODE-associated publications
2. encode_get_references(reference_type="pmid")
   → All manually-linked PMIDs
3. get_article_metadata(pmids=[...additional PMIDs...])
   → Enrich with full PubMed metadata
```

---

## ENCODE + bioRxiv

The bioRxiv MCP server indexes preprints in biological sciences. Many ENCODE-related analyses appear as preprints before peer review.

### Workflow 1: Find Preprints Analyzing ENCODE Data

Search bioRxiv for recent preprints in genomics that may use ENCODE data.

```
User: Are there recent bioRxiv preprints about H3K27me3 in pancreatic development?

Claude chains:
1. search_preprints(category="genomics", recent_days=90)
   → Recent genomics preprints
2. encode_search_experiments(target="H3K27me3", organ="pancreas")
   → ENCODE experiments for this mark/tissue combination
3. encode_get_facets(assay_title="Histone ChIP-seq", organ="pancreas")
   → What targets/biosamples are available in ENCODE
```

### Workflow 2: Track Preprint-to-Publication Pipeline

Link both the preprint DOI and the eventual published PMID to an experiment.

```
User: Link this bioRxiv preprint about our ENCODE analysis to the experiment

Claude chains:
1. get_preprint(doi="10.1101/2024.01.15.123456")
   → Get preprint metadata
2. encode_link_reference("ENCSR133RZO", "preprint_doi", "10.1101/2024.01.15.123456",
     "Preprint describing our analysis")
   → Store preprint link
3. search_published_preprints(date_from="2024-06-01", date_to="2025-03-01")
   → Check if preprint has been published
4. If published: encode_link_reference("ENCSR133RZO", "doi", published_doi,
     "Published version")
```

---

## ENCODE + ClinicalTrials.gov

The ClinicalTrials.gov MCP server searches clinical trial data. ENCODE provides foundational genomic data for many therapeutic targets being tested in trials.

### Workflow 1: Bridge Preclinical ENCODE Data to Clinical Trials

Find clinical trials targeting the same genes/pathways studied in ENCODE.

```
User: Are there clinical trials targeting genes we've found in our ENCODE ChIP-seq data?

Claude chains:
1. encode_search_experiments(assay_title="TF ChIP-seq", organ="pancreas",
     biosample_type="tissue")
   → Find transcription factor ChIP-seq experiments
   → Extract target names: CTCF, FOXA2, PDX1, etc.
2. search_trials(condition="diabetes", intervention="FOXA2")
   → Find trials related to these targets
3. encode_link_reference("ENCSR...", "nct_id", "NCT04567890",
     "Clinical trial targeting FOXA2 in diabetes")
   → Link trial to ENCODE experiment
```

### Workflow 2: Epigenomic Context for Clinical Targets

Use ENCODE data to understand the regulatory landscape of clinical trial targets.

```
User: What does ENCODE tell us about the regulatory landscape of BRCA1?

Claude chains:
1. encode_search_experiments(target="BRCA1")
   → Find all ENCODE experiments targeting BRCA1
2. encode_get_facets(assay_title="TF ChIP-seq", organ="breast")
   → Available breast tissue data
3. search_trials(condition="breast cancer", intervention="BRCA")
   → Active BRCA-related trials
4. analyze_endpoints(condition="breast cancer", phase=["PHASE3"])
   → Common endpoints in breast cancer trials
```

---

## ENCODE + Consensus

The Consensus MCP server searches 200M+ academic papers with quality filtering. Use it for broader literature context around ENCODE data.

### Workflow 1: Literature Review for ENCODE Targets

Find high-quality published research on specific histone marks or transcription factors.

```
User: What does the literature say about H3K4me3 in gene regulation?

Claude chains:
1. search(query="H3K4me3 histone modification gene regulation",
     year_min=2020, sjr_max=2)
   → High-quality recent papers on H3K4me3
2. encode_search_experiments(target="H3K4me3", limit=10)
   → Available ENCODE data for this mark
3. encode_get_facets(assay_title="Histone ChIP-seq")
   → What tissues/cell types have H3K4me3 data
```

### Workflow 2: Validate ENCODE Data Quality Against Literature

Cross-reference ENCODE experiment quality with published benchmarks.

```
User: Are there papers about ChIP-seq quality standards I should compare my ENCODE data against?

Claude chains:
1. search(query="ChIP-seq quality control standards ENCODE",
     year_min=2019, sjr_max=1)
   → Papers on ChIP-seq QC standards
2. encode_summarize_collection()
   → Overview of tracked experiments with audit counts
3. encode_export_data(format="csv")
   → Export for comparison with published benchmarks
```

---

## Multi-Server Workflows

### Example: Pancreatic Cancer Epigenomics

A complete research workflow using all five servers.

```
Step 1: Discover ENCODE data
> encode_search_experiments(assay_title="Histone ChIP-seq", organ="pancreas",
    biosample_type="tissue")
→ Find pancreas histone ChIP-seq experiments

Step 2: Track and summarize
> encode_track_experiment("ENCSR...") (for each relevant experiment)
> encode_summarize_collection(organ="pancreas")
→ Overview: which marks, how many experiments, quality

Step 3: Find published analyses (PubMed)
> encode_get_citations(export_format="json")
→ Extract PMIDs from ENCODE publications
> find_related_articles(pmids=[...])
→ Expand to related PubMed articles

Step 4: Check preprints (bioRxiv)
> search_preprints(category="cancer biology", recent_days=180)
→ Recent preprints on pancreatic cancer epigenomics

Step 5: Literature context (Consensus)
> search(query="pancreatic cancer epigenomics histone modifications",
    year_min=2022, sjr_max=2)
→ High-quality papers providing broader context

Step 6: Clinical translation (ClinicalTrials.gov)
> search_trials(condition="pancreatic cancer", status=["RECRUITING"])
→ Active pancreatic cancer trials
> analyze_endpoints(condition="pancreatic cancer", phase=["PHASE3"])
→ Common endpoints and outcomes

Step 7: Link everything together
> encode_link_reference("ENCSR...", "pmid", "12345678", "Key paper")
> encode_link_reference("ENCSR...", "nct_id", "NCT04567890", "Related trial")
> encode_export_data(format="csv")
→ Complete exportable record with cross-references
```

### Example: BRCA1 Regulatory Landscape

```
Step 1: ENCODE data for BRCA1
> encode_search_experiments(target="BRCA1")
> encode_search_experiments(assay_title="ATAC-seq", organ="breast")

Step 2: Literature on BRCA1 regulation
> search(query="BRCA1 transcriptional regulation chromatin", year_min=2021)
> search_articles(query="BRCA1 enhancer regulation breast cancer")

Step 3: Clinical context
> search_trials(condition="breast cancer", intervention="BRCA")
> search_by_eligibility(condition="breast cancer",
    eligibility_keywords="BRCA mutation")

Step 4: Preprint watch
> search_preprints(category="cancer biology", recent_days=60)
```

### Example: Drug Target Validation

Connecting ENCODE regulatory data to clinical development.

```
Step 1: Find ENCODE data for target gene
> encode_search_experiments(target="TP53")
> encode_list_files(experiment_accession, file_format="bed",
    output_type="IDR thresholded peaks")

Step 2: Published evidence
> search(query="TP53 reactivation therapeutic strategy", year_min=2022)
> search_articles(query="TP53[Title] AND drug development")

Step 3: Clinical pipeline
> search_trials(intervention="TP53", status=["RECRUITING", "ACTIVE_NOT_RECRUITING"])
> search_by_sponsor(sponsor_name="Novartis", condition="TP53")

Step 4: Track and cross-link
> encode_track_experiment("ENCSR...")
> encode_link_reference("ENCSR...", "nct_id", "NCT...", "TP53 reactivation trial")
> encode_link_reference("ENCSR...", "pmid", "...", "Key mechanism paper")
```

---

## Reference Linking System

The `encode_link_reference` and `encode_get_references` tools form the bridge between ENCODE and other servers.

### Supported Reference Types

| Type | Description | Example ID | Target Server |
|------|-------------|-----------|---------------|
| `pmid` | PubMed article ID | `32728249` | PubMed MCP |
| `doi` | Digital Object Identifier | `10.1038/s41586-020-2012-7` | Any |
| `preprint_doi` | bioRxiv/medRxiv DOI | `10.1101/2024.01.15.123456` | bioRxiv MCP |
| `nct_id` | ClinicalTrials.gov ID | `NCT04567890` | ClinicalTrials MCP |
| `geo_accession` | GEO dataset ID | `GSE118349` | GEO (future) |
| `other` | Any other identifier | Free text | Any |

### Auto-Linking

When you track an experiment with `encode_track_experiment`, the server automatically extracts and links:
- **GEO accessions** from the experiment's `dbxrefs` field
- **PMIDs** from the experiment's `dbxrefs` field
- **Publications** from the experiment's associated papers

This means many cross-references are available immediately after tracking, without manual linking.

### Querying References

```
# All PMIDs across all tracked experiments
encode_get_references(reference_type="pmid")

# All references for a specific experiment
encode_get_references(experiment_accession="ENCSR133RZO")

# All clinical trial links
encode_get_references(reference_type="nct_id")
```

---

## Data Export for Cross-Referencing

### CSV/TSV Export

The `encode_export_data` tool generates tabular exports that include PMIDs and reference counts, making it easy to import into R, Python, or Excel for cross-referencing with other data sources.

```
encode_export_data(format="csv")
```

Output columns include:
- `accession`, `assay_title`, `target`, `organism`, `organ`
- `biosample_term_name`, `lab`, `assembly`, `status`, `date_released`
- `pmids` — comma-separated list of linked PubMed IDs
- `publication_count`, `reference_count`

### Collection Summary

The `encode_summarize_collection` tool provides grouped statistics:

```
encode_summarize_collection()
```

Returns counts grouped by assay type, target, organism, organ, biosample type, and lab, along with totals for publications, derived files, and external references.

### BibTeX/RIS Citation Export

For bibliography managers (Zotero, Mendeley, EndNote):

```
encode_get_citations(export_format="bibtex")  # For LaTeX
encode_get_citations(export_format="ris")     # For Zotero/Mendeley/EndNote
```

---

## Tips for Effective Cross-Server Workflows

1. **Track first, then link.** Always `encode_track_experiment` before linking references — the experiment must be in your local tracker.

2. **Use auto-linking.** When tracking experiments, GEO accessions and PMIDs from ENCODE metadata are linked automatically. Check `encode_get_references` to see what was auto-discovered.

3. **Export regularly.** Use `encode_export_data(format="csv")` to create snapshots of your tracked collection with all cross-references.

4. **Link as you discover.** When PubMed, bioRxiv, or ClinicalTrials returns relevant results, immediately link them with `encode_link_reference` so the connection isn't lost.

5. **Summarize before deep dives.** Use `encode_summarize_collection` to understand what you have before diving into specific analyses.

6. **Shared identifiers are the key.** PMIDs, DOIs, NCT IDs, and GEO accessions are the common language between servers. When you see one, you can always pass it to the appropriate server.
