# Connecting ENCODE Regulatory Data to Disease Variants

> This vignette shows how to use ENCODE data alongside external databases to
> understand the regulatory context of disease-associated genetic variants.
> ENCODE output is from real API queries. External database steps describe
> guidance that Claude provides through specialized skills.

## Scenario

You have GWAS hits for Type 2 Diabetes (T2D) and want to understand which
variants fall in regulatory elements active in pancreatic islets.

## Step 1: Find Pancreatic Islet Regulatory Data

**You ask Claude:**
> "Find ENCODE experiments for pancreatic islets -- I need chromatin accessibility and histone marks."

**Claude calls:** `encode_search_experiments(organ="pancreas", biosample_term_name="islet of Langerhans")`

**Result:**
```json
{
  "results": [
    {
      "accession": "ENCSR000DDA",
      "assay_title": "FAIRE-seq",
      "biosample_summary": "Homo sapiens islet of Langerhans tissue",
      "lab": "jason-lieb",
      "replication_type": "unreplicated"
    },
    {
      "accession": "ENCSR000DFB",
      "assay_title": "RRBS",
      "biosample_summary": "Homo sapiens islet of Langerhans tissue",
      "lab": "richard-myers",
      "replication_type": "isogenic"
    }
  ],
  "total": 2
}
```

**What this tells you:** ENCODE has very limited islet-specific data -- only FAIRE-seq
(an older open chromatin assay) and RRBS (methylation). Neither provides histone marks
or ATAC-seq needed for enhancer annotation.

**Claude follows up with:** `encode_get_facets(organ="pancreas")`

**Biosample breakdown (real facet counts):**
```
pancreas                                108 experiments
body of pancreas                         72 experiments
Panc1 (cell line)                        47 experiments
endocrine pancreas                       22 experiments
type B pancreatic cell                   15 experiments
islet of Langerhans                       3 experiments
```

**Practical strategy:** Broaden to bulk pancreas (108 experiments, full histone coverage)
and endocrine pancreas (22). The `type B pancreatic cell` entries are beta cells -- the
primary T2D-relevant cell type. Avoid Panc1 (ductal adenocarcinoma line). For a complete
islet atlas, supplement with Pasquali et al. chromatin maps (PMID: 24413736).

## Step 2: Build Your Regulatory Reference from ENCODE

**You ask Claude:**
> "Find H3K27ac ChIP-seq peaks for pancreas in GRCh38."

**Claude calls:** `encode_search_files(file_format="bed", target="H3K27ac", organ="pancreas", assembly="GRCh38")`

Claude returns BED narrowPeak files marking active enhancers and promoters. Use
`preferred_default=True` for the highest-confidence peak set. Key marks:

| Mark | What it marks | T2D relevance |
|------|--------------|---------------|
| H3K27ac | Active enhancers/promoters | Primary variant-to-enhancer signal |
| H3K4me1 | Poised and active enhancers | Broader set, includes primed elements |
| H3K4me3 | Active promoters | Links variants to target gene promoters |
| CTCF | Insulator / TAD boundaries | Defines enhancer-gene reach |

## Step 3: Cross-Reference with GWAS Catalog

**You ask Claude:**
> "What T2D-associated variants overlap with these pancreatic regulatory elements?"

**Claude uses the variant-annotation skill** to guide the intersection:

1. **Retrieve T2D GWAS associations** from the NHGRI-EBI GWAS Catalog
   (Sollis et al. 2023, PMID: 36350656). Filter for genome-wide significance (p < 5e-8).
2. **Expand to credible sets** using fine-mapping from Mahajan et al. 2018
   (PMID: 30297969) -- lead SNPs are rarely causal.
3. **Intersect with ENCODE enhancers:**
   ```bash
   bedtools intersect -a t2d_credible_sets.bed \
                      -b encode_pancreas_H3K27ac.bed \
                      -wa -wb > t2d_variants_in_enhancers.bed
   ```
4. **Annotate with chromatin state** using ChromHMM (Ernst & Kellis 2012,
   PMID: 22373907) to classify active enhancers, promoters, and repressed regions.

Over 90% of T2D GWAS variants are non-coding (Maurano et al. 2012, PMID: 22955828).
Without cell-type-specific regulatory annotations from ENCODE, you cannot determine
which have functional consequences.

## Step 4: Tissue Expression Context

**You ask Claude:**
> "What genes are expressed near these variants in pancreatic tissue?"

**Claude uses the disease-research skill** to guide eQTL integration:

1. **Query GTEx** (GTEx Consortium 2020, PMID: 32913098) for pancreas eQTLs.
   For each variant in an ENCODE enhancer, check for significant eQTLs
   (FDR < 0.05) within 1 Mb.
2. **Prioritize beta cell genes:** *INS*, *GCK*, *KCNJ11*, *ABCC8*,
   *SLC30A8*, *TCF7L2*, *HNF1A*.
