---
name: cross-reference
description: Cross-reference ENCODE data with PubMed, GEO, ClinicalTrials, and bioRxiv
---

Link ENCODE experiments with external databases for integrated analysis.

The experiment must be tracked first with `encode_track_experiment`. Use `encode_link_reference` with a `reference_type` of "pmid", "doi", "nct_id", "preprint_doi", "geo_accession", or "other". Use `encode_get_references` to retrieve linked identifiers, optionally filtered by experiment or type. Tracking an experiment also auto-links the GEO and PMID entries in its ENCODE dbxrefs. Pass the retrieved identifiers to the PubMed, bioRxiv and ClinicalTrials.gov MCP servers; GEO is reached through the geo-connector skill.

Refer to the cross-reference skill for detailed guidance.
