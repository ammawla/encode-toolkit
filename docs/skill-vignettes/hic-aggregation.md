# Hi-C Aggregation -- Union Catalogs of Chromatin Loops

> **Category:** Data Aggregation | **Tools Used:** `encode_search_experiments`, `encode_search_files`, `encode_download_files`, `encode_track_experiment`, `encode_log_derived_file`

## What This Skill Does

Builds a comprehensive catalog of chromatin loops (BEDPE) for a tissue by merging loop calls across multiple ENCODE Hi-C experiments, donors, and labs. Uses resolution-aware anchor matching to create a union set of both constitutive and individual-specific 3D contacts.

## Why Union Matters for Hi-C

Loop callers disagree substantially. Wolff et al. 2022 (GigaScience) benchmarked HICCUPS, Mustache, Fit-Hi-C, and HiCExplorer and found they intersect by roughly 50% at most. The Loop Catalog (Reyna et al. 2025, Nucleic Acids Research) addressed this by building union catalogs across 1,089 datasets, recovering 4.19M unique loops -- about 3x more than any single experiment. If a loop is detected in one donor but absent in another, the contact is real; absence reflects depth or caller sensitivity.

## Example Session

### Scientist's Request

> "I need all known chromatin loops in human brain tissue. Build me a union catalog from ENCODE Hi-C data."

### Step 1: Find Hi-C Experiments and Download Loop Calls

```
encode_search_experiments(
    assay_title="Hi-C", organ="brain", biosample_type="tissue",
    organism="Homo sapiens", status="released", limit=50)
```

Not all Hi-C experiments include called loops. Search specifically for BEDPE files:

```
encode_search_files(
    assay_title="Hi-C", organ="brain",
    output_type="chromatin interactions", assembly="GRCh38", limit=50)
```

Each BEDPE row encodes one loop as a pair of anchor regions:

```
chr1  1200000  1205000  chr1  1450000  1455000  loop_1  45.2  .  .
```

Download the files and track each source experiment:

```
encode_download_files(
    file_accessions=["ENCFF001ABC", "ENCFF002DEF", "ENCFF003GHI"],
    download_dir="/data/hic_brain_loops", organize_by="experiment")
encode_track_experiment(accession="ENCSR001XYZ")
```

### Step 2: Resolution-Aware Anchor Matching

Hi-C loop anchors are binned regions. A 5kb experiment produces 5,000 bp anchors; a 10kb experiment produces 10,000 bp anchors. Merging them directly creates false mismatches. Harmonize first:

```bash
# Re-bin 5kb anchors to 10kb resolution
awk -v res=10000 'BEGIN{OFS="\t"} {
    bin1_s = int($2/res) * res; bin1_e = bin1_s + res
    bin2_s = int($5/res) * res; bin2_e = bin2_s + res
    print $1, bin1_s, bin1_e, $4, bin2_s, bin2_e, $7, $8
}' fine_res_loops.bedpe > harmonized.bedpe
```

### Step 3: Union Merge

Following the Loop Catalog approach (Reyna et al. 2025), bin anchors, canonically order, then deduplicate:

```bash
cat sample*.clean.bedpe | \
awk -v res=10000 'BEGIN{OFS="\t"} {
    a1=$1":"int($2/res)*res; a2=$4":"int($5/res)*res
    if (a1<a2) id=a1"-"a2; else id=a2"-"a1; print id,$0
}' | sort -k1,1 | \
awk 'BEGIN{OFS="\t"} {
    if ($1!=prev) { if(NR>1) print c1,s1,e1,c2,s2,e2,n
        prev=$1;c1=$2;s1=$3;e1=$4;c2=$5;s2=$6;e2=$7;n=1 }
    else n++
} END { print c1,s1,e1,c2,s2,e2,n }' > union_loops.bedpe
```

Alternatively, mariner (Flores et al. 2024) provides `mergePairs()` with configurable anchor tolerance, and AQuA Tools (Chakraborty et al. 2025) handles BEDPE set operations.

### Step 4: Annotate Caller Concordance

With N source experiments, label each loop by detection breadth:

| Label | Criterion | Meaning |
|---|---|---|
| HIGH | >=50% of samples | Constitutive loop across individuals |
| SUPPORTED | 2+ samples | Likely real, some donor variation |
| SINGLETON | 1 sample | May reflect depth or individual biology |

Singletons are not noise -- many validate when depth increases.

### Step 5: Log Provenance

```
encode_log_derived_file(
    file_path="/data/hic_brain_loops/union_loops.annotated.bedpe",
    source_accessions=["ENCSR001XYZ", "ENCSR002ABC", "ENCSR003DEF"],
    description="Union chromatin loops across 3 brain Hi-C experiments",
    file_type="aggregated_loops", tool_used="awk resolution-binned merge at 10kb",
    parameters="blocklist filtered, self-ligation >=20kb, 10kb resolution binning")
```

## Key Pitfalls

- **Never mix assemblies.** Hi-C resolution binning makes liftOver error-prone. Use GRCh38 throughout.
- **Resolution mismatch silently inflates counts.** Always harmonize anchor widths before merging.
- **Loops are not TADs.** Loops are paired anchors; TADs are domains. Aggregate them separately.
- **Short-range artifacts.** Remove anchor pairs less than 20kb apart -- typically undigested chromatin.

## Related Skills

- **histone-aggregation** -- Annotate loop anchors with H3K27ac/H3K4me1 for enhancer-promoter contacts.
- **accessibility-aggregation** -- Validate loop anchors by requiring overlap with accessible chromatin.
- **pipeline-hic** -- Process raw Hi-C FASTQ through the ENCODE-aligned pipeline.
- **regulatory-elements** -- Connect distal enhancers to target promoters via loop-based linkage.

---

*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 43 skills for genomics research*