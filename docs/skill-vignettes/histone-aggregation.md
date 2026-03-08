# Histone Aggregation -- Union Peak Catalogs Across Experiments

> **Category:** Data Aggregation | **Tools Used:** `encode_search_experiments`, `encode_list_files`, `encode_download_files`, `encode_log_derived_file`

## What This Skill Does

Builds a comprehensive map of histone mark binding for a tissue by merging narrowPeak files from multiple ENCODE experiments into a single union peak set. The core principle: if a mark is detected in ANY sample, it CAN bind there -- we want the UNION of all detections, not a consensus.

## When to Use This

- You need to answer "where does this mark bind in my tissue?" by combining peaks across donors and labs.
- You are building a tissue-level regulatory catalog with maximum sensitivity -- singletons included.

## Example Session

A scientist aggregates all H3K27ac peaks across human pancreas tissue experiments.

### Step 1: Find H3K27ac Experiments on Pancreas

```
encode_search_experiments(
    assay_title="Histone ChIP-seq", target="H3K27ac",
    organ="pancreas", biosample_type="tissue", status="released", limit=50
)
```

Five experiments returned from two labs (Ren/UCSD, Bernstein/Broad) across four donors (ages 29-62, both sexes). All five pass quality-gating: no ERROR audit flags, IDR thresholded peaks available.

### Step 2: Download IDR Thresholded Peaks

```
encode_download_files(
    file_accessions=["ENCFF635JIA", "ENCFF388RZD", "ENCFF912KLN", "ENCFF447QBT", "ENCFF201XMW"],
    download_dir="/data/h3k27ac_pancreas/peaks", organize_by="flat"
)
```

All five files are GRCh38 narrowPeak format, verified by MD5 checksum.

### Step 3: Blacklist Filter + SignalValue Filter

Two per-sample noise filters applied BEFORE merging. First, remove artifact-prone regions (Amemiya et al. 2019). Then retain peaks above the 25th percentile signalValue -- the top 75% are most consistent across pipelines (Perna et al. 2024). Each sample has a different signal distribution, so thresholds are computed per-sample:

```bash
for f in /data/h3k27ac_pancreas/peaks/*.narrowPeak; do
    # Remove blacklisted regions (centromeres, telomeres, rDNA repeats)
    bedtools intersect -a "$f" -b hg38-blacklist.v2.bed -v > "${f%.narrowPeak}.bl.narrowPeak"
    # Filter to top 75% by signalValue (column 7)
    BL="${f%.narrowPeak}.bl.narrowPeak"
    THRESHOLD=$(sort -k7,7n "$BL" | awk -v p=$(wc -l < "$BL") 'NR==int(p*0.25){print $7}')
    awk -v t="$THRESHOLD" '$7 >= t' "$BL" > "${f%.narrowPeak}.qf.narrowPeak"
done
```

### Step 4: Union Merge with bedtools

Tag peaks by sample, concatenate, sort, and merge. H3K27ac is a narrow mark -- no gap tolerance needed:

```bash
# Tag each sample with a unique ID in the name column
for i in 1 2 3 4 5; do
    awk -v sid="sample${i}" 'BEGIN{OFS="\t"} {$4=sid; print}' \
        "sample${i}.qf.narrowPeak" > "sample${i}.tagged.bed"
done

# Concatenate, sort, merge -- count_distinct avoids inflating support
cat sample*.tagged.bed | bedtools sort -i - > all_peaks.sorted.bed
bedtools merge -i all_peaks.sorted.bed -c 4,7,9 -o count_distinct,max,max \
    > h3k27ac_pancreas_union.bed
```

Output columns: chr, start, end, n_samples, max_signalValue, max_qValue. Using `count_distinct` on column 4 ensures overlapping peaks from the same sample count as one.

### Step 5: Results

```
Input:       5 experiments, 4 donors, 2 labs
Peaks in:    142,318 total (after per-sample QC)
Union peaks: 87,641
  HIGH (3-5 samples):   34,219  (39.0%)
  SUPPORTED (2 samples): 28,746  (32.8%)
  SINGLETON (1 sample):  24,676  (28.2%)
Genome coverage:         48.3 Mb (1.6% of GRCh38)
```

The 24,676 singletons are NOT discarded. A peak detected in one donor is a real binding event -- individual variation and antibody lot differences explain absence in other samples, not that presence is spurious.

### Step 6: Log Provenance

```
encode_log_derived_file(
    file_path="/data/h3k27ac_pancreas/h3k27ac_pancreas_union.bed",
    source_accessions=["ENCSR831YAX", "ENCSR976DGM", "ENCSR149DGJ", "ENCSR440KDQ", "ENCSR552EBT"],
    description="Union H3K27ac peaks across 5 pancreas samples, confidence-annotated",
    file_type="aggregated_peaks", tool_used="bedtools merge v2.31.0",
    parameters="blacklist=hg38-blacklist.v2.bed; signalValue>=25th pctl per sample; merge -d 0"
)
```

## Key Principles

- **Filter noise per-sample, not post-merge.** Each experiment has a different signal distribution. A universal threshold biases toward high-depth samples.
- **Union, not consensus.** For cataloging questions ("where CAN this mark bind?"), requiring presence in N/M samples discards real biology. Consensus is for high-confidence subsets only.
- **Broad marks need gap tolerance.** H3K27me3 and H3K9me3 span 10-100kb domains -- use `bedtools merge -d 1000` for those marks instead of the overlap-only merge shown here.

## Related Skills

- **accessibility-aggregation** -- Same union approach for ATAC-seq and DNase-seq open chromatin regions.
- **peak-annotation** -- Annotate the union peak set with nearest genes and genomic features.
- **regulatory-elements** -- Combine union peaks from multiple marks to identify enhancers and promoters.
- **pipeline-chipseq** -- Process raw FASTQ data through the ENCODE ChIP-seq pipeline before aggregation.

---

*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 43 skills for genomics research*
