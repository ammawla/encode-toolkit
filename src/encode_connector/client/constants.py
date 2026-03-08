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
    "Histone ChIP-seq",
    "TF ChIP-seq",
    "Control ChIP-seq",
    "Mint-ChIP-seq",
    "ATAC-seq",
    "DNase-seq",
    "RNA-seq",
    "total RNA-seq",
    "small RNA-seq",
    "long read RNA-seq",
    "microRNA-seq",
    "polyA plus RNA-seq",
    "polyA minus RNA-seq",
    "single-cell RNA sequencing assay",
    "CAGE",
    "RAMPAGE",
    "RRBS",
    "WGBS",
    "whole-genome shotgun bisulfite sequencing",
    "Hi-C",
    "intact Hi-C",
    "in situ Hi-C",
    "Micro-C",
    "ChIA-PET",
    "HiChIP",
    "PLAC-seq",
    "PRO-seq",
    "GRO-seq",
    "CUT&RUN",
    "CUT&Tag",
    "STARR-seq",
    "MPRA",
    "CRISPR screen",
    "proliferation CRISPR screen",
    "FlowFISH CRISPR screen",
    "eCLIP",
    "iCLIP",
    "shRNA knockdown followed by RNA-seq",
    "siRNA knockdown followed by RNA-seq",
    "CRISPRi followed by RNA-seq",
    "MeDIP-seq",
    "MRE-seq",
    "MNase-seq",
    "5C",
    "BruUV-seq",
    "genetic modification followed by DNase-seq",
    "long read sequencing assay",
    "direct RNA-seq",
    "Parse SPLiT-seq",
    "SHARE-seq",
    "10x multiome",
    "single-nucleus ATAC-seq",
    "single-nucleus RNA-seq",
    "snATAC-seq",
    "Repli-seq",
    "Repli-chip",
    "Switchgear",
    "genotyping HTS",
    "whole genome sequencing assay",
]

ORGANISMS = [
    "Homo sapiens",
    "Mus musculus",
    "Drosophila melanogaster",
    "Caenorhabditis elegans",
    "Saccharomyces cerevisiae",
]

BIOSAMPLE_CLASSIFICATIONS = [
    "tissue",
    "cell line",
    "primary cell",
    "in vitro differentiated cells",
    "organoid",
    "whole organisms",
    "single cell",
    "induced pluripotent stem cell line",
    "stem cell",
]

ORGAN_SLIMS = [
    "adrenal gland",
    "arterial blood vessel",
    "bone element",
    "bone marrow",
    "brain",
    "breast",
    "bronchus",
    "connective tissue",
    "embryo",
    "esophagus",
    "extraembryonic component",
    "eye",
    "gonad",
    "heart",
    "intestine",
    "kidney",
    "large intestine",
    "limb",
    "liver",
    "lung",
    "lymph node",
    "lymphoid tissue",
    "mammary gland",
    "mouth",
    "musculature of body",
    "nerve",
    "nose",
    "ovary",
    "pancreas",
    "penis",
    "placenta",
    "prostate gland",
    "skeleton",
    "skin of body",
    "small intestine",
    "spinal cord",
    "spleen",
    "stomach",
    "testis",
    "thymus",
    "thyroid gland",
    "tongue",
    "tonsil",
    "ureter",
    "urinary bladder",
    "uterus",
    "vagina",
    "vasculature",
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
    "reads",
    "alignments",
    "unfiltered alignments",
    "transcriptome alignments",
    "signal",
    "signal of unique reads",
    "signal of all reads",
    "signal p-value",
    "fold change over control",
    "peaks",
    "IDR thresholded peaks",
    "conservative IDR thresholded peaks",
    "optimal IDR thresholded peaks",
    "pseudoreplicated peaks",
    "replicated peaks",
    "stable peaks",
    "hotspots",
    "narrowPeaks",
    "broadPeaks",
    "gappedPeaks",
    "gene quantifications",
    "transcript quantifications",
    "exon quantifications",
    "splice junctions",
    "genome reference",
    "genome index",
    "transcriptome reference",
    "transcriptome index",
    "spike-in sequence",
    "contact matrix",
    "contact domains",
    "topologically associated domains",
    "chromatin interactions",
    "DNA accessibility raw signal",
    "DNA accessibility enrichment signal",
    "methylation state at CpG",
    "methylation state at CHG",
    "methylation state at CHH",
    "enrichment",
    "FDR cut rate",
    "element quantifications",
    "guide quantifications",
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
