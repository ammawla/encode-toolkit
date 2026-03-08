"""Tests for Pydantic models and parsing."""

from encode_connector.client.models import (
    DownloadResult,
    ExperimentDetail,
    ExperimentSummary,
    FileSummary,
    _extract_organism,
    _human_size,
)


class TestHumanSize:
    def test_zero(self):
        assert _human_size(0) == "0 B"

    def test_bytes(self):
        assert _human_size(500) == "500.0 B"

    def test_kilobytes(self):
        assert _human_size(1024) == "1.0 KB"

    def test_megabytes(self):
        assert _human_size(1024 * 1024) == "1.0 MB"

    def test_gigabytes(self):
        assert _human_size(1024**3) == "1.0 GB"

    def test_terabytes(self):
        assert _human_size(1024**4) == "1.0 TB"


class TestExtractOrganism:
    def test_direct_dict(self):
        data = {"organism": {"scientific_name": "Homo sapiens"}}
        assert _extract_organism(data) == "Homo sapiens"

    def test_direct_string_path(self):
        data = {"organism": "/organisms/human/"}
        assert _extract_organism(data) == "human"

    def test_from_replicates(self):
        data = {
            "replicates": [{"library": {"biosample": {"donor": {"organism": {"scientific_name": "Mus musculus"}}}}}]
        }
        assert _extract_organism(data) == "Mus musculus"

    def test_empty(self):
        assert _extract_organism({}) == ""

    def test_none_organism(self):
        assert _extract_organism({"organism": None}) == ""


class TestExperimentSummary:
    def test_from_api_basic(self):
        data = {
            "accession": "ENCSR133RZO",
            "assay_title": "Histone ChIP-seq",
            "status": "released",
            "description": "Test experiment",
            "date_released": "2024-01-15",
        }
        exp = ExperimentSummary.from_api(data)
        assert exp.accession == "ENCSR133RZO"
        assert exp.assay_title == "Histone ChIP-seq"
        assert exp.status == "released"

    def test_from_api_with_target_dict(self):
        data = {
            "accession": "ENCSR133RZO",
            "target": {"label": "H3K27me3"},
        }
        exp = ExperimentSummary.from_api(data)
        assert exp.target == "H3K27me3"

    def test_from_api_with_target_string(self):
        data = {
            "accession": "ENCSR133RZO",
            "target": "/targets/H3K27me3-human/",
        }
        exp = ExperimentSummary.from_api(data)
        assert exp.target == "H3K27me3-human"

    def test_from_api_with_lab_dict(self):
        data = {
            "accession": "ENCSR133RZO",
            "lab": {"title": "Bernstein Lab"},
        }
        exp = ExperimentSummary.from_api(data)
        assert exp.lab == "Bernstein Lab"

    def test_from_api_with_biosample_ontology(self):
        data = {
            "accession": "ENCSR133RZO",
            "biosample_ontology": {
                "classification": "tissue",
                "organ_slims": ["pancreas"],
            },
        }
        exp = ExperimentSummary.from_api(data)
        assert exp.biosample_type == "tissue"
        assert exp.organ == "pancreas"

    def test_from_api_empty(self):
        exp = ExperimentSummary.from_api({})
        assert exp.accession == ""

    def test_from_api_assembly_extraction(self):
        data = {
            "accession": "ENCSR133RZO",
            "files": [
                {"assembly": "GRCh38"},
                {"assembly": "GRCh38"},
                {"assembly": "hg19"},
                {"assembly": ""},  # empty should be excluded
            ],
        }
        exp = ExperimentSummary.from_api(data)
        assert exp.assembly == ["GRCh38", "hg19"]

    def test_from_api_assembly_empty(self):
        data = {"accession": "ENCSR133RZO"}
        exp = ExperimentSummary.from_api(data)
        assert exp.assembly == []

    def test_from_api_audit_counts(self):
        data = {
            "accession": "ENCSR133RZO",
            "audit": {
                "ERROR": [{"category": "error1"}, {"category": "error2"}],
                "WARNING": [{"category": "warn1"}],
            },
        }
        exp = ExperimentSummary.from_api(data)
        assert exp.audit_error_count == 2
        assert exp.audit_warning_count == 1

    def test_from_api_audit_counts_empty(self):
        data = {"accession": "ENCSR133RZO"}
        exp = ExperimentSummary.from_api(data)
        assert exp.audit_error_count == 0
        assert exp.audit_warning_count == 0

    def test_from_api_dbxrefs(self):
        data = {
            "accession": "ENCSR133RZO",
            "dbxrefs": ["GEO:GSE123456", "PMID:12345"],
        }
        exp = ExperimentSummary.from_api(data)
        assert exp.dbxrefs == ["GEO:GSE123456", "PMID:12345"]

    def test_from_api_dbxrefs_empty(self):
        data = {"accession": "ENCSR133RZO"}
        exp = ExperimentSummary.from_api(data)
        assert exp.dbxrefs == []

    def test_from_api_url_generated(self):
        data = {"accession": "ENCSR133RZO"}
        exp = ExperimentSummary.from_api(data)
        assert exp.url == "https://www.encodeproject.org/experiments/ENCSR133RZO/"

    def test_from_api_url_empty_accession(self):
        data = {}
        exp = ExperimentSummary.from_api(data)
        assert exp.url == ""


