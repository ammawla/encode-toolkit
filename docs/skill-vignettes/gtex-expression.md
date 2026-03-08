# GTEx Expression -- Tissue Expression Context for ENCODE Regulatory Data

> **Category:** External Databases | **Tools Used:** GTEx Portal REST API v2, `encode_search_experiments`, `encode_get_facets`

## What This Skill Does

Integrates GTEx tissue-specific gene expression data with ENCODE regulatory element catalogs. Queries the GTEx Portal REST API v2 (`gtexportal.org/api/v2`, no authentication required) to retrieve median TPM values across 54 human tissues from ~1,000 donors, then cross-references expression patterns with ENCODE enhancers, promoters, and accessibility data.

## When to Use This

- You found an active enhancer (H3K27ac+) in ENCODE and need to confirm the nearby gene is expressed in the matching tissue.
- You want to identify tissue-enriched genes to guide ENCODE biosample selection for a new analysis.
- You need to validate that differential regulatory elements across tissues correspond to differential gene expression.

## Example Session

### Scientist's Request

> "I study pancreatic islet transcription factors. Check GTEx expression of INS, GCG, SST, and PDX1 across tissues. Then show me what ENCODE regulatory data exists in pancreas to cross-reference."

### Step 1: Query GTEx for Tissue-Specific Expression

Query the GTEx gene expression endpoint for each gene. GTEx requires Ensembl gene IDs, so resolve symbols first via the reference endpoint.

```python
import requests

genes = {
    "INS":  "ENSG00000254647",
    "GCG":  "ENSG00000115263",
    "SST":  "ENSG00000157005",
    "PDX1": "ENSG00000139515"
}

for symbol, ensembl_id in genes.items():
    resp = requests.get("https://gtexportal.org/api/v2/expression/geneExpression",
                        params={"geneId": ensembl_id, "datasetId": "gtex_v8"})
    data = resp.json()["data"]
    top = sorted(data, key=lambda x: x["median"], reverse=True)[:3]
    print(f"\n{symbol} ({ensembl_id}) -- top 3 tissues:")
    for entry in top:
        print(f"  {entry['tissueSiteDetailId']}: {entry['median']:.1f} TPM")
```

### Step 2: Interpret Expression Patterns

| Gene | Top Tissue | TPM | 2nd Tissue | TPM | Expressed in >1 tissue? |
|------|-----------|-----|-----------|-----|------------------------|
| INS  | Pancreas  | 387.2 | Minor_Salivary_Gland | 0.4 | No (tissue-specific, tau > 0.95) |
| GCG  | Pancreas  | 98.6 | Small_Intestine_Terminal_Ileum | 42.3 | Yes (gut L-cells produce GLP-1) |
| SST  | Pancreas  | 48.1 | Brain_Hypothalamus | 31.7 | Yes (neuroendocrine) |
| PDX1 | Pancreas  | 19.4 | Small_Intestine_Terminal_Ileum | 3.2 | Weak secondary expression |

INS is almost exclusively pancreatic -- any regulatory element near INS in a non-pancreatic tissue warrants skepticism. GCG and SST have biologically meaningful expression outside pancreas, so enhancers near these genes in gut or brain are expected. PDX1 is a transcription factor expressed at moderate levels; its regulatory elements should show active promoter marks (H3K4me3) in islets.

### Step 3: Cross-Reference with ENCODE Regulatory Data

Check what ENCODE data exists for pancreas to pair with GTEx expression.

```
encode_get_facets(organ="pancreas")
```

Available pancreas data includes Histone ChIP-seq (38 experiments), ATAC-seq (6), RNA-seq (12), and DNase-seq (4). This is sufficient to build a regulatory profile around each gene.

```
encode_search_experiments(
    assay_title="Histone ChIP-seq", target="H3K27ac",
    organ="pancreas", biosample_type="tissue", status="released"
)
```

### Step 4: Evaluate Concordance

Apply the validation logic: active ENCODE enhancer + GTEx expression > 1 TPM = concordant.

| Gene | Pancreas TPM | ENCODE H3K27ac near locus? | ENCODE ATAC-seq open? | Verdict |
|------|-------------|---------------------------|----------------------|---------|
| INS  | 387.2       | Strong peaks at promoter + upstream enhancers | Open chromatin confirmed | Concordant -- active regulatory landscape matches high expression |
| GCG  | 98.6        | Peaks at promoter, fewer enhancers than INS | Open at promoter | Concordant -- fewer enhancers consistent with lower expression |
| SST  | 48.1        | Moderate peaks | Accessible | Concordant |
| PDX1 | 19.4        | Active promoter, distal enhancers | Open | Concordant -- TF expression is typically lower than hormone genes |

All four genes show concordance between GTEx expression and ENCODE regulatory activity in pancreas. If any gene showed high GTEx expression but no ENCODE enhancer signal, it would suggest either incomplete ENCODE coverage or promoter-driven regulation (check H3K4me3 instead of H3K27ac).

## Key Interpretation Notes

- **1 TPM threshold**: Below this, expression is difficult to distinguish from noise in bulk RNA-seq. However, genes expressed only in rare cell types (e.g., delta cells are ~5% of islets) may appear low in bulk GTEx but be highly expressed at single-cell resolution. Use the `cellxgene-context` skill for cell-type deconvolution.
- **Tissue mapping**: GTEx "Pancreas" is whole pancreas (~95% exocrine). Islet genes like INS still dominate because beta cells express INS at extremely high levels per cell. Always note this caveat when reporting bulk TPM for endocrine genes.
- **eQTLs**: Query `https://gtexportal.org/api/v2/eqtl/singleTissueEqtl` with the gene and tissue to find variants that regulate expression. Intersect eQTL positions with ENCODE peak files for functional variant prioritization.

## Related Skills

- **cellxgene-context** -- Single-cell expression when GTEx bulk resolution is insufficient.
- **regulatory-elements** -- Characterize the ENCODE enhancers and promoters near expressed genes.
- **variant-annotation** -- Combine GTEx eQTLs with ENCODE peaks for variant prioritization.
- **cross-reference** -- Link ENCODE experiments to GTEx, GEO, and other external databases.
- **ensembl-annotation** -- Convert gene symbols to Ensembl IDs required by GTEx API.

---

*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 43 skills for genomics research*
