"""Tests for bioinformatics audit: check_filter_value, assembly/audit helpers,
search_term forwarding, None guards, and constants correctness.
"""

from unittest.mock import MagicMock

from encode_connector.client.constants import (
    ASSAY_TITLES,
    BIOSAMPLE_CLASSIFICATIONS,
    ORGAN_SLIMS,
    OUTPUT_TYPES,
)
from encode_connector.client.encode_client import EncodeClient
from encode_connector.client.models import (
    ExperimentDetail,
    ExperimentSummary,
    _extract_assemblies,
    _extract_audit_counts,
)
from encode_connector.client.validation import check_filter_value

# ======================================================================
# check_filter_value
# ======================================================================


class TestCheckFilterValue:
    """Tests for check_filter_value in validation.py."""

    def test_exact_match_returns_none(self):
        """An exact match should return None (no warning)."""
        result = check_filter_value("Histone ChIP-seq", ASSAY_TITLES, "assay_title")
        assert result is None

    def test_wrong_case_returns_correction_warning(self):
        """Wrong case should return a warning with the correct casing."""
        result = check_filter_value("histone chip-seq", ASSAY_TITLES, "assay_title")
        assert result is not None
        assert "wrong case" in result
        assert "Histone ChIP-seq" in result

    def test_unknown_value_returns_not_found_warning(self):
        """A completely unknown value should return a 'not found' warning."""
        result = check_filter_value("Nonexistent Assay XYZ", ASSAY_TITLES, "assay_title")
        assert result is not None
        assert "not found" in result

    def test_empty_valid_values_unknown(self):
        """With an empty valid_values list, any value is reported as not found."""
        result = check_filter_value("anything", [], "test_filter")
        assert result is not None
        assert "not found" in result

    def test_empty_valid_values_empty_string(self):
        """Empty string value returns None (treated as no filter)."""
        result = check_filter_value("", [], "test_filter")
        assert result is None

    def test_case_correction_for_organ(self):
        """Case correction works for organ values too."""
        result = check_filter_value("Blood", ORGAN_SLIMS, "organ")
        assert result is not None
        assert "wrong case" in result
        assert "blood" in result

    def test_exact_match_organ(self):
        """Exact organ match returns None."""
        result = check_filter_value("blood", ORGAN_SLIMS, "organ")
        assert result is None

    def test_warning_message_includes_filter_name(self):
        """The warning message should reference the filter name."""
        result = check_filter_value("bogus", ["real"], "my_filter")
        assert "my_filter" in result


# ======================================================================
# ExperimentSummary.assembly field
# ======================================================================


class TestExperimentSummaryAssembly:
    """Tests for the assembly field on ExperimentSummary."""

    def test_assembly_populated_from_files(self):
        """Assembly list is extracted from files with assembly info."""
        data = {
            "accession": "ENCSR000AAA",
            "files": [
                {"assembly": "GRCh38"},
                {"assembly": "hg19"},
            ],
        }
        exp = ExperimentSummary.from_api(data)
        assert "GRCh38" in exp.assembly
        assert "hg19" in exp.assembly

    def test_assembly_empty_when_no_files(self):
        """Assembly list is empty when there are no files."""
        data = {"accession": "ENCSR000AAA"}
        exp = ExperimentSummary.from_api(data)
        assert exp.assembly == []

    def test_assembly_deduplicates_and_sorts(self):
        """Assembly list removes duplicates and sorts alphabetically."""
        data = {
            "accession": "ENCSR000AAA",
            "files": [
                {"assembly": "hg19"},
                {"assembly": "GRCh38"},
                {"assembly": "hg19"},
                {"assembly": "GRCh38"},
                {"assembly": "GRCh38"},
            ],
        }
        exp = ExperimentSummary.from_api(data)
        assert exp.assembly == ["GRCh38", "hg19"]

    def test_assembly_excludes_empty_strings(self):
        """Files with empty assembly strings are excluded."""
        data = {
            "accession": "ENCSR000AAA",
            "files": [
                {"assembly": "GRCh38"},
                {"assembly": ""},
                {},
            ],
        }
        exp = ExperimentSummary.from_api(data)
        assert exp.assembly == ["GRCh38"]


