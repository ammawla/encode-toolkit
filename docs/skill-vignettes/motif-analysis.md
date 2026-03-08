# Motif Analysis -- Discovering TF Binding Sites in ENCODE Peaks

> **Category:** Analysis | **Tools Used:** `encode_search_experiments`, `encode_list_files`, `encode_download_files`, `encode_log_derived_file`

## What This Skill Does

Guides de novo motif discovery and known motif enrichment analysis on ENCODE ChIP-seq and ATAC-seq peaks using HOMER and MEME-ChIP. Two purposes: (1) validate that a ChIP-seq experiment captured the expected TF, and (2) discover co-regulatory partners that bind nearby.

## When to Use This

- You have ENCODE peaks and want to identify enriched TFs, validate a ChIP-seq target, or find co-binding partners.

## Example Session

A scientist identifies transcription factor motifs enriched in H3K27ac peaks from human pancreatic islets to discover which TFs drive islet-specific enhancer activity.

### Step 1: Find H3K27ac Experiments on Pancreas

```
encode_search_experiments(
    assay_title="Histone ChIP-seq", target="H3K27ac",
    organ="pancreas", biosample_type="tissue", status="released", limit=25
)
```

Three experiments returned with IDR thresholded peaks available on GRCh38.

### Step 2: Download IDR Thresholded Peaks

```
encode_list_files(
    experiment_accession="ENCSR831YAX",
    file_format="bed", output_type="IDR thresholded peaks",
    assembly="GRCh38", preferred_default=True
)

encode_download_files(
    file_accessions=["ENCFF635JIA"],
    download_dir="/data/motif_analysis/pancreas_h3k27ac"
)
```

One narrowPeak file downloaded and verified by MD5 checksum. 87,641 peaks on GRCh38.

### Step 3: Prepare Input Sequences

H3K27ac marks broad enhancer domains, not point TF binding. Use full peak regions and subsample the top peaks by signal:

```bash
# Remove blacklisted regions (Amemiya et al. 2019)
bedtools intersect -a ENCFF635JIA.narrowPeak \
    -b hg38-blacklist.v2.bed -v > peaks_clean.narrowPeak

# Subsample top 10,000 by signalValue (column 7)
sort -k7,7nr peaks_clean.narrowPeak | head -10000 > top10k.narrowPeak

# Extract FASTA for MEME-ChIP (requires genome FASTA)
bedtools getfasta -fi hg38.fa -bed top10k.narrowPeak -fo top10k.fa
```

### Step 4: Run HOMER

```bash
findMotifsGenome.pl top10k.narrowPeak hg38 homer_pancreas_h3k27ac/ \
    -size given -mask -p 8 -preparsedDir homer_preparsed/
```

`-size given` uses full peak boundaries because H3K27ac marks span enhancer domains rather than point binding sites. `-mask` prevents repeat-derived spurious motifs.

### Step 5: Run MEME-ChIP

```bash
meme-chip -meme-maxw 30 -meme-nmotifs 10 -meme-minw 6 \
    -db JASPAR2024_CORE_vertebrates.meme \
    -o memechip_pancreas_h3k27ac/ top10k.fa
```

### Step 6: Interpret Results

Both tools converge on the same islet-specific TF motifs. The top known motif enrichments from HOMER:

| Rank | Motif | Family | p-value | % Targets | % Background | Interpretation |
|------|-------|--------|---------|-----------|--------------|----------------|
| 1 | FOXA2 | Forkhead | 1e-892 | 38.2% | 12.1% | Pioneer factor opening islet chromatin |
| 2 | PDX1 | Homeodomain | 1e-631 | 29.7% | 9.8% | Master beta-cell TF |
| 3 | NKX6.1 | NK-homeodomain | 1e-418 | 22.4% | 8.3% | Beta-cell identity and maintenance |
| 4 | HNF1B | Homeodomain | 1e-287 | 18.1% | 7.6% | Pancreatic lineage factor |
| 5 | CTCF | Zinc finger | 1e-204 | 14.3% | 6.9% | Architectural factor near insulators |

FOXA2 tops the list as a pioneer factor that opens islet chromatin. PDX1 and NKX6.1 -- the defining beta-cell TFs -- rank second and third, confirming these H3K27ac peaks mark islet-specific regulatory elements. CentriMo from MEME-ChIP confirms FOXA2 and PDX1 show central enrichment, indicating direct binding rather than indirect co-association.

### Step 7: Log Provenance

```
encode_log_derived_file(
    file_path="/data/motif_analysis/pancreas_h3k27ac/homer_pancreas_h3k27ac/",
    source_accessions=["ENCSR831YAX"],
    description="HOMER + MEME-ChIP motif analysis of top 10k H3K27ac peaks, pancreas",
    tool_used="HOMER v4.11; MEME Suite v5.5.5",
    parameters="-size given -mask; -meme-maxw 30 -db JASPAR2024; blacklist=hg38-blacklist.v2"
)
```

## Key Principles

- **Summit vs full peak.** For TF ChIP-seq, center on the summit with a narrow 200bp window to concentrate signal. For histone marks and ATAC-seq, use `-size given` because relevant features span the full region.
- **Always repeat-mask.** Without `-mask`, Alu elements and LINEs dominate de novo results with biologically meaningless "motifs."
- **Subsample strong peaks.** Top 5,000-10,000 peaks by signal produce cleaner motifs than the full set. Quality over quantity.
- **Run both tools.** HOMER and MEME-ChIP use different algorithms. Concordant results are high-confidence. Discordant results warrant investigation.

## Related Skills

- **jaspar-motifs** -- Targeted scanning for specific TF motifs at base-pair resolution across a genome.
- **peak-annotation** -- Annotate motif-containing peaks with nearest genes and genomic features.
- **regulatory-elements** -- Define enhancers and promoters from multi-mark data, then characterize their motif content.
- **epigenome-profiling** -- Full epigenomic profiles provide context for which TFs are active in a tissue.
- **publication-trust** -- Verify literature claims backing motif analysis decisions.

---
*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 43 skills for genomics research*
