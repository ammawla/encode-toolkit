# Changelog

All notable changes to the ENCODE Toolkit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0-beta.1] - 2026-03-08

Initial public beta release.

### Features

- **20 MCP tools** for searching, downloading, and tracking ENCODE data
  - Search experiments and files with comprehensive filters and pagination
  - Download files with MD5 verification, concurrent downloads, and directory organization
  - Local experiment tracking with SQLite (publications, pipelines, quality metrics)
  - Cross-reference with PubMed, bioRxiv, ClinicalTrials.gov, GEO
  - Citation export (BibTeX, RIS) for reference managers
  - Data provenance chain for derived files
  - Batch download with dry-run preview

- **47 skills** across 10 categories
  - Core: setup, search, download, track, cross-reference
  - Analysis: quality assessment, integrative analysis, regulatory elements, epigenome profiling, compare biosamples, visualization, motif analysis, peak annotation, batch analysis
  - Functional genomics: CRISPR/MPRA/STARR-seq screen analysis
  - Data aggregation: histone, accessibility, Hi-C, methylation
  - External databases: UCSC, GEO, gnomAD, Ensembl, GTEx, ClinVar, CELLxGENE, GWAS Catalog, JASPAR
  - Workflows: provenance, citations, variant annotation, pipelines, single-cell, disease research, publication trust, bioinformatics installer, scientific writing, liftover coordinates
  - Pipeline execution: ChIP-seq, ATAC-seq, RNA-seq, WGBS, Hi-C, DNase-seq, CUT&RUN (Nextflow + Docker)
  - Meta-analysis: scRNA-seq meta-analysis, multi-omics integration

- **Async ENCODE API client** with retry logic, 1-hour TTL cache, and rate limiting
- **OS keyring credential management** with Fernet-encrypted file fallback
- **Thread-safe SQLite tracker** with full transaction safety
- **Streaming downloads** with 64KB chunks and SSRF-safe redirect validation
- **506 tests** with 98% code coverage
- **34 literature reference documents** (~320 papers cataloged with DOI, PMID, key findings)
- **9 scientist-facing vignettes** with real ENCODE API output
- **GitHub Actions CI/CD** (pytest across Python 3.10–3.13, ruff lint, plugin validation)
