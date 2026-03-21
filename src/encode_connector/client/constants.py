"""ENCODE API constants, endpoints, and known filter values."""

BASE_URL = "https://www.encodeproject.org"
SEARCH_ENDPOINT = "/search/"


# Rate limiting
MAX_REQUESTS_PER_SECOND = 10
DOWNLOAD_CONCURRENCY = 3

# Request defaults
DEFAULT_TIMEOUT = 30.0
DOWNLOAD_TIMEOUT = 300.0
DEFAULT_LIMIT = 25
try:
    import importlib.metadata

    _version = importlib.metadata.version("encode-toolkit")
except importlib.metadata.PackageNotFoundError:
    _version = "0.3.0"
USER_AGENT = f"encode-toolkit/{_version} (MCP; +https://github.com/ammawla/encode-toolkit)"

# Keyring service name for credential storage
KEYRING_SERVICE = "encode-connector"
KEYRING_ACCESS_KEY = "access_key"
KEYRING_SECRET_KEY = "secret_key"

# -------------------------------------------------------------------
# Known ENCODE filter values (for metadata/autocomplete)
# -------------------------------------------------------------------

ASSAY_TITLES = [
    # ChIP-seq family
    "Histone ChIP-seq",
    "TF ChIP-seq",
    "Control ChIP-seq",
    "Mint-ChIP-seq",
    "Control Mint-ChIP-seq",
    # Accessibility
    "ATAC-seq",
    "DNase-seq",
    "GM DNase-seq",
    "FAIRE-seq",
    "MNase-seq",
    "snATAC-seq",
    # RNA-seq family
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
    # Single-cell
    "scRNA-seq",
    "long read scRNA-seq",
    "snRNA-seq",
    # Transcription / TSS
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
    # Methylation
    "WGBS",
    "RRBS",
    "MeDIP-seq",
    "MRE-seq",
    "TAB-seq",
    "DNAme array",
    # 3D genome
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
    # CUT&RUN / CUT&Tag
    "CUT&RUN",
    "CUT&Tag",
    # CLIP family
    "eCLIP",
    "Control eCLIP",
    "iCLIP",
    "RIP-seq",
    "RIP-chip",
    "RNA Bind-n-Seq",
    # Functional screens
    "STARR-seq",
    "MPRA",
    "CRISPR screen",
    "proliferation CRISPR screen",
    "FlowFISH CRISPR screen",
    # Genotyping / Sequencing
    "WGS",
    "genotyping array",
    "RNA microarray",
    # Replication
    "Repli-seq",
    "Repli-chip",
    # Other assays
    "Switchgear",
    "MS-MS",
    "RNA-PET",
    "DNA-PET",
    "icSHAPE",
    "icLASER",
    "seqFISH",
    "Circulome-seq",
    "5' RLM RACE",
]

ORGANISMS = [
    "Homo sapiens",
    "Mus musculus",
    "Drosophila melanogaster",
    "Caenorhabditis elegans",
    "Saccharomyces cerevisiae",
]

BIOSAMPLE_CLASSIFICATIONS = [
    "cell line",
    "tissue",
    "primary cell",
    "whole organisms",
    "in vitro differentiated cells",
    "cell-free sample",
    "organoid",
    "technical sample",
]

ORGAN_SLIMS = [
    "adipose tissue",
    "adrenal gland",
    "arterial blood vessel",
    "blood",
    "blood vessel",
    "bodily fluid",
    "bone element",
    "bone marrow",
    "brain",
    "breast",
    "bronchus",
    "colon",
    "connective tissue",
    "ear",
    "embryo",
    "endocrine gland",
    "epithelium",
    "esophagus",
    "exocrine gland",
    "extraembryonic component",
    "eye",
    "gallbladder",
    "gonad",
    "hair follicle",
    "heart",
    "immune organ",
    "intestine",
    "kidney",
    "large intestine",
    "limb",
    "liver",
    "lung",
    "lymph node",
    "lymphatic vessel",
    "lymphoid tissue",
    "major salivary gland",
    "mammary gland",
    "mouth",
    "musculature of body",
    "nerve",
    "nose",
    "ovary",
    "pancreas",
    "pericardium",
    "penis",
    "placenta",
    "prostate gland",
    "skeleton",
    "skin of body",
    "skin of prepuce of penis",
    "small intestine",
    "spinal cord",
    "spleen",
    "stomach",
    "testis",
    "thymus",
    "thyroid gland",
    "tongue",
    "tonsil",
    "trachea",
    "ureter",
    "urinary bladder",
    "uterus",
    "vagina",
    "vasculature",
    "vein",
]

FILE_FORMATS = [
    "fastq",
    "bam",
    "bed",
    "bigWig",
    "bigBed",
    "tsv",
    "csv",
    "tar",
    "hic",
    "tagAlign",
    "bedpe",
    "pairs",
    "fasta",
    "gff",
    "gtf",
    "idat",
    "CEL",
    "rcc",
    "sra",
    "csfasta",
    "csqual",
    "2bit",
    "database",
    "vcf",
    "bigInteract",
    "idx",
    "dat",
    "txt",
]