# ======================================================================
# ExperimentDetail.assembly field
# ======================================================================


class TestExperimentDetailAssembly:
    """Tests for the assembly field on ExperimentDetail."""

    def test_assembly_populated_from_api_data_files(self):
        """Assembly list is extracted from the data dict's files."""
        data = {
            "accession": "ENCSR000AAA",
            "files": [
                {"assembly": "GRCh38"},
                {"assembly": "mm10"},
            ],
        }
        detail = ExperimentDetail.from_api(data)
        assert "GRCh38" in detail.assembly
        assert "mm10" in detail.assembly

    def test_assembly_empty_when_no_files_in_data(self):
        """Assembly list is empty when the data dict has no files."""
        data = {"accession": "ENCSR000AAA"}
        detail = ExperimentDetail.from_api(data)
        assert detail.assembly == []

    def test_assembly_deduplicates_and_sorts(self):
        """Assembly list removes duplicates and sorts."""
        data = {
            "accession": "ENCSR000AAA",
            "files": [
                {"assembly": "mm10"},
                {"assembly": "GRCh38"},
                {"assembly": "mm10"},
            ],
        }
        detail = ExperimentDetail.from_api(data)
        assert detail.assembly == ["GRCh38", "mm10"]


# ======================================================================
# audit_not_compliant_count — ExperimentSummary
# ======================================================================


class TestExperimentSummaryAuditNotCompliant:
    """Tests for audit_not_compliant_count on ExperimentSummary."""

    def test_not_compliant_count_populated(self):
        """NOT_COMPLIANT audit count is extracted from API data."""
        data = {
            "accession": "ENCSR000AAA",
            "audit": {
                "ERROR": [{"category": "err1"}],
                "NOT_COMPLIANT": [
                    {"category": "nc1"},
                    {"category": "nc2"},
                    {"category": "nc3"},
                ],
                "WARNING": [{"category": "warn1"}],
            },
        }
        exp = ExperimentSummary.from_api(data)
        assert exp.audit_not_compliant_count == 3
        assert exp.audit_error_count == 1
        assert exp.audit_warning_count == 1

    def test_not_compliant_zero_when_absent(self):
        """NOT_COMPLIANT count is 0 when no NOT_COMPLIANT audits exist."""
        data = {
            "accession": "ENCSR000AAA",
            "audit": {
                "ERROR": [],
                "WARNING": [{"category": "warn1"}],
            },
        }
        exp = ExperimentSummary.from_api(data)
        assert exp.audit_not_compliant_count == 0

    def test_not_compliant_zero_when_no_audit(self):
        """NOT_COMPLIANT count is 0 when no audit key exists at all."""
        data = {"accession": "ENCSR000AAA"}
        exp = ExperimentSummary.from_api(data)
        assert exp.audit_not_compliant_count == 0

    def test_all_audit_counts_together(self):
        """All four audit counts work together correctly."""
        data = {
            "accession": "ENCSR000AAA",
            "audit": {
                "ERROR": [{"category": "e1"}, {"category": "e2"}],
                "NOT_COMPLIANT": [{"category": "nc1"}],
                "WARNING": [{"category": "w1"}, {"category": "w2"}, {"category": "w3"}],
                "INTERNAL_ACTION": [{"category": "ia1"}, {"category": "ia2"}],
            },
        }
        exp = ExperimentSummary.from_api(data)
        assert exp.audit_error_count == 2
        assert exp.audit_not_compliant_count == 1
        assert exp.audit_warning_count == 3
        assert exp.audit_internal_action_count == 2

    def test_internal_action_zero_when_absent(self):
        """INTERNAL_ACTION count is 0 when key is missing."""
        data = {
            "accession": "ENCSR000AAA",
            "audit": {"ERROR": [{"category": "e1"}]},
        }
        exp = ExperimentSummary.from_api(data)
        assert exp.audit_internal_action_count == 0