class TestFileSummary:
    def test_from_api_basic(self):
        data = {
            "accession": "ENCFF635JIA",
            "file_format": "bed",
            "file_type": "bed narrowPeak",
            "output_type": "IDR thresholded peaks",
            "file_size": 1048576,
            "status": "released",
            "href": "/files/ENCFF635JIA/@@download/ENCFF635JIA.bed.gz",
            "md5sum": "abc123",
        }
        f = FileSummary.from_api(data)
        assert f.accession == "ENCFF635JIA"
        assert f.file_format == "bed"
        assert f.file_size == 1048576
        assert f.file_size_human == "1.0 MB"
        assert "encodeproject.org" in f.download_url
        assert f.md5sum == "abc123"

    def test_from_api_with_dataset_string(self):
        data = {
            "accession": "ENCFF635JIA",
            "dataset": "/experiments/ENCSR133RZO/",
        }
        f = FileSummary.from_api(data)
        assert f.experiment_accession == "ENCSR133RZO"

    def test_from_api_with_dataset_dict(self):
        data = {
            "accession": "ENCFF635JIA",
            "dataset": {"accession": "ENCSR133RZO"},
        }
        f = FileSummary.from_api(data)
        assert f.experiment_accession == "ENCSR133RZO"

    def test_from_api_zero_size(self):
        data = {"accession": "ENCFF635JIA", "file_size": 0}
        f = FileSummary.from_api(data)
        assert f.file_size == 0
        assert f.file_size_human == "0 B"

    def test_from_api_none_size(self):
        data = {"accession": "ENCFF635JIA", "file_size": None}
        f = FileSummary.from_api(data)
        assert f.file_size == 0


class TestExperimentDetail:
    def test_from_api_with_organism(self):
        data = {
            "accession": "ENCSR133RZO",
            "organism": {"scientific_name": "Homo sapiens"},
            "assay_title": "ChIP-seq",
        }
        detail = ExperimentDetail.from_api(data)
        assert detail.organism == "Homo sapiens"

    def test_from_api_with_controls(self):
        data = {
            "accession": "ENCSR133RZO",
            "possible_controls": [
                {"accession": "ENCSR000ABC"},
                "/experiments/ENCSR000DEF/",
            ],
        }
        detail = ExperimentDetail.from_api(data)
        assert "ENCSR000ABC" in detail.possible_controls
        assert "ENCSR000DEF" in detail.possible_controls

    def test_from_api_with_files(self):
        files = [
            {"accession": "ENCFF001", "file_format": "bed", "file_size": 100},
            {"accession": "ENCFF002", "file_format": "bam", "file_size": 200},
        ]
        detail = ExperimentDetail.from_api({"accession": "ENCSR133RZO"}, files=files)
        assert len(detail.files) == 2

    def test_url_generated(self):
        detail = ExperimentDetail.from_api({"accession": "ENCSR133RZO"})
        assert "ENCSR133RZO" in detail.url


class TestExperimentSummaryEdgeCases:
    def test_from_api_with_lab_string(self):
        """Cover line 49: lab as string path."""
        data = {
            "accession": "ENCSR133RZO",
            "lab": "/labs/bernstein/",
        }
        exp = ExperimentSummary.from_api(data)
        assert exp.lab == "bernstein"

    def test_from_api_with_biosample_ontology_string(self):
        """Cover lines 62-63: biosample_ontology as string."""
        data = {
            "accession": "ENCSR133RZO",
            "biosample_ontology": "tissue",
        }
        exp = ExperimentSummary.from_api(data)
        assert exp.biosample_type == "tissue"

    def test_from_api_files_with_non_dict_entries(self):
        """Assembly extraction filters out non-dict file entries."""
        data = {
            "accession": "ENCSR133RZO",
            "files": [
                {"assembly": "GRCh38"},
                "/files/ENCFF001/",  # string entry, not dict
            ],
        }
        exp = ExperimentSummary.from_api(data)
        assert exp.assembly == ["GRCh38"]


class TestExperimentDetailEdgeCases:
    def test_from_api_with_target_string(self):
        """Cover line 230: target as string path in ExperimentDetail."""
        data = {
            "accession": "ENCSR133RZO",
            "target": "/targets/H3K27me3-human/",
        }
        detail = ExperimentDetail.from_api(data)
        assert detail.target == "H3K27me3-human"

    def test_from_api_with_lab_string(self):
        """Cover line 239: lab as string path in ExperimentDetail."""
        data = {
            "accession": "ENCSR133RZO",
            "lab": "/labs/bernstein/",
        }
        detail = ExperimentDetail.from_api(data)
        assert detail.lab == "bernstein"

    def test_from_api_with_award_string(self):
        """Cover line 248: award as string path."""
        data = {
            "accession": "ENCSR133RZO",
            "award": "/awards/U54HG007004/",
        }
        detail = ExperimentDetail.from_api(data)
        assert detail.award == "U54HG007004"

    def test_from_api_with_award_dict(self):
        """Cover line 250: award as dict with project."""
        data = {
            "accession": "ENCSR133RZO",
            "award": {"project": "ENCODE"},
        }
        detail = ExperimentDetail.from_api(data)
        assert detail.award == "ENCODE"

    def test_from_api_with_controls_string_no_path(self):
        """Possible control as string without path separators."""
        data = {
            "accession": "ENCSR133RZO",
            "possible_controls": ["ENCSR000ABC"],
        }
        detail = ExperimentDetail.from_api(data)
        assert "ENCSR000ABC" in detail.possible_controls

    def test_from_api_empty_controls(self):
        """No possible_controls key."""
        data = {"accession": "ENCSR133RZO"}
        detail = ExperimentDetail.from_api(data)
        assert detail.possible_controls == []


class TestDownloadResult:
    def test_default_values(self):
        r = DownloadResult(accession="ENCFF001")
        assert r.success is False
        assert r.error == ""
        assert r.md5_verified is False

    def test_with_all_fields(self):
        r = DownloadResult(
            accession="ENCFF001",
            success=True,
            file_path="/data/file.bed",
            file_size=1024,
            file_size_human="1.0 KB",
            md5_verified=True,
            error="",
        )
        assert r.success is True
        assert r.file_size == 1024
