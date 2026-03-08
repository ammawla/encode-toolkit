"""Tests for MCP tool OUTPUT structure validation.

The existing test suite (test_server.py, test_client.py, etc.) validates inputs.
These tests validate that tool responses have the correct JSON structure, required
fields, pagination metadata, and format compliance.

All tool functions are async and return JSON strings. Tests mock _get_client()
and _get_tracker() to inject realistic ENCODE data without network calls.
"""

import asyncio
import csv
import io
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from encode_connector.client.models import ExperimentSummary, FileSummary
from encode_connector.server.main import mcp

# ---------------------------------------------------------------------------
# Realistic mock data builders
# ---------------------------------------------------------------------------


def _mock_experiment_summary(**overrides) -> ExperimentSummary:
    """Build a realistic ExperimentSummary for mocking."""
    defaults = {
        "accession": "ENCSR133RZO",
        "assay_title": "Histone ChIP-seq",
        "target": "H3K27ac-human",
        "biosample_summary": "pancreas tissue male adult (54 years)",
        "organism": "Homo sapiens",
        "organ": "pancreas",
        "biosample_type": "tissue",
        "status": "released",
        "date_released": "2020-02-14",
        "description": "H3K27ac ChIP-seq on human pancreas",
        "lab": "Bing Ren, UCSD",
        "file_count": 42,
        "replication_type": "isogenic",
        "life_stage": "adult",
        "assembly": ["GRCh38"],
        "audit_error_count": 0,
        "audit_warning_count": 1,
        "dbxrefs": ["GEO:GSE ENCODE"],
        "url": "https://www.encodeproject.org/experiments/ENCSR133RZO/",
    }
    defaults.update(overrides)
    return ExperimentSummary(**defaults)


def _mock_file_summary(**overrides) -> FileSummary:
    """Build a realistic FileSummary for mocking."""
    defaults = {
        "accession": "ENCFF635JIA",
        "file_format": "bed",
        "file_type": "bed narrowPeak",
        "output_type": "IDR thresholded peaks",
        "output_category": "annotation",
        "file_size": 1048576,
        "file_size_human": "1.0 MB",
        "assembly": "GRCh38",
        "biological_replicates": [1, 2],
        "technical_replicates": ["1_1", "2_1"],
        "status": "released",
        "download_url": "https://www.encodeproject.org/files/ENCFF635JIA/@@download/ENCFF635JIA.bed.gz",
        "s3_uri": "s3://encode-public/2020/02/14/abcdef-1234/ENCFF635JIA.bed.gz",
        "md5sum": "d41d8cd98f00b204e9800998ecf8427e",
        "experiment_accession": "ENCSR133RZO",
        "experiment_assay": "Histone ChIP-seq",
        "biosample_summary": "pancreas tissue male adult (54 years)",
        "preferred_default": True,
        "date_created": "2020-02-14T00:00:00.000000+00:00",
    }
    defaults.update(overrides)
    return FileSummary(**defaults)


def _make_search_result(experiments: list[ExperimentSummary], total: int = 100) -> dict:
    """Build the dict that EncodeClient.search_experiments returns."""
    return {
        "results": experiments,
        "total": total,
        "limit": 25,
        "offset": 0,
    }


def _make_file_search_result(files: list[FileSummary], total: int = 50) -> dict:
    """Build the dict that EncodeClient.search_files returns."""
    return {
        "results": files,
        "total": total,
        "limit": 25,
        "offset": 0,
    }


# ======================================================================
# 1. Tool Annotation Tests
# ======================================================================


class TestToolAnnotations:
    """Validate that all registered tools have required MCP annotations."""

    def _get_tools(self):
        return mcp._tool_manager.list_tools()

    def test_all_tools_have_titles(self):
        """Every tool must have a title for display in Claude UI."""
        tools = self._get_tools()
        assert len(tools) == 20, f"Expected 20 tools, got {len(tools)}"
        for tool in tools:
            # FastMCP stores title on the Tool object itself (not inside annotations)
            assert tool.title, f"Tool {tool.name} missing title"

    def test_all_tools_have_hint_annotations(self):
        """Every tool must declare readOnlyHint so Claude knows side-effect status."""
        tools = self._get_tools()
        for tool in tools:
            assert tool.annotations is not None, f"Tool {tool.name} missing annotations"
            # readOnlyHint must be explicitly set (True or False)
            assert tool.annotations.readOnlyHint is not None, f"Tool {tool.name} missing readOnlyHint"
            # destructiveHint must also be set
            assert tool.annotations.destructiveHint is not None, f"Tool {tool.name} missing destructiveHint"

    def test_tool_names_under_64_chars(self):
        """Anthropic requires tool names under 64 characters."""
        tools = self._get_tools()
        for tool in tools:
            assert len(tool.name) < 64, f"Tool name too long ({len(tool.name)} chars): {tool.name}"


# ======================================================================
# 2. Search Tool Response Tests
# ======================================================================


class TestSearchResponses:
    """Validate output structure of search/discovery tools."""

    @pytest.mark.asyncio
    async def test_search_experiments_response_structure(self):
        """Search results must include total, results list, pagination keys."""
        mock_client = AsyncMock()
        mock_client.search_experiments.return_value = _make_search_result(
            [_mock_experiment_summary(), _mock_experiment_summary(accession="ENCSR000AKS")],
            total=100,
        )

        with patch("encode_connector.server.main._get_client", new=AsyncMock(return_value=mock_client)):
            from encode_connector.server.main import encode_search_experiments

            raw = await encode_search_experiments(
                assay_title="Histone ChIP-seq",
                organ="pancreas",
            )

        data = json.loads(raw)

        # Required top-level keys
        assert "results" in data
        assert "total" in data
        assert "has_more" in data
        assert "next_offset" in data

        # Pagination consistency
        assert isinstance(data["total"], int)
        assert isinstance(data["has_more"], bool)
        assert data["total"] == 100
        assert data["has_more"] is True
        assert data["next_offset"] == 25

        # Each result must have core experiment fields
        for exp in data["results"]:
            assert "accession" in exp
            assert exp["accession"].startswith("ENCSR")
            assert "assay_title" in exp
            assert "organism" in exp
            assert "url" in exp

    @pytest.mark.asyncio
    async def test_search_experiments_empty_returns_suggestion(self):
        """Empty results must include a helpful suggestion key."""
        mock_client = AsyncMock()
        mock_client.search_experiments.return_value = _make_search_result([], total=0)

        with patch("encode_connector.server.main._get_client", new=AsyncMock(return_value=mock_client)):
            from encode_connector.server.main import encode_search_experiments

            raw = await encode_search_experiments(
                assay_title="nonexistent_assay",
                organ="nonexistent_organ",
            )

        data = json.loads(raw)
        assert data["total"] == 0
        assert "suggestion" in data
        assert "encode_get_facets" in data["suggestion"]

    @pytest.mark.asyncio
    async def test_get_facets_response_structure(self):
        """Facets must return a dict of field -> list of {term, count}."""
        mock_client = AsyncMock()
        mock_client.search_facets.return_value = {
            "assay_title": [
                {"term": "Histone ChIP-seq", "count": 3421},
                {"term": "ATAC-seq", "count": 1205},
            ],
            "biosample_ontology.classification": [
                {"term": "tissue", "count": 812},
                {"term": "cell line", "count": 2156},
            ],
        }

        with patch("encode_connector.server.main._get_client", new=AsyncMock(return_value=mock_client)):
            from encode_connector.server.main import encode_get_facets

            raw = await encode_get_facets(organ="pancreas")

        data = json.loads(raw)

        # Must be a dict of facet fields
        assert isinstance(data, dict)
        assert len(data) > 0

        # Each facet must have term + count entries
        for field, terms in data.items():
            assert isinstance(terms, list), f"Facet {field} should be a list"
            for entry in terms:
                assert "term" in entry
                assert "count" in entry
                assert isinstance(entry["count"], int)

    @pytest.mark.asyncio
    async def test_get_metadata_response_structure(self):
        """Metadata must return values list, metadata_type, and count."""
        mock_client = MagicMock()
        mock_client.get_metadata.return_value = [
            "Histone ChIP-seq",
            "TF ChIP-seq",
            "ATAC-seq",
            "DNase-seq",
            "RNA-seq",
            "total RNA-seq",
            "WGBS",
            "Hi-C",
        ]

        with patch("encode_connector.server.main._get_client", new=AsyncMock(return_value=mock_client)):
            from encode_connector.server.main import encode_get_metadata

            raw = await encode_get_metadata(metadata_type="assays")

        data = json.loads(raw)
        assert "metadata_type" in data
        assert data["metadata_type"] == "assays"
        assert "values" in data
        assert isinstance(data["values"], list)
        assert "count" in data
        assert data["count"] == len(data["values"])
        assert data["count"] > 0


