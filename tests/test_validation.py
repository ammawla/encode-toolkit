"""Tests for input validation module."""

import pytest

from encode_connector.client.validation import (
    MAX_QUERY_LIMIT,
    clamp_limit,
    escape_like,
    escape_lucene,
    safe_path_component,
    validate_accession,
    validate_data_export_format,
    validate_date,
    validate_download_url,
    validate_encode_path,
    validate_export_format,
    validate_organize_by,
    validate_redirect_url,
    validate_reference_type,
)

# ---------- validate_accession ----------


class TestValidateAccession:
    def test_valid_experiment_accession(self):
        assert validate_accession("ENCSR133RZO") == "ENCSR133RZO"

    def test_valid_file_accession(self):
        assert validate_accession("ENCFF635JIA") == "ENCFF635JIA"

    def test_valid_longer_accession(self):
        assert validate_accession("ENCAB12345678") == "ENCAB12345678"

    def test_invalid_no_enc_prefix(self):
        with pytest.raises(ValueError, match="Invalid ENCODE accession"):
            validate_accession("SR133RZO")

    def test_invalid_empty(self):
        with pytest.raises(ValueError):
            validate_accession("")

    def test_invalid_lowercase(self):
        with pytest.raises(ValueError):
            validate_accession("encsr133rzo")

    def test_invalid_path_traversal(self):
        with pytest.raises(ValueError):
            validate_accession("../../etc/passwd")

    def test_invalid_injection(self):
        with pytest.raises(ValueError):
            validate_accession("ENCSR133RZO; DROP TABLE")

    def test_invalid_url(self):
        with pytest.raises(ValueError):
            validate_accession("https://evil.com")


# ---------- validate_date ----------


class TestValidateDate:
    def test_valid_date(self):
        assert validate_date("2024-01-15") == "2024-01-15"

    def test_valid_date_boundaries(self):
        assert validate_date("2000-12-31") == "2000-12-31"

    def test_invalid_format(self):
        with pytest.raises(ValueError, match="Invalid date format"):
            validate_date("01/15/2024")

    def test_invalid_string(self):
        with pytest.raises(ValueError):
            validate_date("not-a-date")

    def test_invalid_injection(self):
        with pytest.raises(ValueError):
            validate_date("2024-01-01] OR *:*")

    def test_invalid_empty(self):
        with pytest.raises(ValueError):
            validate_date("")

    def test_impossible_calendar_date_feb_30(self):
        """Cover lines 95-96: date passes regex but fails fromisoformat()."""
        with pytest.raises(ValueError, match="Invalid calendar date"):
            validate_date("2024-02-30")

    def test_impossible_calendar_date_month_13(self):
        """Cover lines 95-96: month 13 passes regex but is not a valid date."""
        with pytest.raises(ValueError, match="Invalid calendar date"):
            validate_date("2024-13-01")

    def test_impossible_calendar_date_apr_31(self):
        """Cover lines 95-96: April 31 passes regex but does not exist."""
        with pytest.raises(ValueError, match="Invalid calendar date"):
            validate_date("2024-04-31")

    def test_impossible_calendar_date_feb_29_non_leap(self):
        """Cover lines 95-96: Feb 29 in a non-leap year."""
        with pytest.raises(ValueError, match="Invalid calendar date"):
            validate_date("2023-02-29")

    def test_valid_leap_year_date(self):
        """Feb 29 in a leap year should be valid."""
        assert validate_date("2024-02-29") == "2024-02-29"

    def test_impossible_calendar_date_day_00(self):
        """Cover lines 95-96: day 00 passes regex but is not a valid date."""
        with pytest.raises(ValueError, match="Invalid calendar date"):
            validate_date("2024-01-00")

    def test_impossible_calendar_date_month_00(self):
        """Cover lines 95-96: month 00 passes regex but is not a valid date."""
        with pytest.raises(ValueError, match="Invalid calendar date"):
            validate_date("2024-00-15")


# ---------- validate_encode_path ----------


class TestValidateEncodePath:
    def test_valid_experiment_path(self):
        assert validate_encode_path("/experiments/ENCSR133RZO/") == "/experiments/ENCSR133RZO/"

    def test_valid_file_path(self):
        assert validate_encode_path("/files/ENCFF635JIA/") == "/files/ENCFF635JIA/"

    def test_valid_publication_path(self):
        assert validate_encode_path("/publications/PMID123/") == "/publications/PMID123/"

    def test_reject_absolute_http(self):
        with pytest.raises(ValueError, match="Refusing to follow absolute URL"):
            validate_encode_path("http://evil.com/steal")

    def test_reject_absolute_https(self):
        with pytest.raises(ValueError, match="Refusing to follow absolute URL"):
            validate_encode_path("https://evil.com/steal")

    def test_reject_path_traversal(self):
        with pytest.raises(ValueError):
            validate_encode_path("/../../../etc/passwd")

    def test_reject_empty(self):
        with pytest.raises(ValueError):
            validate_encode_path("")