# ======================================================================
# audit_not_compliant_count — ExperimentDetail
# ======================================================================


class TestExperimentDetailAuditNotCompliant:
    """Tests for audit_not_compliant_count on ExperimentDetail."""

    def test_not_compliant_count_populated(self):
        """NOT_COMPLIANT audit count is extracted from API data."""
        data = {
            "accession": "ENCSR000AAA",
            "audit": {
                "NOT_COMPLIANT": [
                    {"category": "nc1"},
                    {"category": "nc2"},
                ],
            },
        }
        detail = ExperimentDetail.from_api(data)
        assert detail.audit_not_compliant_count == 2

    def test_not_compliant_zero_when_absent(self):
        """NOT_COMPLIANT count is 0 when key is missing from audit dict."""
        data = {
            "accession": "ENCSR000AAA",
            "audit": {
                "ERROR": [{"category": "err1"}],
            },
        }
        detail = ExperimentDetail.from_api(data)
        assert detail.audit_not_compliant_count == 0
        assert detail.audit_error_count == 1

    def test_not_compliant_zero_when_no_audit(self):
        """NOT_COMPLIANT count is 0 when there is no audit key at all."""
        data = {"accession": "ENCSR000AAA"}
        detail = ExperimentDetail.from_api(data)
        assert detail.audit_not_compliant_count == 0
        assert detail.audit_error_count == 0
        assert detail.audit_warning_count == 0

    def test_all_audit_counts_on_detail(self):
        """All four audit counts work together on ExperimentDetail."""
        data = {
            "accession": "ENCSR000AAA",
            "audit": {
                "ERROR": [{"category": "e1"}],
                "NOT_COMPLIANT": [{"category": "nc1"}, {"category": "nc2"}],
                "WARNING": [{"category": "w1"}],
                "INTERNAL_ACTION": [{"category": "ia1"}],
            },
        }
        detail = ExperimentDetail.from_api(data)
        assert detail.audit_error_count == 1
        assert detail.audit_not_compliant_count == 2
        assert detail.audit_warning_count == 1
        assert detail.audit_internal_action_count == 1

    def test_internal_action_zero_when_absent_detail(self):
        """INTERNAL_ACTION count is 0 when key is missing on ExperimentDetail."""
        data = {
            "accession": "ENCSR000AAA",
            "audit": {"WARNING": [{"category": "w1"}]},
        }
        detail = ExperimentDetail.from_api(data)
        assert detail.audit_internal_action_count == 0


# ======================================================================
# search_term forwarding in search_files when organism is set
# ======================================================================