# ======================================================================
# 3. File Tool Response Tests
# ======================================================================


class TestFileResponses:
    """Validate output structure of file listing/search tools."""

    @pytest.mark.asyncio
    async def test_list_files_response_structure(self):
        """File listings must return list of objects with accession, format, size, download_url."""
        mock_client = AsyncMock()
        mock_client.list_files.return_value = [
            _mock_file_summary(),
            _mock_file_summary(
                accession="ENCFF388RZD",
                file_format="bigWig",
                file_type="bigWig",
                output_type="fold change over control",
                output_category="signal",
                file_size=52428800,
                file_size_human="50.0 MB",
                md5sum="a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
            ),
        ]

        with patch("encode_connector.server.main._get_client", new=AsyncMock(return_value=mock_client)):
            from encode_connector.server.main import encode_list_files

            raw = await encode_list_files(experiment_accession="ENCSR133RZO")

        data = json.loads(raw)

        # Must be a list
        assert isinstance(data, list)
        assert len(data) == 2

        # Each file must have required fields
        for f in data:
            assert "accession" in f
            assert f["accession"].startswith("ENCFF")
            assert "file_format" in f
            assert "file_size" in f
            assert isinstance(f["file_size"], int)
            assert "download_url" in f
            assert f["download_url"].startswith("https://")
            assert "md5sum" in f
            assert "assembly" in f

    @pytest.mark.asyncio
    async def test_search_files_response_structure(self):
        """Cross-experiment file search must include total and pagination."""
        mock_client = AsyncMock()
        mock_client.search_files.return_value = _make_file_search_result(
            [_mock_file_summary(), _mock_file_summary(accession="ENCFF222ABC")],
            total=50,
        )

        with patch("encode_connector.server.main._get_client", new=AsyncMock(return_value=mock_client)):
            from encode_connector.server.main import encode_search_files

            raw = await encode_search_files(
                file_format="bed",
                assay_title="Histone ChIP-seq",
                organ="pancreas",
            )

        data = json.loads(raw)

        assert "results" in data
        assert "total" in data
        assert "has_more" in data
        assert "next_offset" in data
        assert data["total"] == 50
        assert data["has_more"] is True

        for f in data["results"]:
            assert "accession" in f
            assert "file_format" in f
            assert "download_url" in f

    @pytest.mark.asyncio
    async def test_get_file_info_response_structure(self):
        """File info must include accession, format, size, md5sum, download_url."""
        mock_client = AsyncMock()
        mock_client.get_file_info.return_value = _mock_file_summary(
            accession="ENCFF635JIA",
            file_format="bed",
            file_size=1048576,
            md5sum="d41d8cd98f00b204e9800998ecf8427e",
        )

        with patch("encode_connector.server.main._get_client", new=AsyncMock(return_value=mock_client)):
            from encode_connector.server.main import encode_get_file_info

            raw = await encode_get_file_info(accession="ENCFF635JIA")

        data = json.loads(raw)

        assert data["accession"] == "ENCFF635JIA"
        assert data["file_format"] == "bed"
        assert data["file_size"] == 1048576
        assert data["file_size_human"] == "1.0 MB"
        assert data["md5sum"] == "d41d8cd98f00b204e9800998ecf8427e"
        assert "download_url" in data
        assert "assembly" in data
        assert "experiment_accession" in data


# ======================================================================
# 4. Tracking Tool Response Tests
# ======================================================================


