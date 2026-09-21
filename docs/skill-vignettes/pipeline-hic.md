# Hi-C Pipeline -- FASTQ to Contact Matrices and Loop Calls

> **Category:** Pipeline Execution | **Tools Used:** `encode_search_experiments`, `encode_search_files`, `encode_download_files`, `encode_track_experiment`, `encode_log_derived_file`

## What This Skill Does

Runs the ENCODE Hi-C pipeline end-to-end: BWA per-mate alignment, pairtools pair classification and deduplication, Juicer .hic matrix generation, cooler .mcool output, and HiCCUPS loop calling at multiple resolutions. Executes via Nextflow DSL2 with Docker, SLURM, GCP, and AWS profiles.

## Example Session

### Scientist's Request

> "I downloaded Hi-C FASTQs for human pancreas from ENCODE. Run the full pipeline with loop calling."

### Step 1: Locate and Download ENCODE Hi-C Data

```
encode_search_experiments(
    assay_title="Hi-C", organ="pancreas",
    organism="Homo sapiens", status="released", limit=25)
```

Identify the experiment (e.g., ENCSR123ABC), then download paired-end FASTQs:
```
encode_search_files(
    assay_title="Hi-C", organ="pancreas",
    file_format="fastq", assembly="GRCh38", limit=50)
encode_download_files(
    file_accessions=["ENCFF001XYZ", "ENCFF002XYZ"],
    download_dir="/data/hic_pancreas", organize_by="experiment")
encode_track_experiment(accession="ENCSR123ABC")
```

### Step 2: Run the Pipeline

Note the restriction enzyme from the experiment metadata: most ENCODE Hi-C uses MboI (GATC, 4-cutter, ~256 bp fragments), Arima kits use two enzymes (~160 bp), and HindIII (AAGCTT, 6-cutter) yields lower resolution. The workflow itself is enzyme-agnostic: it takes no restriction-site file and does not assign fragments, so the enzyme limits the resolution you can interpret rather than changing how pairs are classified. ENCODE FASTQs are named by accession, so link each pair to `<sample>_R1` / `<sample>_R2` names first.

```bash
nextflow run skills/pipeline-hic/scripts/main.nf \
    -profile local \
    --reads '/data/hic_pancreas/ENCSR123ABC/*_R{1,2}.fastq.gz' \
    --bwa_index '/ref/bwa_index/GRCh38.fa' \
    --chrom_sizes '/ref/hg38.chrom.sizes' \
    --resolutions '5000,10000,25000,50000,100000,250000,500000,1000000' \
    --min_mapq 30 \
    --assembly 'hg38' \
    --outdir /results/hic_pancreas/ \
    -resume
```

### Step 3: Evaluate QC -- Cis/Trans Ratio and Pair Classification

The contact statistics file (`qc/<sample>.contact_stats.txt`) reports the cis/trans ratio and pair type breakdown. ENCODE requires a cis/trans ratio above 1.5 (>60% cis contacts) for passing quality. Below that threshold, the library likely has excessive random ligation.

| Metric | Pass | Warning | Fail |
|--------|------|---------|------|
| Cis/trans ratio | >1.5 (~60%+ cis) | 1.0--1.5 | <1.0 |
| Valid pair fraction (UU) | >40% | 25--40% | <25% |
| Library complexity | >0.7 | 0.5--0.7 | <0.5 |
| WW (same-strand) fraction | <15% | 15--30% | >30% |

High WW fraction signals poor restriction digestion or excessive self-ligation. Check the pair-type breakdown in `pairs/<sample>.parse_stats.txt` and the duplication figures in `pairs/<sample>.dedup_stats.txt` before trusting the matrices.

### Step 4: Contact Matrices and Multi-Resolution Output

The pipeline produces two complementary matrix formats:

- **.hic** (Juicer) -- Multi-resolution contact matrix with KR, VC, and VC_SQRT normalization vectors. Visualize in Juicebox.
- **.mcool** (cooler) -- HDF5-based multi-resolution matrix with ICE balancing. Compatible with cooltools, HiGlass, and FAN-C.

Resolution depends on sequencing depth. Do not call features at resolutions unsupported by contact count:

| Resolution | Minimum Contacts |
|------------|-----------------|
| 5 kb | ~500 million |
| 10 kb | ~200 million |
| 25 kb | ~50 million |
| 100 kb | ~10 million |

### Step 5: Loop Calling with HiCCUPS

HiCCUPS (Rao et al. 2014) detects loops as enriched pixels relative to local background at multiple resolutions. The pipeline calls loops at 5 kb, 10 kb and 25 kb by default (`--hiccups_resolutions`; each must also be in `--resolutions`), in CPU mode unless `--hiccups_gpu` is set, and merges the results into a single BEDPE:

```
results/loops/sample1.hiccups_loops.bedpe
```

The file starts with a `#chr1 x1 x2 ...` header line; each following row is a loop anchor pair. Expect 5,000--15,000 loops from a deeply sequenced human sample at 10 kb resolution.

### Step 6: Log Provenance
```
encode_log_derived_file(
    file_path="/results/hic_pancreas/matrices/sample1.hic",
    source_accessions=["ENCSR123ABC", "ENCFF001XYZ", "ENCFF002XYZ"],
    description="Hi-C contact matrix from an MboI library, with KR, VC and VC_SQRT normalization vectors",
    file_type="hic",
    tool_used="BWA 0.7.18 + pairtools 1.1.2 + Juicer tools 2.20.00 + cooler 0.9.3",
    parameters="MAPQ>=30, resolutions 5kb-1Mb, KR/VC/VC_SQRT normalization")
```

## Key Pitfalls

- **Over-reading a 6-cutter library.** The enzyme sets the fragment size and therefore the finest resolution worth interpreting; a HindIII library does not support 5 kb loop calls. Check the enzyme in the experiment metadata.
- **Calling loops beyond depth.** HiCCUPS at 5 kb from 100M contacts produces noise. Drop 5000 from `--hiccups_resolutions` for shallow libraries; the workflow accepts 5000, 10000 and 25000 only.
- **Mixing normalization methods.** KR (Juicer default) and ICE (cooler default) yield different values. Pick one and document it.
- **Ignoring ligation artifacts.** WW fraction above 30% indicates failed digestion. Reprocessing will not fix a bad library.
- **Never mix assemblies.** Hi-C bin coordinates are resolution-dependent. LiftOver introduces anchor drift.

## Related Skills

- **hic-aggregation** -- Merge loop calls across donors into a union catalog.
- **pipeline-guide** -- Parent skill for compute resource assessment and cloud setup.
- **quality-assessment** -- Systematic evaluation of pipeline QC metrics.
- **regulatory-elements** -- Connect distal enhancers to promoters via loop anchors.
- **data-provenance** -- Audit trail for pipeline inputs, outputs, and parameters.

---

*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 47 skills for genomics research*