# ---------- validate_download_url ----------


class TestValidateDownloadUrl:
    def test_valid_encode_url(self):
        url = "https://www.encodeproject.org/files/ENCFF635JIA/@@download/ENCFF635JIA.bed.gz"
        assert validate_download_url(url) == url

    def test_valid_s3_url(self):
        url = "https://encode-public.s3.amazonaws.com/test.bed"
        assert validate_download_url(url) == url

    def test_reject_non_https(self):
        with pytest.raises(ValueError, match="Only HTTPS"):
            validate_download_url("http://www.encodeproject.org/files/test")

    def test_reject_unknown_host(self):
        with pytest.raises(ValueError, match="not allowed"):
            validate_download_url("https://evil.com/steal-data")

    def test_relative_url_allowed(self):
        # Relative URLs are allowed (they get prepended with base_url)
        assert validate_download_url("/files/ENCFF635JIA/@@download") == "/files/ENCFF635JIA/@@download"


# ---------- validate_redirect_url ----------


class TestValidateRedirectUrl:
    def test_valid_encode_redirect(self):
        """Cover lines 181-188: valid ENCODE host redirect passes."""
        url = "https://www.encodeproject.org/files/ENCFF635JIA/@@download"
        assert validate_redirect_url(url) == url

    def test_valid_s3_redirect(self):
        """Cover lines 181-188: valid S3 redirect host passes."""
        url = "https://encode-public.s3.us-west-2.amazonaws.com/2024/01/01/file.bed.gz"
        assert validate_redirect_url(url) == url

    def test_valid_s3_files_redirect(self):
        """Cover lines 186-187: encode-files S3 redirect host passes."""
        url = "https://encode-files.s3.amazonaws.com/data/file.bam"
        assert validate_redirect_url(url) == url

    def test_valid_s3_files_regional_redirect(self):
        """Cover lines 186-187: encode-files regional S3 redirect host passes."""
        url = "https://encode-files.s3.us-west-2.amazonaws.com/data/file.bam"
        assert validate_redirect_url(url) == url

    def test_valid_plain_s3_redirect(self):
        """Cover lines 186-187: plain s3.amazonaws.com redirect passes."""
        url = "https://s3.amazonaws.com/encode-public/data/file.bed"
        assert validate_redirect_url(url) == url

    def test_reject_non_https_redirect(self):
        """Cover lines 184-185: HTTP scheme is rejected."""
        with pytest.raises(ValueError, match="Only HTTPS"):
            validate_redirect_url("http://www.encodeproject.org/files/test")

    def test_reject_ftp_redirect(self):
        """Cover lines 184-185: FTP scheme is rejected."""
        with pytest.raises(ValueError, match="Only HTTPS"):
            validate_redirect_url("ftp://encode-public.s3.amazonaws.com/file.bed")

    def test_reject_unknown_host_redirect(self):
        """Cover lines 186-187: unknown host is rejected."""
        with pytest.raises(ValueError, match="Redirect host not allowed"):
            validate_redirect_url("https://evil.com/steal-data")

    def test_reject_similar_host_redirect(self):
        """Cover lines 186-187: similar-looking but non-allowed host is rejected."""
        with pytest.raises(ValueError, match="Redirect host not allowed"):
            validate_redirect_url("https://fake-encodeproject.org/files/test")

    def test_relative_redirect_allowed(self):
        """Relative redirect URLs pass (no scheme or netloc to check)."""
        url = "/files/ENCFF635JIA/@@download"
        assert validate_redirect_url(url) == url


# ---------- validate_organize_by ----------


class TestValidateOrganizeBy:
    def test_valid_flat(self):
        assert validate_organize_by("flat") == "flat"

    def test_valid_experiment(self):
        assert validate_organize_by("experiment") == "experiment"

    def test_valid_format(self):
        assert validate_organize_by("format") == "format"

    def test_valid_experiment_format(self):
        assert validate_organize_by("experiment_format") == "experiment_format"

    def test_invalid_path_traversal(self):
        with pytest.raises(ValueError):
            validate_organize_by("../../etc")

    def test_invalid_arbitrary(self):
        with pytest.raises(ValueError):
            validate_organize_by("anything_else")