class TestTrackingResponses:
    """Validate output structure of local tracker tools."""

    @pytest.mark.asyncio
    async def test_track_experiment_response_structure(self):
        """Tracking result must confirm success with tracking and publications keys."""
        mock_client = AsyncMock()
        # Simulate the raw ENCODE API response for experiment fetch
        mock_client.get_experiment_raw.return_value = {
            "accession": "ENCSR133RZO",
            "assay_title": "Histone ChIP-seq",
            "target": {"label": "H3K27ac"},
            "biosample_summary": "pancreas tissue male adult (54 years)",
            "status": "released",
            "date_released": "2020-02-14",
            "description": "H3K27ac ChIP-seq on human pancreas",
            "lab": {"title": "Bing Ren, UCSD"},
            "award": {"project": "ENCODE"},
            "biosample_ontology": {
                "classification": "tissue",
                "organ_slims": ["pancreas"],
            },
            "organism": {"scientific_name": "Homo sapiens"},
            "replication_type": "isogenic",
            "dbxrefs": ["GEO:GSE PancChIP"],
            "references": [],
            "analyses": [],
            "files": [],
        }

        mock_tracker = MagicMock()
        mock_tracker.track_experiment.return_value = {
            "accession": "ENCSR133RZO",
            "action": "tracked",
        }
        mock_tracker.add_note.return_value = True
        mock_tracker.store_publications.return_value = 0
        mock_tracker.store_pipeline_info.return_value = 0
        mock_tracker.link_reference.return_value = {"action": "linked"}

        with (
            patch("encode_connector.server.main._get_client", new=AsyncMock(return_value=mock_client)),
            patch("encode_connector.server.main._get_tracker", return_value=mock_tracker),
        ):
            from encode_connector.server.main import encode_track_experiment

            raw = await encode_track_experiment(accession="ENCSR133RZO")

        data = json.loads(raw)

        # Must have tracking result
        assert "tracking" in data
        assert data["tracking"]["accession"] == "ENCSR133RZO"
        assert data["tracking"]["action"] in ("tracked", "updated")

        # Must report publication and pipeline counts
        assert "publications_found" in data
        assert isinstance(data["publications_found"], int)
        assert "pipelines_found" in data
        assert isinstance(data["pipelines_found"], int)

    @pytest.mark.asyncio
    async def test_export_data_csv_format(self):
        """CSV export must be valid CSV with a header row and correct columns."""
        mock_tracker = MagicMock()
        # Simulate the tracker returning a proper CSV
        csv_header = "accession,assay_title,target,organism,organ,biosample_type,biosample_summary,lab,assembly,status,date_released,replication_type,life_stage,publication_count,pmids,derived_file_count,external_reference_count"
        csv_row = 'ENCSR133RZO,Histone ChIP-seq,H3K27ac,Homo sapiens,pancreas,tissue,"pancreas tissue male adult (54 years)","Bing Ren, UCSD",GRCh38,released,2020-02-14,isogenic,adult,2,32728249;33219093,1,3'
        mock_tracker.export_tracked_data.return_value = f"{csv_header}\n{csv_row}"

        with patch("encode_connector.server.main._get_tracker", return_value=mock_tracker):
            from encode_connector.server.main import encode_export_data

            raw = await encode_export_data(format="csv")

        # Must be parseable as CSV
        reader = csv.reader(io.StringIO(raw))
        rows = list(reader)
        assert len(rows) >= 2, "CSV must have header + at least 1 data row"

        headers = rows[0]
        assert "accession" in headers
        assert "assay_title" in headers
        assert "organism" in headers
        assert "publication_count" in headers

        # Data row accession must be an ENCODE accession
        data_row = rows[1]
        assert data_row[0].startswith("ENCSR")

    @pytest.mark.asyncio
    async def test_get_citations_bibtex_format(self):
        """BibTeX export must contain @article entries with required fields."""
        mock_tracker = MagicMock()
        mock_tracker.export_citations_bibtex.return_value = (
            "@article{32728249,\n"
            "  title = {An atlas of gene regulatory elements in adult mouse cerebrum},\n"
            "  author = {Li YE, Preissl S, Hou X},\n"
            "  journal = {Nature},\n"
            "  year = {2021},\n"
            "  doi = {10.1038/s41586-021-03604-1},\n"
            "  pmid = {32728249},\n"
            "  note = {ENCODE experiment: ENCSR133RZO},\n"
            "}"
        )

        with patch("encode_connector.server.main._get_tracker", return_value=mock_tracker):
            from encode_connector.server.main import encode_get_citations

            raw = await encode_get_citations(
                accession="ENCSR133RZO",
                export_format="bibtex",
            )

        # Must contain BibTeX @article entries
        assert "@article{" in raw
        assert "title =" in raw
        assert "author =" in raw
        assert "journal =" in raw
        assert "year =" in raw


# ======================================================================
# 5. Provenance Tool Response Tests
# ======================================================================


class TestProvenanceResponses:
    """Validate output structure of provenance and reference linking tools."""

    @pytest.mark.asyncio
    async def test_log_derived_file_response(self):
        """Logging must return success flag and provenance record ID."""
        mock_tracker = MagicMock()
        mock_tracker.log_derived_file.return_value = 42

        with patch("encode_connector.server.main._get_tracker", return_value=mock_tracker):
            from encode_connector.server.main import encode_log_derived_file

            raw = await encode_log_derived_file(
                file_path="/data/encode/filtered_peaks.bed",
                source_accessions=["ENCSR133RZO", "ENCFF635JIA"],
                description="Filtered H3K27ac peaks in pancreas",
                file_type="filtered_peaks",
                tool_used="bedtools intersect",
                parameters="-wa -wb -f 0.5",
            )

        data = json.loads(raw)

        assert data["success"] is True
        assert "record_id" in data
        assert isinstance(data["record_id"], int)
        assert data["record_id"] == 42
        assert data["file_path"] == "/data/encode/filtered_peaks.bed"
        assert "ENCSR133RZO" in data["source_accessions"]
        assert "ENCFF635JIA" in data["source_accessions"]
        assert "message" in data
        assert "encode_get_provenance" in data["message"]

    @pytest.mark.asyncio
    async def test_link_reference_response(self):
        """Linking must confirm success with action, accession, and ref type."""
        mock_tracker = MagicMock()
        mock_tracker.link_reference.return_value = {
            "action": "linked",
            "experiment_accession": "ENCSR133RZO",
            "reference_type": "pmid",
            "reference_id": "32728249",
        }

        with patch("encode_connector.server.main._get_tracker", return_value=mock_tracker):
            from encode_connector.server.main import encode_link_reference

            raw = await encode_link_reference(
                experiment_accession="ENCSR133RZO",
                reference_type="pmid",
                reference_id="32728249",
                description="Primary publication for this ChIP-seq dataset",
            )

        data = json.loads(raw)

        assert data["action"] == "linked"
        assert data["experiment_accession"] == "ENCSR133RZO"
        assert data["reference_type"] == "pmid"
        assert data["reference_id"] == "32728249"


# ======================================================================
# 6. Additional Response Structure Tests
# ======================================================================


