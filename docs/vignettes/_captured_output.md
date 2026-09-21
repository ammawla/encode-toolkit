# Captured ENCODE API Output for Vignettes

> Generated: 2026-03-07
> Source: Live ENCODE MCP tool calls against encodeproject.org
> Purpose: Embed in vignette documentation as real-world examples
>
> Revised: sections 1, 3, 5 and 6 were captured from an earlier build whose responses no
> longer match what the tools return. They have been corrected against the current server:
> the search response now carries the labels, organism, organ, biosample classification and
> assemblies the client asks ENCODE to embed, plus `has_more` / `next_offset`; the assay list
> in section 6 is the server's own vocabulary verbatim. Counts and accessions are unchanged.

---

## 1. Search Experiments -- Human Pancreas Histone ChIP-seq

**Tool:** `encode_search_experiments`
**Parameters:**
```json
{
  "assay_title": "Histone ChIP-seq",
  "organ": "pancreas",
  "limit": 3
}
```

**Response:**
```json
{
  "results": [
    {
      "accession": "ENCSR133RZO",
      "assay_title": "Histone ChIP-seq",
      "target": "H3K27me3",
      "biosample_summary": "Homo sapiens pancreas tissue female child (16 years)",
      "organism": "Homo sapiens",
      "organ": "pancreas",
      "biosample_type": "tissue",
      "status": "released",
      "date_released": "2021-06-24",
      "description": "H3K27me3 ChIP-seq on pancreas tissue female child (16 years)",
      "lab": "Bradley Bernstein, Broad",
      "file_count": 14,
      "replication_type": "unreplicated",
      "life_stage": "child 16 years",
      "assembly": ["GRCh38"],
      "audit_error_count": 0,
      "audit_not_compliant_count": 0,
      "audit_warning_count": 8,
      "audit_internal_action_count": 2,
      "dbxrefs": [
        "GEO:GSE187091"
      ],
      "url": "https://www.encodeproject.org/experiments/ENCSR133RZO/"
    },
    {
      "accession": "ENCSR511LIV",
      "assay_title": "Histone ChIP-seq",
      "target": "H3K27me3",
      "biosample_summary": "Homo sapiens pancreas tissue female adult (61 years)",
      "organism": "Homo sapiens",
      "organ": "pancreas",
      "biosample_type": "tissue",
      "status": "released",
      "date_released": "2021-06-24",
      "description": "H3K27me3 ChIP-seq on pancreas tissue female adult (61 years)",
      "lab": "Bradley Bernstein, Broad",
      "file_count": 14,
      "replication_type": "unreplicated",
      "life_stage": "adult 61 years",
      "assembly": ["GRCh38"],
      "audit_error_count": 0,
      "audit_not_compliant_count": 0,
      "audit_warning_count": 8,
      "audit_internal_action_count": 0,
      "dbxrefs": [
        "GEO:GSE187520"
      ],
      "url": "https://www.encodeproject.org/experiments/ENCSR511LIV/"
    },
    {
      "accession": "ENCSR368EPJ",
      "assay_title": "Histone ChIP-seq",
      "target": "H3K9me3",
      "biosample_summary": "Homo sapiens pancreas tissue female adult (59 years)",
      "organism": "Homo sapiens",
      "organ": "pancreas",
      "biosample_type": "tissue",
      "status": "released",
      "date_released": "2021-06-24",
      "description": "H3K9me3 ChIP-seq on pancreas tissue female adult (59 years)",
      "lab": "Bradley Bernstein, Broad",
      "file_count": 18,
      "replication_type": "unreplicated",
      "life_stage": "adult 59 years",
      "assembly": ["GRCh38"],
      "audit_error_count": 0,
      "audit_not_compliant_count": 0,
      "audit_warning_count": 12,
      "audit_internal_action_count": 0,
      "dbxrefs": [
        "GEO:GSE187290"
      ],
      "url": "https://www.encodeproject.org/experiments/ENCSR368EPJ/"
    }
  ],
  "total": 73,
  "limit": 3,
  "offset": 0,
  "has_more": true,
  "next_offset": 3
}
```

---

## 2. Get Facets -- What Assays Exist for Pancreas

