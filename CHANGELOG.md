# Changelog

All notable changes to the ENCODE Toolkit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **`encode_track_experiment` failed for every experiment.** The tool passed the experiment's
  assemblies to the tracker as a list, which SQLite cannot store, so tracking stopped with
  `Error binding parameter 13: type 'list' is not supported`. The tests did not see it because
  they mocked the tracker. Assemblies are now stored as joined text, two experiments count as
  compatible when they share an assembly, and a test runs the tool against a real tracker.
- `encode_connector.__version__` was a hard-coded `0.2.1`; it now reports the installed version.
- **Four pipelines failed at their last step.** MultiQC names its report after `--title`, so
  CUT&RUN, DNase-seq, Hi-C and WGBS never produced the `multiqc_report.html` they declare. They
  now pass `--filename multiqc_report` (checked against MultiQC 1.21).
- **WGBS**: `MethylDackel extract` was given `--maxDepth`, which 0.6.1 does not accept, so
  extraction could not start. The `--nOT/--nOB` values excluded the 3' ends of reads rather than
  the end-repair bias they were documented to remove (Trim Galore's `--clip_R2 10` already does
  that), so they are gone. The M-bias report captured stdout while MethylDackel prints its
  suggested bounds on stderr. The final sorted BAM was never published. `--min_coverage` now
  filters the bedMethyl files only, so the coverage statistics describe every covered CpG.
- **RNA-seq**: plus- and minus-strand signal tracks were swapped for reverse-stranded (dUTP)
  libraries, the default. Track naming now follows `--strandedness` the way ENCODE's
  `STAR_RSEM.sh` does, and unstranded libraries get a single track. `--strandedness` is
  validated. The kallisto index and the RSeQC gene model were hard-wired to file names in the
  launch directory; they are now `--kallisto_index` and `--rseqc_bed`.
- **DNase-seq**: insert sizes used Picard `CollectInsertSizeMetrics`, which needs R for its
  mandatory histogram and the image has none. It now uses `samtools stats`.
- **ChIP-seq**: `--chrom_sizes` is required up front instead of failing on a missing
  `chrom.sizes` file, the BWA index directory is a parameter (`--bwa_index`), and duplication
  metrics are published (the `publishDir` pattern never matched the file name).
- **ATAC-seq**: the Bowtie2 index directory is a parameter (`--bowtie2_index`), the
  mitochondrial statistics are published, and two parameters that nothing read are removed.
- **CUT&RUN** publishes the fragment BED and the spike-in counts. **Hi-C** publishes the
  pairtools parse statistics and passes the normalization to HiCCUPS explicitly.
- **Cloud profiles**: every pipeline takes `--gcp_project`/`--gcp_workdir` and
  `--aws_queue`/`--aws_workdir`, and stops with a clear message when `-profile gcp` or `aws` is
  used without them. All seven configs now come from one template, so resource limits, SLURM
  queue/account and report settings no longer differ between pipelines.
- `install-nextflow.sh` accepted any Nextflow already on the PATH, which skipped both the pinned
  version and the checksum. It now accepts only the pinned release.
- Trimmed-read FastQC reports are kept and passed to MultiQC in every pipeline that trims.
- Conda environments: `idr` added to ATAC-seq, `picard` added to DNase-seq, BWA 0.7.18.

### Changed

- **One version of every tool.** The ChIP-seq, ATAC-seq and RNA-seq images move to the versions
  the other four images and all seven conda environments already pinned: samtools 1.19, Picard
  3.1.1 (Java 17), MultiQC 1.21, cutadapt 4.6, Trim Galore 0.6.10, FastQC 0.12.1, STAR 2.7.11b,
  kallisto 0.50.1, RSeQC 5.0.3. Bowtie2 is 2.5.4 in every image. A kallisto index has to be
  built with 0.50.1; older index files are rejected.
- **FRiP is computed** by the ChIP-seq, ATAC-seq and CUT&RUN workflows
  (`qc/<sample>.frip_mqc.tsv`, shown as a table in MultiQC).
- **IDR compares every pair of replicates** instead of only the first two. Outputs are named
  `peaks/idr/<sampleA>_vs_<sampleB>.idr_peaks.txt`.
- **Hi-C honours `--resolutions`**: the cooler base bin is the smallest requested resolution,
  and the new `--hiccups_resolutions` selects the loop-calling resolutions. Both lists are
  validated before anything runs.
- ATAC-seq publishes `samtools idxstats` (which MultiQC reads) in place of a text line that
  needed `bc` and failed on genomes without the mitochondrial contig.
- WGBS coverage statistics also report the run's `--min_coverage`; deduplication reports reach
  MultiQC. RNA-seq publishes the unique-mapper signal bedGraphs and kallisto's HDF5 output.
- In WGBS, Hi-C, DNase-seq and CUT&RUN every process asks for more memory on a retry.

### Documentation

- Every pipeline skill was reconciled with its workflow: parameters, example commands, output
  layouts, step lists and QC tables now describe what the workflow does. Analyses it does not
  run (for example FRiP, NSC/RSC, TSS enrichment, TAD and compartment calling, bisulfite
  conversion rate) are labelled as manual steps instead of being listed as outputs.
- `encode_*` tool calls in 40 skills used 135 parameter names the server does not have (for
  example `encode_list_files(accession=...)` instead of `experiment_accession=`). All are
  corrected.
- Reference commands were checked against the pinned tool versions (Hotspot2, MethylDackel,
  SEACR, Juicer tools, pairtools, RGT, MPRAflow) and corrected.

### CI