class TestAdditionalResponses:
    """Additional output structure tests for edge cases and key tools."""

    @pytest.mark.asyncio
    async def test_list_tracked_response_structure(self):
        """List tracked experiments must return experiments array, count, stats."""
        mock_tracker = MagicMock()
        mock_tracker.list_tracked_experiments.return_value = [
            {"accession": "ENCSR133RZO"},
            {"accession": "ENCSR000AKS"},
        ]
        mock_tracker.get_metadata_table.return_value = [
            {
                "accession": "ENCSR133RZO",
                "assay_title": "Histone ChIP-seq",
                "organism": "Homo sapiens",
                "organ": "pancreas",
                "publication_count": 2,
                "derived_file_count": 1,
            },
            {
                "accession": "ENCSR000AKS",
                "assay_title": "ATAC-seq",
                "organism": "Homo sapiens",
                "organ": "brain",
                "publication_count": 0,
                "derived_file_count": 0,
            },
        ]
        mock_tracker.stats = {
            "tracked_experiments": 2,
            "publications": 2,
            "pipeline_records": 1,
            "quality_metrics": 0,
            "derived_files": 1,
            "external_references": 3,
            "db_path": "/tmp/test_tracker.db",
        }

        with patch("encode_connector.server.main._get_tracker", return_value=mock_tracker):
            from encode_connector.server.main import encode_list_tracked

            raw = await encode_list_tracked()

        data = json.loads(raw)

        assert "experiments" in data
        assert "count" in data
        assert "stats" in data
        assert data["count"] == 2
        assert isinstance(data["experiments"], list)
        assert data["stats"]["tracked_experiments"] == 2

    @pytest.mark.asyncio
    async def test_get_references_response_structure(self):
        """Get references must return references list and count."""
        mock_tracker = MagicMock()
        mock_tracker.get_references.return_value = [
            {
                "id": 1,
                "experiment_accession": "ENCSR133RZO",
                "reference_type": "pmid",
                "reference_id": "32728249",
                "description": "Primary publication",
                "linked_at": 1709856000.0,
            },
            {
                "id": 2,
                "experiment_accession": "ENCSR133RZO",
                "reference_type": "geo_accession",
                "reference_id": "GSE PancChIP",
                "description": "Auto-extracted from ENCODE dbxrefs",
                "linked_at": 1709856001.0,
            },
        ]

        with patch("encode_connector.server.main._get_tracker", return_value=mock_tracker):
            from encode_connector.server.main import encode_get_references

            raw = await encode_get_references(experiment_accession="ENCSR133RZO")

        data = json.loads(raw)

        assert "references" in data
        assert "count" in data
        assert data["count"] == 2
        assert isinstance(data["references"], list)

        for ref in data["references"]:
            assert "experiment_accession" in ref
            assert "reference_type" in ref
            assert "reference_id" in ref

    @pytest.mark.asyncio
    async def test_search_files_empty_returns_suggestion(self):
        """Empty file search should include suggestion text."""
        mock_client = AsyncMock()
        mock_client.search_files.return_value = _make_file_search_result([], total=0)

        with patch("encode_connector.server.main._get_client", new=AsyncMock(return_value=mock_client)):
            from encode_connector.server.main import encode_search_files

            raw = await encode_search_files(
                file_format="nonexistent_format",
            )

        data = json.loads(raw)
        assert data["total"] == 0
        assert "suggestion" in data
        assert "encode_get_metadata" in data["suggestion"]

    @pytest.mark.asyncio
    async def test_get_citations_json_format(self):
        """JSON citation export must return publications list with count."""
        mock_tracker = MagicMock()
        mock_tracker.get_publications.return_value = [
            {
                "id": 1,
                "experiment_accession": "ENCSR133RZO",
                "pmid": "32728249",
                "doi": "10.1038/s41586-021-03604-1",
                "title": "An atlas of gene regulatory elements in adult mouse cerebrum",
                "authors": "Li YE, Preissl S, Hou X",
                "journal": "Nature",
                "year": "2021",
                "abstract": "The mammalian cerebrum...",
            },
        ]

        with patch("encode_connector.server.main._get_tracker", return_value=mock_tracker):
            from encode_connector.server.main import encode_get_citations

            raw = await encode_get_citations(
                accession="ENCSR133RZO",
                export_format="json",
            )

        data = json.loads(raw)
        assert "publications" in data
        assert "count" in data
        assert data["count"] == 1

        pub = data["publications"][0]
        assert "pmid" in pub
        assert "doi" in pub
        assert "title" in pub
        assert "authors" in pub
        assert "journal" in pub

    @pytest.mark.asyncio
    async def test_search_experiments_pagination_no_more(self):
        """When total <= offset + limit, has_more must be False and next_offset null."""
        mock_client = AsyncMock()
        mock_client.search_experiments.return_value = _make_search_result(
            [_mock_experiment_summary()],
            total=1,
        )

        with patch("encode_connector.server.main._get_client", new=AsyncMock(return_value=mock_client)):
            from encode_connector.server.main import encode_search_experiments

            raw = await encode_search_experiments(assay_title="Histone ChIP-seq")

        data = json.loads(raw)
        assert data["has_more"] is False
        assert data["next_offset"] is None


# ======================================================================
# 7. Helper Function Tests
# ======================================================================


class TestHelperFunctions:
    """Validate helper functions that manage global state."""

    @pytest.mark.asyncio
    async def test_get_client_lock_creates_lock(self):
        """_get_client_lock() must return an asyncio.Lock, creating one if needed."""
        with patch("encode_connector.server.main._client_lock", None):
            from encode_connector.server.main import _get_client_lock

            lock = _get_client_lock()
            assert isinstance(lock, asyncio.Lock)

    @pytest.mark.asyncio
    async def test_get_client_raises_when_none(self):
        """_get_client() must raise RuntimeError when client is not initialized."""
        with (
            patch("encode_connector.server.main._client", None),
            patch("encode_connector.server.main._client_lock", asyncio.Lock()),
        ):
            from encode_connector.server.main import _get_client

            with pytest.raises(RuntimeError, match="ENCODE client not initialized"):
                await _get_client()

    def test_get_downloader_raises_when_none(self):
        """_get_downloader() must raise RuntimeError when downloader is not initialized."""
        with patch("encode_connector.server.main._downloader", None):
            from encode_connector.server.main import _get_downloader

            with pytest.raises(RuntimeError, match="File downloader not initialized"):
                _get_downloader()

    def test_get_tracker_raises_when_none(self):
        """_get_tracker() must raise RuntimeError when tracker is not initialized."""
        with patch("encode_connector.server.main._tracker", None):
            from encode_connector.server.main import _get_tracker

            with pytest.raises(RuntimeError, match="Experiment tracker not initialized"):
                _get_tracker()

    @pytest.mark.asyncio
    async def test_lifespan_initializes_and_cleans_up(self):
        """lifespan context manager must set up and tear down global state."""
        import encode_connector.server.main as main_mod

        mock_client_instance = AsyncMock()
        mock_downloader_instance = MagicMock()
        mock_tracker_instance = MagicMock()

        with (
            patch.object(main_mod, "_credential_manager", MagicMock()),
            patch("encode_connector.server.main.EncodeClient", return_value=mock_client_instance),
            patch("encode_connector.server.main.FileDownloader", return_value=mock_downloader_instance),
            patch("encode_connector.server.main.ExperimentTracker", return_value=mock_tracker_instance),
        ):
            from encode_connector.server.main import lifespan
            from encode_connector.server.main import mcp as mcp_server

            # Save original state
            original_client = main_mod._client
            original_downloader = main_mod._downloader
            original_tracker = main_mod._tracker
            original_lock = main_mod._client_lock

            try:
                async with lifespan(mcp_server):
                    # Inside context: globals must be set
                    assert main_mod._client is mock_client_instance
                    assert main_mod._downloader is mock_downloader_instance
                    assert main_mod._tracker is mock_tracker_instance
                    assert isinstance(main_mod._client_lock, asyncio.Lock)

                # After context: cleanup called
                mock_client_instance.close.assert_awaited_once()
                mock_tracker_instance.close.assert_called_once()
            finally:
                # Restore original state
                main_mod._client = original_client
                main_mod._downloader = original_downloader
                main_mod._tracker = original_tracker
                main_mod._client_lock = original_lock


# ======================================================================
# 8. Get Experiment Response Tests
# ======================================================================


