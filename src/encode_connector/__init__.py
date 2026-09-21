"""ENCODE Project connector - MCP server and Python client."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("encode-toolkit")
except PackageNotFoundError:  # a source tree that is not installed
    __version__ = "0+unknown"
__author__ = "Dr. Alex M. Mawla, PhD"