**Tool:** `encode_get_facets`
**Parameters:**
```json
{
  "organ": "pancreas"
}
```

**Response (trimmed to key facets):**
```json
{
  "assay_title": [
    { "term": "Histone ChIP-seq", "count": 73 },
    { "term": "DNase-seq", "count": 31 },
    { "term": "Control ChIP-seq", "count": 28 },
    { "term": "TF ChIP-seq", "count": 25 },
    { "term": "snATAC-seq", "count": 17 },
    { "term": "Mint-ChIP-seq", "count": 12 },
    { "term": "total RNA-seq", "count": 11 },
    { "term": "ATAC-seq", "count": 10 },
    { "term": "microRNA-seq", "count": 9 },
    { "term": "DNAme array", "count": 8 },
    { "term": "PRO-cap", "count": 8 },
    { "term": "polyA plus RNA-seq", "count": 7 },
    { "term": "snRNA-seq", "count": 6 },
    { "term": "RRBS", "count": 5 },
    { "term": "WGBS", "count": 5 },
    { "term": "intact Hi-C", "count": 5 },
    { "term": "RNA microarray", "count": 3 },
    { "term": "genotyping array", "count": 3 },
    { "term": "long read RNA-seq", "count": 3 },
    { "term": "Bru-seq", "count": 2 },
    { "term": "BruChase-seq", "count": 2 },
    { "term": "ChIA-PET", "count": 2 },
    { "term": "Control Mint-ChIP-seq", "count": 2 },
    { "term": "FAIRE-seq", "count": 2 },
    { "term": "RAMPAGE", "count": 2 },
    { "term": "microRNA counts", "count": 2 },
    { "term": "small RNA-seq", "count": 2 },
    { "term": "BruUV-seq", "count": 1 },
    { "term": "WGS", "count": 1 },
    { "term": "in situ Hi-C", "count": 1 }
  ],
  "target.label": [
    { "term": "CTCF", "count": 16 },
    { "term": "H3K4me3", "count": 16 },
    { "term": "H3K27ac", "count": 15 },
    { "term": "H3K27me3", "count": 14 },
    { "term": "H3K9me3", "count": 14 },
    { "term": "H3K4me1", "count": 13 },
    { "term": "H3K36me3", "count": 12 },
    { "term": "POLR2A", "count": 5 },
    { "term": "REST", "count": 3 },
    { "term": "H3K9ac", "count": 1 },
    { "term": "POLR2AphosphoS5", "count": 1 },
    { "term": "SIN3A", "count": 1 },
    { "term": "TCF7L2", "count": 1 }
  ],
  "biosample_ontology.classification": [
    { "term": "tissue", "count": 200 },
    { "term": "cell line", "count": 51 },
    { "term": "in vitro differentiated cells", "count": 32 },
    { "term": "organoid", "count": 5 }
  ],
  "biosample_ontology.term_name": [
    { "term": "pancreas", "count": 108 },
    { "term": "body of pancreas", "count": 72 },
    { "term": "Panc1", "count": 47 },
    { "term": "endocrine pancreas", "count": 22 },
    { "term": "progenitor cell of endocrine pancreas", "count": 15 },
    { "term": "type B pancreatic cell", "count": 15 },
    { "term": "islet of Langerhans", "count": 3 },
    { "term": "8988T", "count": 2 },
    { "term": "HPDE6-E6E7", "count": 2 },
    { "term": "islet precursor cell", "count": 2 }
  ],
  "replication_type": [
    { "term": "unreplicated", "count": 211 },
    { "term": "isogenic", "count": 75 },
    { "term": "anisogenic", "count": 2 }
  ],
  "lab.title": [
    { "term": "Bradley Bernstein, Broad", "count": 82 },
    { "term": "Michael Snyder, Stanford", "count": 47 },
    { "term": "John Stamatoyannopoulos, UW", "count": 30 },
    { "term": "Richard Myers, HAIB", "count": 26 },
    { "term": "Bing Ren, UCSD", "count": 18 },
    { "term": "Joseph Costello, UCSF", "count": 14 },
    { "term": "Ali Mortazavi, UCI", "count": 12 },
    { "term": "Barbara Wold, Caltech", "count": 9 },
    { "term": "Haiyuan Yu, Cornell", "count": 8 },
    { "term": "Peggy Farnham, USC", "count": 8 }
  ],
  "assembly": [
    { "term": "GRCh38", "count": 262 },
    { "term": "hg19", "count": 118 },
    { "term": "mm10", "count": 1 }
  ]
}
```