- The seven `nextflow.config` files are generated by `.github/scripts/gen-pipeline-configs.py`, and CI fails
  when a config differs from what the generator writes.
- `check-tool-versions.py` fails the build when a pipeline image and its conda environment pin
  different versions of the same tool.
- `check-skill-docs.py` fails the build when a skill shows a tool call the server would reject
  or a `nextflow run` example with a parameter or profile the pipeline does not declare.
- Image smoke tests start FastQC and Trim Galore; the preview suite covers the new parameters
  and the cloud-profile checks.

## [0.3.3] - 2026-09-20

Pipeline skills release. The Python package (MCP server) is functionally identical to 0.3.2.

### Fixed

- **All seven Nextflow pipelines now run on current Nextflow (validated on 26.04.6).** The
  workflows mixed top-level statements with process definitions and four configs defined a
  function, both of which the strict parser rejects. Validation and channel setup moved into the
  `workflow` block, and `check_max` was replaced by `process.resourceLimits`.
- **ChIP-seq**: the workflow called each process twice (samples, then controls), which Nextflow
  does not allow, so it could not start. Controls now go through the same calls and are split
  off before peak calling, where they are pooled. `--control` is optional. Signal tracks now
  receive the sample ID they were missing.
- **CUT&RUN**: SEACR was given the control BAM instead of a control bedGraph; spike-in scale
  factors were computed but never applied to the signal track; `--seacr_mode` was ignored;
  MACS2 peak calling always failed on a no-op `mv`; fragments were extracted from a
  coordinate-sorted BAM, which drops most read pairs; `--control` and chromosome sizes were
  not staged into tasks.
- **DNase-seq**: Hotspot2 was called with options it does not have and without its mandatory
  center-sites file; the image pinned a Hotspot2 tag that does not exist and lacked `modwt`
  and `bc`. Footprinting could pair a BAM with another sample's peaks. `--hotspot_index` is
  replaced by `--hotspot_center_sites` and `--hotspot_mappable`.
  HINT footprinting needs an RGT data directory that the container's unprivileged user could
  never find; it is now an explicit input, `--rgt_data`, checked before the run starts.
- **WGBS**: the bedMethyl conversion divided by zero on MethylDackel's header line, so
  extraction always failed; only CpG was converted although CHG and CHH were promised;
  `--no_overlap` toggled `--mergeContext`, which is unrelated to mate overlap (renamed
  `--merge_context`). bedMethyl score and strand now follow the ENCODE format.
- **RNA-seq**: the RSEM reference is a file prefix but was required to be a directory.
- **ATAC-seq**: the BAM index was not passed to the Tn5 shift step, which `alignmentSieve`
  requires; the mitochondrial fraction used `bc`, which the image lacked, and silently wrote an
  empty value; duplication metrics were never published. The workflow now states that it needs
  paired-end reads instead of filtering every single-end read away.
- **Hi-C**: `pairtools sort` was given a temporary directory that was never created. HiCCUPS
  now runs its CPU mode by default, because the image has no CUDA runtime (`--hiccups_gpu`).
- **IDR** (ChIP-seq, ATAC-seq) picked two peak files in arbitrary order and crashed with a
  single replicate. The pair is now sorted, and IDR is skipped below two replicates.
- **Pipeline images had never been built.** Beyond missing `build-essential`, `unzip`, `bc`, and
  Boost: `idr`, `trim-galore`, and `phantompeakqualtools` are not PyPI packages; `deeptools
  3.5.4` was never published; BWA 0.7.17 does not link with current GCC (now 0.7.18); Picard 3
  needs Java 17; MethylDackel needs libBigWig; SEACR could not find its R script through a
  symlink; RGT 0.13.2 and pairtools 1.0.3 no longer install (now 1.0.2 and 1.1.2). Index
  prefixes are resolved from staged files, so cloud executors work.
- **Conda environment files** pinned packages that do not exist (`hotspot2`, `hint`, `f-seq2`)
  or cannot be installed together. All seven now solve, and the Anaconda `defaults` channel is
  no longer used.
- Pipelines referenced container images that do not exist. Each config now uses an image built
  from the skill's own Dockerfile, with a fixed tag and a `--container` override.
- `gcp` profiles used the retired `google-lifesciences` executor; they now use `google-batch`.
- QC references: `samtools view` needs `-L` for a BED file; the WGBS coverage one-liner never
  counted bases at 5x or more.

### Changed

- **Removed parameters that had no effect**: `--aligner` and `--lambda_genome` (WGBS),
  `--motif_db` (DNase-seq), `--restriction_site` (Hi-C), `--gtf` (RNA-seq). The skills now
  describe what the workflows actually do.
- `install-nextflow.sh` installs a pinned Nextflow release and verifies its SHA-256 before use,
  instead of piping a remote script into a shell. It no longer fails when the install
  directory is not on the `PATH`.
- `install-python-packages.sh` installs against `constraints.txt`, a lock file with exact
  versions for Python 3.10+, generated from `requirements.in`.
- The pipeline guide now separates the official ENCODE WDL pipelines from this toolkit's own
  Nextflow implementations, and no longer cites repositories or images that do not exist.
  Pipeline images are no longer labelled as maintained by the ENCODE DCC.

### Added

- `Pipelines` CI workflow: `nextflow lint`, `nextflow run -preview` across parameter
  combinations, profile resolution, a Docker build of every pipeline image with checks that
  the tools each workflow calls are present and actually start, a dry-run solve of every conda
  environment, shellcheck, and a `skills/` vs `plugin/skills/` identity check.

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