OUTPUT_TYPES = [
    # Raw data
    "reads",
    "index reads",
    "filtered reads",
    "subreads",
    # Alignments
    "alignments",
    "unfiltered alignments",
    "transcriptome alignments",
    "redacted alignments",
    "redacted unfiltered alignments",
    "spike-in alignments",
    # Signal tracks
    "signal",
    "signal of unique reads",
    "signal of all reads",
    "signal p-value",
    "fold change over control",
    "control normalized signal",
    "read-depth normalized signal",
    "raw signal",
    "plus strand signal of unique reads",
    "minus strand signal of unique reads",
    "plus strand signal of all reads",
    "minus strand signal of all reads",
    # Peaks
    "peaks",
    "IDR thresholded peaks",
    "conservative IDR thresholded peaks",
    "optimal IDR thresholded peaks",
    "pseudoreplicated peaks",
    "pseudoreplicated IDR thresholded peaks",
    "replicated peaks",
    "stable peaks",
    "hotspots",
    "footprints",
    "peaks and background as input for IDR",
    "IDR ranked peaks",
    "candidate Cis-Regulatory Elements",
    "candidate enhancers",
    "candidate promoters",
    "DHS peaks",
    "filtered peaks",
    # Quantifications
    "gene quantifications",
    "transcript quantifications",
    "exon quantifications",
    "microRNA quantifications",
    "element quantifications",
    "guide quantifications",
    "differential expression quantifications",
    "splice junctions",
    # References
    "genome reference",
    "genome index",
    "transcriptome reference",
    "transcriptome index",
    "elements reference",
    "TSS reference",
    # 3D genome
    "contact matrix",
    "mapping quality thresholded contact matrix",
    "contact domains",
    "loops",
    "genome compartments",
    "genome subcompartments",
    "chromatin stripes",
    "thresholded links",
    # Methylation
    "methylation state at CpG",
    "methylation state at CHG",
    "methylation state at CHH",
    "CpG sites coverage",
    "plus strand methylation state at CpG",
    "minus strand methylation state at CpG",
    # Other
    "enrichment",
    "FDR cut rate",
    "transcription start sites",
    "element gene links",
    "thresholded element gene links",
    "semi-automated genome annotation",
    "TF binding prediction model",
    "enhancer prediction model",
    "promoter prediction model",
    "PWMs",
    "kmer weights",
    "perturbation signal",
    "replication timing profile",
    "fragments",
    "pairs",
    "contigs",
    "variant calls",
    "fine-mapped variants",
]

OUTPUT_CATEGORIES = [
    "raw data",
    "alignment",
    "signal",
    "annotation",
    "quantification",
    "reference",
    "quality metric",
]

FILE_STATUSES = [
    "released",
    "archived",
    "in progress",
    "revoked",
    "deleted",
    "content error",
    "upload failed",
]

EXPERIMENT_STATUSES = [
    "released",
    "archived",
    "revoked",
    "deleted",
    "replaced",
    "in progress",
    "submitted",
    "preliminary",
]

ASSEMBLIES = [
    "GRCh38",
    "hg19",
    "mm10",
    "mm9",
    "GRCm39",
    "dm6",
    "dm3",
    "ce11",
    "ce10",
]

LIFE_STAGES = [
    "embryonic",
    "postnatal",
    "newborn",
    "child",
    "adolescent",
    "adult",
    "unknown",
]

REPLICATION_TYPES = [
    "isogenic",
    "anisogenic",
    "unreplicated",
]

# Map of metadata_type to its values for the get_metadata tool
METADATA_MAP = {
    "assays": ASSAY_TITLES,
    "organisms": ORGANISMS,
    "organs": ORGAN_SLIMS,
    "biosample_types": BIOSAMPLE_CLASSIFICATIONS,
    "file_formats": FILE_FORMATS,
    "output_types": OUTPUT_TYPES,
    "output_categories": OUTPUT_CATEGORIES,
    "assemblies": ASSEMBLIES,
    "life_stages": LIFE_STAGES,
    "replication_types": REPLICATION_TYPES,
    "statuses": EXPERIMENT_STATUSES,
    "file_statuses": FILE_STATUSES,
}

# ENCODE API parameter name mapping (user-friendly -> API param)
EXPERIMENT_FILTER_MAP = {
    "assay_title": "assay_title",
    "organism": "replicates.library.biosample.donor.organism.scientific_name",
    "organ": "biosample_ontology.organ_slims",
    "biosample_type": "biosample_ontology.classification",
    "biosample_term_name": "biosample_ontology.term_name",
    "target": "target.label",
    "status": "status",
    "lab": "lab.title",
    "award": "award.project",
    "assembly": "assembly",
    "replication_type": "replication_type",
    "life_stage": "replicates.library.biosample.life_stage",
    "sex": "replicates.library.biosample.sex",
    "perturbed": "replicates.library.biosample.perturbed",
    "treatment": "replicates.library.biosample.treatments.treatment_term_name",
    "genetic_modification": "replicates.library.biosample.applied_modifications.category",
    "date_released": "date_released",
    "searchTerm": "searchTerm",
}

FILE_FILTER_MAP = {
    "file_format": "file_format",
    "file_type": "file_type",
    "output_type": "output_type",
    "output_category": "output_category",
    "assembly": "assembly",
    "status": "status",
    "biological_replicates": "biological_replicates",
    "preferred_default": "preferred_default",
    "dataset": "dataset",
}
