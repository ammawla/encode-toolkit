"""Tests for the ENCODE client — targeting near-100% coverage of encode_client.py.

Covers: input validation, rate limiting, retry logic, search_experiments,
get_experiment, list_files, search_files, get_file_info, get_metadata,
search_facets, TTL cache, context manager, close, credentials, _ensure_client.
"""

import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from encode_connector.client.encode_client import (
    MAX_RETRIES,
    RETRYABLE_STATUS_CODES,
    EncodeClient,
)

# ======================================================================
# Helpers
# ======================================================================


def _make_response(status_code: int, json_data: dict | None = None) -> httpx.Response:
    """Build an httpx.Response with a proper Request attached."""
    return httpx.Response(
        status_code,
        json=json_data or {},
        request=httpx.Request("GET", "https://www.encodeproject.org/search/"),
    )


def _mock_http_client(side_effect=None, return_value=None):
    """Build a mock httpx.AsyncClient with .get and .is_closed."""
    mock = AsyncMock()
    mock.is_closed = False
    if side_effect:
        mock.get = AsyncMock(side_effect=side_effect)
    elif return_value is not None:
        mock.get = AsyncMock(return_value=return_value)
    else:
        mock.get = AsyncMock(return_value=_make_response(200, {"@graph": [], "total": 0}))
    return mock


def _inject_mock_client(client: EncodeClient, mock_http=None):
    """Inject a mock HTTP client so _ensure_client returns it without network."""
    if mock_http is None:
        mock_http = _mock_http_client()
    client._client = mock_http
    return mock_http


SAMPLE_EXPERIMENT_API = {
    "accession": "ENCSR000AAA",
    "assay_title": "Histone ChIP-seq",
    "target": {"label": "H3K27me3"},
    "biosample_summary": "K562",
    "organism": {"scientific_name": "Homo sapiens"},
    "biosample_ontology": {
        "classification": "cell line",
        "organ_slims": ["blood"],
    },
    "status": "released",
    "date_released": "2024-01-15",
    "description": "Test experiment",
    "lab": {"title": "Bernstein, Broad"},
    "award": {"project": "ENCODE"},
    "replicates": [],
    "files": [],
    "audit": {"ERROR": [], "WARNING": [{"detail": "w1"}]},
    "dbxrefs": ["GEO:GSM123"],
}

SAMPLE_FILE_API = {
    "accession": "ENCFF001AAA",
    "file_format": "bed",
    "file_type": "bed narrowPeak",
    "output_type": "IDR thresholded peaks",
    "output_category": "annotation",
    "file_size": 1024000,
    "assembly": "GRCh38",
    "biological_replicates": [1, 2],
    "technical_replicates": ["1_1", "2_1"],
    "status": "released",
    "href": "/files/ENCFF001AAA/@@download/ENCFF001AAA.bed.gz",
    "s3_uri": "s3://encode-public/2024/01/15/abc.bed.gz",
    "md5sum": "d41d8cd98f00b204e9800998ecf8427e",
    "dataset": "/experiments/ENCSR000AAA/",
    "assay_title": "Histone ChIP-seq",
    "biosample_summary": "K562",
    "preferred_default": True,
    "date_created": "2024-01-16",
}


# ======================================================================
# Input validation (existing tests preserved)
# ======================================================================


class TestInputValidation:
    """Test that client methods validate inputs before making API calls."""

    async def test_get_experiment_validates_accession(self):
        async with EncodeClient() as client:
            with pytest.raises(ValueError, match="Invalid ENCODE accession"):
                await client.get_experiment("invalid")

    async def test_get_experiment_rejects_path_traversal(self):
        async with EncodeClient() as client:
            with pytest.raises(ValueError):
                await client.get_experiment("../../etc/passwd")

    async def test_list_files_validates_accession(self):
        async with EncodeClient() as client:
            with pytest.raises(ValueError, match="Invalid ENCODE accession"):
                await client.list_files("not-valid")

    async def test_get_file_info_validates_accession(self):
        async with EncodeClient() as client:
            with pytest.raises(ValueError, match="Invalid ENCODE accession"):
                await client.get_file_info("../../etc/passwd")

    async def test_search_experiments_validates_date(self):
        async with EncodeClient() as client:
            with pytest.raises(ValueError, match="Invalid date"):
                await client.search_experiments(
                    date_released_from="not-a-date",
                )

    async def test_search_experiments_validates_date_to(self):
        async with EncodeClient() as client:
            with pytest.raises(ValueError, match="Invalid date"):
                await client.search_experiments(
                    date_released_from="2024-01-01",
                    date_released_to="invalid",
                )

    async def test_get_experiment_raw_validates_accession(self):
        async with EncodeClient() as client:
            with pytest.raises(ValueError, match="Invalid ENCODE accession"):
                await client.get_experiment_raw("bad-accession")


# ======================================================================
# Limit clamping (existing tests preserved)
# ======================================================================


