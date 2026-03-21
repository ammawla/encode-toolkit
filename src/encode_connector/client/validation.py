"""Input validation utilities for security.

Centralizes all input validation to prevent injection, SSRF, and path traversal.
"""

from __future__ import annotations

import re

# ENCODE accession format: ENC + 2-4 letter type + 3-8 alphanumeric
ACCESSION_RE = re.compile(r"^ENC[A-Z]{2,4}[A-Z0-9]{3,8}$")

# Date format: YYYY-MM-DD
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# ENCODE API relative path: /type/id/ or /type/
ENCODE_PATH_RE = re.compile(r"^/[a-zA-Z0-9][a-zA-Z0-9/_@.+-]*/?$")

# Lucene special characters that need escaping
_LUCENE_SPECIAL = re.compile(r'([+\-&|!(){}\[\]^"~*?:\\/])')

# Valid organize_by values
VALID_ORGANIZE_BY = frozenset({"flat", "experiment", "format", "experiment_format"})

# Valid export formats
VALID_EXPORT_FORMATS = frozenset({"json", "bibtex", "ris"})

# Allowed download hosts
ALLOWED_DOWNLOAD_HOSTS = frozenset(
    {
        "www.encodeproject.org",
        "encodeproject.org",
        "encode-public.s3.amazonaws.com",
    }
)

# Allowed redirect hosts (includes S3 regions used by ENCODE)
ALLOWED_REDIRECT_HOSTS = frozenset(
    {
        "www.encodeproject.org",
        "encodeproject.org",
        "encode-public.s3.amazonaws.com",
        "encode-files.s3.amazonaws.com",
        "s3.amazonaws.com",
        "encode-public.s3.us-west-2.amazonaws.com",
        "encode-files.s3.us-west-2.amazonaws.com",
    }
)

# Maximum limit for API queries
MAX_QUERY_LIMIT = 1000


# Valid external reference types for cross-server integration
VALID_REFERENCE_TYPES = frozenset(
    {
        "pmid",
        "doi",
        "nct_id",
        "preprint_doi",
        "geo_accession",
        "other",
    }
)

# Valid data export formats
VALID_DATA_EXPORT_FORMATS = frozenset({"csv", "tsv", "json"})


def validate_accession(accession: str) -> str:
    """Validate ENCODE accession format. Raises ValueError if invalid."""
    if not ACCESSION_RE.match(accession):
        raise ValueError(
            f"Invalid ENCODE accession format: {accession!r}. "
            "Expected format like ENCSR133RZO (experiments) or ENCFF635JIA (files). "
            "Accessions start with ENC followed by 2-4 uppercase letters "
            "and 3-8 alphanumeric characters."
        )
    return accession


def validate_date(date_str: str) -> str:
    """Validate date format (YYYY-MM-DD) and calendar correctness.

    Raises ValueError if format is wrong or date doesn't exist
    (e.g., 2024-02-30, 2024-13-01).
    """
    if not DATE_RE.match(date_str):
        raise ValueError(f"Invalid date format: {date_str!r}. Use YYYY-MM-DD.")
    # Validate that the date is a real calendar date
    import datetime

    try:
        datetime.date.fromisoformat(date_str)
    except ValueError:
        raise ValueError(f"Invalid calendar date: {date_str!r}. Date does not exist.")
    return date_str


def validate_encode_path(path: str) -> str:
    """Validate that a path is a relative ENCODE API path, never a full URL."""
    if path.startswith("http://") or path.startswith("https://"):
        raise ValueError(f"Refusing to follow absolute URL from API response: {path!r}")
    if not ENCODE_PATH_RE.match(path):
        raise ValueError(f"Invalid ENCODE API path: {path!r}")
    return path


def escape_lucene(value: str) -> str:
    """Escape Lucene special characters in a query value."""
    return _LUCENE_SPECIAL.sub(r"\\\1", value)


def validate_organize_by(value: str) -> str:
    """Validate organize_by parameter."""
    if value not in VALID_ORGANIZE_BY:
        raise ValueError(f"organize_by must be one of {sorted(VALID_ORGANIZE_BY)}, got {value!r}")
    return value


