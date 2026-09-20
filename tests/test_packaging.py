"""Tests for package metadata that guards against dependency breakage."""

from importlib.metadata import requires

from packaging.requirements import Requirement


def _mcp_requirement() -> Requirement:
    requirements = [Requirement(r) for r in requires("encode-toolkit") or []]
    return next(r for r in requirements if r.name == "mcp")


class TestMcpDependencyBounds:
    """mcp 2.x removed mcp.server.fastmcp, which the server imports at startup."""

    def test_excludes_mcp_2x(self):
        assert not _mcp_requirement().specifier.contains("2.0.0")

    def test_allows_mcp_1x(self):
        assert _mcp_requirement().specifier.contains("1.30.0")