3. **Islet-specific refinement.** GTEx pancreas mixes exocrine and endocrine.
   Compare against sorted beta cell RNA-seq (Ackermann et al. 2016,
   PMID: 27364731) or the Human Pancreas Analysis Program (HPAP).

**Caveat:** A variant near a gene does not prove it regulates that gene. Use
ENCODE Hi-C data (5 intact Hi-C experiments for pancreas) to identify chromatin
contacts between enhancers and promoters.

## Step 5: Motif Disruption Analysis

**You ask Claude:**
> "Could any of these variants disrupt transcription factor binding?"

**Claude uses the variant-annotation skill** to outline motif scanning:

1. **Scan against JASPAR** (Castro-Mondragon et al. 2022, PMID: 34850907)
   using FIMO or motifbreakR (Coetzee et al. 2015, PMID: 26272984).
2. **Prioritize islet-relevant TFs:**

   | TF | Role in islets | PMID |
   |----|---------------|------|
   | PDX1 | Master regulator of beta cell identity | 9856459 |
   | NKX6.1 | Beta cell maturation and insulin secretion | 22190676 |
   | MAFB | Alpha and beta cell differentiation | 17446529 |
   | FOXA2 | Endoderm and pancreas development | 15486300 |
   | NKX2.2 | Endocrine cell specification | 10393122 |
   | PAX6 | Endocrine lineage commitment | 12832481 |
   | TCF7L2 | Wnt signaling; strongest T2D GWAS signal | 21490949 |
   | RFX6 | Islet cell differentiation | 20299564 |

3. **Validate with ENCODE TF ChIP-seq.** Pancreas facets show CTCF (16),
   POLR2A (5), REST (3), and TCF7L2 (1) experiments. The TCF7L2 experiment
   is especially valuable given its status as the strongest T2D risk locus.

## Step 6: Population Frequency and Clinical Context

**You ask Claude:**
> "What are the population frequencies and clinical classifications?"

**Claude uses the disease-research skill** to guide annotation:

- **gnomAD** (Karczewski et al. 2020, PMID: 32461654) -- Most T2D variants are
  common (MAF > 5%). Population-stratified frequencies reveal ancestry-specific
  effects, e.g., *SLC30A8* differs between East Asian and European populations.
- **ClinVar** (Landrum et al. 2018, PMID: 30371827) -- Most T2D GWAS variants
  are benign or absent. ClinVar targets Mendelian disease, not complex trait
  risk. Monogenic diabetes genes (*GCK*, *HNF1A*, *KCNJ11*) have pathogenic
  entries, but these are distinct from common GWAS variants.
- **Open Targets** (Ochoa et al. 2023, PMID: 36399499) -- Integrated evidence
  scores aggregating GWAS, functional genomics, and literature.

## Putting It All Together

```
GWAS Catalog          What variants are associated with T2D?
    |
ENCODE enhancers      Which fall in active regulatory elements?
    |
GTEx eQTLs            Which genes do those elements regulate?
    |
JASPAR motifs         Do variants disrupt TF binding?
    |
gnomAD / ClinVar      What is the population and clinical context?
```

Each layer narrows the candidate list. Starting from hundreds of GWAS loci, you
arrive at variants that (a) sit in pancreas-active H3K27ac-marked enhancers,
(b) are eQTLs for islet-expressed genes, and (c) disrupt binding motifs for
pancreatic TFs. These are candidates for STARR-seq, MPRA, or CRISPR follow-up.

## Skills Demonstrated

- **search-encode** -- Finding pancreas/islet experiments and regulatory peak files
- **variant-annotation** -- Intersecting variants with regulatory elements
- **disease-research** -- Integrating GWAS, eQTL, and clinical databases

## Key References

| Database | Reference | PMID |
|----------|-----------|------|
| GWAS Catalog | Sollis et al. 2023, Nucleic Acids Res | 36350656 |
| GTEx | GTEx Consortium 2020, Science | 32913098 |
| JASPAR | Castro-Mondragon et al. 2022, Nucleic Acids Res | 34850907 |
| gnomAD | Karczewski et al. 2020, Nature | 32461654 |
| ClinVar | Landrum et al. 2018, Nucleic Acids Res | 30371827 |
| Open Targets | Ochoa et al. 2023, Nucleic Acids Res | 36399499 |
| ChromHMM | Ernst & Kellis 2012, Nat Methods | 22373907 |
| T2D fine-mapping | Mahajan et al. 2018, Nat Genet | 30297969 |
| Non-coding GWAS | Maurano et al. 2012, Science | 22955828 |

## What's Next

- [Motif & Regulatory](06-motif-and-regulatory.md) -- Deep dive into TF binding
  analysis with ENCODE ChIP-seq and motif databases
- [Cross-Reference & Integration](09-cross-reference-and-integration.md) -- Full
  multi-database workflow connecting ENCODE, PubMed, bioRxiv, and clinical trials