class TestSearchFilesSearchTermForwarding:
    """Tests for search_term being forwarded to search_experiments when organism is set."""

    async def test_search_term_forwarded_with_organism(self):
        """search_term is passed to search_experiments when organism is specified."""
        client = EncodeClient()
        captured_kwargs = {}

        exp_summary = MagicMock()
        exp_summary.accession = "ENCSR000AAA"

        async def mock_search_experiments(**kwargs):
            captured_kwargs.update(kwargs)
            return {"results": [exp_summary], "total": 1}

        async def mock_list_files(experiment_accession, **kwargs):
            from encode_connector.client.models import FileSummary

            return [
                FileSummary.from_api(
                    {
                        "accession": "ENCFF001AAA",
                        "file_format": "bed",
                        "file_size": 1024,
                    }
                )
            ]

        client.search_experiments = mock_search_experiments
        client.list_files = mock_list_files

        await client.search_files(
            organism="Mus musculus",
            search_term="liver",
        )
        assert captured_kwargs.get("search_term") == "liver"

    async def test_search_term_forwarded_with_organism_and_assay(self):
        """search_term is forwarded alongside other experiment-level filters."""
        client = EncodeClient()
        captured_kwargs = {}

        exp_summary = MagicMock()
        exp_summary.accession = "ENCSR000AAA"

        async def mock_search_experiments(**kwargs):
            captured_kwargs.update(kwargs)
            return {"results": [exp_summary], "total": 1}

        async def mock_list_files(experiment_accession, **kwargs):
            from encode_connector.client.models import FileSummary

            return [
                FileSummary.from_api(
                    {
                        "accession": "ENCFF001AAA",
                        "file_format": "bam",
                        "file_size": 2048,
                    }
                )
            ]

        client.search_experiments = mock_search_experiments
        client.list_files = mock_list_files

        await client.search_files(
            organism="Homo sapiens",
            assay_title="ATAC-seq",
            search_term="K562",
        )
        assert captured_kwargs.get("search_term") == "K562"
        assert captured_kwargs.get("assay_title") == "ATAC-seq"
        assert captured_kwargs.get("organism") == "Homo sapiens"


# ======================================================================
# Constants correctness
# ======================================================================


class TestConstantsCorrectness:
    """Verify specific values are present or absent in ENCODE constant lists."""

    def test_blood_in_organ_slims(self):
        """'blood' is a valid organ slim."""
        assert "blood" in ORGAN_SLIMS

    def test_cell_free_sample_in_biosample_classifications(self):
        """'cell-free sample' is a valid biosample classification."""
        assert "cell-free sample" in BIOSAMPLE_CLASSIFICATIONS

    def test_scrna_seq_in_assay_titles(self):
        """Assay is 'scRNA-seq', not 'single-cell RNA sequencing assay'."""
        assert "scRNA-seq" in ASSAY_TITLES
        assert "single-cell RNA sequencing assay" not in ASSAY_TITLES

    def test_shrna_rna_seq_in_assay_titles(self):
        """Assay is 'shRNA RNA-seq', not 'shRNA knockdown followed by RNA-seq'."""
        assert "shRNA RNA-seq" in ASSAY_TITLES
        assert "shRNA knockdown followed by RNA-seq" not in ASSAY_TITLES

    def test_footprints_in_output_types(self):
        """'footprints' is a valid output type."""
        assert "footprints" in OUTPUT_TYPES

    def test_narrowpeaks_not_in_output_types(self):
        """'narrowPeaks' is NOT a valid output type (file_type, not output_type)."""
        assert "narrowPeaks" not in OUTPUT_TYPES

    def test_dna_accessibility_raw_signal_not_in_output_types(self):
        """'DNA accessibility raw signal' is NOT a valid output type."""
        assert "DNA accessibility raw signal" not in OUTPUT_TYPES


# ======================================================================
# Extracted helpers: _extract_assemblies, _extract_audit_counts
# ======================================================================


class TestExtractAssemblies:
    """Tests for the _extract_assemblies helper function."""

    def test_basic_extraction(self):
        files = [{"assembly": "GRCh38"}, {"assembly": "mm10"}]
        assert _extract_assemblies(files) == ["GRCh38", "mm10"]

    def test_deduplication(self):
        files = [{"assembly": "GRCh38"}, {"assembly": "GRCh38"}, {"assembly": "mm10"}]
        assert _extract_assemblies(files) == ["GRCh38", "mm10"]

    def test_empty_list(self):
        assert _extract_assemblies([]) == []

    def test_skips_non_dict_items(self):
        files = [{"assembly": "GRCh38"}, "/files/ENCFF001AAA/", None, 42]
        assert _extract_assemblies(files) == ["GRCh38"]

    def test_skips_empty_assembly(self):
        files = [{"assembly": "GRCh38"}, {"assembly": ""}, {}]
        assert _extract_assemblies(files) == ["GRCh38"]

    def test_sorted_output(self):
        files = [{"assembly": "mm10"}, {"assembly": "GRCh38"}, {"assembly": "hg19"}]
        assert _extract_assemblies(files) == ["GRCh38", "hg19", "mm10"]


