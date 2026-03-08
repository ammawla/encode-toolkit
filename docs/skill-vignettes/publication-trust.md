# Publication Trust -- Checking Papers Before You Cite Them

> **Category:** Workflow | **Tools Used:** `get_article_metadata`, `search_articles`, `find_related_articles`, `convert_article_ids`, Consensus `search`

## What This Skill Does

Assesses the scientific integrity of a publication before you rely on its findings. Checks for formal retractions, corrections, expressions of concern, and -- critically -- informal contradictions where independent groups failed to reproduce key claims. Assigns a Trust Level from 1 (Compromised) to 5 (High confidence) so you can make an informed decision about whether to cite, build on, or discard a study.

## When to Use This

- You are about to cite a paper and want to confirm it has not been retracted or contradicted.
- A collaborator sends a paper that seems too good to be true and you want a reality check.
- You are building a pipeline on a published method and need to know it has been validated independently.

## Example Session

A scientist studying alpha-to-beta cell transdifferentiation in pancreatic islets encounters a 2016 Cell paper claiming artemisinins convert alpha cells to beta cells. Before citing it in a grant proposal, they run a trust assessment.

### Step 1: Retrieve Publication Metadata

```
get_article_metadata(pmids=["27984723"])
```

| Field | Value |
|---|---|
| Title | Artemisinins Target GABA Receptor Signaling and Impair Alpha Cell Identity |
| Journal | Cell |
| Year | 2016 |
| Senior Author | Kubicek S |
| Article Types | Journal Article |
| Retraction | None |

No retraction or expression of concern. Trust Level starts at 4 (Standard).

### Step 2: Search for Formal Integrity Markers

```
search_articles(query="27984723[PMID] AND (Retracted Publication[pt] OR Expression of Concern[pt])")
```

No results. The formal record is clean.

### Step 3: Search for Contradicting Publications

This is the most important step. Most problematic papers are never formally retracted -- they are contradicted by subsequent independent work.

```
search_articles(query="artemisinin alpha cell beta cell AND (\"fail to replicate\" OR \"does not\" OR \"unable to reproduce\" OR \"contradicts\")")
```

One hit: van der Meulen et al. 2017, Cell Metabolism -- a direct replication attempt by an independent group. Retrieve its metadata:

```
get_article_metadata(pmids=["28768169"])
```

| Field | Value |
|---|---|
| Title | Artemether Does Not Turn Alpha Cells into Beta Cells |
| Journal | Cell Metabolism |
| Year | 2017 |
| Senior Author | Huising MO |

The contradicting paper was published one year later by an independent lab using primary islet cells rather than the cell lines in the original study.

### Step 4: Evaluate the Contradiction

| Factor | Assessment |
|---|---|
| Independent lab | Yes -- different institution, different reagents |
| Model system | Primary cells in the contradiction vs. cell lines in the original (stronger model) |
| Specificity | Directly tests the same claim: alpha-to-beta conversion |
| Mechanism | Provides alternative explanation: artemether suppresses Ins2 expression and causes general dedifferentiation, not directed transdifferentiation |

### Step 5: Generate Trust Report

```
## Publication Trust Assessment

**Paper**: Artemisinins Target GABA Receptor Signaling and Impair Alpha Cell Identity (Cell, 2016)
**PMID**: 27984723 | **DOI**: 10.1016/j.cell.2016.11.010

### Trust Level: 2/5 -- Reliability Concerns

### Formal Markers
- Retraction: None
- Corrections: None
- Expression of Concern: None

### Contradicting Evidence
- van der Meulen et al. 2017, Cell Metabolism (PMID: 28768169)
  -- Direct replication by independent group found no alpha-to-beta conversion
  -- Primary islet cells showed artemether suppresses Ins2 100-fold
  -- Concluded the effect is general dedifferentiation, not directed transdifferentiation

### Recommendation
Do not cite as evidence for artemisinin-mediated transdifferentiation.
If referencing this work, cite both the original and the contradiction,
and note the discrepancy.
```

## Key Principles

- **Default trust is 4, not 5.** Absence of contradictions does not equal independent replication. A paper earns level 5 only when independent groups confirm the key findings.
- **Informal contradictions matter more than you think.** A direct replication failure in a peer-reviewed journal is a serious signal even without a retraction notice.
- **Reanalysis is the strongest contradiction.** When someone uses the original data and reaches different conclusions, methodology differences cannot explain the discrepancy (Baggerly & Coombes 2009).
- **Use measured language.** Report what the published record shows. Avoid terms like "fraud" or "fabrication" unless a formal investigation has concluded with those findings.
- **Trust assessments are living documents.** A paper at level 2 today could move to level 1 if retracted, or back to 3 if the contradiction is itself challenged.

## Related Skills

- **cite-encode** -- Integrates trust levels into citation lists, flagging compromised papers.
- **quality-assessment** -- Evaluates ENCODE experiment quality; complements publication quality.
- **data-provenance** -- Records trust assessments in the provenance chain for reproducibility.
- **disease-research** -- Flags when disease mechanisms depend on contradicted findings.

---

*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 43 skills for genomics research*