class TestLimitClamping:
    """Test that limits are clamped to safe values."""

    async def test_search_experiments_clamps_limit(self):
        async with EncodeClient() as client:
            captured = {}

            async def mock_request(path, params=None):
                captured.update(params or {})
                return {"@graph": [], "total": 0}

            client._request = mock_request
            await client.search_experiments(limit=99999)
            assert captured["limit"] <= 1000

    async def test_search_files_clamps_limit(self):
        async with EncodeClient() as client:
            captured = {}

            async def mock_request(path, params=None):
                captured.update(params or {})
                return {"@graph": [], "total": 0}

            client._request = mock_request
            await client.search_files(limit=99999)
            assert captured["limit"] <= 1000

    async def test_list_files_clamps_limit(self):
        async with EncodeClient() as client:
            captured = {}

            async def mock_request(path, params=None):
                captured.update(params or {})
                return {"@graph": [], "total": 0}

            client._request = mock_request
            await client.list_files("ENCSR000AAA", limit=99999)
            assert captured["limit"] <= 1000


# ======================================================================
# Client lifecycle
# ======================================================================


class TestClientLifecycle:
    async def test_context_manager(self):
        async with EncodeClient() as client:
            assert client._client is None  # Lazy init

    async def test_context_manager_closes_client(self):
        """__aexit__ closes the HTTP client."""
        client = EncodeClient()
        mock_http = _inject_mock_client(client)
        async with client:
            pass
        mock_http.aclose.assert_awaited_once()

    async def test_close_with_open_client(self):
        """close() calls aclose on the httpx client."""
        client = EncodeClient()
        mock_http = _inject_mock_client(client)
        await client.close()
        mock_http.aclose.assert_awaited_once()
        assert client._client is None

    async def test_close_already_closed(self):
        """close() on already-closed client is a no-op."""
        client = EncodeClient()
        await client.close()  # _client is None, should not raise
        assert client._client is None

    async def test_close_when_client_is_closed_flag(self):
        """close() when client.is_closed is True is a no-op."""
        client = EncodeClient()
        mock_http = AsyncMock()
        mock_http.is_closed = True
        client._client = mock_http
        await client.close()
        mock_http.aclose.assert_not_awaited()

    def test_has_credentials_without_creds(self):
        client = EncodeClient()
        client._credential_manager._keyring_available = False
        client._credential_manager._fallback_file = Path("/nonexistent")
        assert not client.has_credentials

    def test_metadata(self):
        client = EncodeClient()
        assays = client.get_metadata("assays")
        assert isinstance(assays, list)
        assert len(assays) > 0
        assert "Histone ChIP-seq" in assays

    def test_metadata_invalid_type(self):
        client = EncodeClient()
        with pytest.raises(ValueError, match="Unknown metadata type"):
            client.get_metadata("invalid_type")


# ======================================================================
# _ensure_client
# ======================================================================


class TestEnsureClient:
    """Cover lines 86-111: _ensure_client."""

    async def test_creates_client_without_auth(self):
        """Creates httpx.AsyncClient when no credentials are available."""
        client = EncodeClient()
        client._credential_manager._keyring_available = False
        client._credential_manager._fallback_file = Path("/nonexistent")
        http_client = await client._ensure_client()
        assert isinstance(http_client, httpx.AsyncClient)
        assert "Accept" in http_client.headers
        assert "User-Agent" in http_client.headers
        await client.close()

    async def test_creates_client_with_auth(self):
        """Creates httpx.AsyncClient with auth headers when credentials exist."""
        client = EncodeClient()
        client._credential_manager._access_key = "test_ak"
        client._credential_manager._secret_key = "test_sk"
        http_client = await client._ensure_client()
        assert isinstance(http_client, httpx.AsyncClient)
        assert "Authorization" in http_client.headers
        await client.close()

    async def test_reuses_existing_client(self):
        """Returns the same client on subsequent calls."""
        client = EncodeClient()
        mock_http = _inject_mock_client(client)
        result = await client._ensure_client()
        assert result is mock_http

    async def test_recreates_when_closed(self):
        """Creates new client if existing one is closed."""
        client = EncodeClient()
        client._credential_manager._keyring_available = False
        client._credential_manager._fallback_file = Path("/nonexistent")
        mock_http = AsyncMock()
        mock_http.is_closed = True
        client._client = mock_http
        new_client = await client._ensure_client()
        assert isinstance(new_client, httpx.AsyncClient)
        assert new_client is not mock_http
        await client.close()


# ======================================================================
# _request and get_json
# ======================================================================


