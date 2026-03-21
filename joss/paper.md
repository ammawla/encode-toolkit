---
title: 'ENCODE Toolkit: An End-to-End, AI-Native Genomics Suite for the Portable Researcher'
tags:
  - Python
  - bioinformatics
  - genomics
  - epigenomics
  - ENCODE
  - functional genomics
  - MCP
authors:
  - name: Alex M. Mawla
    orcid: 0000-0003-0907-464X
    corresponding: true
    affiliation: 1
affiliations:
  - name: Independent Researcher
    index: 1
date: 20 March 2026
bibliography: paper.bib
---

# Summary

ENCODE Toolkit gives researchers a complete, portable environment for working with functional genomics data from the Encyclopedia of DNA Elements (ENCODE) Project [@encode2012; @encode2020]. It covers the entire research workflow — discovery, download, experiment tracking, cross-database integration, quality assessment, pipeline execution, provenance, and publication output — so a researcher can move from hypothesis to publication-ready results in a single session. A local SQLite database acts as a personal experiment library, tracking metadata, publications, quality metrics, derived files, and cross-references to 14 external databases including GEO [@geo2013], GTEx [@gtex2020], ClinVar [@clinvar2018], GWAS Catalog [@gwas2023], gnomAD [@gnomad2020], JASPAR [@jaspar2024], Ensembl [@ensembl2023], UCSC Genome Browser [@ucsc2023], Open Targets [@opentargets2023], and CELLxGENE [@cellxgene2025]. Seven Nextflow pipelines cover the major ENCODE assay types — ChIP-seq [@landt2012], ATAC-seq [@buenrostro2013], RNA-seq [@conesa2016], WGBS [@lister2009], Hi-C [@lieberman2009], DNase-seq [@thurman2012], and CUT&RUN [@skene2017] — each implementing the foundational protocol for that assay. Forty-seven literature-backed workflow skills guide researchers through multi-step analyses — data aggregation, variant annotation, motif analysis, meta-analysis — each with its own documentation, literature references, and validation scripts. ENCODE Toolkit builds on the Model Context Protocol [@mcp2024] and ships via PyPI, npm, and the Claude Code plugin marketplace.

# Statement of Need

The ENCODE Project has generated thousands of functional genomics datasets across hundreds of cell types and tissues — histone modifications, transcription factor binding, chromatin accessibility, DNA methylation, RNA expression, and 3D genome organization [@encode2012; @encode2020]. Researchers routinely need to search, download, and integrate these datasets with GWAS catalogs, clinical variant databases, and tissue expression atlases. The current workflow requires navigating web portals, writing custom API scripts, manually tracking file provenance, and reconciling metadata across databases. This is slow, error-prone, and difficult to reproduce.

ENCODE Toolkit fills this gap. It installs with a single command (`pip install encode-toolkit`), handles its own dependencies, and connects to all required databases and bioinformatics tools — following established protocols and community standards at every step. Built on the Model Context Protocol [@mcp2024], it enables AI assistants to access ENCODE data through natural language while maintaining full programmatic control. A researcher can say "find all H3K27ac ChIP-seq experiments in human pancreas" and receive structured results with quality metrics, audit status, and download capabilities. From there, the toolkit supports the full downstream workflow: launching Nextflow pipelines, tracking every derived file back to its source data, and generating publication-ready methods sections and citations.

# State of the Field

Existing tools for ENCODE data access address individual steps but not the full workflow. The ENCODE portal provides a web interface and REST API for search and download, but neither offers integrated cross-referencing, provenance tracking, or pipeline execution. The ENCODE `metadata.tsv` downloader handles bulk file retrieval but lacks search capabilities and quality assessment. Bioinformatics pipeline frameworks such as nf-core [@ewels2020] provide standardized Nextflow workflows for common assays, but they operate independently of ENCODE's metadata, audit, and cross-referencing infrastructure. Galaxy [@afgan2018] offers web-based workflow execution with provenance tracking, but requires server infrastructure and does not integrate ENCODE-specific quality thresholds or cross-database linking. No existing tool combines ENCODE data access with cross-database integration, automated quality control using published thresholds [@landt2012; @buenrostro2013], reproducible analysis pipelines, and end-to-end provenance tracking in a single, locally installable platform.

# Software Design

Five functional layers address distinct stages of the research workflow:

**Discovery and search.** Four search tools query the ENCODE API with over 20 filters — assay type, organism, organ, biosample, target, treatment, life stage, sex, genetic modification, date range, and free text. A live facet explorer returns dynamic counts of available data before committing to a search. A metadata reference provides valid filter values to prevent query errors, and the toolkit warns when filter values have wrong casing or are unrecognized.

**Data acquisition.** A download manager handles concurrent file retrieval with MD5 integrity verification, SSRF-safe redirect validation, and configurable directory organization. A batch download tool combines search and download in one operation with dry-run preview. An OS keyring credential manager with Fernet-encrypted fallback handles authenticated access to restricted datasets.