**Full facets response** also includes: `assay_slims`, `status`, `perturbed`, `target.investigated_as`, `biosample_ontology.organ_slims`, `biosample_ontology.cell_slims`, `biosample_ontology.system_slims`, `replicates.library.biosample.life_stage`, `replicates.library.biosample.sex`, `control_type`, `award.project`, `award.rfa`, `files.file_type`, `files.platform.term_name`, `files.run_type`, `files.read_length`, `date_released`, `audit.*` categories. Total pancreas experiments: **288**.

---

## 3. Get Experiment Details -- ENCSR133RZO

**Tool:** `encode_get_experiment`
**Parameters:**
```json
{
  "accession": "ENCSR133RZO"
}
```

**Response:**
```json
{
  "accession": "ENCSR133RZO",
  "assay_title": "Histone ChIP-seq",
  "assay_term_name": "ChIP-seq",
  "target": "H3K27me3",
  "biosample_summary": "Homo sapiens pancreas tissue female child (16 years)",
  "description": "H3K27me3 ChIP-seq on pancreas tissue female child (16 years)",
  "status": "released",
  "date_released": "2021-06-24",
  "lab": "Bradley Bernstein, Broad",
  "award": "ENCODE",
  "organism": "Homo sapiens",
  "organ": "pancreas",
  "biosample_type": "tissue",
  "life_stage": "child 16 years",
  "replication_type": "unreplicated",
  "assembly": ["GRCh38"],
  "bio_replicate_count": 1,
  "tech_replicate_count": 2,
  "possible_controls": [
    "ENCSR618UQQ"
  ],
  "related_series": [],
  "documents": [
    "/documents/75bad2f5-a924-40fe-9c48-ed322649bc31/",
    "/documents/be2a0f12-af38-430c-8f2d-57953baab5f5/",
    "/documents/ceb000f0-e354-4138-967f-f4314b8c5d98/",
    "/documents/bc380aee-992d-4c64-8508-587937f4ab35/",
    "/documents/8fe184e1-e3f5-4acf-b7aa-188af5a3f3b4/"
  ],
  "url": "https://www.encodeproject.org/experiments/ENCSR133RZO/",
  "files": [
    {
      "accession": "ENCFF763GUV",
      "file_format": "bam",
      "file_type": "bam",
      "output_type": "unfiltered alignments",
      "output_category": "alignment",
      "file_size": 4221319561,
      "file_size_human": "3.9 GB",
      "assembly": "GRCh38",
      "biological_replicates": [1],
      "technical_replicates": ["1_1", "1_2"],
      "status": "released",
      "download_url": "https://www.encodeproject.org/files/ENCFF763GUV/@@download/ENCFF763GUV.bam",
      "s3_uri": "s3://encode-public/2021/06/23/b4d87e15-8753-4004-b198-2644e08b8363/ENCFF763GUV.bam",
      "md5sum": "934009f4ab48e93da772b74a72d4c123",
      "experiment_accession": "ENCSR133RZO",
      "experiment_assay": "Histone ChIP-seq",
      "biosample_summary": "",
      "preferred_default": false,
      "date_created": "2021-06-23T11:03:59.081109+00:00"
    },
    {
      "accession": "ENCFF977UZL",
      "file_format": "bam",
      "file_type": "bam",
      "output_type": "alignments",
      "output_category": "alignment",
      "file_size": 3546672634,
      "file_size_human": "3.3 GB",
      "assembly": "GRCh38",
      "biological_replicates": [1],
      "technical_replicates": ["1_1", "1_2"],
      "status": "released",
      "download_url": "https://www.encodeproject.org/files/ENCFF977UZL/@@download/ENCFF977UZL.bam",
      "s3_uri": "s3://encode-public/2021/06/23/a4316be1-91b0-452e-b106-174fbfb8dc9e/ENCFF977UZL.bam",
      "md5sum": "3b311789578760eb2db1cc318ce1dca2",
      "experiment_accession": "ENCSR133RZO",
      "experiment_assay": "Histone ChIP-seq",
      "biosample_summary": "",
      "preferred_default": false,
      "date_created": "2021-06-23T11:04:03.351064+00:00"
    },
    {
      "accession": "ENCFF199LSM",
      "file_format": "bigBed",
      "file_type": "bigBed narrowPeak",
      "output_type": "pseudoreplicated peaks",
      "output_category": "annotation",
      "file_size": 183334,
      "file_size_human": "179.0 KB",
      "assembly": "GRCh38",
      "biological_replicates": [1],
      "technical_replicates": ["1_1", "1_2"],
      "status": "released",
      "download_url": "https://www.encodeproject.org/files/ENCFF199LSM/@@download/ENCFF199LSM.bigBed",
      "s3_uri": "s3://encode-public/2021/06/23/a4891231-ed54-494a-b833-c6bca0c2b62f/ENCFF199LSM.bigBed",
      "md5sum": "fdf1d8738052f17edf5d4ad1a4220caf",
      "experiment_accession": "ENCSR133RZO",
      "experiment_assay": "Histone ChIP-seq",
      "biosample_summary": "",
      "preferred_default": true,
      "date_created": "2021-06-23T11:04:13.836410+00:00"
    },
    {
      "accession": "ENCFF635JIA",
      "file_format": "bed",
      "file_type": "bed narrowPeak",
      "output_type": "pseudoreplicated peaks",
      "output_category": "annotation",
      "file_size": 40482,
      "file_size_human": "39.5 KB",
      "assembly": "GRCh38",
      "biological_replicates": [1],
      "technical_replicates": ["1_1", "1_2"],
      "status": "released",
      "download_url": "https://www.encodeproject.org/files/ENCFF635JIA/@@download/ENCFF635JIA.bed.gz",
      "s3_uri": "s3://encode-public/2021/06/23/c5d28a48-3c7c-4b0f-978c-0ab0ec5c6068/ENCFF635JIA.bed.gz",
      "md5sum": "2a41c04233d7ba1cac7b73b912161d50",
      "experiment_accession": "ENCSR133RZO",
      "experiment_assay": "Histone ChIP-seq",
      "biosample_summary": "",
      "preferred_default": true,
      "date_created": "2021-06-23T11:04:10.999047+00:00"
    },
    {
      "accession": "ENCFF757TPV",
      "file_format": "fastq",
      "file_type": "fastq",
      "output_type": "reads",
      "output_category": "raw data",
      "file_size": 520459788,
      "file_size_human": "496.3 MB",
      "assembly": "",
      "biological_replicates": [1],
      "technical_replicates": ["1_1"],
      "status": "released",
      "download_url": "https://www.encodeproject.org/files/ENCFF757TPV/@@download/ENCFF757TPV.fastq.gz",
      "s3_uri": "s3://encode-public/2021/04/30/9d0c3f2e-6f1a-4b6d-9a3e-2f0c1d7b5e44/ENCFF757TPV.fastq.gz",
      "md5sum": "b639731572f81990f3e8cfc96c65c626",
      "experiment_accession": "ENCSR133RZO",
      "experiment_assay": "Histone ChIP-seq",
      "biosample_summary": "",
      "preferred_default": false,
      "date_created": "2021-04-30T04:42:33.808210+00:00"
    },
    {
      "accession": "ENCFF186PZN",
      "file_format": "bigWig",
      "file_type": "bigWig",
      "output_type": "fold change over control",
      "output_category": "signal",
      "file_size": 1325853979,
      "file_size_human": "1.2 GB",
      "assembly": "GRCh38",
      "biological_replicates": [1],
      "technical_replicates": ["1_1", "1_2"],
      "status": "released",
      "download_url": "https://www.encodeproject.org/files/ENCFF186PZN/@@download/ENCFF186PZN.bigWig",
      "s3_uri": "s3://encode-public/2021/06/23/1f3a9c07-2b8e-4d55-90c1-7a6b4e2f8d10/ENCFF186PZN.bigWig",
      "md5sum": "a735b39e5a074c39a42db7299767a444",
      "experiment_accession": "ENCSR133RZO",
      "experiment_assay": "Histone ChIP-seq",
      "biosample_summary": "",
      "preferred_default": false,
      "date_created": "2021-06-23T11:04:07.731630+00:00"
    },
    {
      "accession": "ENCFF387ALH",
      "file_format": "bigWig",
      "file_type": "bigWig",
      "output_type": "signal p-value",
      "output_category": "signal",
      "file_size": 1239311158,
      "file_size_human": "1.2 GB",
      "assembly": "GRCh38",
      "biological_replicates": [1],
      "technical_replicates": ["1_1", "1_2"],
      "status": "released",
      "download_url": "https://www.encodeproject.org/files/ENCFF387ALH/@@download/ENCFF387ALH.bigWig",
      "s3_uri": "s3://encode-public/2021/06/23/6c81b4ad-05f7-4e39-8b2a-c94d3e1f7a62/ENCFF387ALH.bigWig",
      "md5sum": "2c8ec6977bb98c2909dc6f02edfbf676",
      "experiment_accession": "ENCSR133RZO",
      "experiment_assay": "Histone ChIP-seq",
      "biosample_summary": "",
      "preferred_default": true,
      "date_created": "2021-06-23T11:04:07.203960+00:00"
    },
    {
      "accession": "ENCFF388RZD",
      "file_format": "fastq",
      "output_type": "reads",
      "file_size_human": "472.4 MB",
      "preferred_default": false,
      "...": "..."
    },
    {
      "accession": "ENCFF208TEX",
      "file_format": "fastq",
      "output_type": "reads",
      "file_size_human": "509.1 MB",
      "preferred_default": false,
      "...": "..."
    },
    {
      "accession": "ENCFF161KCS",
      "file_format": "fastq",
      "output_type": "reads",
      "file_size_human": "503.7 MB",
      "preferred_default": false,
      "...": "..."
    },
    {
      "accession": "ENCFF867QKO",
      "file_format": "fastq",
      "output_type": "reads",
      "file_size_human": "545.8 MB",
      "preferred_default": false,
      "...": "..."
    },
    {
      "accession": "ENCFF365MQX",
      "file_format": "fastq",
      "output_type": "reads",
      "file_size_human": "551.8 MB",
      "preferred_default": false,
      "...": "..."
    },
    {
      "accession": "ENCFF210ECA",
      "file_format": "fastq",
      "output_type": "reads",
      "file_size_human": "544.9 MB",
      "preferred_default": false,
      "...": "..."
    },
    {
      "accession": "ENCFF004TKM",
      "file_format": "fastq",
      "output_type": "reads",
      "file_size_human": "532.8 MB",
      "preferred_default": false,
      "...": "..."
    }
  ],
  "audit_error_count": 0,
  "audit_not_compliant_count": 0,
  "audit_warning_count": 8,
  "audit_internal_action_count": 2
}
```

