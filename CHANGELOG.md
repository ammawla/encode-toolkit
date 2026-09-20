# Changelog

All notable changes to the ENCODE Toolkit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.2] - 2026-09-20

Maintenance release. The Python package is functionally identical to 0.3.1.

### Fixed

- `bioinformatics-installer` skill: the ChIP-seq walkthrough pointed at `scripts/chipseq-env.yml`
  (the file lives in `environments/`) and at an `annotation-env.yml` that did not exist. The first
  path is corrected and the second is replaced with an explicit `conda create` command.

### Changed

- Removed local tooling configuration files from the repository and ignored them going forward.
- `CONTRIBUTING.md` and `docs/SHOWCASE.md` now use the ENCODE Toolkit name and the current skill
  count (47).

## [0.3.1] - 2026-09-20

### Fixed

- **Server failed to start on fresh installs.** The `mcp` dependency had no upper bound, so new
  environments resolved `mcp` 2.x, which removed `mcp.server.fastmcp`. Startup then crashed with
  `ModuleNotFoundError: No module named 'mcp.server.fastmcp'`. The dependency is now capped at
  `mcp[cli]>=1.0,<2`. Existing installs that already had `mcp` 1.x were not affected.

  If you hit this error, uv may have cached the broken environment. Refresh it once with
  `uvx --refresh encode-toolkit` (or `uv cache clean encode-toolkit`); pip users can run
  `pip install --upgrade encode-toolkit`.

### Security

- The ChIP-seq, ATAC-seq, and RNA-seq pipeline Dockerfiles now download the UCSC
  `bedGraphToBigWig` executable over HTTPS instead of plain HTTP.

### Changed

- The source distribution now contains only the Python package, tests, and project documents.
  It previously bundled the whole repository, including editor configuration and a duplicate
  copy of the plugin tree (1.6 MB down to 118 KB). The wheel is unchanged.
- Updated dead GREAT links in the `peak-annotation` and `multi-omics-integration` skills.

### Added

- Packaging regression test that fails if the `mcp` dependency loses its upper bound.

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
- **568 tests** with 98% code coverage
- **34 literature reference documents** (~320 papers cataloged with DOI, PMID, key findings)
- **9 scientist-facing vignettes** with real ENCODE API output
- **GitHub Actions CI/CD** (pytest across Python 3.10–3.13, ruff lint, plugin validation)
