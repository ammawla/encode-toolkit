# Running ENCODE-Standard Pipelines

> This vignette demonstrates how the ENCODE MCP plugin guides you through setting up
> and running the toolkit's Nextflow pipelines for processing raw sequencing data.

**Prerequisites:** You have downloaded raw FASTQ files from ENCODE, and Nextflow plus Docker
(or Singularity on a cluster) installed. See [Download & Track](02-download-and-track.md) if needed.

**Skills demonstrated:** `pipeline-guide`, `pipeline-chipseq`, `pipeline-atacseq`,
`pipeline-rnaseq`, `quality-assessment`

---

## Scenario

You have raw FASTQ files from three ENCODE assays -- ChIP-seq, ATAC-seq, and RNA-seq --
on human pancreas tissue. You need to process them through ENCODE-standard pipelines to
generate peak calls, signal tracks, and QC metrics comparable to ENCODE portal outputs.

---

## Step 1: Choose the Right Pipeline

**You ask Claude:** "I have ChIP-seq FASTQs from ENCODE. What pipeline should I use?"

**Claude uses the pipeline-guide skill** to separate two things that share the name
"ENCODE pipeline":

- The **official ENCODE uniform pipelines** are WDL workflows, run with Caper/Cromwell.
  They are not Nextflow projects, so `nextflow run ENCODE-DCC/<repo>` cannot work.
- The **toolkit's `pipeline-*` skills** are independent Nextflow DSL2 implementations written
  by the ENCODE Toolkit author, following the same standards. Each ships `scripts/main.nf`,
  `scripts/nextflow.config` and `scripts/Dockerfile`, and each builds its own image.