class TestGetExperimentResponse:
    """Validate output structure of encode_get_experiment."""

    @pytest.mark.asyncio
    async def test_get_experiment_response_structure(self):
        """encode_get_experiment must return JSON with full experiment detail fields."""
        from encode_connector.client.models import ExperimentDetail

        mock_detail = ExperimentDetail(
            accession="ENCSR133RZO",
            assay_title="Histone ChIP-seq",
            target="H3K27ac",
            biosample_summary="pancreas tissue male adult (54 years)",
            organism="Homo sapiens",
            organ="pancreas",
            biosample_type="tissue",
            status="released",
            date_released="2020-02-14",
            description="H3K27ac ChIP-seq on human pancreas",
            lab="Bing Ren, UCSD",
            award="ENCODE",
            url="https://www.encodeproject.org/experiments/ENCSR133RZO/",
        )

        mock_client = AsyncMock()
        mock_client.get_experiment.return_value = mock_detail

        with patch("encode_connector.server.main._get_client", new=AsyncMock(return_value=mock_client)):
            from encode_connector.server.main import encode_get_experiment

            raw = await encode_get_experiment(accession="ENCSR133RZO")

        data = json.loads(raw)
        assert data["accession"] == "ENCSR133RZO"
        assert data["assay_title"] == "Histone ChIP-seq"
        assert data["target"] == "H3K27ac"
        assert data["organism"] == "Homo sapiens"
        assert data["organ"] == "pancreas"
        assert data["status"] == "released"
        assert "url" in data


# ======================================================================
# 9. Download Files Response Tests
# ======================================================================


class TestDownloadFilesResponse:
    """Validate output structure of encode_download_files."""

    @pytest.mark.asyncio
    async def test_download_files_response_structure(self):
        """Download tool must return downloaded list, errors list, and summary."""
        from encode_connector.client.models import DownloadResult

        mock_file = _mock_file_summary(accession="ENCFF635JIA")
        mock_result = DownloadResult(
            accession="ENCFF635JIA",
            file_path="/tmp/test/ENCFF635JIA.bed.gz",
            file_size=1048576,
            success=True,
            md5_verified=True,
            error="",
        )

        mock_client = AsyncMock()
        mock_client.get_file_info.return_value = mock_file

        mock_downloader = AsyncMock()
        mock_downloader.download_batch.return_value = [mock_result]

        with (
            patch("encode_connector.server.main._get_client", new=AsyncMock(return_value=mock_client)),
            patch("encode_connector.server.main._get_downloader", return_value=mock_downloader),
        ):
            from encode_connector.server.main import encode_download_files

            raw = await encode_download_files(
                file_accessions=["ENCFF635JIA"],
                download_dir="/tmp/test",
            )

        data = json.loads(raw)
        assert "downloaded" in data
        assert "errors" in data
        assert "summary" in data
        assert isinstance(data["downloaded"], list)
        assert len(data["downloaded"]) == 1
        assert data["summary"]["total_requested"] == 1
        assert data["summary"]["successful"] == 1
        assert data["summary"]["failed"] == 0
        assert data["summary"]["total_size"] == 1048576
        assert "total_size_human" in data["summary"]

    @pytest.mark.asyncio
    async def test_download_files_with_file_info_error(self):
        """When get_file_info raises, error must appear in output errors list."""
        mock_client = AsyncMock()
        mock_client.get_file_info.side_effect = Exception("File not found: ENCFF000ZZZ")

        mock_downloader = AsyncMock()
        mock_downloader.download_batch.return_value = []

        with (
            patch("encode_connector.server.main._get_client", new=AsyncMock(return_value=mock_client)),
            patch("encode_connector.server.main._get_downloader", return_value=mock_downloader),
        ):
            from encode_connector.server.main import encode_download_files

            raw = await encode_download_files(
                file_accessions=["ENCFF000ZZZ"],
                download_dir="/tmp/test",
            )

        data = json.loads(raw)
        assert len(data["errors"]) == 1
        assert data["errors"][0]["accession"] == "ENCFF000ZZZ"
        assert "File not found" in data["errors"][0]["error"]
        assert data["summary"]["failed"] == 1


# ======================================================================
# 10. Batch Download Response Tests
# ======================================================================


class TestBatchDownloadResponse:
    """Validate output structure of encode_batch_download."""

    @pytest.mark.asyncio
    async def test_batch_download_dry_run_response(self):
        """Dry run must return preview with file_count, total_size, search_total, has_more."""
        mock_client = AsyncMock()
        # search_total (500) > limit (100) so has_more=True and next_offset=100
        mock_client.search_files.return_value = _make_file_search_result(
            [_mock_file_summary(), _mock_file_summary(accession="ENCFF222ABC")],
            total=500,
        )

        mock_downloader = MagicMock()
        mock_downloader.preview_downloads.return_value = {
            "file_count": 2,
            "total_size": 2097152,
            "total_size_human": "2.0 MB",
            "files": [
                {"accession": "ENCFF635JIA", "file_size": 1048576},
                {"accession": "ENCFF222ABC", "file_size": 1048576},
            ],
        }

        with (
            patch("encode_connector.server.main._get_client", new=AsyncMock(return_value=mock_client)),
            patch("encode_connector.server.main._get_downloader", return_value=mock_downloader),
        ):
            from encode_connector.server.main import encode_batch_download

            raw = await encode_batch_download(
                download_dir="/tmp/test",
                file_format="bed",
                assay_title="Histone ChIP-seq",
                organ="pancreas",
                dry_run=True,
            )

        data = json.loads(raw)
        assert "message" in data
        assert "dry_run=False" in data["message"]
        assert data["file_count"] == 2
        assert data["total_size"] == 2097152
        assert data["search_total"] == 500
        assert data["has_more"] is True
        assert data["next_offset"] == 100

    @pytest.mark.asyncio
    async def test_batch_download_actual_download_response(self):
        """Actual download must return downloaded list and summary with counts."""
        from encode_connector.client.models import DownloadResult

        mock_file = _mock_file_summary(accession="ENCFF635JIA")
        mock_result = DownloadResult(
            accession="ENCFF635JIA",
            file_path="/tmp/test/ENCFF635JIA.bed.gz",
            file_size=1048576,
            success=True,
            md5_verified=True,
            error="",
        )

        mock_client = AsyncMock()
        mock_client.search_files.return_value = _make_file_search_result(
            [mock_file],
            total=1,
        )

        mock_downloader = AsyncMock()
        mock_downloader.download_batch.return_value = [mock_result]

        with (
            patch("encode_connector.server.main._get_client", new=AsyncMock(return_value=mock_client)),
            patch("encode_connector.server.main._get_downloader", return_value=mock_downloader),
        ):
            from encode_connector.server.main import encode_batch_download

            raw = await encode_batch_download(
                download_dir="/tmp/test",
                file_format="bed",
                dry_run=False,
            )

        data = json.loads(raw)
        assert "downloaded" in data
        assert "summary" in data
        assert data["summary"]["total_found"] == 1
        assert data["summary"]["total_downloaded"] == 1
        assert data["summary"]["successful"] == 1
        assert data["summary"]["failed"] == 0
        assert data["summary"]["total_size"] == 1048576
        assert "total_size_human" in data["summary"]
        assert data["has_more"] is False
        assert data["next_offset"] is None

    @pytest.mark.asyncio
    async def test_batch_download_empty_search(self):
        """Empty search result must return 'No files found' message with suggestion."""
        mock_client = AsyncMock()
        mock_client.search_files.return_value = _make_file_search_result([], total=0)

        mock_downloader = MagicMock()

        with (
            patch("encode_connector.server.main._get_client", new=AsyncMock(return_value=mock_client)),
            patch("encode_connector.server.main._get_downloader", return_value=mock_downloader),
        ):
            from encode_connector.server.main import encode_batch_download

            raw = await encode_batch_download(
                download_dir="/tmp/test",
                file_format="nonexistent_format",
            )

        data = json.loads(raw)
        assert "No files found" in data["message"]
        assert data["total"] == 0
        assert data["has_more"] is False
        assert "suggestion" in data


