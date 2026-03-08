# Accessibility Aggregation -- Union Catalogs from ATAC-seq and DNase-seq

> **Category:** Data Aggregation | **Tools Used:** `encode_search_experiments`, `encode_list_files`, `encode_download_files`, `encode_log_derived_file`

## What This Skill Does

Builds a comprehensive open chromatin map by merging ATAC-seq and DNase-seq narrowPeak files into a union peak set. Both assays detect nucleosome-depleted regions through different enzymes (Tn5 transposase vs. DNase I). Corces et al. 2017 showed ~75% overlap, making a combined union scientifically justified.

## When to Use This

- You need a complete catalog of accessible regions, not just one assay's view.
- ENCODE has DNase-seq from earlier phases and ATAC-seq from newer submissions for your organ.
- You are building regulatory element maps and need accessibility as the foundation layer.

## Example Session

> "Build a union chromatin accessibility map for human liver using all available ATAC-seq and DNase-seq."

### Step 1: Search for Both Assay Types

```
encode_search_experiments(assay_title="ATAC-seq", organ="liver", biosample_type="tissue", limit=50)
encode_search_experiments(assay_title="DNase-seq", organ="liver", biosample_type="tissue", limit=50)
```

```
ATAC-seq (3):  ENCSR832UMM (M,37y), ENCSR605AVQ (F,51y), ENCSR317JGA (M,44y)  -- snyder
DNase-seq (5): ENCSR000ENR (M,32y), ENCSR000EPH (F,53y), ENCSR000ENO (M,3y),
               ENCSR913JDV (F,59y), ENCSR762NIO (M,27y)  -- stam
```

Eight samples across sexes, ages, and two labs. Use `encode_list_files` per experiment to find IDR thresholded peaks in GRCh38.

### Step 2: Download Peak Files

```
encode_download_files(
    file_accessions=["ENCFF635JIA","ENCFF922MXZ","ENCFF410KOW","ENCFF388RZD",
                     "ENCFF770EAT","ENCFF441OZJ","ENCFF819QBH","ENCFF503TVR"],
    download_dir="/data/liver/accessibility", organize_by="flat")
```

### Step 3: Filter -- Blacklist, Signal, and ATAC Artifacts

```bash
# 3a. ENCODE blacklist removal (Amemiya et al. 2019)
for f in *.narrowPeak; do
    bedtools intersect -a "$f" -b hg38-blacklist.v2.bed -v > "${f%.narrowPeak}.bl.narrowPeak"
done

# 3b. Per-sample signalValue filter (remove bottom 25%)
for f in *.bl.narrowPeak; do
    THR=$(sort -k7,7n "$f" | awk -v p=$(wc -l < "$f") 'NR==int(p*0.25){print $7}')
    awk -v t="$THR" '$7 >= t' "$f" > "${f%.bl.narrowPeak}.qf.narrowPeak"
done

# 3c. ATAC-only: remove Tn5 insertion artifacts (<50 bp peaks; skip for DNase-seq)
for f in atac_*.qf.narrowPeak; do
    awk '($3 - $2) >= 50' "$f" > "${f%.qf.narrowPeak}.clean.narrowPeak"
done
```

### Step 4: Tag by Sample, Union Merge

```bash
# Tag each file with a unique sample ID
awk -v sid="atac_s1" 'BEGIN{OFS="\t"}{$4=sid; print}' atac_s1.clean.narrowPeak > atac_s1.tagged.bed
awk -v sid="dnase_s1" 'BEGIN{OFS="\t"}{$4=sid; print}' dnase_s1.qf.narrowPeak > dnase_s1.tagged.bed
# ... repeat for all 8 samples

cat *.tagged.bed | bedtools sort -i - | \
    bedtools merge -c 4,7,9 -o count_distinct,max,max \
    > liver_union_accessible.bed
# Output: chr, start, end, n_samples, max_signalValue, max_qValue
```

No gap tolerance (`-d 0`) -- accessibility peaks are narrow/point-source. Counting unique samples prevents deeply-sequenced experiments from inflating support counts.

### Step 5: Annotate Confidence and Inspect Output

```bash
awk -v N=8 '{
    if ($4 >= N*0.5) conf="HIGH"; else if ($4 >= 2) conf="SUPPORTED"; else conf="SINGLETON";
    print $0"\t"conf"\t"$4"/"N
}' liver_union_accessible.bed > liver_union_accessible.annotated.bed
```

```
chr1  1013468  1014280  8  42.7  118.3  HIGH       8/8    <- constitutive open chromatin
chr1  1026840  1027510  5  28.1   67.9  HIGH       5/8
chr1  1189280  1189740  2  14.3   22.1  SUPPORTED  2/8
chr1  1256710  1257090  1   9.8   11.4  SINGLETON  1/8    <- keep: individual-specific or depth-limited
```

### Step 6: Log Provenance

```
encode_log_derived_file(
    file_path="/data/liver/accessibility/liver_union_accessible.annotated.bed",
    source_accessions=["ENCSR832UMM","ENCSR605AVQ","ENCSR317JGA","ENCSR000ENR",
                       "ENCSR000EPH","ENCSR000ENO","ENCSR913JDV","ENCSR762NIO"],
    description="Union accessible regions (3 ATAC-seq + 5 DNase-seq) across 8 liver samples",
    file_type="aggregated_accessibility", tool_used="bedtools merge v2.31.0",
    parameters="blacklist filtered, signalValue >= 25th pctl, ATAC min width 50bp, merge -d 0")
```

## Why Combine ATAC-seq and DNase-seq

ENCODE's historical catalog is richest in DNase-seq; newer experiments favor ATAC-seq. Combining both maximizes donor count and captures regions one assay may miss due to enzymatic bias. Detection is binary: if open chromatin is found by either enzyme in any sample, the site is real.

## Related Skills

- **histone-aggregation** -- Same union merge approach for ChIP-seq narrowPeak data.
- **regulatory-elements** -- Intersect accessibility with histone marks to classify enhancers and promoters.
- **motif-analysis** -- Find enriched TF motifs in accessible regions (HOMER, MEME).
- **pipeline-atacseq** -- Process raw ATAC-seq FASTQ through the ENCODE-aligned Nextflow pipeline.

---
*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 43 skills for genomics research*