# ---------- validate_export_format ----------


class TestValidateExportFormat:
    def test_valid_json(self):
        assert validate_export_format("json") == "json"

    def test_valid_bibtex(self):
        assert validate_export_format("bibtex") == "bibtex"

    def test_valid_ris(self):
        assert validate_export_format("ris") == "ris"

    def test_invalid(self):
        with pytest.raises(ValueError):
            validate_export_format("csv")


# ---------- escape_lucene ----------


class TestEscapeLucene:
    def test_special_chars_escaped(self):
        result = escape_lucene("hello + world")
        assert "\\+" in result

    def test_plain_string_unchanged(self):
        assert escape_lucene("hello world") == "hello world"

    def test_colon_escaped(self):
        assert "\\" in escape_lucene("field:value")


# ---------- safe_path_component ----------


class TestSafePathComponent:
    def test_valid_accession(self):
        assert safe_path_component("ENCSR133RZO") == "ENCSR133RZO"

    def test_special_chars_replaced(self):
        assert safe_path_component("a/b\\c") == "a_b_c"

    def test_max_length(self):
        result = safe_path_component("a" * 100)
        assert len(result) == 64

    def test_reject_dot_dot(self):
        with pytest.raises(ValueError, match="Unsafe"):
            safe_path_component("..")

    def test_reject_dot(self):
        with pytest.raises(ValueError, match="Unsafe"):
            safe_path_component(".")


# ---------- clamp_limit ----------


class TestClampLimit:
    def test_normal_value(self):
        assert clamp_limit(50) == 50

    def test_too_high(self):
        assert clamp_limit(5000) == MAX_QUERY_LIMIT

    def test_too_low(self):
        assert clamp_limit(-1) == 1

    def test_zero(self):
        assert clamp_limit(0) == 1

    def test_exact_max(self):
        assert clamp_limit(MAX_QUERY_LIMIT) == MAX_QUERY_LIMIT


# ---------- escape_like ----------


class TestEscapeLike:
    def test_percent_escaped(self):
        assert escape_like("100%") == "100\\%"

    def test_underscore_escaped(self):
        assert escape_like("a_b") == "a\\_b"

    def test_backslash_escaped(self):
        assert escape_like("a\\b") == "a\\\\b"

    def test_normal_string(self):
        assert escape_like("hello") == "hello"


# ---------- validate_reference_type ----------


class TestValidateReferenceType:
    def test_valid_pmid(self):
        assert validate_reference_type("pmid") == "pmid"

    def test_valid_doi(self):
        assert validate_reference_type("doi") == "doi"

    def test_valid_nct_id(self):
        assert validate_reference_type("nct_id") == "nct_id"

    def test_valid_preprint_doi(self):
        assert validate_reference_type("preprint_doi") == "preprint_doi"

    def test_valid_geo_accession(self):
        assert validate_reference_type("geo_accession") == "geo_accession"

    def test_valid_other(self):
        assert validate_reference_type("other") == "other"

    def test_invalid_type(self):
        with pytest.raises(ValueError, match="reference_type"):
            validate_reference_type("invalid")

    def test_invalid_empty(self):
        with pytest.raises(ValueError):
            validate_reference_type("")

    def test_error_message_helpful(self):
        with pytest.raises(ValueError, match="PubMed"):
            validate_reference_type("pubmed_id")


# ---------- validate_data_export_format ----------


class TestValidateDataExportFormat:
    def test_valid_csv(self):
        assert validate_data_export_format("csv") == "csv"

    def test_valid_tsv(self):
        assert validate_data_export_format("tsv") == "tsv"

    def test_valid_json(self):
        assert validate_data_export_format("json") == "json"

    def test_invalid_format(self):
        with pytest.raises(ValueError, match="format"):
            validate_data_export_format("xml")

    def test_error_message_helpful(self):
        with pytest.raises(ValueError, match="spreadsheets"):
            validate_data_export_format("excel")


# ---------- improved error messages ----------


class TestImprovedErrorMessages:
    def test_accession_error_message_explains_format(self):
        with pytest.raises(ValueError, match="ENC followed by"):
            validate_accession("INVALID")

    def test_accession_error_gives_examples(self):
        with pytest.raises(ValueError, match="ENCSR133RZO"):
            validate_accession("bad")