---

## 4. List Files -- BED Files for ENCSR133RZO

**Tool:** `encode_list_files`
**Parameters:**
```json
{
  "experiment_accession": "ENCSR133RZO",
  "file_format": "bed"
}
```

**Response:**
```json
[
  {
    "accession": "ENCFF635JIA",
    "file_format": "bed",
    "file_type": "bed narrowPeak",
    "output_type": "pseudoreplicated peaks",
    "output_category": "annotation",
    "file_size": 40482,
    "file_size_human": "39.5 KB",
    "assembly": "GRCh38",
    "biological_replicates": [1],
    "technical_replicates": ["1_1", "1_2"],
    "status": "released",
    "download_url": "https://www.encodeproject.org/files/ENCFF635JIA/@@download/ENCFF635JIA.bed.gz",
    "s3_uri": "s3://encode-public/2021/06/23/c5d28a48-3c7c-4b0f-978c-0ab0ec5c6068/ENCFF635JIA.bed.gz",
    "md5sum": "2a41c04233d7ba1cac7b73b912161d50",
    "experiment_accession": "ENCSR133RZO",
    "experiment_assay": "Histone ChIP-seq",
    "biosample_summary": "",
    "preferred_default": true,
    "date_created": "2021-06-23T11:04:10.999047+00:00"
  }
]
```

