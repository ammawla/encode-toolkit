# Loop Calling with HiCCUPS

HiCCUPS (Hi-C Computational Unbiased Peak Search) identifies chromatin loops
from contact matrices. It is the ENCODE-standard loop caller, part of
Juicer tools.

## HiCCUPS Loop Calling

```bash
java -Xmx16g -jar juicer_tools.jar hiccups \
    --cpu \
    --threads 4 \
    -k KR \
    -r 5000,10000,25000 \
    -f 0.1,0.1,0.1 \
    -p 4,2,1 \
    -i 7,5,3 \
    -d 20000,20000,50000 \
    sample.hic \
    loops_output/
```

This is the command `main.nf` runs. `--cpu` is required with the container
image, which has no CUDA runtime; drop it only with `--hiccups_gpu` on a host
with an NVIDIA GPU. CPU mode restricts the search to a band along the
diagonal (8 Mb by default), so very long-range loops are not reported.

### Key Parameters

| Parameter | Value | Meaning |
|-----------|-------|---------|
| `--cpu` | flag | CPU mode; needed without a CUDA runtime, searches 8 Mb from the diagonal |
| `-k` | KR | Normalization vector to read from the .hic file |
| `-r` | 5000,10000,25000 | Resolutions to search for loops |
| `-f` | 0.1,0.1,0.1 | FDR threshold per resolution |
| `-p` | 4,2,1 | Peak width (pixels) per resolution |
| `-i` | 7,5,3 | Window width for local background per resolution |
| `-d` | 20000,20000,50000 | Distance within which nearby enriched pixels are merged into one loop centroid |

`juicer_tools pre` must have written the `-k` vector into the .hic file:
`main.nf` builds KR, VC and VC_SQRT.

### Resolution Selection

| Resolution | Detects | Minimum Contacts |
|------------|---------|------------------|
| 5 kb | Fine-scale loops | >1 billion |
| 10 kb | Standard loops | >500 million |
| 25 kb | Large-scale loops | >100 million |

## HiCCUPS Output Format

HiCCUPS produces a BEDPE-like file with loop anchors:

```
chr1  start1  end1  chr2  start2  end2  color  observed  expected_BL  expected_donut  expected_H  expected_V  FDR_BL  FDR_donut  FDR_H  FDR_V
```

Key columns:
- `chr1:start1-end1` -- Upstream anchor
- `chr2:start2-end2` -- Downstream anchor
- `observed` -- Observed contact count
- `expected_donut` -- Expected count from donut background model
- `FDR_donut` -- FDR from donut model (primary significance)

## Merge Loops Across Resolutions

HiCCUPS calls loops at each resolution independently and merges them itself:
it writes `merged_loops.bedpe` into the output directory alongside the
per-resolution files. There is no separate merge command (`juicer_tools` has
no `hiccups_merge` tool).

`main.nf` copies that merged file to `loops/{sample}.hiccups_loops.bedpe`,
which is the only loop file published; the per-resolution files stay in the
Nextflow work directory.

## Alternative: Mustache Loop Caller (manual, not in the image)

Mustache (Roayaei Ardakany 2020, ~165 citations) uses a scale-space
representation for loop detection. It is not installed in the container
image and the workflow does not run it:

```bash
mustache \
    -f sample.mcool \
    -r 10000 \
    -ch hg38.chrom.sizes \
    -o mustache_loops.bedpe \
    -pt 0.05 \
    -st 0.8
```

### HiCCUPS vs Mustache

| Feature | HiCCUPS | Mustache |
|---------|---------|----------|
| Background model | Donut + 3 others | Scale-space Gaussian |
| GPU support | Yes (CUDA; the image ships CPU mode only) | No |
| Speed | Faster with GPU | Moderate |
| Sensitivity | Standard | Higher (more loops) |
| ENCODE standard | Yes | Alternative |
| Concordance | ~50% overlap between callers (Wolff 2022) |

## Loop QC Metrics

### Loop Count by Resolution

HiCCUPS writes two files per resolution: `enriched_pixels_<res>.bedpe`
(pre-filter candidates) and `postprocessed_pixels_<res>.bedpe` (the final
calls that go into `merged_loops.bedpe`). Count the post-filter file:

```bash
for res in 5000 10000 25000; do
    count=$(wc -l < loops_output/postprocessed_pixels_${res}.bedpe)
    echo "Resolution ${res}: ${count} loops"
done
```

These per-resolution files are not published by the workflow; they remain in
the task's work directory. From a finished run, count the merged file instead:

```bash
wc -l < results/loops/sample.hiccups_loops.bedpe
```

Expected loop counts (human cell line, >1B contacts):
- 5 kb: 5,000-15,000 loops
- 10 kb: 3,000-10,000 loops
- 25 kb: 1,000-5,000 loops

### Loop Size Distribution

```bash
awk '{print $5 - $2}' results/loops/sample.hiccups_loops.bedpe | \
    sort -n | \
    awk '{a[NR]=$1} END {
        print "Median loop size:", a[int(NR/2)];
        print "Min:", a[1];
        print "Max:", a[NR]
    }'
```

Typical loop sizes:
- Median: 200-400 kb
- Range: 50 kb to 5 Mb
- Loops <50 kb may be artifacts at lower resolutions

### CTCF Enrichment at Anchors (manual, not run by this workflow)

True loops are enriched for CTCF binding at anchors. bedtools is not in the
container image, so run this outside the workflow:

```bash
bedtools intersect \
    -a loop_anchors.bed \
    -b CTCF_peaks.bed \
    -u | wc -l
```

Expect >60% of loop anchors to overlap CTCF peaks for convergent CTCF loops.