class TestExtractAuditCounts:
    """Tests for the _extract_audit_counts helper function."""

    def test_all_four_levels(self):
        data = {
            "audit": {
                "ERROR": [
                    {"category": "insufficient read depth", "detail": "...", "level": 60},
                    {"category": "missing controls", "detail": "...", "level": 60},
                ],
                "NOT_COMPLIANT": [
                    {"category": "NRF below threshold", "detail": "...", "level": 45},
                ],
                "WARNING": [
                    {"category": "low read depth", "detail": "...", "level": 30},
                    {"category": "mild bias", "detail": "...", "level": 30},
                    {"category": "short reads", "detail": "...", "level": 30},
                ],
                "INTERNAL_ACTION": [
                    {"category": "needs review", "detail": "...", "level": 20},
                ],
            }
        }
        counts = _extract_audit_counts(data)
        assert counts["error"] == 2
        assert counts["not_compliant"] == 1
        assert counts["warning"] == 3
        assert counts["internal_action"] == 1

    def test_missing_audit_key(self):
        counts = _extract_audit_counts({})
        assert counts == {"error": 0, "not_compliant": 0, "warning": 0, "internal_action": 0}

    def test_audit_not_dict(self):
        counts = _extract_audit_counts({"audit": "malformed"})
        assert counts == {"error": 0, "not_compliant": 0, "warning": 0, "internal_action": 0}

    def test_partial_levels(self):
        data = {"audit": {"WARNING": [{"category": "w1"}]}}
        counts = _extract_audit_counts(data)
        assert counts["warning"] == 1
        assert counts["error"] == 0
        assert counts["not_compliant"] == 0
        assert counts["internal_action"] == 0

    def test_empty_audit_dict(self):
        counts = _extract_audit_counts({"audit": {}})
        assert counts == {"error": 0, "not_compliant": 0, "warning": 0, "internal_action": 0}

    def test_audit_level_non_list_value(self):
        """Non-list audit level values (dict, string) are treated as 0."""
        data = {
            "audit": {
                "ERROR": {"category": "foo"},  # dict, not list
                "WARNING": "malformed",  # string, not list
                "NOT_COMPLIANT": [{"category": "nc1"}],  # correct list
            }
        }
        counts = _extract_audit_counts(data)
        assert counts["error"] == 0  # dict treated as 0
        assert counts["warning"] == 0  # string treated as 0
        assert counts["not_compliant"] == 1  # list counted correctly

    def test_audit_level_integer_value(self):
        """Integer audit level value is treated as 0."""
        data = {"audit": {"ERROR": 42, "WARNING": [{"category": "w1"}]}}
        counts = _extract_audit_counts(data)
        assert counts["error"] == 0
        assert counts["warning"] == 1


class TestExtractAssembliesNullSafety:
    """Tests for _extract_assemblies handling None/null input."""

    def test_none_input(self):
        assert _extract_assemblies(None) == []

    def test_files_null_in_summary(self):
        """ExperimentSummary.from_api handles files=null from API."""
        data = {"accession": "ENCSR000AAA", "files": None}
        exp = ExperimentSummary.from_api(data)
        assert exp.assembly == []
        assert exp.file_count == 0

    def test_files_null_in_detail(self):
        """ExperimentDetail.from_api handles files=null from API."""
        data = {"accession": "ENCSR000AAA", "files": None}
        detail = ExperimentDetail.from_api(data)
        assert detail.assembly == []


# ======================================================================
# check_filter_value edge cases
# ======================================================================