---

## 5. Search Files -- BED Files for H3K27ac (GRCh38)

**Tool:** `encode_search_files`
**Parameters:**
```json
{
  "file_format": "bed",
  "target": "H3K27ac",
  "assembly": "GRCh38",
  "limit": 3
}
```

**Note:** `output_type` is a supported filter here -- it is forwarded to the ENCODE file
search like `file_format`, `output_category`, `assembly` and `status`. It must be one of
ENCODE's own output types (`"IDR thresholded peaks"`, `"pseudoreplicated peaks"`,
`"fold change over control"`, ...); an unknown string simply matches nothing.

**Response:**
```json
{
  "results": [
    {
      "accession": "ENCFF253JWT",
      "file_format": "bed",
      "file_type": "bed narrowPeak",
      "output_type": "replicated peaks",
      "output_category": "annotation",
      "file_size": 1646265,
      "file_size_human": "1.6 MB",
      "assembly": "GRCh38",
      "biological_replicates": [1, 2],
      "technical_replicates": ["1_1", "2_1"],
      "status": "released",
      "download_url": "https://www.encodeproject.org/files/ENCFF253JWT/@@download/ENCFF253JWT.bed.gz",
      "s3_uri": "s3://encode-public/2023/02/16/cdd555c5-d52d-4e74-91e0-06d6ace490cb/ENCFF253JWT.bed.gz",
      "md5sum": "5b1c725ef87302f4a6bb0516104c3bbf",
      "experiment_accession": "ENCSR039AHR",
      "experiment_assay": "Histone ChIP-seq",
      "biosample_summary": "",
      "preferred_default": false,
      "date_created": "2023-02-16T20:33:18.316407+00:00"
    },
    {
      "accession": "ENCFF795TNK",
      "file_format": "bed",
      "file_type": "bed narrowPeak",
      "output_type": "pseudoreplicated peaks",
      "output_category": "annotation",
      "file_size": 1844870,
      "file_size_human": "1.8 MB",
      "assembly": "GRCh38",
      "biological_replicates": [1, 2],
      "technical_replicates": ["1_1", "2_1"],
      "status": "released",
      "download_url": "https://www.encodeproject.org/files/ENCFF795TNK/@@download/ENCFF795TNK.bed.gz",
      "s3_uri": "s3://encode-public/2023/02/16/568da960-15ce-4305-b331-cbea15da4061/ENCFF795TNK.bed.gz",
      "md5sum": "08c0ea45a4c02d8f7b6f710d8663613a",
      "experiment_accession": "ENCSR039AHR",
      "experiment_assay": "Histone ChIP-seq",
      "biosample_summary": "",
      "preferred_default": true,
      "date_created": "2023-02-16T20:33:15.904115+00:00"
    },
    {
      "accession": "ENCFF202SSZ",
      "file_format": "bed",
      "file_type": "bed narrowPeak",
      "output_type": "pseudoreplicated peaks",
      "output_category": "annotation",
      "file_size": 1737486,
      "file_size_human": "1.7 MB",
      "assembly": "GRCh38",
      "biological_replicates": [2],
      "technical_replicates": ["2_1"],
      "status": "released",
      "download_url": "https://www.encodeproject.org/files/ENCFF202SSZ/@@download/ENCFF202SSZ.bed.gz",
      "s3_uri": "s3://encode-public/2023/02/16/97bb2de1-4417-4b48-9628-03b5a3491563/ENCFF202SSZ.bed.gz",
      "md5sum": "411adb9385941a0cc0ebef7d34081674",
      "experiment_accession": "ENCSR039AHR",
      "experiment_assay": "Histone ChIP-seq",
      "biosample_summary": "",
      "preferred_default": false,
      "date_created": "2023-02-16T20:33:13.605368+00:00"
    }
  ],
  "total": 2055,
  "limit": 3,
  "offset": 0,
  "has_more": true,
  "next_offset": 3
}
```

