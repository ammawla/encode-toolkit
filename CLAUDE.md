# ENCODE Toolkit

MCP server for the ENCODE Project (encodeproject.org) — the largest public catalog of functional genomic elements. Version 0.3.0-beta.

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest                    # 568 tests, 98% coverage
ruff check src/           # lint
ruff format src/          # auto-format
encode-toolkit            # run MCP server
```

## Source Architecture

```
src/encode_connector/
  server/main.py          # MCP server — 20 tools, ~1500 lines (entry point)
  client/encode_client.py # Async ENCODE API client, ~585 lines, 1-hour TTL cache
  client/downloader.py    # File download manager, ~305 lines, MD5 verification
  client/auth.py          # OS keyring + Fernet credential storage, ~262 lines
  client/models.py        # Pydantic models for API responses, ~367 lines
  client/constants.py     # API URLs, filter values, ~450 lines
  client/tracker.py       # SQLite experiment tracker, ~1129 lines
  client/validation.py    # Input validation, ~226 lines
skills/                   # 47 skills, each with SKILL.md + references/ + scripts/
tests/                    # 568 tests (pytest-asyncio, asyncio_mode=auto), 98% coverage
```

## Package Identity

- **PyPI / console command**: `encode-toolkit`
- **npm**: `encode-toolkit` (thin wrapper → uvx encode-toolkit)
- **Plugin marketplace**: `encode-toolkit`
- **Python module**: `encode_connector`

## Development Gotchas

- Use `.venv/bin/python` on macOS (`python` may not exist)
- `asyncio_mode = "auto"` in pytest — no need for `@pytest.mark.asyncio`
- `main.py` is ~53KB — don't send full contents to subagents (causes timeouts)
- MCP SDK: use `instructions=` parameter, not `description=`
- Integration tests hit live ENCODE API — deselect with `-m "not integration"`
- `server.json` is for MCP registry; `.claude-plugin/plugin.json` is for Claude marketplace — keep both in sync
- `conftest.py` sets up shared fixtures (tmp_path, mock tracker) — read before adding tests
- npm `package.json` + `index.js` are thin wrappers that call `uvx encode-toolkit` — no JS logic

## What This Server Does

Provides 20 tools to search, download, and track ENCODE data:
- **Search**: Find experiments by assay, organ, biosample, target, organism
- **Download**: Get BED, FASTQ, BAM, bigWig files with MD5 verification
- **Track**: Local experiment tracking with publications, citations, provenance
- **Cross-reference**: Link to PubMed, bioRxiv, ClinicalTrials, GEO

## Key Concepts

**Assay types**: Histone ChIP-seq, TF ChIP-seq, ATAC-seq, DNase-seq, total RNA-seq, polyA plus RNA-seq, WGBS, intact Hi-C, scRNA-seq, snATAC-seq, snRNA-seq, CRISPR screen, STARR-seq, MPRA, eCLIP, CUT&RUN, CUT&Tag

**Biosample hierarchy**: tissue > primary cell > cell line > in vitro differentiated > organoid

**Tier 1 cell lines** (most data): K562, GM12878, H1-hESC

**File selection priority**: preferred_default=True > IDR thresholded peaks > fold change over control

**Assembly**: Use GRCh38 for human, mm10 for mouse. Never mix assemblies.

## Tool Selection Guide

| User wants to... | Use tool |
|---|---|
| Find experiments | `encode_search_experiments` |
| Explore what data exists (live counts) | `encode_get_facets` |
| Get valid filter strings (static list) | `encode_get_metadata` |
| Get experiment details | `encode_get_experiment` |
| Find specific file types | `encode_search_files` |
| List files for experiment | `encode_list_files` |
| Get file details | `encode_get_file_info` |
| Download specific files by accession | `encode_download_files` |
| Search + download in one step | `encode_batch_download` |
| Track experiments locally | `encode_track_experiment` |
| Compare experiments | `encode_compare_experiments` |
| Get citations | `encode_get_citations` |
| Log derived files | `encode_log_derived_file` |
| Link to PubMed/GEO | `encode_link_reference` |
| List tracked experiments | `encode_list_tracked` |
| Export tracking data | `encode_export_data` |
| View file provenance | `encode_get_provenance` |
| View linked references | `encode_get_references` |
| Get collection summary | `encode_summarize_collection` |
| Manage API credentials | `encode_manage_credentials` |

### Example Queries

**Search**: `encode_search_experiments(assay_title="Histone ChIP-seq", organ="pancreas", target="H3K27ac")` → finds all H3K27ac ChIP-seq in pancreas tissue

**Download**: `encode_download_files(file_accessions=["ENCFF123ABC"], download_dir="/data/encode")` → downloads with MD5 verification

**Track**: `encode_track_experiment(accession="ENCSR000ABC", notes="Liver H3K4me3 for enhancer analysis")` → saves to local SQLite with publications

**Explore**: `encode_get_facets(assay_title="Histone ChIP-seq", organ="pancreas")` → shows available targets, labs, biosample types

**Batch download**: `encode_batch_download(assay_title="ATAC-seq", organ="liver", file_format="bed", output_type="IDR thresholded peaks", dry_run=True)` → previews matching files before download

**Compare**: `encode_compare_experiments(accession1="ENCSR123ABC", accession2="ENCSR456DEF")` → checks compatibility for combined analysis

## 47 Skills Available

**Core**: setup, search-encode, download-encode, track-experiments, cross-reference

**Analysis**: quality-assessment, integrative-analysis, regulatory-elements, epigenome-profiling, compare-biosamples, visualization-workflow, motif-analysis, peak-annotation, batch-analysis

**Functional Genomics**: functional-screen-analysis

**Data Aggregation**: histone-aggregation, accessibility-aggregation, hic-aggregation, methylation-aggregation

**External Databases**: gtex-expression, clinvar-annotation, cellxgene-context, gwas-catalog, jaspar-motifs, ensembl-annotation, geo-connector, gnomad-variants, ucsc-browser

**Workflows**: data-provenance, cite-encode, variant-annotation, pipeline-guide, single-cell-encode, disease-research, publication-trust, bioinformatics-installer, scientific-writing, liftover-coordinates

**Pipeline Execution**: pipeline-chipseq, pipeline-atacseq, pipeline-rnaseq, pipeline-wgbs, pipeline-hic, pipeline-dnaseseq, pipeline-cutandrun

**Meta-Analysis**: scrna-meta-analysis, multi-omics-integration

## Reference Files

- `skills/histone-aggregation/references/histone-marks-reference.md` — Comprehensive chromatin biology catalog (1,442 lines, 74 references, 12 sections: histone marks, ChromHMM states, functional categories, contradictions, TF combinations, chromatin remodeling, DNA methylation interplay, nucleosome dynamics, 3D genome organization, chromatin in disease)
- `skills/*/references/literature.md` — 34 literature reference documents (33 per-skill + 1 chromatin biology catalog, ~320 papers with DOI, PMID, citation counts, key findings)

## Quality Awareness

- ENCODE audits: ERROR > NOT_COMPLIANT > WARNING > INTERNAL_ACTION
- ChIP-seq metrics: FRiP ≥1%, NSC >1.05, RSC >0.8, NRF ≥0.8 (Landt et al. 2012)
- ATAC-seq metrics: TSS enrichment ≥5 (GRCh38), ≥6 (hg19), ≥10 (mm10), fragment size nucleosomal ladder (ENCODE data standards)
- RNA-seq: Mapping rate 70-90% expected (Conesa et al. 2016), rRNA <10% (community standard), replicate correlation ≥0.9 isogenic / ≥0.8 anisogenic (ENCODE data standards)
- WGBS: Bisulfite conversion ≥98%, CpG coverage ≥10× for DMRs (ENCODE data standards)
- Hi-C: Cis/trans ratio >60%, long-range cis >40% (Yardimci et al. 2019)
- CUT&RUN/CUT&Tag: Different QC profiles from ChIP-seq; use suspect list (Nordin et al. 2023)
- Always use 2+ biological replicates
- Always apply ENCODE Blacklist v2 (Amemiya et al. 2019)
- No single metric is sufficient — interpret collectively

## Provenance Standard

Every operation should log: tool name + version, exact command, input accessions + MD5, reference files + source + MD5, output descriptions + counts, and statistics. Scripts stored with sequential numbering. Enables auto-generation of publication-ready methods sections.

## Cross-Database Integration

This plugin works with MCP servers:
- **PubMed** (search_articles) — Literature search and citation
- **bioRxiv** (search_preprints) — Preprint discovery
- **ClinicalTrials.gov** (search_trials) — Clinical trial cross-reference
- **Open Targets** (query_open_targets_graphql) — Drug target identification
- **Consensus** (search) — Academic paper search across 200M+ papers

And via skills (REST API/CLI):
- **UCSC Genome Browser** — cCRE tracks, TF binding, sequence retrieval via REST API
- **NCBI GEO** — Complementary expression/epigenomic datasets via E-utilities
- **gnomAD** — Population allele frequencies and gene constraint via GraphQL
- **Ensembl** — VEP variant annotation, Regulatory Build, coordinate liftover via REST API
- **NCBI SRA** — Raw sequencing reads linked from GEO (via E-utilities elink)
- **GTEx** — Tissue-specific gene expression for ENCODE regulatory element interpretation via REST API
- **ClinVar** — Clinical variant significance for ENCODE-identified regulatory variants via E-utilities
- **CELLxGENE** — Single-cell expression context for ENCODE bulk data via REST API
- **GWAS Catalog** — GWAS associations in ENCODE regulatory regions via REST API
- **JASPAR** — Transcription factor binding motifs for ENCODE ChIP-seq peak analysis via REST API
