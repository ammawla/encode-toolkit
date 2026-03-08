"""Tests for the MCP server tool definitions and validation."""

import pytest

from encode_connector.server.main import mcp


class TestServerSetup:
    def test_server_has_name(self):
        assert mcp.name == "ENCODE Project"

    def test_server_has_instructions(self):
        assert mcp.instructions is not None
        assert "ENCODE" in mcp.instructions

    def test_tools_registered(self):
        """Verify all 20 tools are registered."""
        tool_names = [t.name for t in mcp._tool_manager.list_tools()]
        expected_tools = [
            "encode_search_experiments",
            "encode_get_experiment",
            "encode_list_files",
            "encode_search_files",
            "encode_download_files",
            "encode_get_metadata",
            "encode_batch_download",
            "encode_manage_credentials",
            "encode_get_facets",
            "encode_get_file_info",
            "encode_track_experiment",
            "encode_list_tracked",
            "encode_get_citations",
            "encode_compare_experiments",
            "encode_log_derived_file",
            "encode_get_provenance",
            "encode_export_data",
            "encode_summarize_collection",
            "encode_link_reference",
            "encode_get_references",
        ]
        for tool_name in expected_tools:
            assert tool_name in tool_names, f"Missing tool: {tool_name}"

    def test_tool_count(self):
        """Verify exactly 20 tools are registered."""
        tools = mcp._tool_manager.list_tools()
        assert len(tools) == 20, f"Expected 20 tools, got {len(tools)}: {[t.name for t in tools]}"


class TestToolInputValidation:
    """Test that tools reject invalid inputs before making API calls."""

    @pytest.mark.asyncio
    async def test_get_experiment_rejects_invalid_accession(self):
        """encode_get_experiment should reject non-ENCODE accessions."""
        from encode_connector.server.main import encode_get_experiment

        with pytest.raises(ValueError, match="Invalid ENCODE accession"):
            await encode_get_experiment(accession="invalid")

    @pytest.mark.asyncio
    async def test_list_files_rejects_invalid_accession(self):
        from encode_connector.server.main import encode_list_files

        with pytest.raises(ValueError, match="Invalid ENCODE accession"):
            await encode_list_files(experiment_accession="../../etc/passwd")

    @pytest.mark.asyncio
    async def test_get_file_info_rejects_invalid_accession(self):
        from encode_connector.server.main import encode_get_file_info

        with pytest.raises(ValueError, match="Invalid ENCODE accession"):
            await encode_get_file_info(accession="DROP TABLE files")

    @pytest.mark.asyncio
    async def test_compare_rejects_invalid_accession(self):
        from encode_connector.server.main import encode_compare_experiments

        with pytest.raises(ValueError, match="Invalid ENCODE accession"):
            await encode_compare_experiments(
                accession1="invalid1",
                accession2="invalid2",
            )

    @pytest.mark.asyncio
    async def test_citations_rejects_invalid_format(self):
        from encode_connector.server.main import encode_get_citations

        with pytest.raises(ValueError, match="export_format"):
            await encode_get_citations(export_format="csv")

    @pytest.mark.asyncio
    async def test_download_rejects_invalid_organize_by(self):
        from encode_connector.server.main import encode_download_files

        with pytest.raises(ValueError, match="organize_by"):
            await encode_download_files(
                file_accessions=["ENCFF635JIA"],
                download_dir="/tmp/test",
                organize_by="../../etc",
            )

    @pytest.mark.asyncio
    async def test_link_reference_rejects_invalid_accession(self):
        from encode_connector.server.main import encode_link_reference

        with pytest.raises(ValueError, match="Invalid ENCODE accession"):
            await encode_link_reference(
                experiment_accession="invalid",
                reference_type="pmid",
                reference_id="12345",
            )

    @pytest.mark.asyncio
    async def test_link_reference_rejects_invalid_type(self):
        from encode_connector.server.main import encode_link_reference

        with pytest.raises(ValueError, match="reference_type"):
            await encode_link_reference(
                experiment_accession="ENCSR133RZO",
                reference_type="invalid_type",
                reference_id="12345",
            )

    @pytest.mark.asyncio
    async def test_export_data_rejects_invalid_format(self):
        from encode_connector.server.main import encode_export_data

        with pytest.raises(ValueError, match="format"):
            await encode_export_data(format="xml")

    @pytest.mark.asyncio
    async def test_get_references_rejects_invalid_accession(self):
        from encode_connector.server.main import encode_get_references

        with pytest.raises(ValueError, match="Invalid ENCODE accession"):
            await encode_get_references(experiment_accession="invalid")