---

## 6. Get Metadata -- Available Assay Types

**Tool:** `encode_get_metadata`
**Parameters:**
```json
{
  "metadata_type": "assays"
}
```

**Response:**
```json
{
  "metadata_type": "assays",
  "values": [
    "Histone ChIP-seq",
    "TF ChIP-seq",
    "Control ChIP-seq",
    "Mint-ChIP-seq",
    "Control Mint-ChIP-seq",
    "ATAC-seq",
    "DNase-seq",
    "GM DNase-seq",
    "FAIRE-seq",
    "MNase-seq",
    "snATAC-seq",
    "total RNA-seq",
    "polyA plus RNA-seq",
    "polyA minus RNA-seq",
    "small RNA-seq",
    "long read RNA-seq",
    "microRNA-seq",
    "microRNA counts",
    "shRNA RNA-seq",
    "siRNA RNA-seq",
    "CRISPR RNA-seq",
    "CRISPRi RNA-seq",
    "scRNA-seq",
    "long read scRNA-seq",
    "snRNA-seq",
    "CAGE",
    "RAMPAGE",
    "PRO-seq",
    "PRO-cap",
    "GRO-seq",
    "GRO-cap",
    "PAS-seq",
    "Bru-seq",
    "BruChase-seq",
    "BruUV-seq",
    "WGBS",
    "RRBS",
    "MeDIP-seq",
    "MRE-seq",
    "TAB-seq",
    "DNAme array",
    "Hi-C",
    "intact Hi-C",
    "in situ Hi-C",
    "dilution Hi-C",
    "capture Hi-C",
    "Micro-C",
    "ChIA-PET",
    "HiChIP",
    "PLAC-seq",
    "SPRITE",
    "5C",
    "CUT&RUN",
    "CUT&Tag",
    "eCLIP",
    "Control eCLIP",
    "iCLIP",
    "RIP-seq",
    "RIP-chip",
    "RNA Bind-n-Seq",
    "STARR-seq",
    "MPRA",
    "CRISPR screen",
    "proliferation CRISPR screen",
    "FlowFISH CRISPR screen",
    "WGS",
    "genotyping array",
    "RNA microarray",
    "Repli-seq",
    "Repli-chip",
    "Switchgear",
    "MS-MS",
    "RNA-PET",
    "DNA-PET",
    "icSHAPE",
    "icLASER",
    "seqFISH",
    "Circulome-seq",
    "5' RLM RACE"
  ],
  "count": 79
}
```