class TestRequestAndGetJson:
    """Cover _request retry logic and get_json public wrapper."""

    async def test_get_json_delegates_to_request(self):
        """get_json is a public wrapper of _request."""
        client = EncodeClient()
        mock_http = _mock_http_client(return_value=_make_response(200, {"key": "value"}))
        _inject_mock_client(client, mock_http)
        result = await client.get_json("/test/", {"param": "val"})
        assert result == {"key": "value"}
        await client.close()

    async def test_successful_request(self):
        """Successful request returns parsed JSON."""
        client = EncodeClient()
        mock_http = _mock_http_client(
            return_value=_make_response(200, {"@graph": [{"accession": "ENCSR000AAA"}], "total": 1})
        )
        _inject_mock_client(client, mock_http)
        result = await client._request("/search/", {"type": "Experiment"})
        assert result["total"] == 1
        await client.close()

    async def test_rate_limiter_sleeps_when_too_fast(self):
        """Rate limiter triggers asyncio.sleep when requests arrive too fast (line 126)."""
        client = EncodeClient()
        mock_http = _mock_http_client(return_value=_make_response(200, {"ok": True}))
        _inject_mock_client(client, mock_http)

        # Simulate a very recent request so elapsed < min_interval
        client._last_request_time = time.monotonic()

        with patch("encode_connector.client.encode_client.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await client._request("/test/")
            assert result == {"ok": True}
            # asyncio.sleep should have been called at least once for rate limiting
            # (It may also be called for retries, but the rate limiter call is the one we want)
            assert mock_sleep.await_count >= 1
        await client.close()


# ======================================================================
# Retry logic (existing tests preserved + new)
# ======================================================================


class TestRetryLogic:
    """Test retry behavior for transient failures."""

    def test_retryable_status_codes_defined(self):
        assert 429 in RETRYABLE_STATUS_CODES
        assert 503 in RETRYABLE_STATUS_CODES
        assert 502 in RETRYABLE_STATUS_CODES
        assert 504 in RETRYABLE_STATUS_CODES

    def test_non_retryable_not_included(self):
        assert 400 not in RETRYABLE_STATUS_CODES
        assert 404 not in RETRYABLE_STATUS_CODES
        assert 200 not in RETRYABLE_STATUS_CODES

    def test_max_retries_value(self):
        assert MAX_RETRIES == 3

    async def test_retry_on_connect_error_then_success(self):
        """Test that ConnectError triggers retry and succeeds on second attempt."""
        async with EncodeClient() as client:
            attempts = []

            async def mock_get(path, params=None):
                attempts.append(1)
                if len(attempts) == 1:
                    raise httpx.ConnectError("Connection refused")
                return _make_response(200, {"@graph": [], "total": 0})

            mock_http = _mock_http_client()
            mock_http.get = mock_get
            client._client = mock_http
            await client.search_experiments(limit=1)
            assert len(attempts) >= 2

    async def test_retry_on_503_status(self):
        """Test that 503 response triggers retry."""
        async with EncodeClient() as client:
            attempts = []

            async def mock_get(path, params=None):
                attempts.append(1)
                if len(attempts) == 1:
                    return _make_response(503)
                return _make_response(200, {"@graph": [], "total": 0})

            mock_http = _mock_http_client()
            mock_http.get = mock_get
            client._client = mock_http

            await client.search_experiments(limit=1)
            assert len(attempts) == 2

    async def test_no_retry_on_client_error(self):
        """Test that 404 does NOT trigger retry."""
        async with EncodeClient() as client:
            attempts = []

            async def mock_get(path, params=None):
                attempts.append(1)
                return _make_response(404)

            mock_http = _mock_http_client()
            mock_http.get = mock_get
            client._client = mock_http

            with pytest.raises(httpx.HTTPStatusError):
                await client.search_experiments(limit=1)
            assert len(attempts) == 1

    async def test_retry_exhaustion_on_503(self):
        """All retries exhausted on 503 raises HTTPStatusError."""
        async with EncodeClient() as client:
            attempts = []

            async def mock_get(path, params=None):
                attempts.append(1)
                return _make_response(503)

            mock_http = _mock_http_client()
            mock_http.get = mock_get
            client._client = mock_http

            with pytest.raises(httpx.HTTPStatusError):
                await client._request("/test/")
            assert len(attempts) == MAX_RETRIES + 1

    async def test_retry_on_read_timeout_then_success(self):
        """ReadTimeout triggers retry."""
        async with EncodeClient() as client:
            attempts = []

            async def mock_get(path, params=None):
                attempts.append(1)
                if len(attempts) == 1:
                    raise httpx.ReadTimeout("read timed out")
                return _make_response(200, {"result": "ok"})

            mock_http = _mock_http_client()
            mock_http.get = mock_get
            client._client = mock_http

            result = await client._request("/test/")
            assert result == {"result": "ok"}
            assert len(attempts) == 2

    async def test_retry_exhaustion_on_connect_error(self):
        """All retries exhausted on ConnectError re-raises the error."""
        async with EncodeClient() as client:

            async def mock_get(path, params=None):
                raise httpx.ConnectError("refused")

            mock_http = _mock_http_client()
            mock_http.get = mock_get
            client._client = mock_http

            with pytest.raises(httpx.ConnectError):
                await client._request("/test/")

    async def test_retry_on_connect_timeout(self):
        """ConnectTimeout triggers retry."""
        async with EncodeClient() as client:
            attempts = []

            async def mock_get(path, params=None):
                attempts.append(1)
                if len(attempts) <= 1:
                    raise httpx.ConnectTimeout("timed out")
                return _make_response(200, {"ok": True})

            mock_http = _mock_http_client()
            mock_http.get = mock_get
            client._client = mock_http

            result = await client._request("/test/")
            assert result == {"ok": True}
            assert len(attempts) == 2


# ======================================================================
# search_experiments
# ======================================================================


class TestSearchExperiments:
    """Cover lines 210-297: search_experiments with various filters."""

    async def test_basic_search(self):
        """Basic search with no filters returns results."""
        client = EncodeClient()
        captured = {}

        async def mock_request(path, params=None):
            captured.update(params or {})
            return {
                "@graph": [SAMPLE_EXPERIMENT_API],
                "total": 1,
            }

        client._request = mock_request
        result = await client.search_experiments()
        assert result["total"] == 1
        assert len(result["results"]) == 1
        assert result["results"][0].accession == "ENCSR000AAA"
        assert captured["type"] == "Experiment"

    async def test_with_organism_filter(self):
        """Organism filter maps to ENCODE API parameter."""
        client = EncodeClient()
        captured = {}

        async def mock_request(path, params=None):
            captured.update(params or {})
            return {"@graph": [], "total": 0}

        client._request = mock_request
        await client.search_experiments(organism="Homo sapiens")
        assert "replicates.library.biosample.donor.organism.scientific_name" in captured

    async def test_with_organ_filter(self):
        """Organ filter maps to biosample_ontology.organ_slims."""
        client = EncodeClient()
        captured = {}

        async def mock_request(path, params=None):
            captured.update(params or {})
            return {"@graph": [], "total": 0}

        client._request = mock_request
        await client.search_experiments(organ="pancreas")
        assert captured.get("biosample_ontology.organ_slims") == "pancreas"

    async def test_with_target_filter(self):
        """Target filter maps to target.label."""
        client = EncodeClient()
        captured = {}

        async def mock_request(path, params=None):
            captured.update(params or {})
            return {"@graph": [], "total": 0}

        client._request = mock_request
        await client.search_experiments(target="H3K27me3")
        assert captured.get("target.label") == "H3K27me3"

    async def test_with_offset(self):
        """Offset > 0 adds 'from' parameter."""
        client = EncodeClient()
        captured = {}

        async def mock_request(path, params=None):
            captured.update(params or {})
            return {"@graph": [], "total": 50}

        client._request = mock_request
        result = await client.search_experiments(offset=25)
        assert captured.get("from") == 25
        assert result["offset"] == 25

    async def test_offset_zero_no_from(self):
        """Offset == 0 does not add 'from' parameter."""
        client = EncodeClient()
        captured = {}

        async def mock_request(path, params=None):
            captured.update(params or {})
            return {"@graph": [], "total": 0}

        client._request = mock_request
        await client.search_experiments(offset=0)
        assert "from" not in captured

    async def test_perturbed_true(self):
        """Perturbed=True sends 'true' string."""
        client = EncodeClient()
        captured = {}

        async def mock_request(path, params=None):
            captured.update(params or {})
            return {"@graph": [], "total": 0}

        client._request = mock_request
        await client.search_experiments(perturbed=True)
        assert captured.get("replicates.library.biosample.perturbed") == "true"

    async def test_perturbed_false(self):
        """Perturbed=False sends 'false' string."""
        client = EncodeClient()
        captured = {}

        async def mock_request(path, params=None):
            captured.update(params or {})
            return {"@graph": [], "total": 0}

        client._request = mock_request
        await client.search_experiments(perturbed=False)
        assert captured.get("replicates.library.biosample.perturbed") == "false"

    async def test_perturbed_none(self):
        """Perturbed=None does not add perturbed filter."""
        client = EncodeClient()
        captured = {}

        async def mock_request(path, params=None):
            captured.update(params or {})
            return {"@graph": [], "total": 0}

        client._request = mock_request
        await client.search_experiments(perturbed=None)
        assert "replicates.library.biosample.perturbed" not in captured

    async def test_date_range_both(self):
        """Both date_released_from and date_released_to add advancedQuery."""
        client = EncodeClient()
        captured = {}

        async def mock_request(path, params=None):
            captured.update(params or {})
            return {"@graph": [], "total": 0}

        client._request = mock_request
        await client.search_experiments(
            date_released_from="2024-01-01",
            date_released_to="2024-12-31",
        )
        assert "advancedQuery" in captured
        assert "date_released:[2024-01-01 TO 2024-12-31]" in captured["advancedQuery"]

    async def test_date_released_from_only(self):
        """Only date_released_from uses * for to_date."""
        client = EncodeClient()
        captured = {}

        async def mock_request(path, params=None):
            captured.update(params or {})
            return {"@graph": [], "total": 0}

        client._request = mock_request
        await client.search_experiments(date_released_from="2024-06-01")
        assert "date_released:[2024-06-01 TO *]" in captured["advancedQuery"]

    async def test_date_released_to_only(self):
        """Only date_released_to uses * for from_date."""
        client = EncodeClient()
        captured = {}

        async def mock_request(path, params=None):
            captured.update(params or {})
            return {"@graph": [], "total": 0}

        client._request = mock_request
        await client.search_experiments(date_released_to="2024-12-31")
        assert "date_released:[* TO 2024-12-31]" in captured["advancedQuery"]

    async def test_search_term(self):
        """search_term maps to searchTerm parameter."""
        client = EncodeClient()
        captured = {}

        async def mock_request(path, params=None):
            captured.update(params or {})
            return {"@graph": [], "total": 0}

        client._request = mock_request
        await client.search_experiments(search_term="K562")
        assert captured.get("searchTerm") == "K562"

    async def test_multiple_filters(self):
        """Multiple filters all applied to params."""
        client = EncodeClient()
        captured = {}

        async def mock_request(path, params=None):
            captured.update(params or {})
            return {"@graph": [], "total": 0}

        client._request = mock_request
        await client.search_experiments(
            assay_title="Histone ChIP-seq",
            organism="Homo sapiens",
            organ="pancreas",
            biosample_type="tissue",
            target="H3K27me3",
            status="released",
            lab="Bernstein",
            assembly="GRCh38",
            life_stage="adult",
            sex="female",
        )
        assert captured.get("assay_title") == "Histone ChIP-seq"
        assert captured.get("biosample_ontology.organ_slims") == "pancreas"
        assert captured.get("biosample_ontology.classification") == "tissue"
        assert captured.get("target.label") == "H3K27me3"
        assert captured.get("status") == "released"

    async def test_result_structure(self):
        """Result dict has expected keys."""
        client = EncodeClient()

        async def mock_request(path, params=None):
            return {"@graph": [], "total": 42}

        client._request = mock_request
        result = await client.search_experiments(limit=10)
        assert "results" in result
        assert "total" in result
        assert "limit" in result
        assert "offset" in result
        assert result["total"] == 42
        assert result["limit"] == 10
        assert result["offset"] == 0


# ======================================================================
# get_experiment_raw
# ======================================================================


class TestGetExperimentRaw:
    """Cover lines 299-305: get_experiment_raw."""

    async def test_returns_raw_dict(self):
        client = EncodeClient()
        captured_paths = []

        async def mock_request(path, params=None):
            captured_paths.append(path)
            return SAMPLE_EXPERIMENT_API

        client._request = mock_request
        result = await client.get_experiment_raw("ENCSR000AAA")
        assert result["accession"] == "ENCSR000AAA"
        assert "/experiments/ENCSR000AAA/" in captured_paths[0]

    async def test_validates_accession(self):
        client = EncodeClient()
        with pytest.raises(ValueError, match="Invalid ENCODE accession"):
            await client.get_experiment_raw("bad")


# ======================================================================
# get_experiment
# ======================================================================


class TestGetExperiment:
    """Cover lines 307-329: get_experiment."""

    async def test_returns_experiment_detail(self):
        """Fetches experiment + files and returns ExperimentDetail."""
        client = EncodeClient()
        call_count = []

        async def mock_request(path, params=None):
            call_count.append(path)
            if "/experiments/" in path and "/search/" not in path:
                return SAMPLE_EXPERIMENT_API
            # Files search
            return {"@graph": [SAMPLE_FILE_API], "total": 1}

        client._request = mock_request
        result = await client.get_experiment("ENCSR000AAA")
        assert result.accession == "ENCSR000AAA"
        assert result.assay_title == "Histone ChIP-seq"
        assert len(result.files) == 1
        assert result.files[0].accession == "ENCFF001AAA"
        # Two API calls: experiment + files
        assert len(call_count) == 2

    async def test_validates_accession(self):
        client = EncodeClient()
        with pytest.raises(ValueError, match="Invalid ENCODE accession"):
            await client.get_experiment("invalid-id")

    async def test_no_files(self):
        """Experiment with no files returns empty files list."""
        client = EncodeClient()

        async def mock_request(path, params=None):
            if "/experiments/" in path and "/search/" not in path:
                return SAMPLE_EXPERIMENT_API
            return {"@graph": [], "total": 0}

        client._request = mock_request
        result = await client.get_experiment("ENCSR000AAA")
        assert result.files == []


# ======================================================================
# list_files
# ======================================================================


class TestListFiles:
    """Cover lines 335-376: list_files with filters."""

    async def test_basic_list(self):
        """List files for an experiment."""
        client = EncodeClient()
        captured = {}

        async def mock_request(path, params=None):
            captured.update(params or {})
            return {"@graph": [SAMPLE_FILE_API]}

        client._request = mock_request
        result = await client.list_files("ENCSR000AAA")
        assert len(result) == 1
        assert result[0].accession == "ENCFF001AAA"
        assert captured["dataset"] == "/experiments/ENCSR000AAA/"

    async def test_with_file_format_filter(self):
        """file_format filter is applied."""
        client = EncodeClient()
        captured = {}

        async def mock_request(path, params=None):
            captured.update(params or {})
            return {"@graph": []}

        client._request = mock_request
        await client.list_files("ENCSR000AAA", file_format="bed")
        assert captured.get("file_format") == "bed"

    async def test_with_output_type_filter(self):
        """output_type filter is applied."""
        client = EncodeClient()
        captured = {}

        async def mock_request(path, params=None):
            captured.update(params or {})
            return {"@graph": []}

        client._request = mock_request
        await client.list_files("ENCSR000AAA", output_type="IDR thresholded peaks")
        assert captured.get("output_type") == "IDR thresholded peaks"

    async def test_with_assembly_filter(self):
        """assembly filter is applied."""
        client = EncodeClient()
        captured = {}

        async def mock_request(path, params=None):
            captured.update(params or {})
            return {"@graph": []}

        client._request = mock_request
        await client.list_files("ENCSR000AAA", assembly="GRCh38")
        assert captured.get("assembly") == "GRCh38"

    async def test_preferred_default_true(self):
        """preferred_default=True sends 'true' string."""
        client = EncodeClient()
        captured = {}

        async def mock_request(path, params=None):
            captured.update(params or {})
            return {"@graph": []}

        client._request = mock_request
        await client.list_files("ENCSR000AAA", preferred_default=True)
        assert captured.get("preferred_default") == "true"

    async def test_preferred_default_false(self):
        """preferred_default=False sends 'false' string."""
        client = EncodeClient()
        captured = {}

        async def mock_request(path, params=None):
            captured.update(params or {})
            return {"@graph": []}

        client._request = mock_request
        await client.list_files("ENCSR000AAA", preferred_default=False)
        assert captured.get("preferred_default") == "false"

    async def test_preferred_default_none(self):
        """preferred_default=None does not add filter."""
        client = EncodeClient()
        captured = {}

        async def mock_request(path, params=None):
            captured.update(params or {})
            return {"@graph": []}

        client._request = mock_request
        await client.list_files("ENCSR000AAA", preferred_default=None)
        assert "preferred_default" not in captured

    async def test_with_status_filter(self):
        """status filter is applied."""
        client = EncodeClient()
        captured = {}

        async def mock_request(path, params=None):
            captured.update(params or {})
            return {"@graph": []}

        client._request = mock_request
        await client.list_files("ENCSR000AAA", status="released")
        assert captured.get("status") == "released"

    async def test_with_multiple_filters(self):
        """Multiple file filters all applied."""
        client = EncodeClient()
        captured = {}

        async def mock_request(path, params=None):
            captured.update(params or {})
            return {"@graph": []}

        client._request = mock_request
        await client.list_files(
            "ENCSR000AAA",
            file_format="bed",
            output_type="peaks",
            assembly="GRCh38",
            status="released",
            preferred_default=True,
        )
        assert captured.get("file_format") == "bed"
        assert captured.get("output_type") == "peaks"
        assert captured.get("assembly") == "GRCh38"
        assert captured.get("status") == "released"
        assert captured.get("preferred_default") == "true"


# ======================================================================
# search_files
# ======================================================================


class TestSearchFiles:
    """Cover lines 378-486: search_files."""

    async def test_simple_search_without_organism(self):
        """Search files without organism (simple path, single API call)."""
        client = EncodeClient()
        captured = {}

        async def mock_request(path, params=None):
            captured.update(params or {})
            return {"@graph": [SAMPLE_FILE_API], "total": 1}

        client._request = mock_request
        result = await client.search_files(file_format="bed")
        assert result["total"] == 1
        assert len(result["results"]) == 1
        assert captured.get("file_format") == "bed"

    async def test_with_offset(self):
        """Offset > 0 adds 'from' param."""
        client = EncodeClient()
        captured = {}

        async def mock_request(path, params=None):
            captured.update(params or {})
            return {"@graph": [], "total": 0}

        client._request = mock_request
        result = await client.search_files(offset=50)
        assert captured.get("from") == 50
        assert result["offset"] == 50

    async def test_with_search_term(self):
        """search_term appended when organism is absent."""
        client = EncodeClient()
        captured = {}

        async def mock_request(path, params=None):
            captured.update(params or {})
            return {"@graph": [], "total": 0}

        client._request = mock_request
        await client.search_files(search_term="K562")
        assert captured.get("searchTerm") == "K562"

    async def test_with_experiment_level_filters(self):
        """assay_title, organ, biosample_type, target are applied."""
        client = EncodeClient()
        captured = {}

        async def mock_request(path, params=None):
            captured.update(params or {})
            return {"@graph": [], "total": 0}

        client._request = mock_request
        await client.search_files(
            assay_title="Histone ChIP-seq",
            organ="pancreas",
            biosample_type="tissue",
            target="H3K27me3",
        )
        assert captured.get("assay_title") == "Histone ChIP-seq"
        assert captured.get("biosample_ontology.organ_slims") == "pancreas"
        assert captured.get("biosample_ontology.classification") == "tissue"
        assert captured.get("target.label") == "H3K27me3"

    async def test_preferred_default_filter(self):
        """preferred_default handled in search_files."""
        client = EncodeClient()
        captured = {}

        async def mock_request(path, params=None):
            captured.update(params or {})
            return {"@graph": [], "total": 0}

        client._request = mock_request
        await client.search_files(preferred_default=True)
        assert captured.get("preferred_default") == "true"

    async def test_with_organism_two_step_search(self):
        """When organism is specified, uses two-step search (experiments then files)."""
        client = EncodeClient()
        call_log = []

        exp_summary = MagicMock()
        exp_summary.accession = "ENCSR000AAA"

        async def mock_search_experiments(**kwargs):
            call_log.append("search_experiments")
            return {"results": [exp_summary], "total": 1}

        async def mock_list_files(experiment_accession, **kwargs):
            call_log.append(f"list_files:{experiment_accession}")
            from encode_connector.client.models import FileSummary

            return [FileSummary.from_api(SAMPLE_FILE_API)]

        client.search_experiments = mock_search_experiments
        client.list_files = mock_list_files

        result = await client.search_files(
            file_format="bed",
            organism="Homo sapiens",
            limit=25,
        )
        assert "search_experiments" in call_log
        assert any("list_files" in c for c in call_log)
        assert len(result["results"]) == 1
        assert "total_note" in result

    async def test_with_organism_no_experiments_found(self):
        """Two-step search returns empty when no experiments match."""
        client = EncodeClient()

        async def mock_search_experiments(**kwargs):
            return {"results": [], "total": 0}

        client.search_experiments = mock_search_experiments

        result = await client.search_files(organism="Mus musculus")
        assert result["results"] == []
        assert result["total"] == 0

    async def test_with_organism_respects_limit(self):
        """Two-step search stops collecting files after reaching limit."""
        client = EncodeClient()

        exp1 = MagicMock()
        exp1.accession = "ENCSR000AAA"
        exp2 = MagicMock()
        exp2.accession = "ENCSR000BBB"

        async def mock_search_experiments(**kwargs):
            return {"results": [exp1, exp2], "total": 2}

        list_files_calls = []

        async def mock_list_files(experiment_accession, **kwargs):
            list_files_calls.append(experiment_accession)
            from encode_connector.client.models import FileSummary

            # Return 3 files per experiment
            files = []
            for i in range(3):
                data = SAMPLE_FILE_API.copy()
                data["accession"] = f"ENCFF{experiment_accession[-3:]}{i:03d}"
                files.append(FileSummary.from_api(data))
            return files

        client.search_experiments = mock_search_experiments
        client.list_files = mock_list_files

        result = await client.search_files(organism="Homo sapiens", limit=2)
        # Should limit results to 2
        assert len(result["results"]) == 2


# ======================================================================
# get_file_info
# ======================================================================


class TestGetFileInfo:
    """Cover lines 488-495: get_file_info."""

    async def test_returns_file_summary(self):
        client = EncodeClient()
        captured_path = []

        async def mock_request(path, params=None):
            captured_path.append(path)
            return SAMPLE_FILE_API

        client._request = mock_request
        result = await client.get_file_info("ENCFF001AAA")
        assert result.accession == "ENCFF001AAA"
        assert result.file_format == "bed"
        assert "/files/ENCFF001AAA/" in captured_path[0]

    async def test_validates_accession(self):
        client = EncodeClient()
        with pytest.raises(ValueError, match="Invalid ENCODE accession"):
            await client.get_file_info("bad-accession")


# ======================================================================
# get_metadata (caching)
# ======================================================================


class TestGetMetadata:
    """Cover lines 501-523: get_metadata with caching."""

    def test_known_type(self):
        """Returns valid list for known metadata type."""
        client = EncodeClient()
        assays = client.get_metadata("assays")
        assert isinstance(assays, list)
        assert "Histone ChIP-seq" in assays

    def test_unknown_type(self):
        """Raises ValueError for unknown metadata type."""
        client = EncodeClient()
        with pytest.raises(ValueError, match="Unknown metadata type"):
            client.get_metadata("nonexistent_type")

    def test_caching_behavior(self):
        """Second call returns cached value."""
        client = EncodeClient()
        result1 = client.get_metadata("assays")
        result2 = client.get_metadata("assays")
        assert result1 == result2
        # Verify it's actually cached
        cache_key = "metadata:assays"
        assert cache_key in client._cache

    def test_all_metadata_types(self):
        """All expected metadata types are available."""
        client = EncodeClient()
        expected_types = [
            "assays",
            "organisms",
            "organs",
            "biosample_types",
            "file_formats",
            "output_types",
            "output_categories",
            "assemblies",
            "life_stages",
            "replication_types",
            "statuses",
            "file_statuses",
        ]
        for metadata_type in expected_types:
            result = client.get_metadata(metadata_type)
            assert isinstance(result, list)
            assert len(result) > 0


# ======================================================================
# search_facets (caching)
# ======================================================================


class TestSearchFacets:
    """Cover lines 525-563: search_facets with caching."""

    async def test_returns_facets(self):
        """Parses facets from API response."""
        client = EncodeClient()

        async def mock_request(path, params=None):
            return {
                "facets": [
                    {
                        "field": "assay_title",
                        "terms": [
                            {"key": "Histone ChIP-seq", "doc_count": 500},
                            {"key": "ATAC-seq", "doc_count": 300},
                            {"key": "empty", "doc_count": 0},  # Should be filtered out
                        ],
                    },
                    {
                        "field": "status",
                        "terms": [
                            {"key": "released", "doc_count": 1000},
                        ],
                    },
                ],
                "@graph": [],
                "total": 0,
            }

        client._request = mock_request
        result = await client.search_facets()
        assert "assay_title" in result
        assert len(result["assay_title"]) == 2  # empty filtered out
        assert result["assay_title"][0]["term"] == "Histone ChIP-seq"
        assert result["assay_title"][0]["count"] == 500
        assert "status" in result

    async def test_caching(self):
        """Second call with same params returns cached result."""
        client = EncodeClient()
        call_count = []

        async def mock_request(path, params=None):
            call_count.append(1)
            return {"facets": [], "@graph": [], "total": 0}

        client._request = mock_request
        await client.search_facets(search_type="Experiment")
        await client.search_facets(search_type="Experiment")
        # Only one API call; second is from cache
        assert len(call_count) == 1

    async def test_different_filters_different_cache(self):
        """Different filter combos get separate cache entries."""
        client = EncodeClient()
        call_count = []

        async def mock_request(path, params=None):
            call_count.append(1)
            return {"facets": [], "@graph": [], "total": 0}

        client._request = mock_request
        await client.search_facets(search_type="Experiment", assay_title="ATAC-seq")
        await client.search_facets(search_type="Experiment", assay_title="ChIP-seq")
        assert len(call_count) == 2

    async def test_with_filters(self):
        """Filters are passed through to the API call."""
        client = EncodeClient()
        captured = {}

        async def mock_request(path, params=None):
            captured.update(params or {})
            return {"facets": [], "@graph": [], "total": 0}

        client._request = mock_request
        await client.search_facets(
            search_type="File",
            assay_title="RNA-seq",
            status="released",
        )
        assert captured.get("type") == "File"
        assert captured.get("assay_title") == "RNA-seq"
        assert captured.get("status") == "released"
        assert captured.get("limit") == 0

    async def test_empty_facets(self):
        """Empty facets field returns empty dict."""
        client = EncodeClient()

        async def mock_request(path, params=None):
            return {"facets": [], "@graph": [], "total": 0}

        client._request = mock_request
        result = await client.search_facets()
        assert result == {}

    async def test_facets_with_empty_terms_field(self):
        """Facet with empty terms list is not included."""
        client = EncodeClient()

        async def mock_request(path, params=None):
            return {
                "facets": [{"field": "empty_facet", "terms": []}],
            }

        client._request = mock_request
        result = await client.search_facets()
        assert "empty_facet" not in result


# ======================================================================
# TTL cache
# ======================================================================


class TestTTLCache:
    """Cover lines 194-204: _get_cached and _set_cached."""

    def test_set_and_get(self):
        """Set a value and get it back."""
        client = EncodeClient()
        client._set_cached("test_key", ["value1", "value2"])
        result = client._get_cached("test_key")
        assert result == ["value1", "value2"]

    def test_get_missing_key(self):
        """Missing key returns None."""
        client = EncodeClient()
        assert client._get_cached("nonexistent") is None

    def test_expired_entry(self):
        """Expired cache entry returns None."""
        client = EncodeClient()
        client._cache["expired_key"] = (["data"], time.time() - 7200)  # 2 hours ago
        assert client._get_cached("expired_key") is None

    def test_not_expired(self):
        """Non-expired entry returns value."""
        client = EncodeClient()
        client._cache["fresh_key"] = (["data"], time.time())  # just now
        assert client._get_cached("fresh_key") == ["data"]

    def test_ttl_boundary(self):
        """Entry exactly at TTL boundary still valid (just under)."""
        client = EncodeClient()
        # Set to just under TTL
        client._cache["edge_key"] = (["data"], time.time() - (client._cache_ttl - 1))
        assert client._get_cached("edge_key") == ["data"]

    def test_set_overwrites(self):
        """Setting same key overwrites previous value."""
        client = EncodeClient()
        client._set_cached("key", "first")
        client._set_cached("key", "second")
        assert client._get_cached("key") == "second"


# ======================================================================
# Credentials via EncodeClient
# ======================================================================


class TestClientCredentials:
    """Cover lines 569-585: store_credentials and clear_credentials."""

    def test_store_credentials_resets_client(self):
        """store_credentials nulls _client for fresh auth headers."""
        client = EncodeClient()
        client._client = MagicMock()  # simulate open client
        client._credential_manager.store_credentials = MagicMock(return_value="OS keyring")
        result = client.store_credentials("ak", "sk")
        assert client._client is None
        assert "keyring" in result.lower() or "OS" in result

    def test_clear_credentials_resets_client(self):
        """clear_credentials nulls _client."""
        client = EncodeClient()
        client._client = MagicMock()
        client._credential_manager.clear_credentials = MagicMock()
        client.clear_credentials()
        assert client._client is None
        client._credential_manager.clear_credentials.assert_called_once()

    def test_has_credentials_delegates(self):
        """has_credentials delegates to credential_manager."""
        client = EncodeClient()
        client._credential_manager._access_key = "ak"
        client._credential_manager._secret_key = "sk"
        assert client.has_credentials is True


# ======================================================================
# Constructor
# ======================================================================


class TestConstructor:
    def test_default_construction(self):
        """Default constructor sets expected defaults."""
        client = EncodeClient()
        assert client.base_url == "https://www.encodeproject.org"
        assert client._client is None
        assert client._cache == {}

    def test_custom_base_url(self):
        """Custom base_url is stripped of trailing slash."""
        client = EncodeClient(base_url="https://custom.encode.org/")
        assert client.base_url == "https://custom.encode.org"

    def test_explicit_credentials_stored(self):
        """Explicit credentials are stored via credential manager."""
        mock_cm = MagicMock()
        mock_cm.store_credentials.return_value = "memory"
        EncodeClient(
            access_key="ak",
            secret_key="sk",
            credential_manager=mock_cm,
        )
        mock_cm.store_credentials.assert_called_once_with("ak", "sk")

    def test_no_credentials_no_store(self):
        """Without explicit credentials, store_credentials is not called."""
        mock_cm = MagicMock()
        EncodeClient(credential_manager=mock_cm)
        mock_cm.store_credentials.assert_not_called()

    def test_partial_credentials_not_stored(self):
        """Only access_key without secret_key does not store."""
        mock_cm = MagicMock()
        EncodeClient(access_key="ak", credential_manager=mock_cm)
        mock_cm.store_credentials.assert_not_called()