def validate_export_format(value: str) -> str:
    """Validate export format parameter."""
    if value not in VALID_EXPORT_FORMATS:
        raise ValueError(f"export_format must be one of {sorted(VALID_EXPORT_FORMATS)}, got {value!r}")
    return value


def validate_download_url(url: str) -> str:
    """Validate that a download URL points to an allowed host."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if parsed.scheme and parsed.scheme != "https":
        raise ValueError(f"Only HTTPS downloads allowed, got: {parsed.scheme}")
    if parsed.netloc and parsed.netloc not in ALLOWED_DOWNLOAD_HOSTS:
        raise ValueError(f"Download host not allowed: {parsed.netloc}")
    return url


def safe_path_component(value: str, max_len: int = 64) -> str:
    """Sanitize a string for use as a filesystem path component."""
    cleaned = re.sub(r"[^a-zA-Z0-9._-]", "_", value)[:max_len]
    if not cleaned or cleaned in (".", ".."):
        raise ValueError(f"Unsafe path component: {value!r}")
    return cleaned


def clamp_limit(limit: int) -> int:
    """Clamp a query limit to a safe maximum."""
    return max(1, min(limit, MAX_QUERY_LIMIT))


def escape_like(value: str) -> str:
    """Escape SQL LIKE wildcard characters."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def validate_reference_type(value: str) -> str:
    """Validate external reference type for cross-server linking."""
    if value not in VALID_REFERENCE_TYPES:
        raise ValueError(
            f"reference_type must be one of {sorted(VALID_REFERENCE_TYPES)}, got {value!r}. "
            "Use 'pmid' for PubMed IDs, 'doi' for DOIs, 'nct_id' for ClinicalTrials.gov, "
            "'preprint_doi' for bioRxiv/medRxiv, 'geo_accession' for GEO, or 'other'."
        )
    return value


def validate_data_export_format(value: str) -> str:
    """Validate data export format parameter."""
    if value not in VALID_DATA_EXPORT_FORMATS:
        raise ValueError(
            f"format must be one of {sorted(VALID_DATA_EXPORT_FORMATS)}, got {value!r}. "
            "Use 'csv' for spreadsheets, 'tsv' for tab-separated, or 'json' for programmatic use."
        )
    return value


# Pre-built case-insensitive lookup maps (keyed by tuple for stable identity)
_LOWER_MAPS: dict[tuple[str, ...], dict[str, str]] = {}


def _get_lower_map(valid_values: list[str]) -> dict[str, str]:
    """Get or build a cached lowercase→original map for a constants list."""
    key = tuple(valid_values)
    if key not in _LOWER_MAPS:
        _LOWER_MAPS[key] = {v.lower(): v for v in valid_values}
    return _LOWER_MAPS[key]


def check_filter_value(value: str, valid_values: list[str], filter_name: str) -> str | None:
    """Check if a filter value is in the known valid values.

    Returns a warning message if the value doesn't match any known value,
    or None if it's valid. Does NOT raise — unknown values may be valid
    if ENCODE has added new values since the constants were last updated.
    """
    if not isinstance(value, str) or not value:
        return None
    if value in valid_values:
        return None
    # Case-insensitive check using cached map
    lower_map = _get_lower_map(valid_values)
    lower_value = value.lower()
    if lower_value in lower_map:
        correct = lower_map[lower_value]
        return (
            f"Filter '{filter_name}' value '{value}' has wrong case. "
            f"ENCODE API is case-sensitive — use '{correct}' instead."
        )
    return (
        f"Filter '{filter_name}' value '{value}' not found in known ENCODE values. "
        f"This may cause empty results. Check encode_get_metadata for valid values."
    )


def validate_redirect_url(url: str) -> str:
    """Validate that a redirect URL points to an allowed ENCODE/S3 host."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if parsed.scheme and parsed.scheme != "https":
        raise ValueError(f"Only HTTPS redirects allowed, got: {parsed.scheme}")
    if parsed.netloc and parsed.netloc not in ALLOWED_REDIRECT_HOSTS:
        raise ValueError(f"Redirect host not allowed: {parsed.netloc}")
    return url
