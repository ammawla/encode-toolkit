# ENCODE Toolkit — Genomics Research Infrastructure for Claude

<!-- mcp-name: io.github.ammawla/encode-toolkit -->

[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC_BY--NC_4.0-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-0.3.0--beta.10-yellow)](CHANGELOG.md)
[![Status](https://img.shields.io/badge/status-beta-yellow)]()
[![Skills](https://img.shields.io/badge/skills-47-orange)](docs/skill-vignettes/)
[![Tools](https://img.shields.io/badge/MCP_tools-20-purple)](src/encode_connector/server/main.py)
[![Pipelines](https://img.shields.io/badge/pipelines-7-green)](skills/pipeline-chipseq/)
[![Databases](https://img.shields.io/badge/databases-14-teal)](docs/SHOWCASE.md)
[![Tests](https://img.shields.io/badge/tests-506_passing-brightgreen)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-98%25-brightgreen)](tests/)
[![Security](https://img.shields.io/badge/security-no_telemetry-blue)]()
[![Claude Code](https://img.shields.io/badge/Claude_Code-plugin-blueviolet)](https://claude.com/claude-code)
[![Provenance](https://img.shields.io/badge/provenance-full_audit_trail-green)]()
[![smithery badge](https://smithery.ai/badge/encode-toolkit)](https://smithery.ai/server/encode-toolkit)
[![PyPI version](https://img.shields.io/pypi/v/encode-toolkit.svg?include_prereleases)](https://pypi.org/project/encode-toolkit/)
[![PyPI Downloads](https://img.shields.io/pypi/dw/encode-toolkit?style=flat&label=PyPI%20Downloads)](https://pypi.org/project/encode-toolkit/)
[![npm version](https://img.shields.io/npm/v/encode-toolkit.svg)](https://www.npmjs.com/package/encode-toolkit)
[![NPM Downloads](https://img.shields.io/npm/dw/encode-toolkit?style=flat&label=NPM%20Downloads)](https://www.npmjs.com/package/encode-toolkit)
[![GitHub Clones](https://img.shields.io/badge/dynamic/json?color=success&label=Clones&query=count&url=https://gist.githubusercontent.com/ammawla/8fdeb4cd92776739d329df9afd942b2e/raw/clone.json&logo=github)](https://github.com/ammawla/encode-toolkit)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18917519.svg)](https://doi.org/10.5281/zenodo.18917511)

<a href="https://glama.ai/mcp/servers/ammawla/encode-toolkit">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/ammawla/encode-toolkit/badge" />
</a>

Search ENCODE, cross-reference 14 databases, run 7 analysis pipelines, and generate publication-ready methods — all from natural language in Claude Code.

> Start from ENCODE but go everywhere: discover histone peaks, cross-reference with GWAS variants, check ClinVar pathogenicity, pull GTEx expression, analyze TF binding motifs from JASPAR, run pipelines, and generate publication-ready methods with full provenance — in one conversation.

---

## Citation Notes

If you use **ENCODE-Toolkit**, please cite:

Alex M. Mawla. (2026). *ENCODE-Toolkit: an MCP server, Claude plugin, and skills suite for ENCODE genomic data access and analysis*. Zenodo. https://doi.org/10.5281/zenodo.18917511

### BibTeX

```bibtex
@software{mawla_2026_encode_toolkit,
  author  = {Mawla, Alex M.},
  title   = {ENCODE-Toolkit: an MCP server, Claude plugin, and skills suite for ENCODE genomic data access and analysis},
  year    = {2026},
  publisher = {Zenodo},
  doi     = {10.5281/zenodo.18917511},
  url     = {https://doi.org/10.5281/zenodo.18917511}
}
```

---

## Quick Start

### Claude Code Plugin (recommended)

Start a new Claude Code session and enter:

```
/plugin marketplace add ammawla/encode-toolkit

/plugin install encode-toolkit
```

That's it. All 20 tools, 47 skills, and the MCP connector are now available.

<details>
<summary><strong>MCP-only install (tools only, no skills)</strong></summary>

If you only need the 20 MCP tools without the 47 workflow skills:

```bash
claude mcp add encode -- uvx encode-toolkit
```

</details>

<details>
<summary><strong>Other editors and platforms</strong></summary>

#### npx (Node.js)

```bash
npx encode-toolkit
```

Or in MCP client config: `{ "command": "npx", "args": ["encode-toolkit"] }`

#### pip install

```bash
pip install encode-toolkit
```

Then use `encode-toolkit` as the command in any MCP client configuration:

```json
{
  "mcpServers": {
    "encode": {
      "command": "encode-toolkit"
    }
  }
}
```

</details>

<details>
<summary><strong>Claude Desktop (MCP only)</strong></summary>

Add to your `claude_desktop_config.json`:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "encode": {
      "command": "uvx",
      "args": ["encode-toolkit"]
    }
  }
}
```

> No installation needed when using `uvx`. Just add the config and restart Claude.

</details>

<details>
<summary><strong>VS Code / Copilot</strong></summary>

Add to `.vscode/mcp.json` in your workspace:

```json
{
  "mcp": {
    "servers": {
      "encode": {
        "command": "uvx",
        "args": ["encode-toolkit"]
      }
    }
  }
}
```

</details>

<details>
<summary><strong>Cursor</strong></summary>

Add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "encode": {
      "command": "uvx",
      "args": ["encode-toolkit"]
    }
  }
}
```

</details>

<details>
<summary><strong>Windsurf</strong></summary>

Add to `.windsurf/mcp.json`:

```json
{
  "mcpServers": {
    "encode": {
      "command": "uvx",
      "args": ["encode-toolkit"]
    }
  }
}
```

</details>

---

## Connected Databases

ENCODE Toolkit integrates 14 databases through live API tools and guided skills.

| Database | Access Method | Use Case |
|----------|---------------|----------|
| **ENCODE** | 20 MCP tools (live API) | ChIP-seq, ATAC-seq, RNA-seq, Hi-C, WGBS, CUT&RUN data |
| **GTEx** | REST API (skill) | Tissue-specific gene expression across 54 tissues |
| **ClinVar** | E-utilities (skill) | Variant clinical significance and pathogenicity |
| **GWAS Catalog** | REST API (skill) | Trait-variant associations from genome-wide studies |
| **JASPAR** | REST API (skill) | Transcription factor binding motif profiles |
| **CellxGene** | Census API (skill) | Single-cell expression atlas across tissues |
| **gnomAD** | GraphQL (skill) | Population allele frequencies and gene constraint |
| **Ensembl** | REST API (skill) | VEP annotation, Regulatory Build, coordinate liftover |
| **UCSC Genome Browser** | REST API (skill) | cCRE tracks, TF clusters, sequence retrieval |
| **GEO** | E-utilities (skill) | Complementary expression/epigenomic datasets |
| **PubMed** | MCP server | Literature search and citation |
| **bioRxiv** | MCP server | Preprint discovery |
| **ClinicalTrials.gov** | MCP server | Clinical trial cross-reference |
| **Open Targets** | MCP server | Drug target identification |

---

## What You Can Ask Claude

### Search and explore

- *"Find all histone ChIP-seq experiments for human pancreas tissue"*
- *"What ATAC-seq data is available for mouse brain?"*
- *"Search for RNA-seq on GM12878 cell line"*
- *"What histone marks have ChIP-seq data for pancreas?"*

### Download and track

- *"Download all BED files from ENCSR133RZO to ~/data/encode"*
- *"Track experiment ENCSR133RZO with its publications"*
- *"Export citations for my tracked experiments as BibTeX"*

### Cross-reference databases

- *"What GWAS variants overlap islet enhancers?"*
- *"Check ClinVar pathogenicity for rs7903146"*
- *"Pull GTEx expression for TCF7L2 across tissues"*
- *"Find JASPAR motifs for HNF4A binding sites"*

### Run pipelines

- *"Set up a ChIP-seq pipeline for my H3K27ac experiments"*
- *"Run ATAC-seq analysis with ENCODE-standard QC thresholds"*

### Generate methods and provenance

- *"Log that I created filtered_peaks.bed from ENCSR133RZO using bedtools"*
- *"Generate a methods section for my analysis with citations"*

<details>
<summary><strong>More example prompts</strong></summary>

#### Experiment details
- *"Show me the full details for experiment ENCSR133RZO"*
- *"What files are available for ENCSR133RZO?"*
- *"List only the BED files from ENCSR133RZO"*

#### Bulk downloads
- *"Download all FASTQs from human pancreas ChIP-seq to /data/fastqs"*
- *"Get the IDR thresholded peaks from these experiments"*
- *"Download the bigWig signal tracks for H3K27me3 in GRCh38"*

#### Compatibility analysis
- *"Are experiments ENCSR133RZO and ENCSR000AKS compatible for combined analysis?"*
- *"Compare these two ChIP-seq experiments"*

#### Provenance chains
- *"Show me the provenance chain for my derived files"*
- *"What files have I derived from ENCSR133RZO?"*

</details>

---

## The Problem

Using genomics databases today means:

1. Navigate web portals, click through dozens of filters
2. Manually find the right experiments and files across multiple databases
3. Write custom scripts to batch download
4. Lose track of which files came from where

**With ENCODE Toolkit**, just tell Claude what you need:

> "Find all histone ChIP-seq data for human pancreas tissue"

Claude searches ENCODE, returns a structured table of 66 experiments with targets, replicates, and file counts. Downloads are organized by experiment with MD5 verification and full provenance tracking.

---

## Available Tools (20)

Five core tools are shown below. The remaining 15 are collapsed for readability.

### `encode_search_experiments`

Search ENCODE experiments with 20+ filters.

| Parameter | Type | Description |
|-----------|------|-------------|
| `assay_title` | string | Assay type: "Histone ChIP-seq", "ATAC-seq", "RNA-seq", "Hi-C", etc. |
| `organism` | string | Species (default: "Homo sapiens") |
| `organ` | string | Organ: "pancreas", "brain", "liver", "heart", "kidney", etc. |
| `biosample_type` | string | "tissue", "cell line", "primary cell", "organoid" |
| `target` | string | ChIP target: "H3K27me3", "H3K4me3", "CTCF", etc. |
| `biosample_term_name` | string | Specific biosample: "GM12878", "HepG2", etc. |
| `limit` | int | Max results (default: 25) |

### `encode_get_experiment`

Get full details for a single experiment including all files, quality metrics, and audit info.

| Parameter | Type | Description |
|-----------|------|-------------|
| `accession` | string | Experiment ID (e.g., "ENCSR133RZO") |

### `encode_download_files`

Download specific files by accession to a local directory.

| Parameter | Type | Description |
|-----------|------|-------------|
| `file_accessions` | list[str] | File IDs to download (e.g., ["ENCFF635JIA"]) |
| `download_dir` | string | Local path to save files |
| `organize_by` | string | "flat", "experiment", "format", "experiment_format" |
| `verify_md5` | bool | Verify file integrity (default: true) |

### `encode_batch_download`

Search + download in one step. Runs in preview mode by default.

| Parameter | Type | Description |
|-----------|------|-------------|
| `download_dir` | string | Local path to save files |
| `file_format` | string | File format to download |
| `assay_title` | string | Assay type filter |
| `organ` | string | Organ filter |
| `dry_run` | bool | Preview only (default: true). Set false to download. |

### `encode_track_experiment`

Track an experiment locally with its publications, methods, and pipeline info.

| Parameter | Type | Description |
|-----------|------|-------------|
| `accession` | string | Experiment ID to track |
| `fetch_publications` | bool | Fetch associated publications (default: true) |
| `fetch_pipelines` | bool | Fetch pipeline/analysis info (default: true) |
| `notes` | string | Optional notes to attach |

<details>
<summary><strong>Search and discovery tools (4)</strong></summary>

### `encode_list_files`

List files for a specific experiment with format/type filters.

| Parameter | Type | Description |
|-----------|------|-------------|
| `experiment_accession` | string | Experiment ID |
| `file_format` | string | "fastq", "bam", "bed", "bigWig", "bigBed", etc. |
| `output_type` | string | "reads", "peaks", "signal", "alignments", etc. |
| `assembly` | string | "GRCh38", "mm10", etc. |
| `preferred_default` | bool | Only return recommended files |

### `encode_search_files`

Search files across all experiments with combined experiment + file filters.

| Parameter | Type | Description |
|-----------|------|-------------|
| `file_format` | string | File format filter |
| `assay_title` | string | Assay type of parent experiment |
| `organ` | string | Organ of parent experiment |
| `target` | string | ChIP/CUT&RUN target |
| `output_type` | string | Output type filter |
| `assembly` | string | Genome assembly |

### `encode_get_metadata`

List valid filter values for any parameter.

| Parameter | Type | Description |
|-----------|------|-------------|
| `metadata_type` | string | "assays", "organisms", "organs", "biosample_types", "file_formats", "output_types", "assemblies" |

### `encode_get_facets`

Get live counts from ENCODE showing what data exists for given filters.

| Parameter | Type | Description |
|-----------|------|-------------|
| `assay_title` | string | Pre-filter by assay |
| `organism` | string | Pre-filter by organism |
| `organ` | string | Pre-filter by organ |

</details>

<details>
<summary><strong>File and credential tools (2)</strong></summary>

### `encode_get_file_info`

Get detailed metadata for a single file.

| Parameter | Type | Description |
|-----------|------|-------------|
| `accession` | string | File ID (e.g., "ENCFF635JIA") |

### `encode_manage_credentials`

Store, check, or clear ENCODE credentials for restricted data access.

| Parameter | Type | Description |
|-----------|------|-------------|
| `action` | string | "store", "check", or "clear" |
| `access_key` | string | ENCODE access key (for "store") |
| `secret_key` | string | ENCODE secret key (for "store") |

</details>

<details>
<summary><strong>Tracking and provenance tools (4)</strong></summary>

### `encode_list_tracked`

List all experiments in your local tracker with metadata, publication counts, and derived file counts.

| Parameter | Type | Description |
|-----------|------|-------------|
| `assay_title` | string | Filter by assay type |
| `organism` | string | Filter by organism |
| `organ` | string | Filter by organ |

### `encode_get_citations`

Get publications for tracked experiments. Export as BibTeX or RIS for reference managers.

| Parameter | Type | Description |
|-----------|------|-------------|
| `accession` | string | Specific experiment (or all if omitted) |
| `export_format` | string | "json" (default), "bibtex", or "ris" |

### `encode_compare_experiments`

Analyze whether two experiments are compatible for combined analysis.

| Parameter | Type | Description |
|-----------|------|-------------|
| `accession1` | string | First experiment ID |
| `accession2` | string | Second experiment ID |

### `encode_summarize_collection`

Get grouped statistics of your tracked experiment collection.

| Parameter | Type | Description |
|-----------|------|-------------|
| `assay_title` | string | Filter by assay type |
| `organism` | string | Filter by organism |
| `organ` | string | Filter by organ |

</details>

<details>
<summary><strong>Provenance and export tools (4)</strong></summary>

### `encode_log_derived_file`

Log a file you created from ENCODE data for provenance tracking.

| Parameter | Type | Description |
|-----------|------|-------------|
| `file_path` | string | Path to your derived file |
| `source_accessions` | list[str] | ENCODE accessions this was derived from |
| `description` | string | What the file contains |
| `tool_used` | string | Tool/software used |
| `parameters` | string | Command or parameters used |

### `encode_get_provenance`

View provenance chains from derived files back to source ENCODE data.

| Parameter | Type | Description |
|-----------|------|-------------|
| `file_path` | string | Get provenance for a specific file |
| `source_accession` | string | List all files derived from an accession |

### `encode_export_data`

Export tracked experiments as a table (CSV, TSV, or JSON) for Excel, R, pandas.

| Parameter | Type | Description |
|-----------|------|-------------|
| `format` | string | "csv" (default), "tsv", or "json" |
| `assay_title` | string | Filter by assay type |

### `encode_link_reference`

Link external references (PubMed, bioRxiv, ClinicalTrials, GEO) to tracked experiments.

| Parameter | Type | Description |
|-----------|------|-------------|
| `experiment_accession` | string | ENCODE experiment accession |
| `reference_type` | string | "pmid", "doi", "nct_id", "preprint_doi", "geo_accession", "other" |
| `reference_id` | string | The identifier value |

### `encode_get_references`

Get external references linked to tracked experiments for cross-server workflows.

| Parameter | Type | Description |
|-----------|------|-------------|
| `experiment_accession` | string | Filter by experiment (optional) |
| `reference_type` | string | Filter by type (optional) |

</details>

---

## Authentication

**Most ENCODE data is public and requires no authentication.** Just install and use.

For restricted/unreleased data, ask Claude: *"Store my ENCODE credentials"*

Credentials are encrypted using your OS keyring (macOS Keychain, Linux Secret Service, Windows Credential Locker) and never stored in plaintext. Get your access keys from your [ENCODE profile](https://www.encodeproject.org/).

---

## Plugin Skills (47)

When installed as a Claude Code plugin, ENCODE Toolkit includes 47 literature-backed workflow skills that guide Claude through complex genomics tasks. Each analysis skill includes evidence-based quality thresholds, assay-specific metrics, and citations to primary literature.

### Core Skills

| Skill | Description |
|-------|-------------|
| `setup` | Install and configure the ENCODE Toolkit server |
| `search-encode` | Search and explore ENCODE experiments and files |
| `download-encode` | Download files with organization and verification |
| `track-experiments` | Track experiments, citations, and provenance locally |
| `cross-reference` | Connect ENCODE data to PubMed, bioRxiv, ClinicalTrials.gov |

<details>
<summary><strong>Analysis skills (9)</strong></summary>

| Skill | Description |
|-------|-------------|
| `quality-assessment` | Evaluate experiment quality using ENCODE metrics — assay-specific thresholds for ChIP-seq (FRiP, NSC, RSC, NRF, IDR), ATAC-seq (TSS enrichment, NFR ratio), RNA-seq (mapping rate, gene body coverage), WGBS (bisulfite conversion, CpG coverage), Hi-C (cis/trans ratio), and CUT&RUN/CUT&Tag. Backed by Landt 2012, Buenrostro 2013, ENCODE Phase 3 (2020), Li 2011 |
| `integrative-analysis` | Combine multiple experiments with batch effect awareness — integration strategies (peak overlap, signal correlation, DiffBind, DESeq2, ChromHMM, ABC model). Backed by Ernst & Kellis 2012, Ross-Innes 2012, Love 2014, Fulco 2019 |
| `regulatory-elements` | Discover enhancers, promoters, insulators from combinatorial histone marks — ENCODE cCRE classification (926,535 elements), ChromHMM state interpretation. Backed by ENCODE Phase 3 (2020), Roadmap Epigenomics (2015), Whyte 2013 |
| `epigenome-profiling` | Build comprehensive chromatin state profiles — three-tiered histone panels, ChromHMM 15-state model, bivalent chromatin analysis. References the chromatin biology catalog |
| `compare-biosamples` | Compare experiments across tissues and cell types — biosample hierarchy, tissue-specific regulation, batch effect detection. Backed by Roadmap Epigenomics (2015), Leek 2010 |
| `visualization-workflow` | Generate publication-quality visualizations: genome browser tracks, heatmaps, and signal profiles |
| `motif-analysis` | Discover and analyze TF binding motifs in regulatory regions using HOMER, MEME, and JASPAR |
| `peak-annotation` | Annotate genomic peaks with features (promoter/enhancer/intergenic), nearest genes, and functional categories |
| `batch-analysis` | Batch processing and QC screening across multiple ENCODE experiments with systematic quality filtering |

</details>

<details>
<summary><strong>Functional genomics skills (1)</strong></summary>

| Skill | Description |
|-------|-------------|
| `functional-screen-analysis` | Analyze CRISPR screens, MPRA, and STARR-seq data from ENCODE — MAGeCK, BAGEL2, MPRAflow integration |

</details>

<details>
<summary><strong>Data aggregation skills (4)</strong></summary>

| Skill | Description |
|-------|-------------|
| `histone-aggregation` | Union merge of histone ChIP-seq peaks across studies — signalValue-based noise filtering, sample-of-origin tagging, ENCODE blacklist removal. Backed by ChIP-Atlas (Oki 2018), Amemiya 2019, Perna 2024 |
| `accessibility-aggregation` | Union merge of ATAC-seq and DNase-seq peaks — cross-platform integration, peak summit preservation. Backed by Corces 2017, Amemiya 2019, Zhao 2020 |
| `hic-aggregation` | Union catalog of Hi-C chromatin loops (BEDPE) — resolution-aware anchor matching, loop caller concordance tracking. Backed by Loop Catalog (Reyna 2025), Mustache (Roayaei Ardakany 2020) |
| `methylation-aggregation` | Aggregate WGBS methylation profiles — per-CpG weighted averaging, HMR/UMR/PMD identification. Backed by Schultz 2015, DMRcate (Peters 2021), Zhou 2020 |

</details>

<details>
<summary><strong>Multi-omics and meta-analysis skills (2)</strong></summary>

| Skill | Description |
|-------|-------------|
| `scrna-meta-analysis` | Cross-study meta-analysis of scRNA-seq data — reproducibility assessment, TIN-based quality filtering, ambient RNA quantification. Backed by Tran 2020, Luecken & Theis 2019, Stuart 2019, Korsunsky 2019 |
| `multi-omics-integration` | Integrate RNA-seq, ATAC-seq, Histone ChIP-seq, and TF ChIP-seq — ABC model regulatory predictions, signal correlation. Backed by Fulco 2019, Corces 2018, ENCODE Phase 3 (2020) |

</details>

<details>
<summary><strong>Workflow skills (7)</strong></summary>

| Skill | Description |
|-------|-------------|
| `data-provenance` | Full reproducibility tracking — tool versions, reference files, scripts, exact commands, timestamps, source-to-derived provenance chains |
| `cite-encode` | Generate proper citations, BibTeX/RIS export, data availability statements |
| `variant-annotation` | Annotate GWAS/disease variants with ENCODE functional data — variant-to-gene mapping via cCREs. Backed by Finucane 2015, Maurano 2012 |
| `pipeline-guide` | Understand ENCODE uniform analysis pipelines and output types — pipeline specifications, Nextflow integration |
| `single-cell-encode` | Work with scRNA-seq and scATAC-seq data — platform comparison, cross-study integration, WNN multimodal analysis. Backed by Hao 2021, Stuart 2019 |
| `disease-research` | Disease-focused workflows — GWAS variant interpretation, disease-tissue mapping, heritability enrichment, drug target identification via Open Targets. Backed by Buniello 2019, Finucane 2015 |
| `publication-trust` | Publication integrity assessment — 5-level trust scoring, retraction/erratum detection, citation analysis. Integrates with PubMed, bioRxiv, and Consensus |
| `bioinformatics-installer` | Install all bioinformatics tools for ENCODE analyses — 7 conda environment YAMLs, 3 install scripts, 134+ tools across ChIP-seq, ATAC-seq, RNA-seq, WGBS, Hi-C, DNase-seq, CUT&RUN |
| `scientific-writing` | Generate publication-ready methods sections, figure legends, supplementary tables, and data availability statements with full tool citations |
| `liftover-coordinates` | Convert genomic coordinates between assembly versions (hg19/hg38, mm9/mm10) using UCSC liftOver, CrossMap, Ensembl REST API, and rtracklayer |

</details>

<details>
<summary><strong>External database skills (9)</strong></summary>

| Skill | Description |
|-------|-------------|
| `gtex-expression` | Query GTEx tissue expression data via REST API for gene expression context across 54 tissues |
| `clinvar-annotation` | Annotate variants with ClinVar clinical significance, pathogenicity, and review status |
| `cellxgene-context` | Query CellxGene single-cell atlas for cell type expression context across tissues |
| `gwas-catalog` | Search NHGRI-EBI GWAS Catalog for trait associations, risk alleles, and study metadata |
| `jaspar-motifs` | Query JASPAR database for transcription factor binding motifs and matrix profiles |
| `ensembl-annotation` | Ensembl VEP variant annotation, Regulatory Build, coordinate liftover, gene lookup via REST API |
| `geo-connector` | Search NCBI GEO for complementary datasets, cross-reference with ENCODE, FTP downloads |
| `gnomad-variants` | gnomAD population allele frequencies, gene constraint (LOEUF/pLI), structural variants via GraphQL |
| `ucsc-browser` | UCSC Genome Browser REST API for cCRE tracks, TF binding clusters, and sequence retrieval |

</details>

<details>
<summary><strong>Pipeline execution skills (7)</strong></summary>

| Pipeline | Assay | Aligner | Caller |
|----------|-------|---------|--------|
| `pipeline-chipseq` | ChIP-seq | BWA-MEM | MACS2 + IDR |
| `pipeline-atacseq` | ATAC-seq | Bowtie2 | MACS2 (Tn5-adjusted) |
| `pipeline-rnaseq` | RNA-seq | STAR | RSEM + Kallisto |
| `pipeline-wgbs` | WGBS | Bismark | MethylDackel |
| `pipeline-hic` | Hi-C | BWA | Juicer + HiCCUPS |
| `pipeline-dnaseseq` | DNase-seq | BWA | Hotspot2 |
| `pipeline-cutandrun` | CUT&RUN | Bowtie2 | SEACR |

Each pipeline includes a SKILL.md overview, 5-stage reference files (preprocessing through QC), a complete Nextflow DSL2 pipeline, a Dockerfile, and deployment configurations for local, SLURM, GCP, and AWS.

</details>

<details>
<summary><strong>Reference files</strong></summary>

| File | Description |
|-------|-------------|
| `skills/histone-aggregation/references/histone-marks-reference.md` | Comprehensive chromatin biology catalog (1,442 lines) — 21 histone marks with writers/erasers/readers, 5 novel acylation marks, ChromHMM state models (5 to 51 states), TF co-binding patterns, chromatin remodeling complexes, DNA methylation-chromatin interplay, nucleosome dynamics, 3D genome organization, chromatin in disease. 74 primary references |
| `skills/*/references/literature.md` | 33 per-skill literature reference documents — ~250 papers cataloged with DOI, PMID, citation counts, and skill-relevant key findings |

</details>

---

## Why ENCODE Toolkit

Most genomics tools give you one thing. ENCODE Toolkit gives you the full research loop:

| Capability | ENCODE Toolkit | Typical MCP servers |
|------------|-----------|-------------------|
| Live database access | 20 tools across 14 databases | Single database, read-only |
| Executable pipelines | 7 Nextflow DSL2 pipelines with Docker and cloud configs | None |
| Provenance tracking | Full audit trail from source data to derived files | None |
| Publication output | BibTeX/RIS citations, auto-generated methods sections | None |
| Literature backing | 100+ primary references with assay-specific QC thresholds | None |
| Workflow skills | 47 guided skills covering search to publication | Static documentation |

---

## Supported Assay Types

<details>
<summary><strong>50+ assay types across 7 categories</strong></summary>

| Category | Assays |
|----------|--------|
| **Histone/Chromatin** | Histone ChIP-seq, TF ChIP-seq, ATAC-seq, DNase-seq, CUT&RUN, CUT&Tag, MNase-seq |
| **Transcription** | RNA-seq, total RNA-seq, small RNA-seq, long read RNA-seq, CAGE, RAMPAGE, PRO-seq, GRO-seq |
| **3D Genome** | Hi-C, intact Hi-C, Micro-C, ChIA-PET, HiChIP, PLAC-seq, 5C |
| **DNA Methylation** | WGBS, RRBS, MeDIP-seq, MRE-seq |
| **Functional** | STARR-seq, MPRA, CRISPR screen, eCLIP, iCLIP |
| **Single Cell** | scRNA-seq, snATAC-seq, 10x multiome, SHARE-seq, Parse SPLiT-seq |
| **Perturbation** | CRISPRi + RNA-seq, shRNA + RNA-seq, siRNA + RNA-seq |

**Supported file formats**: `fastq` `bam` `bed` `bigWig` `bigBed` `tsv` `csv` `hic` `tagAlign` `bedpe` `pairs` `fasta` `vcf` `tar`

</details>

---

## Security and Privacy

- **100% local execution** — no telemetry, no analytics, no tracking
- **Credentials encrypted at rest** via OS keyring with Fernet fallback
- **Certificate verification enforced** — no `verify=False`
- **Rate limited** to respect ENCODE's 10 req/sec policy
- **MD5 verification** on all downloads by default
- **No data leaves your machine** except queries to public APIs over HTTPS

---

## Vignettes

Step-by-step walkthroughs showing real Claude sessions, including actual API output and scientific interpretation.

| Vignette | Skills Demonstrated |
|----------|-------------------|
| [01 — Discovery & Search](docs/vignettes/01-discovery-and-search.md) | Facets, search, metadata, quality-aware selection |
| [02 — Download & Track](docs/vignettes/02-download-and-track.md) | File listing, download, tracking, citations, provenance |
| [03 — Epigenomics Workflow](docs/vignettes/03-epigenomics-workflow.md) | Histone marks, ATAC-seq, aggregation skills |
| [04 — Variant & Disease Research](docs/vignettes/04-variant-and-disease.md) | GWAS catalog, ClinVar, GTEx, JASPAR, gnomAD |
| [05 — Expression & Single-Cell](docs/vignettes/05-expression-and-single-cell.md) | RNA-seq, scRNA-seq, GTEx, CellxGene, meta-analysis |
| [06 — Motif & Regulatory Analysis](docs/vignettes/06-motif-and-regulatory.md) | TF ChIP-seq, chromatin states, HOMER/MEME |
| [07 — 3D Genome & Methylation](docs/vignettes/07-3d-genome-and-methylation.md) | Hi-C loops, WGBS methylation, integrative analysis |
| [08 — Pipeline Execution](docs/vignettes/08-pipeline-execution.md) | ChIP-seq/ATAC-seq/RNA-seq pipelines, Nextflow |
| [09 — Cross-Reference & Integration](docs/vignettes/09-cross-reference-and-integration.md) | GEO, PubMed, Ensembl, UCSC, multi-omics |

<details>
<summary><strong>Individual skill vignettes</strong></summary>

Every skill has a dedicated vignette in [`docs/skill-vignettes/`](docs/skill-vignettes/) with a complete example session. Highlights:

| Skill | Vignette Scenario |
|-------|------------------|
| [data-provenance](docs/skill-vignettes/data-provenance.md) | Download, blacklist-filter, liftover, auto-generate methods section |
| [histone-aggregation](docs/skill-vignettes/histone-aggregation.md) | Union merge of H3K27ac across 5 pancreas experiments |
| [variant-annotation](docs/skill-vignettes/variant-annotation.md) | rs7903146 in TCF7L2 with islet enhancer evidence scoring |
| [pipeline-chipseq](docs/skill-vignettes/pipeline-chipseq.md) | Full Nextflow pipeline execution with ENCODE QC thresholds |
| [gwas-catalog](docs/skill-vignettes/gwas-catalog.md) | T2D GWAS variants overlaid on islet H3K27ac enhancers |
| [publication-trust](docs/skill-vignettes/publication-trust.md) | Trust assessment of artemisinin transdifferentiation claim |
| [scrna-meta-analysis](docs/skill-vignettes/scrna-meta-analysis.md) | 3-study islet integration following Mawla et al. 2019 framework |

See the [full showcase](docs/SHOWCASE.md) for 15 detailed examples.

</details>

---

## Development

```bash
git clone https://github.com/ammawla/encode-toolkit.git
cd encode-toolkit
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Run the server locally:

```bash
encode-toolkit
```

Run tests:

```bash
pytest
```

---

## Troubleshooting

<details>
<summary><strong>"Server not found" in Claude Desktop</strong></summary>

- Make sure you restarted Claude Desktop after adding the config
- Verify `uvx` is installed: `pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`

</details>

<details>
<summary><strong>"Connection refused" or timeout errors</strong></summary>

- Check your internet connection
- ENCODE API rate limit is 10 requests/sec — the server handles this automatically

</details>

<details>
<summary><strong>Downloads fail with 403</strong></summary>

- The file may require authentication. Ask Claude: *"Store my ENCODE credentials"*
- Or check if the file status is "released" on encodeproject.org

</details>

<details>
<summary><strong>No results for a search</strong></summary>

- Try broader filters (remove biosample_type or organ)
- Use `encode_get_facets` to see what data actually exists for your filters
- Use `encode_get_metadata` to check valid filter values

</details>

---

## Author

**Dr. Alex M. Mawla, PhD**

## License

**Restrictive Non-Commercial License.** Free for personal, educational, and academic research. No derivative works without written permission. Commercial use requires a separate license. See [LICENSE](LICENSE) for full terms.

For commercial licensing inquiries: ammawla@ucdavis.edu
