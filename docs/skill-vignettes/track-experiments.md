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
  "tracking": {
    "accession": "ENCSR133RZO",
    "action": "tracked"
  },
  "auto_linked_references": [
    {"type": "geo_accession", "id": "GSE187091"}
  ],
  "publications_found": 0,
  "publications": [],
  "pipelines_found": 1,
  "pipelines": [
    {
      "title": "Histone ChIP-seq 2 (unreplicated)",
      "version": "1.7.1",
      "software": [{"name": "bowtie2", "version": "2.3.4.3"}],
      "status": "released"
    }
  ]
}
```

The experiment is now in your local SQLite library -- `action` is `"tracked"` on the first
insert and `"updated"` if you track it again. The response confirms what was fetched, not
what was stored: your `notes` and the experiment metadata go straight into the database.
Read them back with `encode_list_tracked`. The note records your research intent --
invaluable when revisiting the collection weeks later.

## Step 2: Track a Matching H3K4me3 Experiment

**You ask Claude:** "Now track ENCSR649YSX -- H3K4me3 on the same tissue type."

**Claude calls:** `encode_track_experiment(accession="ENCSR649YSX", notes="H3K4me3 pancreas, bivalent promoter study")`

```json
{"tracking": {"accession": "ENCSR649YSX", "action": "tracked"},
 "publications_found": 0, "publications": [],
 "pipelines_found": 1,
 "pipelines": [{"title": "Histone ChIP-seq 2 (unreplicated)", "version": "1.7.1",
   "software": [{"name": "bowtie2", "version": "2.3.4.3"}], "status": "released"}]}
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
  "experiment_1": {
    "accession": "ENCSR133RZO",
    "assay": "Histone ChIP-seq",
    "biosample": "Homo sapiens pancreas tissue female child (16 years)"
  },
  "experiment_2": {
    "accession": "ENCSR649YSX",
    "assay": "Histone ChIP-seq",
    "biosample": "Homo sapiens pancreas tissue female adult (51 years)"
  },
  "verdict": "COMPATIBLE_WITH_CAVEATS",
  "recommendation": "These experiments can be compared, but the warnings should be addressed in your analysis.",
  "compatible_aspects": [
    "Same organism: Homo sapiens",
    "Same assembly: GRCh38",
    "Same assay: Histone ChIP-seq",
    "Same biosample type: tissue",
    "Same organ: pancreas",
    "Same lab: Bradley Bernstein, Broad"
  ],
  "issues": [],
  "warnings": ["Different targets: H3K27me3 vs H3K4me3."]
}
```

Organism, assembly, assay, biosample type, organ, and lab all match -- the critical fields.
The one warning is the target difference, which is intentional (you need both marks for
bivalency). Donor age is not compared, so note it in your methods yourself. Warnings alone
give `COMPATIBLE_WITH_CAVEATS`; had organism or assembly mismatched, that would be an entry
in `issues` and the verdict would be `NOT_COMPATIBLE`. With neither, it is
`FULLY_COMPATIBLE`.

## Step 5: Export for Collaborators

**You ask Claude:** "Export my tracked experiments as CSV so I can share them."

**Claude calls:** `encode_export_data(format="csv")`

```csv
accession,assay_title,target,organism,organ,biosample_type,biosample_summary,lab,assembly,status,date_released,replication_type,life_stage,publication_count,pmids,derived_file_count,external_reference_count
ENCSR133RZO,Histone ChIP-seq,H3K27me3,Homo sapiens,pancreas,tissue,"Homo sapiens pancreas tissue female child (16 years)","Bradley Bernstein, Broad",GRCh38,released,2021-06-24,unreplicated,child 16 years,0,,0,1
ENCSR649YSX,Histone ChIP-seq,H3K4me3,Homo sapiens,pancreas,tissue,"Homo sapiens pancreas tissue female adult (51 years)","Bradley Bernstein, Broad",GRCh38,released,2020-11-18,unreplicated,adult 51 years,0,,0,1
```

Your collaborator can open this in Excel, R (`read.csv`), or pandas (`pd.read_csv`).
The CSV and TSV forms always carry these 17 columns; your `notes` are not among them --
export with `format="json"` when you need them, together with `description`, `award`,
`url`, `tracked_at` and `updated_at`.

## Best Practices

- **Always add notes** when tracking. They are the only field that records *why* you chose each experiment.
- **Compare before combining.** Mismatched assemblies produce silent errors in bedtools and deeptools. Run `encode_compare_experiments` first.
- **Export after every session.** A CSV snapshot protects against accidental database issues and provides a shareable record.
- **Track systematically.** When building a collection, track all related experiments in one session with consistent note prefixes for easy filtering.

---

*Part of the [ENCODE Toolkit](https://github.com/ammawla/encode-toolkit) -- 47 skills for genomics research*