---

## Notes for Vignette Authors

1. **Accession stability**: ENCODE accessions (ENCSR*, ENCFF*) are permanent identifiers. These outputs will remain valid indefinitely.

2. **`output_type` must be an ENCODE output type**: `encode_search_files` does forward `output_type` to the portal, alongside `file_format`, `output_category`, `assembly` and `status`. The value has to come from ENCODE's vocabulary (`encode_get_metadata(metadata_type="output_types")`) -- `"IDR thresholded peaks"`, `"pseudoreplicated peaks"`, `"loops"`, `"contact domains"`, and so on. Anything else quietly matches nothing.

3. **Facets are live counts**: The facet numbers reflect the current state of the ENCODE database and may change as new data is released.

4. **Pancreas data summary** (from facets):
   - 288 total experiments
   - 73 Histone ChIP-seq, 31 DNase-seq, 25 TF ChIP-seq, 17 snATAC-seq, 10 ATAC-seq
   - Top histone marks: H3K4me3 (16), H3K27ac (15), H3K27me3 (14), H3K9me3 (14), H3K4me1 (13), H3K36me3 (12)
   - Dominant lab: Bradley Bernstein, Broad (82 experiments)
   - 200 tissue samples, 51 cell line, 32 in vitro differentiated, 5 organoid

5. **File counts** (from facets): 2055 H3K27ac BED files across all tissues/cell types in GRCh38.

6. **Audit counts in `encode_get_experiment`**: up to 0.3.3 this tool asked ENCODE for `frame=embedded`, which omits audits, so its four `audit_*_count` fields were always zero. From 0.3.4 it asks for `frame=page` and reports the same counts as the portal (8 warnings and 2 internal-action flags for ENCSR133RZO when this was checked).

7. **Long responses are trimmed**: where a record shows `"...": "..."`, the remaining fields were cut for readability. Every file record really carries all 19 `FileSummary` fields.
