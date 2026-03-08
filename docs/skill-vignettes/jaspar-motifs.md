# JASPAR Motifs -- Finding TF Binding Profiles in ENCODE Peaks

> **Category:** External Databases | **Tools Used:** `encode_search_experiments`, `encode_list_files`, JASPAR REST API

## What This Skill Does

Queries JASPAR for transcription factor binding motifs -- position weight matrices (PWMs), sequence logos, and quality scores -- then guides motif scanning against ENCODE peaks. JASPAR provides 900+ curated vertebrate TF profiles through a public REST API at `jaspar.elixir.no/api/v1/`.

## When to Use This

- You have ENCODE TF ChIP-seq peaks and want to confirm the expected motif is enriched.
- You need PWMs for specific transcription factors to scan regulatory regions.
- You want to compare multiple JASPAR profiles for the same TF family to select the best one.

## Example Session

A pancreatic islet researcher wants to retrieve binding motifs for three islet-enriched transcription factors -- PDX1, NKX6-1, and FOXA2 -- then scan ENCODE ATAC-seq peaks for motif occurrences.

### Step 1: Retrieve PWMs for Islet TFs

```python
import requests

BASE = "https://jaspar.elixir.no/api/v1/matrix/"

def get_jaspar_profiles(tf_name, collection="CORE"):
    params = {"name": tf_name, "tax_group": "vertebrates", "collection": collection}
    return requests.get(BASE, params=params).json()["results"]

for tf in ["PDX1", "NKX6-1", "FOXA2"]:
    for p in get_jaspar_profiles(tf):
        print(f"{tf}: {p['matrix_id']} v{p['version']}  class={p['class'][0]}")
```

| TF | JASPAR ID | Class | Motif Length |
|---|---|---|---|
| PDX1 | MA0132.1 | Homeodomain | 10 bp |
| NKX6-1 | MA0671.1 | Homeodomain | 10 bp |
| FOXA2 | MA0047.3 | Forkhead | 12 bp |

PDX1 and NKX6-1 are both homeodomain factors but recognize distinct core sequences -- PDX1 binds a TAAT core while NKX6-1 prefers TAATTG. FOXA2 is a forkhead factor with a broader motif. Export all three in MEME format for FIMO:

```python
motifs = {"PDX1": "MA0132.1", "NKX6-1": "MA0671.1", "FOXA2": "MA0047.3"}
for name, mid in motifs.items():
    meme = requests.get(f"{BASE}{mid}/", params={"format": "meme"}).text
    open(f"{name}_motif.meme", "w").write(meme)
```

### Step 2: Get ENCODE Peaks to Scan

```
encode_search_experiments(
    assay_title="ATAC-seq", organ="pancreas",
    biosample_term_name="islet of Langerhans", status="released", limit=10
)

encode_list_files(
    experiment_accession="ENCSR...",
    output_type="IDR thresholded peaks", assembly="GRCh38",
    preferred_default=True
)
```

Extract summit-centered sequences (summit +/- 100 bp) for tighter motif enrichment:

```bash
awk 'BEGIN{OFS="\t"} {summit=$2+$10; print $1,summit-100,summit+100,$4}' \
    islet_atac_peaks.narrowPeak > summit_regions.bed
bedtools getfasta -fi hg38.fa -bed summit_regions.bed -fo peak_sequences.fa
```

### Step 3: Scan Peaks with FIMO

```bash
for tf in PDX1 NKX6-1 FOXA2; do
    fimo --thresh 1e-4 --oc fimo_${tf}/ ${tf}_motif.meme peak_sequences.fa
done
```

| TF | Motif Hits (p < 1e-4) | % Peaks with Hit | Median Score |
|---|---|---|---|
| FOXA2 | 8,412 | 31.2% | 14.8 |
| PDX1 | 5,871 | 22.4% | 11.3 |
| NKX6-1 | 3,204 | 12.8% | 10.7 |

FOXA2 motifs are most prevalent, consistent with its role as a pioneer factor at endoderm-derived enhancers. PDX1 motifs appear in roughly one in five peaks, matching its function as a core islet identity factor.

### Step 4: Compare Motif Quality Across JASPAR Profiles

Some TFs have multiple profiles from different experimental sources. Query all collections to select the best-supported PWM.

```python
foxa2_all = get_jaspar_profiles("FOXA2", collection="")  # all collections
for p in foxa2_all:
    data = requests.get(f"{BASE}{p['matrix_id']}/", params={"format": "json"}).json()
    print(f"{data['matrix_id']} v{data['version']}  sites={data.get('num_sites','N/A')}  "
          f"source={data.get('data_type','N/A')}")
```

Higher `num_sites` indicates a more robust PWM. Profiles from ChIP-seq or HT-SELEX are preferred over single-SELEX experiments.

## Key Principles

- **Always report the matrix ID and version.** JASPAR profiles are versioned (MA0047.2 vs MA0047.3). Different versions may represent updated data or distinct binding modes. Pin the exact ID in your methods.
- **Summit-centered sequences improve enrichment.** Scanning full peak regions dilutes signal. Center on peak summits (+/- 100-150 bp) for strongest motif enrichment (Grant et al. 2011).
- **Motif presence does not equal binding.** A JASPAR match in open chromatin is necessary but not sufficient for TF occupancy. Validate with ENCODE TF ChIP-seq when available.
- **Use a matched background model.** Default uniform frequencies (25% each) inflate hits in GC-rich regions. Generate a background from your sequences with `fasta-get-markov`.

## Related Skills

- **motif-analysis** -- De novo motif discovery with HOMER and MEME in ENCODE peaks.
- **regulatory-elements** -- Characterize the cis-regulatory elements containing motif hits.
- **peak-annotation** -- Annotate ENCODE peaks with genomic features and nearby genes.
- **variant-annotation** -- Assess whether disease variants disrupt TF binding motifs.
- **quality-assessment** -- Use motif enrichment as a QC metric for TF ChIP-seq experiments.

---

*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 43 skills for genomics research*