# ======================================================================
# 11. Manage Credentials Response Tests
# ======================================================================


class TestManageCredentialsResponse:
    """Validate output structure of encode_manage_credentials."""

    @pytest.mark.asyncio
    async def test_credentials_store(self):
        """Store action must return success with message about storage location."""
        mock_cred_mgr = MagicMock()
        mock_cred_mgr.store_credentials.return_value = "os_keyring"

        mock_client_instance = AsyncMock()

        with (
            patch("encode_connector.server.main._credential_manager", mock_cred_mgr),
            patch("encode_connector.server.main._get_client_lock", return_value=asyncio.Lock()),
            patch("encode_connector.server.main._client", mock_client_instance),
            patch("encode_connector.server.main.EncodeClient", return_value=AsyncMock()),
        ):
            from encode_connector.server.main import encode_manage_credentials

            raw = await encode_manage_credentials(
                action="store",
                access_key="ABCDEF",
                secret_key="secretkey123",
            )

        data = json.loads(raw)
        assert data["success"] is True
        assert "os_keyring" in data["message"]
        mock_cred_mgr.store_credentials.assert_called_once_with("ABCDEF", "secretkey123")

    @pytest.mark.asyncio
    async def test_credentials_store_missing_keys(self):
        """Store action without access_key must return error."""
        with (
            patch("encode_connector.server.main._credential_manager", MagicMock()),
            patch("encode_connector.server.main._get_client_lock", return_value=asyncio.Lock()),
        ):
            from encode_connector.server.main import encode_manage_credentials

            raw = await encode_manage_credentials(
                action="store",
                access_key=None,
                secret_key=None,
            )

        data = json.loads(raw)
        assert "error" in data
        assert "access_key" in data["error"]
        assert "help" in data

    @pytest.mark.asyncio
    async def test_credentials_check_configured(self):
        """Check action when credentials exist must report configured."""
        mock_cred_mgr = MagicMock()
        mock_cred_mgr.has_credentials = True

        with patch("encode_connector.server.main._credential_manager", mock_cred_mgr):
            from encode_connector.server.main import encode_manage_credentials

            raw = await encode_manage_credentials(action="check")

        data = json.loads(raw)
        assert data["credentials_configured"] is True
        assert "configured" in data["message"]

    @pytest.mark.asyncio
    async def test_credentials_check_not_configured(self):
        """Check action when no credentials must report not configured."""
        mock_cred_mgr = MagicMock()
        mock_cred_mgr.has_credentials = False

        with patch("encode_connector.server.main._credential_manager", mock_cred_mgr):
            from encode_connector.server.main import encode_manage_credentials

            raw = await encode_manage_credentials(action="check")

        data = json.loads(raw)
        assert data["credentials_configured"] is False
        assert "No credentials" in data["message"]

    @pytest.mark.asyncio
    async def test_credentials_clear(self):
        """Clear action must return success confirmation."""
        mock_cred_mgr = MagicMock()
        mock_client_instance = AsyncMock()

        with (
            patch("encode_connector.server.main._credential_manager", mock_cred_mgr),
            patch("encode_connector.server.main._get_client_lock", return_value=asyncio.Lock()),
            patch("encode_connector.server.main._client", mock_client_instance),
            patch("encode_connector.server.main.EncodeClient", return_value=AsyncMock()),
        ):
            from encode_connector.server.main import encode_manage_credentials

            raw = await encode_manage_credentials(action="clear")

        data = json.loads(raw)
        assert data["success"] is True
        assert "removed" in data["message"]
        mock_cred_mgr.clear_credentials.assert_called_once()


# ======================================================================
# 12. Get Facets Filter Tests
# ======================================================================


class TestGetFacetsFilters:
    """Validate that encode_get_facets passes all filters to the client."""

    @pytest.mark.asyncio
    async def test_get_facets_with_all_filters(self):
        """All four filter params must be forwarded to search_facets."""
        mock_client = AsyncMock()
        mock_client.search_facets.return_value = {
            "target.label": [{"term": "H3K27ac", "count": 120}],
        }

        with patch("encode_connector.server.main._get_client", new=AsyncMock(return_value=mock_client)):
            from encode_connector.server.main import encode_get_facets

            raw = await encode_get_facets(
                assay_title="Histone ChIP-seq",
                organism="Homo sapiens",
                organ="pancreas",
                biosample_type="tissue",
            )

        data = json.loads(raw)
        assert isinstance(data, dict)

        # Verify all filters were passed to search_facets
        call_kwargs = mock_client.search_facets.call_args
        assert call_kwargs.kwargs["assay_title"] == "Histone ChIP-seq"
        assert call_kwargs.kwargs["replicates.library.biosample.donor.organism.scientific_name"] == "Homo sapiens"
        assert call_kwargs.kwargs["biosample_ontology.organ_slims"] == "pancreas"
        assert call_kwargs.kwargs["biosample_ontology.classification"] == "tissue"


# ======================================================================
# 13. Track Experiment Edge Path Tests
# ======================================================================


