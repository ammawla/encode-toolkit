# UCSC Browser -- Regulatory Context and Sequence at Any Locus

> **Category:** External Databases | **API Used:** UCSC Genome Browser REST API (`api.genome.ucsc.edu`)

## What This Skill Does

Queries the UCSC Genome Browser REST API to retrieve DNA sequences, ENCODE cCRE annotations, TF binding clusters, and track data for any genomic region. No authentication required. Complements the ENCODE Portal by providing aggregated, cross-experiment regulatory annotations at a locus.

## When to Use This

- You need the DNA sequence under an ENCODE peak for motif analysis or CRISPR guide design.
- You want to know what cCREs and TF binding events ENCODE predicts at a specific locus.
- You are setting up UCSC track hubs to visualize ENCODE bigWig signal files.
- You need a shareable browser session URL for a collaborator or manuscript figure.

## Example Session

A scientist is investigating a GWAS hit at chr11:2,150,000-2,200,000 (near the insulin gene cluster) and wants to understand the regulatory landscape using ENCODE data hosted on UCSC.

### Step 1: Retrieve DNA Sequence for the Region

Get the underlying sequence to check for known TF binding motifs:

```bash
curl "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr11;start=2150000;end=2200000"
```

The response contains a `dna` field with 50 kb of nucleotide sequence. Save as FASTA for motif scanning:

```bash
curl -s "https://api.genome.ucsc.edu/getData/sequence?genome=hg38;chrom=chr11;start=2150000;end=2200000" \
  | jq -r '">chr11:2150000-2200000\n" + .dna' > ins_locus.fa
```

### Step 2: Query ENCODE cCREs at the Locus

Check what candidate regulatory elements ENCODE has cataloged in this region:

```bash
curl "https://api.genome.ucsc.edu/getData/track?genome=hg38;track=encodeCcreCombined;chrom=chr11;start=2150000;end=2200000;jsonOutputArrays=1"
```

Results show 12 cCREs in the region:

| cCRE Accession | Class | Position | Z-Score |
|---|---|---|---|
| EH38E2174831 | PLS | chr11:2,159,779-2,160,117 | 4.82 |
| EH38E2174835 | dELS | chr11:2,170,432-2,170,891 | 3.41 |
| EH38E2174839 | pELS | chr11:2,181,102-2,181,544 | 5.17 |
| EH38E2174842 | CTCF-only | chr11:2,191,220-2,191,588 | 2.93 |

The PLS element near 2,160 kb marks the INS promoter. The high-scoring pELS at 2,181 kb is a proximal enhancer candidate worth investigating further.

### Step 3: Check TF Binding Across ENCODE Biosamples

Which transcription factors bind at the enhancer candidate?

```bash
curl "https://api.genome.ucsc.edu/getData/track?genome=hg38;track=TFrPeakClusters;chrom=chr11;start=2181000;end=2182000;jsonOutputArrays=1"
```

The TF rPeak clusters show binding by PDX1 (ubiquity 0.12), NKX2-2 (0.08), FOXA2 (0.31), and CTCF (0.87). The low ubiquity for PDX1 and NKX2-2 indicates islet-specific binding -- consistent with the INS locus biology. The `exp` field in each cluster links back to specific ENCODE experiments that can be retrieved with `encode_get_experiment`.

### Step 4: Set Up a Track Hub for ENCODE bigWig Files

To visualize ENCODE signal tracks alongside UCSC annotations, create a track hub. First, find relevant signal files:

```
encode_search_files(
    file_format="bigWig", output_type="fold change over control",
    assay_title="Histone ChIP-seq", target="H3K27ac",
    organ="pancreas", assembly="GRCh38", preferred_default=True
)
```

Then create `hub.txt`, `genomes.txt`, and `trackDb.txt` on a public server or cloud bucket:

```
# trackDb.txt -- one stanza per ENCODE bigWig track
track pancreas_h3k27ac_1
bigDataUrl https://www.encodeproject.org/files/ENCFF635JIA/@@download/ENCFF635JIA.bigWig
shortLabel H3K27ac Panc D1
longLabel H3K27ac pancreas donor 1 fold change over control (ENCSR831YAX)
type bigWig
visibility full
color 255,165,0

track pancreas_h3k27ac_2
bigDataUrl https://www.encodeproject.org/files/ENCFF388RZD/@@download/ENCFF388RZD.bigWig
shortLabel H3K27ac Panc D2
longLabel H3K27ac pancreas donor 2 fold change over control (ENCSR976DGM)
type bigWig
visibility full
color 255,165,0
```

Load the hub: `My Data > Track Hubs > My Hubs > paste hub URL`.

### Step 5: Create a Shareable Browser Session URL

Build a URL that positions the browser at the locus with the relevant tracks visible:

```
https://genome.ucsc.edu/cgi-bin/hgTracks?db=hg38&position=chr11:2150000-2200000&encodeCcreCombined=pack&TFrPeakClusters=dense&hubUrl=https://your-server.com/hub.txt
```

This URL opens the browser at the INS locus with cCREs in pack mode, TF clusters in dense mode, and the custom hub loaded. Share directly in a manuscript supplement or Slack -- no login required.

**Coordinate note:** UCSC REST API uses 0-based, half-open coordinates (BED format). When converting from VCF (1-based), subtract 1 from the position. A VCF variant at chr11:2,181,103 becomes `start=2181102;end=2181103`.

## Related Skills

- **regulatory-elements** -- Classify cCREs from Step 2 into enhancers, promoters, and insulators using chromatin state models.
- **variant-annotation** -- Annotate the GWAS variant with functional impact using ENCODE data and gnomAD constraint.
- **motif-analysis** -- Scan the sequence from Step 1 for TF binding motifs using JASPAR matrices.
- **ensembl-annotation** -- Run VEP on variants within the cCRE regions for regulatory consequence prediction.
- **visualization-workflow** -- Full-featured visualization setup beyond the track hub basics shown here.

---
*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 43 skills for genomics research*
