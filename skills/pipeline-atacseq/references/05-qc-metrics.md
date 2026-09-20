# Stage 5: Signal Tracks and QC Report

Stage 5 of the workflow does two things: it builds one bigWig signal track per sample, and
it runs MultiQC over the logs collected in earlier stages. Everything else on this page is
a **manual step that the workflow does not run**.

## Signal Track Generation (workflow)

The workflow runs `bamCoverage` once per sample, on the blacklist-filtered BAM
(`filtered/<sample>.final.bam`, all fragments), and publishes
`signal/<sample>.signal.bw`:

```bash
bamCoverage -b final.bam -o sample.signal.bw \
  --normalizeUsing RPKM --binSize 10 \
  --numberOfProcessors 4 --extendReads
```

There is no NFR-only signal track. If you want one, run the same command manually against
`filtered/nfr/<sample>.nfr.bam`:

```bash
bamCoverage -b results/filtered/nfr/sample.nfr.bam -o sample_nfr_signal.bw \
  --normalizeUsing RPKM --binSize 10 \
  --numberOfProcessors 8 --extendReads
```

## MultiQC Aggregated Report (workflow)

```bash
multiqc . -o . -f
```

Published as `qc/multiqc/multiqc_report.html` with `qc/multiqc/multiqc_data/`. The workflow
feeds it exactly these inputs:

- FastQC reports for raw reads
- FastQC reports for trimmed reads (from `trim_galore --fastqc`)
- Trim Galore trimming reports
- The Bowtie2 alignment log
- `<sample>.mito_stats.txt` (a single `key=value` line that MultiQC has no module for;
  read the file directly)
- Picard MarkDuplicates metrics
- `samtools flagstat` from the blacklist-filtered BAM

MACS2 output is not passed to MultiQC.

## Comprehensive QC Metrics Table

| Metric | Tool | Threshold | Computed by the workflow? |
|--------|------|-----------|---------------------------|
| Total reads | FastQC, samtools flagstat | >=50M recommended | yes |
| Mapping rate | Bowtie2 log, samtools flagstat | >80% | yes |
| Mitochondrial fraction | `qc/<sample>.mito_stats.txt` | <20% | yes |
| Duplication rate | Picard | <30% | yes |
| IDR peaks | IDR | >50,000 | yes |
| TSS enrichment | deeptools + TSS BED | >=5 | no |
| FRiP | bedtools + samtools | >=0.3 | no |
| NFR fraction | fragment size distribution | >40% | no |
| NRF / PBC1 | pre-dedup BAM | >=0.8 | no |

## Manual step: TSS Enrichment Score

The most important ATAC-seq quality metric, and **not computed by this workflow**: there is
no TSS BED parameter and no `computeMatrix`/`plotProfile` step. deeptools 3.5.5 is in the
image, so this can be run against the published bigWig with a TSS BED you supply (for
example, a GENCODE TSS BED for your assembly):

```bash
computeMatrix reference-point -S results/signal/sample.signal.bw \
  -R tss.bed -a 2000 -b 2000 \
  --referencePoint TSS -o tss_matrix.gz

plotProfile -m tss_matrix.gz -o tss_enrichment.pdf \
  --perGroup --refPointLabel TSS

# TSS enrichment score = max(TSS signal) / mean(flanking signal)
```

| TSS Score | Quality | ENCODE Standard |
|-----------|---------|-----------------|
| >=7 | Excellent | Pass |
| 5-7 | Good | Pass (ENCODE minimum = 5 for GRCh38) |
| 3-5 | Marginal | Borderline |
| <3 | Poor | Fail |

## Manual step: Fragment Size Distribution

**Not computed or plotted by this workflow.** deeptools is in the image; Picard
`CollectInsertSizeMetrics` also needs R, which the image does not have, so prefer
`bamPEFragmentSize`:

```bash
bamPEFragmentSize -b results/filtered/sample.final.bam -o fragment_sizes.pdf \
  --maxFragmentLength 1000 --numberOfProcessors 4
```

Expected pattern: peaks at ~200 bp (NFR), ~400 bp (mono-nuc), ~600 bp (di-nuc).

## Manual step: FRiP Calculation

**Not computed by this workflow.** bedtools and samtools are both in the image:

```bash
READS_IN_PEAKS=$(bedtools intersect -a results/filtered/nfr/sample.nfr.bam \
  -b results/peaks/narrow/sample_peaks.narrowPeak -u -f 0.20 | samtools view -c -)
TOTAL_READS=$(samtools view -c results/filtered/nfr/sample.nfr.bam)
echo "FRiP: $(echo "scale=4; $READS_IN_PEAKS / $TOTAL_READS" | bc)"
```

ATAC-seq FRiP is expected to be >=0.3.

## Manual step: ataqv (ATAC-seq QC)

Comprehensive ATAC-seq-specific QC tool from Parker Lab (Orchard et al. 2020). **ataqv is
not in the pipeline image, not in `atacseq-env.yml`, and is never invoked by the
workflow.** Install it separately, for example with `conda install -c bioconda ataqv`:

```bash
ataqv --peak-file results/peaks/narrow/sample_peaks.narrowPeak --tss-file tss.bed \
  --name sample_name --metrics-file sample.ataqv.json \
  human results/filtered/sample.final.bam

# Generate HTML report
mkarv my_ataqv_report/ sample.ataqv.json
```

ataqv reports TSS enrichment, fragment length distribution, peak metrics,
mitochondrial fraction, and duplicate rate in a single interactive report.
