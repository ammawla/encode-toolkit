# Cross-Reference: Linking ENCODE to External Databases

> Connect your ENCODE experiments to PubMed, GEO, bioRxiv, and ClinicalTrials.gov
> for complete provenance and publication-ready citations.

**Skill:** `cross-reference`
**Tools used:** `encode_link_reference`, `encode_get_references`, `encode_get_citations`

---

## Scenario

You are studying H3K27me3 repression in human pancreas using ENCODE experiment
ENCSR133RZO. You need to link this experiment to its PubMed publication and GEO
submission, then export everything as BibTeX for your manuscript.

**Prerequisite:** The experiment must be tracked first with
`encode_track_experiment(accession="ENCSR133RZO")`.

## Step 1: Link a PubMed Paper

**You ask Claude:** "Link the ENCODE Phase 3 paper (PMID 32728249) to ENCSR133RZO."

**Claude calls:** `encode_link_reference(experiment_accession="ENCSR133RZO", reference_type="pmid", reference_id="32728249", description="ENCODE Phase 3 integrative analysis (Moore et al., Nature 2020)")`

```json
{"status": "linked", "experiment_accession": "ENCSR133RZO",
 "reference_type": "pmid", "reference_id": "32728249"}
```

PMID 32728249 is now attached. This identifier can be passed directly to PubMed MCP
tools (`get_article_metadata`, `find_related_articles`) for literature exploration.

## Step 2: Link a GEO Dataset

**You ask Claude:** "Also link the GEO submission GSE187091 for this experiment."

**Claude calls:** `encode_link_reference(experiment_accession="ENCSR133RZO", reference_type="geo_accession", reference_id="GSE187091", description="GEO submission with supplementary metadata and raw data")`

```json
{"status": "linked", "experiment_accession": "ENCSR133RZO",
 "reference_type": "geo_accession", "reference_id": "GSE187091"}
```

GEO accessions use the GSE format (series level), not GSM (sample level). You can
find GEO accessions in the `dbxrefs` field of `encode_get_experiment` output.

## Step 3: Retrieve All References

**You ask Claude:** "Show me everything I've linked to ENCSR133RZO."

**Claude calls:** `encode_get_references(experiment_accession="ENCSR133RZO")`

```json
{
  "references": [
    {"experiment_accession": "ENCSR133RZO", "reference_type": "pmid",
     "reference_id": "32728249",
     "description": "ENCODE Phase 3 integrative analysis (Moore et al., Nature 2020)"},
    {"experiment_accession": "ENCSR133RZO", "reference_type": "geo_accession",
     "reference_id": "GSE187091",
     "description": "GEO submission with supplementary metadata and raw data"}
  ],
  "total": 2
}
```

Filter by type with `reference_type="pmid"` to retrieve only PubMed links. Supported
types: `pmid`, `doi`, `geo_accession`, `nct_id`, `preprint_doi`, `other`.

## Step 4: Export Citations as BibTeX

**You ask Claude:** "Export my citations in BibTeX format for LaTeX."

**Claude calls:** `encode_get_citations(accession="ENCSR133RZO", export_format="bibtex")`

```bibtex
@article{Moore2020_ENCODE3,
  title   = {Expanded encyclopaedias of {DNA} elements in the human and mouse genomes},
  author  = {Moore, Jill E. and Purcaro, Michael J. and Pratt, Henry E. and others},
  journal = {Nature},
  volume  = {583},
  pages   = {699--710},
  year    = {2020},
  doi     = {10.1038/s41586-020-2493-4},
  note    = {Linked to ENCODE experiment ENCSR133RZO}
}
```

RIS format (for Endnote, Zotero, Mendeley) is also available via `export_format="ris"`.

## Tips

- **Link early.** Attach identifiers when you first track an experiment, not at
  submission time. Metadata is easier to find now than six months from now.
- **PMIDs are plain numbers.** Pass `"32728249"`, not `"PMID:32728249"`.
- **Preprint vs. journal DOI.** Use `reference_type="preprint_doi"` for bioRxiv
  DOIs (`10.1101/YYYY.MM.DD.xxxxxx`) and `reference_type="doi"` for the final
  journal DOI. Track both if a paper has been published from a preprint.
- **NCT IDs must be exact.** Format: `NCT` + 8 digits (e.g., `NCT04567890`).

## Related Skills

| Skill | Use for |
|-------|---------|
| `track-experiments` | Managing your local experiment library |
| `cite-encode` | Generating publication-ready citations |
| `data-provenance` | Logging derived files with full analysis chain |
| `geo-connector` | Querying GEO E-utilities for complementary datasets |
| `disease-research` | Connecting ENCODE regulatory data to disease biology |

---
*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 43 skills for genomics research*