**Experiment tracking.** A thread-safe SQLite database acts as a personal research library. When a researcher tracks an experiment, the toolkit automatically fetches the experiment metadata, associated publications (PMIDs, DOIs, authors, journal, abstract), pipeline information (software versions, methods), and quality metrics. It auto-extracts cross-references from ENCODE's `dbxrefs` field — GEO accessions and PMIDs linked without manual input. A compatibility analyzer checks whether two experiments can be safely combined by comparing organism, assembly, assay type, biosample, and replication strategy.

**Provenance and cross-referencing.** A provenance system logs every derived file — filtered peaks, merged signals, differential analyses — back to its ENCODE source accessions, recording the tool, parameters, and file type. A cross-referencing bridge links tracked experiments to PubMed IDs, DOIs, bioRxiv preprints, ClinicalTrials.gov NCT IDs, and GEO accessions, creating a unified record that spans databases. Export functions produce CSV, TSV, or JSON tables for R or pandas. Citation tools generate BibTeX and RIS entries for reference managers.

**Quality assessment.** The toolkit applies published quality thresholds across assay types: FRiP $\geq$ 1%, NSC $>$ 1.05, and RSC $>$ 0.8 for ChIP-seq [@landt2012]; TSS enrichment $\geq$ 5 for ATAC-seq on GRCh38 per ENCODE data standards; mapping rates of 70–90% and replicate correlation $\geq$ 0.9 (isogenic) for RNA-seq [@conesa2016]; bisulfite conversion $\geq$ 98% for WGBS per ENCODE data standards [@encode2020]. The toolkit surfaces all four levels of ENCODE's own audit system — ERROR, NOT_COMPLIANT, WARNING, INTERNAL_ACTION — alongside these metrics.

All 20 tools are exposed through the Model Context Protocol [@mcp2024], enabling integration with any MCP-compatible client. The async ENCODE API client uses a token-bucket rate limiter respecting ENCODE's 10 requests/second policy and a one-hour TTL cache to minimize redundant calls. All data remains local — no telemetry, no analytics, no data sent to any server other than the ENCODE API over HTTPS.

# Research Impact Statement

ENCODE Toolkit supports workflows across the functional genomics landscape. Epigenomic profiling aggregates histone modification data across experiments to build chromatin state maps for tissues of interest. Variant-to-function mapping overlays GWAS hits on ENCODE regulatory elements, cross-referencing ClinVar pathogenicity annotations and gnomAD population frequencies to prioritize causal variants. Disease mechanism investigation integrates ENCODE annotations with clinical variant databases and tissue-specific expression from GTEx. Single-cell workflows support cross-study meta-analysis with batch correction and cell type harmonization, using Seurat integration [@stuart2019], Harmony batch correction [@tran2020], and scRNA-seq best practices [@luecken2019], following the cross-study reproducibility framework of Mawla et al. [@mawla2019].

The 47 workflow skills draw on approximately 320 cited primary references with assay-specific quality thresholds, ensuring analyses follow community best practices. Seven Nextflow DSL2 pipelines with Docker containerization provide reproducible processing from raw FASTQ files to peaks, signal tracks, contact matrices, and methylation calls using ENCODE-standard parameters.

# Availability

ENCODE Toolkit is available on PyPI (`pip install encode-toolkit`), npm (`npx encode-toolkit`), and the Claude Code plugin marketplace (`/plugin install encode-toolkit`). Source code is at [https://github.com/ammawla/encode-toolkit](https://github.com/ammawla/encode-toolkit) under the AGPL-3.0 license. The package includes 568 automated tests with 98% code coverage, continuous integration across Python 3.10–3.13, and documentation including API reference, walkthrough guide, and 9 scientist-facing vignettes.

# AI Usage Disclosure

Generative AI was used during development and documentation of this software. The model used was Claude Opus (Anthropic, claude-opus-4-20250514) via Claude Code. AI assistance covered the following areas:

- **Skill refinement**: Claude's skill-builder commands were used across the workflow skill documents (SKILL.md files and literature references).
- **Code critique and review**: Identifying bugs, suggesting improvements, and reviewing code quality across the codebase.
- **Test scaffolding**: Generating test case structures and expanding test coverage.
- **CI/CD workflows**: Drafting GitHub Actions workflow files for testing, linting, and release automation.
- **Documentation**: Assisting with API reference documentation, vignettes, and formatting and compliance checks on this paper.

All architecture decisions, software design, API design, and scientific content were made by the human author. All AI-generated outputs were reviewed, edited, and validated by the author prior to inclusion.

# Acknowledgments

This work uses data from the ENCODE Project, funded by the National Human Genome Research Institute (NHGRI). The author thanks the ENCODE Consortium and the ENCODE Data Coordination Center for making functional genomics data freely available.

# References
