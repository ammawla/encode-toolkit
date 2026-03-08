# Track Experiments: Building a Local Research Library

> Track ENCODE experiments locally, compare compatibility, and export
> your collection for collaborators -- all through natural conversation.

**Skill:** `track-experiments` | **Tools used:** `encode_track_experiment`, `encode_list_tracked`, `encode_compare_experiments`, `encode_export_data`

---

## Scenario

You are studying H3K4me3 and H3K27me3 across human pancreas tissue to map bivalent
promoters. You need to build a local collection of experiments, verify they are
compatible for combined analysis, and share the metadata table with your collaborator.

## Step 1: Track Your First Experiment

**You ask Claude:** "Track ENCSR133RZO -- it's H3K27me3 ChIP-seq on pancreas tissue."

**Claude calls:** `encode_track_experiment(accession="ENCSR133RZO", notes="H3K27me3 pancreas, bivalent promoter study")`

```json
{
  "status": "tracked",
  "accession": "ENCSR133RZO",
  "metadata_stored": {
    "assay_title": "Histone ChIP-seq",
    "target": "H3K27me3",
    "biosample_summary": "Homo sapiens pancreas tissue female child (16 years)",
    "organism": "Homo sapiens",
    "assembly": "GRCh38",
    "lab": "Bradley Bernstein, Broad"
  },
  "publications_found": 0,
  "pipelines_found": 1
}
```

The experiment is now in your local SQLite library. The `notes` field records your
research intent -- invaluable when revisiting the collection weeks later.

## Step 2: Track a Matching H3K4me3 Experiment

**You ask Claude:** "Now track ENCSR649YSX -- H3K4me3 on the same tissue type."

**Claude calls:** `encode_track_experiment(accession="ENCSR649YSX", notes="H3K4me3 pancreas, bivalent promoter study")`

```json
{"status": "tracked", "accession": "ENCSR649YSX",
 "metadata_stored": {"assay_title": "Histone ChIP-seq", "target": "H3K4me3",
   "biosample_summary": "Homo sapiens pancreas tissue female adult (51 years)",
   "organism": "Homo sapiens", "assembly": "GRCh38", "lab": "Bradley Bernstein, Broad"},
 "publications_found": 0, "pipelines_found": 1}
```

Your library now holds two experiments -- both human, GRCh38, same lab, but different
donor ages.

## Step 3: View Your Library

**You ask Claude:** "Show me all tracked experiments."

**Claude calls:** `encode_list_tracked()`

| Accession | Assay | Target | Biosample | Publications | Notes |
|-----------|-------|--------|-----------|:---:|-------|
| ENCSR133RZO | Histone ChIP-seq | H3K27me3 | pancreas tissue female child (16y) | 0 | H3K27me3 pancreas, bivalent promoter study |
| ENCSR649YSX | Histone ChIP-seq | H3K4me3 | pancreas tissue female adult (51y) | 0 | H3K4me3 pancreas, bivalent promoter study |

Two experiments tracked. Filter with `assay_title`, `organism`, or `organ` as your
collection grows.

## Step 4: Compare Before Combining

**You ask Claude:** "Are these two experiments compatible for combined analysis?"

**Claude calls:** `encode_compare_experiments(accession1="ENCSR133RZO", accession2="ENCSR649YSX")`

```json
{
  "verdict": "WARNINGS",
  "matching": {"organism": "Homo sapiens", "assembly": "GRCh38",
    "assay_title": "Histone ChIP-seq", "lab": "Bradley Bernstein, Broad"},
  "warnings": ["Different targets: H3K27me3 vs H3K4me3",
    "Different donor age: child (16 years) vs adult (51 years)"],
  "issues": [],
  "recommendation": "Compatible for cross-mark comparison. Target difference is expected for bivalent analysis."
}
```

Organism, assembly, assay, and lab all match -- the critical fields. The target difference
is intentional (you need both marks for bivalency). The age difference is worth noting
in your methods. Had organism or assembly mismatched, the verdict would be
**INCOMPATIBLE**.

## Step 5: Export for Collaborators

**You ask Claude:** "Export my tracked experiments as CSV so I can share them."

**Claude calls:** `encode_export_data(format="csv")`

```csv
accession,assay_title,target,biosample_summary,organism,assembly,lab,date_released,publications,derived_files,notes
ENCSR133RZO,Histone ChIP-seq,H3K27me3,"pancreas tissue female child (16 years)",Homo sapiens,GRCh38,"Bradley Bernstein, Broad",2021-06-24,0,0,"H3K27me3 pancreas, bivalent promoter study"
ENCSR649YSX,Histone ChIP-seq,H3K4me3,"pancreas tissue female adult (51 years)",Homo sapiens,GRCh38,"Bradley Bernstein, Broad",2020-11-18,0,0,"H3K4me3 pancreas, bivalent promoter study"
```

Your collaborator can open this in Excel, R (`read.csv`), or pandas (`pd.read_csv`).
TSV and JSON formats are also available.

## Best Practices

- **Always add notes** when tracking. They are the only field that records *why* you chose each experiment.
- **Compare before combining.** Mismatched assemblies produce silent errors in bedtools and deeptools. Run `encode_compare_experiments` first.
- **Export after every session.** A CSV snapshot protects against accidental database issues and provides a shareable record.
- **Track systematically.** When building a collection, track all related experiments in one session with consistent note prefixes for easy filtering.

---

*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 43 skills for genomics research*