class TestTrackExperimentEdgePaths:
    """Test edge-case code paths in encode_track_experiment."""

    def _make_base_exp_data(self, **overrides):
        """Build a base experiment raw data dict."""
        defaults = {
            "accession": "ENCSR133RZO",
            "assay_title": "Histone ChIP-seq",
            "target": {"label": "H3K27ac"},
            "biosample_summary": "pancreas tissue male adult (54 years)",
            "status": "released",
            "date_released": "2020-02-14",
            "description": "H3K27ac ChIP-seq on human pancreas",
            "lab": {"title": "Bing Ren, UCSD"},
            "award": {"project": "ENCODE"},
            "biosample_ontology": {
                "classification": "tissue",
                "organ_slims": ["pancreas"],
            },
            "organism": {"scientific_name": "Homo sapiens"},
            "replication_type": "isogenic",
            "dbxrefs": [],
            "references": [],
            "analyses": [],
            "files": [],
        }
        defaults.update(overrides)
        return defaults

    def _make_base_tracker(self):
        """Build a base mock tracker with standard return values."""
        mock_tracker = MagicMock()
        mock_tracker.track_experiment.return_value = {
            "accession": "ENCSR133RZO",
            "action": "tracked",
        }
        mock_tracker.add_note.return_value = True
        mock_tracker.store_publications.return_value = 0
        mock_tracker.store_pipeline_info.return_value = 0
        mock_tracker.link_reference.return_value = {"action": "linked"}
        return mock_tracker

    @pytest.mark.asyncio
    async def test_track_experiment_with_notes(self):
        """When notes are provided, tracker.add_note must be called."""
        mock_client = AsyncMock()
        mock_client.get_experiment_raw.return_value = self._make_base_exp_data()
        mock_tracker = self._make_base_tracker()

        with (
            patch("encode_connector.server.main._get_client", new=AsyncMock(return_value=mock_client)),
            patch("encode_connector.server.main._get_tracker", return_value=mock_tracker),
        ):
            from encode_connector.server.main import encode_track_experiment

            raw = await encode_track_experiment(accession="ENCSR133RZO", notes="Important dataset for review")

        data = json.loads(raw)
        assert data["tracking"]["accession"] == "ENCSR133RZO"
        mock_tracker.add_note.assert_called_once_with("ENCSR133RZO", "Important dataset for review")

    @pytest.mark.asyncio
    async def test_track_experiment_dbxrefs_pmid(self):
        """PMID in dbxrefs must be auto-linked via tracker.link_reference."""
        mock_client = AsyncMock()
        mock_client.get_experiment_raw.return_value = self._make_base_exp_data(
            dbxrefs=["PMID:12345"],
        )
        mock_tracker = self._make_base_tracker()

        with (
            patch("encode_connector.server.main._get_client", new=AsyncMock(return_value=mock_client)),
            patch("encode_connector.server.main._get_tracker", return_value=mock_tracker),
        ):
            from encode_connector.server.main import encode_track_experiment

            raw = await encode_track_experiment(accession="ENCSR133RZO")

        data = json.loads(raw)
        # Verify link_reference was called with PMID type
        pmid_calls = [
            c for c in mock_tracker.link_reference.call_args_list if c.args[1] == "pmid" and c.args[2] == "12345"
        ]
        assert len(pmid_calls) == 1
        assert "auto_linked_references" in data
        pmid_refs = [r for r in data["auto_linked_references"] if r["type"] == "pmid"]
        assert len(pmid_refs) == 1
        assert pmid_refs[0]["id"] == "12345"

    @pytest.mark.asyncio
    async def test_track_experiment_references_as_strings(self):
        """String reference paths must be resolved via client.get_json."""
        mock_client = AsyncMock()
        mock_client.get_experiment_raw.return_value = self._make_base_exp_data(
            references=["/publications/abcdef123456/"],
        )
        mock_client.get_json.return_value = {
            "title": "Test Publication",
            "identifiers": [{"identifier": "PMID:99999"}],
        }
        mock_tracker = self._make_base_tracker()

        with (
            patch("encode_connector.server.main._get_client", new=AsyncMock(return_value=mock_client)),
            patch("encode_connector.server.main._get_tracker", return_value=mock_tracker),
        ):
            from encode_connector.server.main import encode_track_experiment

            raw = await encode_track_experiment(accession="ENCSR133RZO")

        data = json.loads(raw)
        # client.get_json must have been called to resolve the string reference
        mock_client.get_json.assert_called()
        assert "publications_found" in data

    @pytest.mark.asyncio
    async def test_track_experiment_analyses_as_strings(self):
        """String analysis paths must be resolved via client.get_json."""
        mock_client = AsyncMock()
        mock_client.get_experiment_raw.return_value = self._make_base_exp_data(
            analyses=["/analyses/abcdef123456/"],
        )
        mock_client.get_json.return_value = {
            "pipeline": {"title": "ENCODE ChIP-seq pipeline"},
            "software_versions": [],
        }
        mock_tracker = self._make_base_tracker()

        with (
            patch("encode_connector.server.main._get_client", new=AsyncMock(return_value=mock_client)),
            patch("encode_connector.server.main._get_tracker", return_value=mock_tracker),
        ):
            from encode_connector.server.main import encode_track_experiment

            raw = await encode_track_experiment(accession="ENCSR133RZO")

        data = json.loads(raw)
        # client.get_json must have been called to resolve the string analysis
        assert mock_client.get_json.call_count >= 1
        assert "pipelines_found" in data


# ======================================================================
# 14. Get Citations Edge Path Tests
# ======================================================================


class TestGetCitationsEdgePaths:
    """Test RIS format and all-experiments JSON paths for encode_get_citations."""

    @pytest.mark.asyncio
    async def test_get_citations_ris_format(self):
        """RIS export must return raw RIS content."""
        mock_tracker = MagicMock()
        mock_tracker.export_citations_ris.return_value = (
            "TY  - JOUR\n"
            "AU  - Li YE\n"
            "TI  - An atlas of gene regulatory elements\n"
            "JO  - Nature\n"
            "PY  - 2021\n"
            "DO  - 10.1038/s41586-021-03604-1\n"
            "ER  -\n"
        )

        with patch("encode_connector.server.main._get_tracker", return_value=mock_tracker):
            from encode_connector.server.main import encode_get_citations

            raw = await encode_get_citations(
                accession="ENCSR133RZO",
                export_format="ris",
            )

        assert "TY  - JOUR" in raw
        assert "AU  - Li YE" in raw
        assert "ER  -" in raw

    @pytest.mark.asyncio
    async def test_get_citations_ris_empty(self):
        """RIS export with no publications must return 'No publications found.'."""
        mock_tracker = MagicMock()
        mock_tracker.export_citations_ris.return_value = ""

        with patch("encode_connector.server.main._get_tracker", return_value=mock_tracker):
            from encode_connector.server.main import encode_get_citations

            raw = await encode_get_citations(
                accession="ENCSR133RZO",
                export_format="ris",
            )

        assert raw == "No publications found."

    @pytest.mark.asyncio
    async def test_get_citations_json_all_experiments(self):
        """JSON export with no accession must aggregate pubs from all tracked experiments."""
        mock_tracker = MagicMock()
        mock_tracker.list_tracked_experiments.return_value = [
            {"accession": "ENCSR133RZO"},
            {"accession": "ENCSR000AKS"},
        ]
        # Return different pubs for each experiment
        mock_tracker.get_publications.side_effect = [
            [{"pmid": "11111", "title": "Paper A"}],
            [{"pmid": "22222", "title": "Paper B"}],
        ]

        with patch("encode_connector.server.main._get_tracker", return_value=mock_tracker):
            from encode_connector.server.main import encode_get_citations

            raw = await encode_get_citations(
                accession=None,
                export_format="json",
            )

        data = json.loads(raw)
        assert "publications" in data
        assert data["count"] == 2
        assert data["publications"][0]["pmid"] == "11111"
        assert data["publications"][1]["pmid"] == "22222"
        # list_tracked_experiments must have been called
        mock_tracker.list_tracked_experiments.assert_called_once()


# ======================================================================
# 15. Compare Experiments Response Tests
# ======================================================================