class TestCheckFilterValueEdgeCases:
    """Edge case tests for check_filter_value robustness."""

    def test_none_input_returns_none(self):
        """None input is treated as no-value (no warning)."""
        result = check_filter_value(None, ASSAY_TITLES, "assay_title")
        assert result is None

    def test_empty_string_returns_none(self):
        """Empty string is treated as no-value (no warning)."""
        result = check_filter_value("", ASSAY_TITLES, "assay_title")
        assert result is None

    def test_integer_input_returns_none(self):
        """Non-string input is treated as no-value (no warning)."""
        result = check_filter_value(123, ASSAY_TITLES, "assay_title")
        assert result is None

    def test_special_characters(self):
        """Values with special characters get a proper warning."""
        result = check_filter_value("ATAC-seq); DROP TABLE", ASSAY_TITLES, "assay_title")
        assert result is not None
        assert "not found" in result

    def test_unicode_value(self):
        """Unicode values are handled without error."""
        result = check_filter_value("Hépatocyte", ORGAN_SLIMS, "organ")
        assert result is not None
        assert "not found" in result

    def test_cache_returns_correct_value(self):
        """Cached map returns the correct case-corrected value."""
        result = check_filter_value("histone chip-seq", ASSAY_TITLES, "assay_title")
        assert result is not None
        assert "Histone ChIP-seq" in result


# ======================================================================
# ExperimentDetail None guards
# ======================================================================


class TestExperimentDetailNoneGuards:
    """Tests for None handling in related_series and documents."""

    def test_related_series_with_none_items(self):
        """None items in related_series are filtered out."""
        data = {
            "accession": "ENCSR000AAA",
            "related_series": [None, "ENCSRXXX001", None],
        }
        detail = ExperimentDetail.from_api(data)
        assert detail.related_series == ["ENCSRXXX001"]

    def test_documents_with_none_items(self):
        """None items in documents are filtered out."""
        data = {
            "accession": "ENCSR000AAA",
            "documents": [None, "/documents/abc123/", None],
        }
        detail = ExperimentDetail.from_api(data)
        assert detail.documents == ["/documents/abc123/"]

    def test_related_series_with_mixed_types(self):
        """related_series keeps str/dict, drops None/int/other types."""
        data = {
            "accession": "ENCSR000AAA",
            "related_series": [
                "ENCSRXXX001",
                {"accession": "ENCSRXXX002"},
                42,
                None,
            ],
        }
        detail = ExperimentDetail.from_api(data)
        assert "ENCSRXXX001" in detail.related_series
        assert "ENCSRXXX002" in detail.related_series
        assert len(detail.related_series) == 2  # int and None filtered out

    def test_documents_with_dict_items(self):
        """documents handles both string and dict items."""
        data = {
            "accession": "ENCSR000AAA",
            "documents": [
                "/documents/abc123/",
                {"@id": "/documents/def456/"},
            ],
        }
        detail = ExperimentDetail.from_api(data)
        assert "/documents/abc123/" in detail.documents
        assert "/documents/def456/" in detail.documents


# ======================================================================
# ExperimentDetail assembly source consistency
# ======================================================================


class TestExperimentDetailAssemblySource:
    """Tests that assembly extraction uses the files parameter when provided."""

    def test_assembly_from_files_param_when_provided(self):
        """When files= is passed, assembly should reflect those files, not data['files']."""
        data = {
            "accession": "ENCSR000AAA",
            "files": [{"assembly": "hg19"}],
        }
        files_param = [{"accession": "ENCFF001", "file_format": "bed", "assembly": "GRCh38"}]
        detail = ExperimentDetail.from_api(data, files=files_param)
        assert "GRCh38" in detail.assembly
        assert "hg19" not in detail.assembly

    def test_assembly_from_data_when_no_files_param(self):
        """When files= is not passed, assembly should use data['files']."""
        data = {
            "accession": "ENCSR000AAA",
            "files": [{"assembly": "mm10"}],
        }
        detail = ExperimentDetail.from_api(data)
        assert detail.assembly == ["mm10"]