| Assay | Official ENCODE pipeline (WDL) | Toolkit skill (Nextflow) |
|-------|-------------------------------|--------------------------|
| ChIP-seq | [ENCODE-DCC/chip-seq-pipeline2](https://github.com/ENCODE-DCC/chip-seq-pipeline2) | `pipeline-chipseq` |
| ATAC-seq | [ENCODE-DCC/atac-seq-pipeline](https://github.com/ENCODE-DCC/atac-seq-pipeline) | `pipeline-atacseq` |
| RNA-seq | [ENCODE-DCC/rna-seq-pipeline](https://github.com/ENCODE-DCC/rna-seq-pipeline) | `pipeline-rnaseq` |
| WGBS | [ENCODE-DCC/dna-me-pipeline](https://github.com/ENCODE-DCC/dna-me-pipeline) | `pipeline-wgbs` |
| Hi-C | [ENCODE-DCC/hic-pipeline](https://github.com/ENCODE-DCC/hic-pipeline) | `pipeline-hic` |
| DNase-seq | [ENCODE-DCC/dnase-seq-pipeline](https://github.com/ENCODE-DCC/dnase-seq-pipeline) | `pipeline-dnaseseq` |
| CUT&RUN | none published by ENCODE | `pipeline-cutandrun` |

Every toolkit pipeline builds one image, `encode-toolkit/pipeline-<name>:1.0.0` (the
`params.container` default in its `nextflow.config`), and defines the same four profiles and no
others: `local` (Docker), `slurm` (Singularity), `gcp` (Google Batch), `aws` (AWS Batch).

---

## Step 2: ChIP-seq Pipeline Setup

**You ask Claude:** "Walk me through setting up the ChIP-seq pipeline for H3K27me3"

**Claude uses the pipeline-chipseq skill** to walk through the stages in its `main.nf`:

1. **Read QC** -- FastQC, then Trim Galore (`--quality 20 --length 36`)
2. **Alignment** -- BWA-MEM against `<bwa_index>/GRCh38.fa` into `samtools view -q 30`. The index
   is yours: the workflow neither builds nor downloads one.
3. **Filtering** -- `samtools view -F 1804 -q 30` (`-F 1028` single-end), Picard MarkDuplicates
   (`REMOVE_DUPLICATES=true`), `bedtools intersect -v` against ENCODE Blacklist v2
4. **Peak calling** -- MACS2 `--qvalue 0.05 --nomodel --keep-dup all -B`, plus `--call-summits`
   (`--peak_type narrow`) or `--broad --broad-cutoff 0.1` (`--peak_type broad`, correct for H3K27me3)
5. **Replicate analysis** -- IDR once per pair of samples, narrow runs only. No pooled or
   pseudoreplicate analysis; a broad run produces no `peaks/idr/`.
6. **Signal tracks** -- `macs2 bdgcmp` (FE, ppois) into `bedGraphToBigWig`: `signal/<sample>.fc.bw`, `.pval.bw`
7. **QC** -- FRiP per ChIP sample (`qc/<sample>.frip_mqc.tsv`) and MultiQC over FastQC, trimming,
   flagstat, duplication metrics and FRiP. NSC/RSC/NRF/PBC are not computed; see Step 6.

Build the image once, with the tag `params.container` expects (it pins BWA 0.7.18, samtools 1.19,
Picard 3.1.1, bedtools 2.31.0, MACS2 2.2.9.1, IDR 2.0.4.2):

```bash
docker build -t encode-toolkit/pipeline-chipseq:1.0.0 skills/pipeline-chipseq/scripts/
```

ENCODE accessions carry no mate suffix, so name the files for Nextflow's `fromFilePairs` first
(each file's page gives its `paired_end` number and the accession it is `paired_with`):

```bash
mkdir -p fastq
ln -s "$PWD/ENCFF001FQ1.fastq.gz" fastq/chip_rep1_R1.fastq.gz
ln -s "$PWD/ENCFF002FQ2.fastq.gz" fastq/chip_rep1_R2.fastq.gz
ln -s "$PWD/ENCFF003FQ1.fastq.gz" fastq/input_rep1_R1.fastq.gz
ln -s "$PWD/ENCFF004FQ2.fastq.gz" fastq/input_rep1_R2.fastq.gz
```

The last two are the control (input/IgG) library. Link it under its own prefix, or drop
`--control` below: a glob that matches nothing stops the run.

**Running the pipeline:**

```bash
nextflow run skills/pipeline-chipseq/scripts/main.nf \
  -profile local \
  --reads 'fastq/chip_*_R{1,2}.fastq.gz' \
  --control 'fastq/input_*_R{1,2}.fastq.gz' \
  --genome GRCh38 \
  --peak_type broad \
  --bwa_index GRCh38_index \
  --chrom_sizes GRCh38.chrom.sizes \
  --outdir results/h3k27me3 \
  -resume
```

`--reads` and `--chrom_sizes` are required; the run stops before the first task without them.
There is no input JSON and no `--target`: the ChIP target changes nothing but `--peak_type`.
Keep the `--reads` and `--control` globs on different prefixes, or the control library is
processed twice -- once as a control and once as a ChIP sample.

**Profiles** as defined in `scripts/nextflow.config` (abridged; identical in every pipeline skill):

```nextflow
profiles {
  local { process.executor = 'local';        docker.enabled = true }
  slurm { process.executor = 'slurm';        process.queue = params.slurm_queue; singularity.enabled = true }
  gcp   { process.executor = 'google-batch'; google.project = params.gcp_project; google.batch.spot = true; workDir = params.gcp_workdir }
  aws   { process.executor = 'awsbatch';     process.queue = params.aws_queue;   aws.region = params.aws_region; workDir = params.aws_workdir }
}
```

---

## Step 3: ATAC-seq Pipeline

**You ask Claude:** "I also have ATAC-seq data. How is that pipeline different?"

**Claude uses the pipeline-atacseq skill** to highlight key differences:

| Step | pipeline-chipseq | pipeline-atacseq |
|------|------------------|------------------|
| Aligner | BWA-MEM, `-q 30` | Bowtie2 `--very-sensitive -X 2000 --no-mixed --no-discordant` |
| Tn5 shift | not applied | `alignmentSieve --ATACshift`, after duplicate removal |
| Mitochondrial reads | kept | dropped by contig name (`--mito_name`, default `chrM`) |
| Peak input | blacklist-filtered BAM | nucleosome-free BAM (fragments below `--nfr_max`, default 150 bp) |
| MACS2 flags | `-f BAMPE` (`BAM` with `--single_end`) plus the peak-type flags | always `-f BAMPE` and `--call-summits` |
| Control | `--control` optional | none; MACS2 uses its local background model |
| Read layout | paired-end or `--single_end` | paired-end only (the run stops on `--single_end`) |

```bash
docker build -t encode-toolkit/pipeline-atacseq:1.0.0 skills/pipeline-atacseq/scripts/

nextflow run skills/pipeline-atacseq/scripts/main.nf \
  -profile local \
  --reads 'fastq/atac_*_R{1,2}.fastq.gz' \
  --genome GRCh38 \
  --bowtie2_index GRCh38_bowtie2_index \
  --outdir results/atac \
  -resume
```

The Tn5 offset (+4 bp / -5 bp) is applied by the workflow -- do not apply it beforehand.
`--shift -75 --extsize 150` is the single-end recipe and has no effect in `-f BAMPE` mode, where
MACS2 takes the fragment from the read pair, so this workflow does not use it. Give the glob at
least two replicates if you want IDR to run.

---

## Step 4: RNA-seq Pipeline

**You ask Claude:** "And for RNA-seq quantification?"

**Claude uses the pipeline-rnaseq skill** to describe the workflow (image: STAR 2.7.11b,
RSEM 1.3.3, kallisto 0.50.1, RSeQC 5.0.3):

- **Alignment:** STAR in 2-pass mode (`--twopassMode Basic`) against `--star_index`
- **Quantification:** RSEM on the transcriptome BAM, plus kallisto unless `--skip_kallisto`
- **Signal:** strand-specific bigWigs from STAR's bedGraphs (`_plus.bw` / `_minus.bw`, or a
  single `_unstranded.bw` with `--strandedness none`)
- **QC:** RSeQC `infer_experiment`, `read_distribution`, `geneBody_coverage`, then MultiQC

The annotation is not a workflow parameter and there is no `--gtf`: it is fixed when the STAR
and RSEM references are built, so it comes from the indexes you pass in.

```bash
docker build -t encode-toolkit/pipeline-rnaseq:1.0.0 skills/pipeline-rnaseq/scripts/

nextflow run skills/pipeline-rnaseq/scripts/main.nf \
  -profile local \
  --reads 'fastq/rna_*_R{1,2}.fastq.gz' \
  --genome GRCh38 \
  --star_index /ref/GRCh38_star_index \
  --rsem_index /ref/GRCh38_rsem_index/GRCh38 \
  --kallisto_index /ref/gencode.v38.kallisto.idx \
  --rseqc_bed /ref/hg38_RefSeq.bed \
  --strandedness reverse \
  --outdir results/rna \
  -resume
```

Check strandedness carefully: `--strandedness` takes one value for the whole run (`reverse` for
dUTP libraries, the ENCODE standard) and the workflow does not detect it. RSeQC's
`qc/rseqc/<sample>.infer_experiment.txt` is a post-hoc check; a wrong value has to be fixed by
rerunning, because counts, abundances and signal tracks all depend on it.

---

## Step 5: Running in the Cloud

**You ask Claude:** "How much will this cost to run on Google Cloud?"

The `gcp` profile submits to Google Batch with spot VMs enabled and stages every task through a
bucket, so the run needs a project, a `gs://` work directory, and an image pushed to a registry
Batch can pull:

```bash
nextflow run skills/pipeline-chipseq/scripts/main.nf \
  -profile gcp \
  --container us-docker.pkg.dev/<project>/<repo>/pipeline-chipseq:1.0.0 \
  --gcp_project <project> \
  --gcp_workdir gs://<bucket>/work \
  --reads 'gs://<bucket>/fastq/chip_*_R{1,2}.fastq.gz' \
  --genome GRCh38 \
  --peak_type broad \
  --bwa_index gs://<bucket>/reference/GRCh38_index \
  --chrom_sizes gs://<bucket>/reference/GRCh38.chrom.sizes \
  --outdir gs://<bucket>/results
```

The workflow stops with an error when `--gcp_project` or the `gs://` work directory is missing.
`-profile aws` has the same shape with `--aws_queue` and `--aws_workdir s3://<bucket>/work`.

**Rough estimates** from the pipeline skills -- planning figures, not measurements from timed runs:

| Assay | Instance | Time | Cost (spot) |
|-------|----------|------|-------------|
| ChIP-seq | n1-standard-8 | 2-4 hr | ~$2-5 |
| ATAC-seq | n1-standard-8 | 2-3 hr | ~$2-4 |
| RNA-seq | n1-highmem-8 | 2-4 hr | ~$3-6 |
| WGBS | n1-highmem-16 | 12-24 hr | ~$10-25 |
| Hi-C | n1-highmem-16 | 8-16 hr | ~$8-20 |

No figures exist for DNase-seq or CUT&RUN; size those from the resource tables in their skills.
FASTQ, BAM and intermediate files can exceed 100 GB per sample. An institutional SLURM cluster
avoids cloud cost entirely: convert the image once with
`singularity build pipeline-chipseq.sif docker-daemon://encode-toolkit/pipeline-chipseq:1.0.0`,
then run `-profile slurm --container /path/to/pipeline-chipseq.sif`.

---

## Step 6: QC Thresholds

**You ask Claude:** "What QC metrics should I check after the pipeline finishes?"

**Claude uses the quality-assessment skill** and separates what the run produced from what is
still a manual step:

| Assay | In the run output | Still manual |
|-------|-------------------|--------------|
| ChIP-seq | FRiP >= 0.01 (`qc/<sample>.frip_mqc.tsv`), mapping rate > 80% (`aligned/*.flagstat.txt`), duplication < 30% (`filtered/*.dup_metrics.txt`), IDR peak counts (narrow runs) | NSC > 1.05, RSC > 0.8 (phantompeakqualtools is not in the image), NRF >= 0.8, PBC1 >= 0.8, PBC2 >= 3 |
| ATAC-seq | FRiP >= 0.3, mitochondrial fraction < 20% (ideally < 5%, `qc/*.idxstats.txt`), mapping rate, duplication, IDR peaks > 50,000 | TSS enrichment >= 5 (GRCh38) / >= 10 (mm10) -- no TSS BED input, no `computeMatrix` step -- NRF/PBC, fragment-size distribution |
| RNA-seq | Uniquely mapped >= 70%, multi-mapped < 10% (`star/*.Log.final.out`), exonic rate > 60%, strandedness agreement (`qc/rseqc/`) | rRNA rate, detected-gene counts, saturation curves |

**ENCODE audit levels** describe portal metadata, not pipeline output:
ERROR > NOT_COMPLIANT > WARNING > INTERNAL_ACTION. Experiments flagged ERROR or NOT_COMPLIANT
should be used with caution or excluded.

---

## Other Pipeline Skills Available

- **pipeline-wgbs** -- Bismark, MethylDackel M-bias and bedMethyl extraction, coverage stats;
  needs `--genome_dir`. Bisulfite conversion rate is not computed.
- **pipeline-hic** -- BWA, pairtools, a Juicer `.hic`, a cooler `.mcool`, HiCCUPS loops; needs
  `--bwa_index` and `--chrom_sizes`. No TAD or compartment calling.
- **pipeline-dnaseseq** -- BWA, hotspot2 peaks with its SPOT score, signal track, optional
  `rgt-hint` footprinting; needs `--bwa_index`, `--chrom_sizes`, `--hotspot_center_sites`, `--blacklist`.
- **pipeline-cutandrun** -- Bowtie2 with optional spike-in scaling, SEACR and/or MACS2 peaks,
  FRiP; needs `--bowtie2_index`, `--chrom_sizes`, `--blacklist`.

Ask Claude about any of these by name for detailed setup instructions.

---

## Best Practices

- **Build the image with the tag the config expects.** `params.container` defaults to
  `encode-toolkit/pipeline-<name>:1.0.0`; override it with `--container` for a `.sif` file or a
  registry image.
- **Bring your own indexes.** No pipeline builds or downloads a genome index or a chrom.sizes file.
- **Never mix assemblies.** GRCh38 for human, mm10 for mouse, in every index, blacklist and
  chromosome-sizes file you pass (`--genome` accepts only those two where it exists).
- **Use `-resume`.** A failed run restarts from the last successful step instead of the beginning.
- **Check QC before downstream analysis**, and remember which metrics the workflow never computed.
- **Log every run.** Use the `encode_log_derived_file` tool to record the pipeline, parameters,
  and output paths for provenance.

---

## What's Next

- [Epigenomics Workflow](03-epigenomics-workflow.md) -- Integrate processed ChIP-seq,
  ATAC-seq, and RNA-seq into a regulatory landscape
- [3D Genome & Methylation](07-3d-genome-and-methylation.md) -- Where Hi-C and WGBS output goes next