class TestCompareExperimentsResponse:
    """Validate output structure of encode_compare_experiments."""

    @pytest.mark.asyncio
    async def test_compare_experiments_response(self):
        """Compare tool must return compatibility analysis JSON."""
        mock_tracker = MagicMock()
        mock_tracker.analyze_compatibility.return_value = {
            "verdict": "compatible",
            "issues": [],
            "warnings": ["Different labs"],
            "recommendations": ["Batch correction recommended"],
            "experiment1": {"accession": "ENCSR133RZO", "assay_title": "Histone ChIP-seq"},
            "experiment2": {"accession": "ENCSR000AKS", "assay_title": "Histone ChIP-seq"},
        }

        with patch("encode_connector.server.main._get_tracker", return_value=mock_tracker):
            from encode_connector.server.main import encode_compare_experiments

            raw = await encode_compare_experiments(
                accession1="ENCSR133RZO",
                accession2="ENCSR000AKS",
            )

        data = json.loads(raw)
        assert data["verdict"] == "compatible"
        assert isinstance(data["issues"], list)
        assert isinstance(data["warnings"], list)
        assert isinstance(data["recommendations"], list)
        assert data["experiment1"]["accession"] == "ENCSR133RZO"
        assert data["experiment2"]["accession"] == "ENCSR000AKS"
        mock_tracker.analyze_compatibility.assert_called_once_with("ENCSR133RZO", "ENCSR000AKS")


# ======================================================================
# 16. Get Provenance Response Tests
# ======================================================================


class TestGetProvenanceResponse:
    """Validate output structure of encode_get_provenance."""

    @pytest.mark.asyncio
    async def test_get_provenance_by_file_path(self):
        """Provenance by file_path must return the provenance chain."""
        mock_tracker = MagicMock()
        mock_tracker.get_provenance_chain.return_value = {
            "file_path": "/data/encode/filtered_peaks.bed",
            "source_accessions": ["ENCSR133RZO", "ENCFF635JIA"],
            "description": "Filtered H3K27ac peaks",
            "tool_used": "bedtools intersect",
            "parameters": "-wa -wb -f 0.5",
        }

        with patch("encode_connector.server.main._get_tracker", return_value=mock_tracker):
            from encode_connector.server.main import encode_get_provenance

            raw = await encode_get_provenance(file_path="/data/encode/filtered_peaks.bed")

        data = json.loads(raw)
        assert data["file_path"] == "/data/encode/filtered_peaks.bed"
        assert "ENCSR133RZO" in data["source_accessions"]
        assert data["tool_used"] == "bedtools intersect"
        mock_tracker.get_provenance_chain.assert_called_once_with("/data/encode/filtered_peaks.bed")

    @pytest.mark.asyncio
    async def test_get_provenance_by_accession(self):
        """Provenance by source_accession must return derived_files list and count."""
        mock_tracker = MagicMock()
        mock_tracker.get_derived_files.return_value = [
            {
                "file_path": "/data/encode/filtered_peaks.bed",
                "description": "Filtered peaks",
            },
            {
                "file_path": "/data/encode/merged_signal.bw",
                "description": "Merged signal",
            },
        ]

        with patch("encode_connector.server.main._get_tracker", return_value=mock_tracker):
            from encode_connector.server.main import encode_get_provenance

            raw = await encode_get_provenance(source_accession="ENCSR133RZO")

        data = json.loads(raw)
        assert "derived_files" in data
        assert "count" in data
        assert data["count"] == 2
        assert len(data["derived_files"]) == 2
        mock_tracker.get_derived_files.assert_called_once_with("ENCSR133RZO")


# ======================================================================
# 17. Export Data Edge Tests
# ======================================================================


class TestExportDataEdge:
    """Test edge cases for encode_export_data."""

    @pytest.mark.asyncio
    async def test_export_data_empty_result(self):
        """Empty export result must return 'No tracked experiments found' message."""
        mock_tracker = MagicMock()
        mock_tracker.export_tracked_data.return_value = ""

        with patch("encode_connector.server.main._get_tracker", return_value=mock_tracker):
            from encode_connector.server.main import encode_export_data

            raw = await encode_export_data(format="csv")

        data = json.loads(raw)
        assert "No tracked experiments found" in data["message"]


# ======================================================================
# 18. Summarize Collection Response Tests
# ======================================================================


class TestSummarizeCollectionResponse:
    """Validate output structure of encode_summarize_collection."""

    @pytest.mark.asyncio
    async def test_summarize_collection_response(self):
        """Summarize must return grouped statistics JSON."""
        mock_tracker = MagicMock()
        mock_tracker.summarize_collection.return_value = {
            "total_experiments": 10,
            "by_assay": {"Histone ChIP-seq": 6, "ATAC-seq": 4},
            "by_organ": {"pancreas": 5, "brain": 5},
            "by_organism": {"Homo sapiens": 10},
            "total_publications": 15,
            "total_derived_files": 3,
        }

        with patch("encode_connector.server.main._get_tracker", return_value=mock_tracker):
            from encode_connector.server.main import encode_summarize_collection

            raw = await encode_summarize_collection()

        data = json.loads(raw)
        assert data["total_experiments"] == 10
        assert "by_assay" in data
        assert data["by_assay"]["Histone ChIP-seq"] == 6
        assert "by_organ" in data
        assert "by_organism" in data
        mock_tracker.summarize_collection.assert_called_once()

    @pytest.mark.asyncio
    async def test_summarize_collection_with_filters(self):
        """Summarize must pass filter params to tracker.summarize_collection."""
        mock_tracker = MagicMock()
        mock_tracker.summarize_collection.return_value = {
            "total_experiments": 3,
            "by_assay": {"Histone ChIP-seq": 3},
        }

        with patch("encode_connector.server.main._get_tracker", return_value=mock_tracker):
            from encode_connector.server.main import encode_summarize_collection

            raw = await encode_summarize_collection(
                assay_title="Histone ChIP-seq",
                organism="Homo sapiens",
                organ="pancreas",
            )

        data = json.loads(raw)
        assert data["total_experiments"] == 3
        mock_tracker.summarize_collection.assert_called_once_with(
            assay_title="Histone ChIP-seq",
            organism="Homo sapiens",
            organ="pancreas",
        )


# ======================================================================
# 19. Get Metadata ValueError Path Test
# ======================================================================


class TestGetMetadataEdge:
    """Test error handling path for encode_get_metadata."""

    @pytest.mark.asyncio
    async def test_get_metadata_invalid_type_returns_error(self):
        """ValueError from client.get_metadata must return error JSON."""
        mock_client = MagicMock()
        mock_client.get_metadata.side_effect = ValueError("Unknown metadata type: invalid_type")

        with patch("encode_connector.server.main._get_client", new=AsyncMock(return_value=mock_client)):
            from encode_connector.server.main import encode_get_metadata

            raw = await encode_get_metadata(metadata_type="assays")

        data = json.loads(raw)
        assert "error" in data
        assert "Unknown metadata type" in data["error"]


# ======================================================================
# 20. Main Entry Point Test
# ======================================================================


class TestMainEntryPoint:
    """Validate the main() entry point."""

    def test_main_calls_mcp_run(self):
        """main() must call mcp.run()."""
        with patch("encode_connector.server.main.mcp") as mock_mcp:
            from encode_connector.server.main import main

            main()
            mock_mcp.run.assert_called_once()
