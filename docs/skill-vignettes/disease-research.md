# Disease Research -- T2D GWAS Variants to Islet Enhancers to Drug Targets

> **Category:** Workflows | **Tools Used:** `encode_search_experiments`, `encode_get_facets`, `encode_list_files`, `encode_track_experiment`, `encode_log_derived_file`, `encode_link_reference`, `encode_get_citations` | **External APIs:** Open Targets GraphQL, ClinicalTrials.gov, GWAS Catalog, PubMed

## What This Skill Does

Guides disease-focused research using ENCODE functional genomics data. Connects GWAS variants to tissue-specific regulatory elements, links disrupted enhancers to target genes, cross-references targets with drug databases and clinical trials, and documents the full provenance chain.

## When to Use This

- You have GWAS loci and want to trace variants through regulatory elements to candidate drug targets.
- You need to build a multi-layer disease regulatory model connecting ENCODE data to clinical applications.

## Example Session

### Scientist's Request

> "I'm researching type 2 diabetes mechanisms. Walk me through connecting T2D GWAS variants to functional regulatory elements in pancreatic islets, identifying the target genes, and finding any drugs or clinical trials targeting those genes."

### Step 1: Map T2D to Relevant Tissue and Survey ENCODE Coverage

Over 90% of GWAS variants fall in non-coding regions (Maurano et al. 2012). T2D risk acts primarily through pancreatic islet beta cells, making tissue mapping the most important decision.

```
encode_get_facets(organ="pancreas")
```

Pancreas has coverage across key assays: H3K27ac ChIP-seq, ATAC-seq, H3K4me3 ChIP-seq, and Hi-C. Sufficient for a multi-layer regulatory model.

### Step 2: Collect ENCODE Regulatory Data for Islets
Pull enhancer marks, accessibility, and 3D contact data:

```
encode_search_experiments(assay_title="Histone ChIP-seq", target="H3K27ac", organ="pancreas", biosample_type="tissue")
encode_search_experiments(assay_title="ATAC-seq", organ="pancreas", biosample_type="tissue")
encode_search_experiments(assay_title="Hi-C", organ="pancreas")
```

From the top H3K27ac experiment, retrieve preferred peak files:

```
encode_list_files(experiment_accession="ENCSR976DGM", file_format="bed",
    output_type="IDR thresholded peaks", assembly="GRCh38", preferred_default=True)
```

### Step 3: Overlay T2D GWAS Variants with Islet Enhancers
Expand GWAS Catalog T2D hits (EFO_0001360) to LD proxies (r2 > 0.8) and intersect with islet H3K27ac peaks:

```bash
bedtools intersect -a t2d_ld_expanded.bed -b islet_h3k27ac_peaks.bed -wa -wb > t2d_in_islet_enhancers.bed
```

| Lead SNP | Locus | In Islet Enhancer | In Islet ATAC Peak | Regulatory Interpretation |
|---|---|---|---|---|
| rs7903146 | TCF7L2 | Yes -- islet-specific | Yes | Disrupts TCF/LEF motif in active enhancer |
| rs10830963 | MTNR1B | Yes | Yes | Melatonin receptor enhancer, beta cell-specific |
| rs5219 | KCNJ11 | No | No | Coding variant (E23K) -- not regulatory |

The rs7903146 and rs10830963 variants overlap islet-specific enhancers, marking them as regulatory candidates. The KCNJ11 coding variant falls outside regulatory elements as expected.

### Step 4: Link Enhancers to Target Genes

Confirm enhancer-promoter contacts using ENCODE Hi-C and the ABC model (Nasser et al. 2021):

```
encode_search_experiments(assay_title="Hi-C", organ="pancreas")
```

The ABC model confirms the rs7903146-containing enhancer contacts the TCF7L2 promoter and the rs10830963 enhancer links to MTNR1B -- bridging non-coding variants to actionable gene targets.

### Step 5: Query Open Targets for Drug and Trial Information

```
search_entities(query_strings=["TCF7L2", "MTNR1B"])
query_open_targets_graphql(
    query_string="query target($ensemblId: String!) { target(ensemblId: $ensemblId) { approvedSymbol tractability { label modality value } knownDrugs { count rows { drug { name } phase mechanismOfAction } } } }",
    variables={"ensemblId": "ENSG00000148737"}
)
```

Then cross-reference with active clinical trials:

```
search_trials(condition="type 2 diabetes", status=["RECRUITING"], phase=["PHASE2", "PHASE3"])
```

### Step 6: Log Provenance

```
encode_track_experiment(accession="ENCSR976DGM", notes="T2D disease research -- islet H3K27ac for GWAS overlay")
encode_log_derived_file(
    file_path="/data/t2d_regulatory_model.tsv",
    source_accessions=["ENCSR976DGM"],
    description="T2D GWAS variants in islet enhancers linked to target genes",
    tool_used="bedtools intersect + ABC model + Open Targets",
    parameters="GRCh38, IDR thresholded peaks, LD r2>0.8, ABC score>0.015"
)
encode_link_reference(experiment_accession="ENCSR976DGM", reference_type="other",
    reference_id="EFO_0001360", description="GWAS Catalog T2D trait")
```

## Key Principles

- **Tissue mapping is the highest-impact decision.** T2D heritability is enriched 15x in islet enhancers (Finucane et al. 2015). Using wrong-tissue data misses the signal entirely.
- **Lead SNPs are not causal variants.** Always expand to LD proxies or fine-mapped credible sets before annotating.
- **Regulatory overlap is not proof of causation.** Proof requires perturbation (CRISPRi/MPRA). State the evidence level.
- **Orthogonal evidence strengthens targets.** Genes with both GWAS association AND ENCODE regulatory disruption are the strongest candidates.

## Related Skills

- **gwas-catalog** -- Retrieve trait-associated variants from the NHGRI-EBI GWAS Catalog.
- **variant-annotation** -- Detailed per-variant functional annotation with ENCODE regulatory elements.
- **regulatory-elements** -- Classify the enhancer, promoter, or insulator harboring a disease variant.
- **clinvar-annotation** -- Check clinical significance classifications for disease-associated variants.
- **gtex-expression** -- Validate target genes with tissue expression and eQTL colocalization.
- **publication-trust** -- Verify literature claims backing the analytical framework.

---

*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 43 skills for genomics research*
