# Downloading ENCODE Files

> Selecting the right files, downloading with integrity verification, and batch retrieval for pancreas H3K27ac ChIP-seq.

**Skill:** `download-encode` | **Tools:** `encode_list_files`, `encode_download_files`, `encode_batch_download`

---

## Scenario

You found experiment **ENCSR817LCE** -- H3K27ac ChIP-seq on human pancreas tissue, GRCh38. You need the processed peak files for enhancer analysis, not the raw FASTQs or BAM alignments.

## Step 1: List All Files for the Experiment

**You ask Claude:** "What files are available for ENCSR817LCE?"

**Claude calls:** `encode_list_files(experiment_accession="ENCSR817LCE")`

```
Accession      Format       Output Type                   Size      Default
ENCFF492VSP    bed          IDR thresholded peaks         1.2 MB    yes
ENCFF731HBR    bigBed       IDR thresholded peaks         842 KB    yes
ENCFF219TQD    bigWig       fold change over control      1.3 GB    yes
ENCFF850PAQ    bigWig       signal p-value                1.4 GB    yes
ENCFF093KLZ    bam          alignments                    4.7 GB    no
ENCFF214RWX    bam          unfiltered alignments         6.1 GB    no
ENCFF339YBT    fastq        reads                         2.8 GB    no
ENCFF771MQJ    fastq        reads                         2.9 GB    no
```

**What matters:** Four files are `preferred_default: true` -- the ENCODE pipeline's recommended outputs. The BED narrowPeak file (ENCFF492VSP) contains your peak coordinates. The fold-change bigWig (ENCFF219TQD) is for genome browser visualization. The BAM and FASTQ files total over 16 GB and are only needed if you plan to re-align from scratch.

## Step 2: Download Peaks and Signal Tracks

**You ask Claude:** "Download the IDR peaks and fold change bigWig to ~/data/encode/pancreas"

**Claude calls:**
```python
encode_download_files(
    file_accessions=["ENCFF492VSP", "ENCFF219TQD"],
    download_dir="~/data/encode/pancreas",
    organize_by="experiment"
)
```

```
File              Size       MD5 Status   Path
ENCFF492VSP.bed   1.2 MB    verified     ~/data/encode/pancreas/ENCSR817LCE/ENCFF492VSP.bed.gz
ENCFF219TQD.bw    1.3 GB    verified     ~/data/encode/pancreas/ENCSR817LCE/ENCFF219TQD.bigWig
```

**What matters:** MD5 verification is on by default -- both checksums matched the ENCODE registry, confirming no corruption. The `organize_by="experiment"` flag nests files under the experiment accession, keeping your directory clean across multiple experiments. The fold-change-over-control bigWig normalizes against the input control, making it directly comparable across experiments and preferable to the signal p-value track for heatmaps.

## Step 3: Batch Download with Dry Run Preview

Now you want all H3K27ac IDR peaks across every pancreas experiment in one step.

**You ask Claude:** "Download all H3K27ac IDR thresholded peaks for pancreas, GRCh38"

**Claude calls (preview first):**
```python
encode_batch_download(
    download_dir="~/data/encode/pancreas_h3k27ac",
    output_type="IDR thresholded peaks",
    target="H3K27ac",
    organ="pancreas",
    assembly="GRCh38",
    assay_title="Histone ChIP-seq",
    organize_by="experiment",
    dry_run=True
)
```

```
DRY RUN -- Preview of download:
  Files:     12
  Total:     14.8 MB
  Formats:   bed narrowPeak (12)
  Assembly:  GRCh38 (all)
  Experiments: ENCSR817LCE, ENCSR491LKP, ENCSR265JSX, ...
  Already downloaded: 1 (ENCFF492VSP -- will be skipped)
```

**You confirm:** "Looks good, download them all"

**Claude calls:** Same parameters with `dry_run=False`

```
Downloaded 11 files (14.8 MB) -- 1 skipped (already exists)
All 11 files passed MD5 verification
```

**What matters:** The dry run showed exactly what would happen before any bytes were transferred. Peak BED files are small (KB-MB range), so 12 files total under 15 MB. The previously downloaded ENCFF492VSP was automatically skipped. Always specify `assembly="GRCh38"` in batch downloads to avoid mixing genome builds.

## File Selection Quick Reference

| You need | Filter by | Typical size |
|----------|-----------|-------------|
| Peak coordinates | `output_type="IDR thresholded peaks"` | 0.5-5 MB |
| Browser signal tracks | `file_format="bigWig"`, `output_type="fold change over control"` | 0.5-2 GB |
| Gene expression tables | `output_type="gene quantifications"` | 5-50 MB |
| Re-alignment from raw | `file_format="fastq"` | 1-20 GB per file |
| ENCODE recommendations | `preferred_default=True` | varies |

## Pitfalls

- **BAM files are large.** A single ChIP-seq BAM can be 5-50 GB. Never batch download BAMs without checking total size via dry run first.
- **Always specify assembly.** Without `assembly="GRCh38"`, a batch download may pull files from both hg19 and GRCh38, breaking downstream analysis.
- **MD5 failures mean re-download.** If verification fails, the file is corrupted. Re-download rather than disabling verification.

---

*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 43 skills for genomics research*
