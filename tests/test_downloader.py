"""Comprehensive tests for the file downloader (path resolution, download, MD5, batch, preview)."""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from encode_connector.client.downloader import FileDownloader
from encode_connector.client.models import DownloadResult, FileSummary

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def downloader():
    """FileDownloader with a mock credential manager that returns no credentials."""
    cred_mgr = MagicMock()
    cred_mgr.get_auth_header.return_value = None
    return FileDownloader(credential_manager=cred_mgr)


@pytest.fixture
def authed_downloader():
    """FileDownloader with a mock credential manager that returns auth headers."""
    cred_mgr = MagicMock()
    cred_mgr.get_auth_header.return_value = {"Authorization": "Basic dGVzdDp0ZXN0"}
    return FileDownloader(credential_manager=cred_mgr)


@pytest.fixture
def sample_file():
    return FileSummary(
        accession="ENCFF635JIA",
        file_format="bed",
        output_type="IDR thresholded peaks",
        file_size=1024,
        download_url="https://www.encodeproject.org/files/ENCFF635JIA/@@download/ENCFF635JIA.bed.gz",
        experiment_accession="ENCSR133RZO",
        md5sum="abc123",
    )


@pytest.fixture
def sample_file_no_url():
    return FileSummary(
        accession="ENCFF001BBB",
        file_format="bam",
        output_type="alignments",
        file_size=2048,
        download_url="",
        experiment_accession="ENCSR999ZZZ",
        md5sum="def456",
    )


@pytest.fixture
def sample_file_no_md5():
    return FileSummary(
        accession="ENCFF002CCC",
        file_format="bigWig",
        output_type="signal",
        file_size=4096,
        download_url="https://www.encodeproject.org/files/ENCFF002CCC/@@download/ENCFF002CCC.bigWig",
        experiment_accession="ENCSR111AAA",
        md5sum="",
    )


# ---------------------------------------------------------------------------
# TestGetHeaders
# ---------------------------------------------------------------------------


class TestGetHeaders:
    def test_headers_without_auth(self, downloader):
        headers = downloader._get_headers()
        assert "User-Agent" in headers
        assert "Authorization" not in headers
        assert "encode-toolkit" in headers["User-Agent"]

    def test_headers_with_auth(self, authed_downloader):
        headers = authed_downloader._get_headers()
        assert "User-Agent" in headers
        assert "Authorization" in headers
        assert headers["Authorization"] == "Basic dGVzdDp0ZXN0"


# ---------------------------------------------------------------------------
# TestResolvePath — preserved from original + new edge cases
# ---------------------------------------------------------------------------


class TestResolvePath:
    def test_flat_organization(self, downloader, sample_file, tmp_path):
        path = downloader._resolve_path(tmp_path, sample_file, "flat")
        assert path.parent == tmp_path.resolve()
        assert "ENCFF635JIA" in path.name

    def test_experiment_organization(self, downloader, sample_file, tmp_path):
        path = downloader._resolve_path(tmp_path, sample_file, "experiment")
        assert "ENCSR133RZO" in str(path)

    def test_format_organization(self, downloader, sample_file, tmp_path):
        path = downloader._resolve_path(tmp_path, sample_file, "format")
        assert "bed" in str(path)

    def test_experiment_format_organization(self, downloader, sample_file, tmp_path):
        path = downloader._resolve_path(tmp_path, sample_file, "experiment_format")
        assert "ENCSR133RZO" in str(path)
        assert "bed" in str(path)

    def test_invalid_organize_by(self, downloader, sample_file, tmp_path):
        with pytest.raises(ValueError):
            downloader._resolve_path(tmp_path, sample_file, "../../etc")

    def test_path_traversal_in_filename(self, downloader, tmp_path):
        """Ensure path traversal in download URL filename is sanitized."""
        malicious_file = FileSummary(
            accession="ENCFF001AAA",
            file_format="bed",
            download_url="https://www.encodeproject.org/files/../../../etc/passwd",
        )
        path = downloader._resolve_path(tmp_path, malicious_file, "flat")
        # Should not escape the download directory
        assert str(tmp_path.resolve()) in str(path)
        assert "etc" not in str(path.parent)

    def test_path_traversal_in_experiment_accession(self, downloader, tmp_path):
        """Ensure path traversal in experiment accession is sanitized."""
        malicious_file = FileSummary(
            accession="ENCFF001AAA",
            file_format="bed",
            experiment_accession="../../etc",
        )
        path = downloader._resolve_path(tmp_path, malicious_file, "experiment")
        # safe_path_component replaces / and . with underscores, keeping path within base dir
        assert path.resolve().is_relative_to(tmp_path.resolve())
        # No actual directory traversal should occur
        assert "/etc/" not in str(path)

    def test_no_download_url(self, downloader, tmp_path):
        f = FileSummary(accession="ENCFF001AAA", file_format="bed")
        path = downloader._resolve_path(tmp_path, f, "flat")
        assert path.name == "ENCFF001AAA.bed"

    def test_no_download_url_uses_accession_and_format(self, downloader, tmp_path):
        """When download_url is empty, filename is accession.file_format."""
        f = FileSummary(accession="ENCFF999ZZZ", file_format="bigWig", download_url="")
        path = downloader._resolve_path(tmp_path, f, "flat")
        assert path.name == "ENCFF999ZZZ.bigWig"

    def test_experiment_mode_without_experiment_accession(self, downloader, tmp_path):
        """organize_by='experiment' without experiment_accession falls back to flat."""
        f = FileSummary(
            accession="ENCFF001AAA",
            file_format="bed",
            download_url="https://www.encodeproject.org/files/ENCFF001AAA/@@download/ENCFF001AAA.bed.gz",
            experiment_accession="",
        )
        path = downloader._resolve_path(tmp_path, f, "experiment")
        # Falls through to the else branch (flat) because experiment_accession is empty
        assert path.parent == tmp_path.resolve()
        assert path.name == "ENCFF001AAA.bed.gz"

    def test_experiment_format_without_experiment_accession(self, downloader, tmp_path):
        """organize_by='experiment_format' without experiment_accession falls back to flat."""
        f = FileSummary(
            accession="ENCFF001AAA",
            file_format="bed",
            download_url="https://www.encodeproject.org/files/ENCFF001AAA/@@download/ENCFF001AAA.bed.gz",
            experiment_accession="",
        )
        path = downloader._resolve_path(tmp_path, f, "experiment_format")
        assert path.parent == tmp_path.resolve()

    def test_format_mode_with_empty_format_falls_back_to_flat(self, downloader, tmp_path):
        """organize_by='format' with empty file_format falls through to flat."""
        f = FileSummary(
            accession="ENCFF001AAA",
            file_format="",
            download_url="https://www.encodeproject.org/files/ENCFF001AAA/@@download/ENCFF001AAA.bed.gz",
        )
        path = downloader._resolve_path(tmp_path, f, "format")
        assert path.parent == tmp_path.resolve()

    def test_url_with_query_params_stripped(self, downloader, tmp_path):
        """Query parameters in download URL should be stripped from filename."""
        f = FileSummary(
            accession="ENCFF001AAA",
            file_format="bed",
            download_url="https://www.encodeproject.org/files/ENCFF001AAA/@@download/ENCFF001AAA.bed.gz?token=abc",
        )
        path = downloader._resolve_path(tmp_path, f, "flat")
        assert "?" not in path.name
        assert path.name == "ENCFF001AAA.bed.gz"


# ---------------------------------------------------------------------------
# TestDownloadFile
# ---------------------------------------------------------------------------


class TestDownloadFile:
    async def test_no_download_url_returns_error(self, downloader, sample_file_no_url, tmp_path):
        """download_file returns error when file has no download URL."""
        result = await downloader.download_file(sample_file_no_url, tmp_path)
        assert not result.success
        assert result.error == "No download URL available"
        assert result.accession == "ENCFF001BBB"

    async def test_file_already_exists_with_matching_md5(self, downloader, sample_file, tmp_path):
        """download_file skips download when file exists and MD5 matches."""
        # Compute real MD5 of known content
        content = b"test file content for md5 check"
        expected_md5 = hashlib.md5(content).hexdigest()

        # Create the file that would be resolved
        file_path = downloader._resolve_path(tmp_path, sample_file, "flat")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(content)

        # Set the md5sum on the sample file to match
        sample_file.md5sum = expected_md5

        result = await downloader.download_file(sample_file, tmp_path, verify_md5=True)
        assert result.success
        assert result.md5_verified
        assert result.file_size == len(content)
        assert result.file_size_human  # Should be populated

    async def test_file_exists_but_md5_mismatch_proceeds_to_download(self, downloader, sample_file, tmp_path):
        """When file exists but MD5 doesn't match, proceeds to re-download."""
        content = b"old content"
        file_path = downloader._resolve_path(tmp_path, sample_file, "flat")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(content)

        # md5sum on sample_file is "abc123" which won't match
        with patch.object(downloader, "_stream_download", new_callable=AsyncMock) as mock_stream:
            mock_stream.side_effect = lambda url, path: path.write_bytes(b"new content")
            result = await downloader.download_file(sample_file, tmp_path, verify_md5=True)

        # Download was attempted (MD5 won't match "abc123" either, so it will fail)
        mock_stream.assert_called_once()
        # The final MD5 of "new content" won't match "abc123", so success=False
        assert not result.success
        assert "MD5 mismatch" in result.error

    async def test_successful_download_with_md5_match(self, downloader, tmp_path):
        """Full successful download with MD5 verification passing."""
        content = b"downloaded file content"
        expected_md5 = hashlib.md5(content).hexdigest()

        f = FileSummary(
            accession="ENCFF100AAA",
            file_format="bed",
            download_url="https://www.encodeproject.org/files/ENCFF100AAA/@@download/ENCFF100AAA.bed.gz",
            md5sum=expected_md5,
            file_size=len(content),
        )

        with patch.object(downloader, "_stream_download", new_callable=AsyncMock) as mock_stream:
            mock_stream.side_effect = lambda url, path: path.write_bytes(content)
            result = await downloader.download_file(f, tmp_path, verify_md5=True)

        assert result.success
        assert result.md5_verified
        assert result.file_size == len(content)
        assert result.file_size_human

    async def test_successful_download_without_md5_verification(self, downloader, sample_file_no_md5, tmp_path):
        """Download succeeds without MD5 check when md5sum is empty."""
        content = b"signal data"

        with patch.object(downloader, "_stream_download", new_callable=AsyncMock) as mock_stream:
            mock_stream.side_effect = lambda url, path: path.write_bytes(content)
            result = await downloader.download_file(sample_file_no_md5, tmp_path, verify_md5=True)

        assert result.success
        assert not result.md5_verified  # No md5sum to verify against

    async def test_successful_download_verify_md5_false(self, downloader, sample_file, tmp_path):
        """Download skips MD5 check when verify_md5=False."""
        content = b"some content"

        with patch.object(downloader, "_stream_download", new_callable=AsyncMock) as mock_stream:
            mock_stream.side_effect = lambda url, path: path.write_bytes(content)
            result = await downloader.download_file(sample_file, tmp_path, verify_md5=False)

        assert result.success
        assert not result.md5_verified

    async def test_md5_mismatch_deletes_file_and_errors(self, downloader, tmp_path):
        """MD5 mismatch after download removes the corrupted file."""
        content = b"wrong content"

        f = FileSummary(
            accession="ENCFF200BBB",
            file_format="bed",
            download_url="https://www.encodeproject.org/files/ENCFF200BBB/@@download/ENCFF200BBB.bed.gz",
            md5sum="0000000000000000000000000000dead",
            file_size=len(content),
        )

        with patch.object(downloader, "_stream_download", new_callable=AsyncMock) as mock_stream:
            mock_stream.side_effect = lambda url, path: path.write_bytes(content)
            result = await downloader.download_file(f, tmp_path, verify_md5=True)

        assert not result.success
        assert "MD5 mismatch" in result.error
        assert "0000000000000000000000000000dead" in result.error
        # The file should have been deleted
        file_path = Path(result.file_path)
        assert not file_path.exists()

    async def test_http_error_cleans_up_partial(self, downloader, sample_file, tmp_path):
        """HTTP error during download cleans up any partial file."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.reason_phrase = "Forbidden"

        with patch.object(downloader, "_stream_download", new_callable=AsyncMock) as mock_stream:
            mock_stream.side_effect = httpx.HTTPStatusError(
                "forbidden",
                request=MagicMock(),
                response=mock_response,
            )
            result = await downloader.download_file(sample_file, tmp_path)

        assert not result.success
        assert "HTTP 403" in result.error
        assert "Forbidden" in result.error
        # Partial file should be cleaned up
        if result.file_path:
            assert not Path(result.file_path).exists()

    async def test_timeout_cleans_up_partial(self, downloader, sample_file, tmp_path):
        """Timeout during download cleans up any partial file."""
        with patch.object(downloader, "_stream_download", new_callable=AsyncMock) as mock_stream:
            mock_stream.side_effect = httpx.TimeoutException("timed out")
            result = await downloader.download_file(sample_file, tmp_path)

        assert not result.success
        assert result.error == "Download timed out"
        if result.file_path:
            assert not Path(result.file_path).exists()

    async def test_generic_exception_cleans_up_partial(self, downloader, sample_file, tmp_path):
        """Generic exception during download cleans up any partial file."""
        with patch.object(downloader, "_stream_download", new_callable=AsyncMock) as mock_stream:
            mock_stream.side_effect = RuntimeError("disk full")
            result = await downloader.download_file(sample_file, tmp_path)

        assert not result.success
        assert "disk full" in result.error
        if result.file_path:
            assert not Path(result.file_path).exists()

    async def test_cancelled_error_cleans_up_and_reraises(self, downloader, sample_file, tmp_path):
        """CancelledError cleans up partial file and re-raises."""
        with patch.object(downloader, "_stream_download", new_callable=AsyncMock) as mock_stream:
            mock_stream.side_effect = asyncio.CancelledError()
            with pytest.raises(asyncio.CancelledError):
                await downloader.download_file(sample_file, tmp_path)

        # Partial file should be cleaned up
        file_path = downloader._resolve_path(tmp_path, sample_file, "flat")
        assert not file_path.exists()

    async def test_file_already_exists_verify_md5_false_still_downloads(self, downloader, sample_file, tmp_path):
        """When verify_md5=False, existing file is overwritten (no skip check)."""
        file_path = downloader._resolve_path(tmp_path, sample_file, "flat")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(b"old")

        new_content = b"new downloaded content"
        with patch.object(downloader, "_stream_download", new_callable=AsyncMock) as mock_stream:
            mock_stream.side_effect = lambda url, path: path.write_bytes(new_content)
            result = await downloader.download_file(sample_file, tmp_path, verify_md5=False)

        assert result.success
        mock_stream.assert_called_once()

    async def test_file_exists_no_md5sum_on_file_info(self, downloader, tmp_path):
        """File exists but file_info has no md5sum: skip check does not trigger."""
        f = FileSummary(
            accession="ENCFF300CCC",
            file_format="bed",
            download_url="https://www.encodeproject.org/files/ENCFF300CCC/@@download/ENCFF300CCC.bed.gz",
            md5sum="",
            file_size=100,
        )
        file_path = downloader._resolve_path(tmp_path, f, "flat")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(b"existing content")

        new_content = b"re-downloaded"
        with patch.object(downloader, "_stream_download", new_callable=AsyncMock) as mock_stream:
            mock_stream.side_effect = lambda url, path: path.write_bytes(new_content)
            result = await downloader.download_file(f, tmp_path, verify_md5=True)

        # Should still download (no md5sum to skip with)
        assert result.success
        mock_stream.assert_called_once()

    async def test_creates_parent_directories(self, downloader, tmp_path):
        """download_file creates nested directories for organized downloads."""
        f = FileSummary(
            accession="ENCFF400DDD",
            file_format="bam",
            download_url="https://www.encodeproject.org/files/ENCFF400DDD/@@download/ENCFF400DDD.bam",
            experiment_accession="ENCSR555EEE",
            md5sum="",
            file_size=512,
        )

        with patch.object(downloader, "_stream_download", new_callable=AsyncMock) as mock_stream:
            mock_stream.side_effect = lambda url, path: path.write_bytes(b"data")
            result = await downloader.download_file(f, tmp_path, organize_by="experiment")

        assert result.success
        assert "ENCSR555EEE" in result.file_path
        assert Path(result.file_path).parent.exists()


# ---------------------------------------------------------------------------
# TestStreamDownload
# ---------------------------------------------------------------------------


class TestStreamDownload:
    async def test_relative_url_prepends_base_url(self, downloader, tmp_path):
        """Relative URL (starts with /) gets base_url prepended."""
        file_path = tmp_path / "test_file.bed"

        # Mock the entire httpx.AsyncClient context manager chain
        mock_stream_response = AsyncMock()
        mock_stream_response.raise_for_status = MagicMock()
        mock_stream_response.aiter_bytes = MagicMock(return_value=_async_iter([b"chunk1", b"chunk2"]))

        mock_head_response = MagicMock()
        mock_head_response.is_redirect = False
        mock_head_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.head = AsyncMock(return_value=mock_head_response)
        mock_client.stream = MagicMock(return_value=_AsyncCtx(mock_stream_response))

        with patch("encode_connector.client.downloader.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _AsyncCtx(mock_client)
            await downloader._stream_download("/files/ENCFF001AAA/@@download/ENCFF001AAA.bed.gz", file_path)

        # HEAD should be called with the full URL
        call_args = mock_client.head.call_args
        assert call_args[0][0] == "https://www.encodeproject.org/files/ENCFF001AAA/@@download/ENCFF001AAA.bed.gz"

    async def test_redirect_with_location_header(self, downloader, tmp_path):
        """Redirect response uses location header URL with stripped auth."""
        file_path = tmp_path / "test_file.bed"
        redirect_url = "https://encode-public.s3.amazonaws.com/files/ENCFF001AAA.bed.gz"

        mock_head_response = MagicMock()
        mock_head_response.is_redirect = True
        mock_head_response.headers = {"location": redirect_url}

        mock_stream_response = AsyncMock()
        mock_stream_response.raise_for_status = MagicMock()
        mock_stream_response.aiter_bytes = MagicMock(return_value=_async_iter([b"data"]))

        mock_client = AsyncMock()
        mock_client.head = AsyncMock(return_value=mock_head_response)
        mock_client.stream = MagicMock(return_value=_AsyncCtx(mock_stream_response))

        with patch("encode_connector.client.downloader.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _AsyncCtx(mock_client)
            await downloader._stream_download(
                "https://www.encodeproject.org/files/ENCFF001AAA/@@download/ENCFF001AAA.bed.gz",
                file_path,
            )

        # Stream should be called with the redirect URL
        stream_call = mock_client.stream.call_args
        assert stream_call[0][1] == redirect_url
        # Auth headers should be stripped (only User-Agent)
        stream_headers = stream_call[1]["headers"]
        assert "Authorization" not in stream_headers
        assert "User-Agent" in stream_headers

    async def test_redirect_without_location_header(self, downloader, tmp_path):
        """Redirect response without location header falls back to original URL."""
        file_path = tmp_path / "test_file.bed"
        original_url = "https://www.encodeproject.org/files/ENCFF001AAA/@@download/ENCFF001AAA.bed.gz"

        mock_head_response = MagicMock()
        mock_head_response.is_redirect = True
        mock_head_response.headers = {}  # No location header

        mock_stream_response = AsyncMock()
        mock_stream_response.raise_for_status = MagicMock()
        mock_stream_response.aiter_bytes = MagicMock(return_value=_async_iter([b"data"]))

        mock_client = AsyncMock()
        mock_client.head = AsyncMock(return_value=mock_head_response)
        mock_client.stream = MagicMock(return_value=_AsyncCtx(mock_stream_response))

        with patch("encode_connector.client.downloader.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _AsyncCtx(mock_client)
            await downloader._stream_download(original_url, file_path)

        # Should stream from original URL (not redirect)
        stream_call = mock_client.stream.call_args
        assert stream_call[0][1] == original_url

    async def test_non_redirect_calls_raise_for_status(self, downloader, tmp_path):
        """Non-redirect HEAD response calls raise_for_status."""
        file_path = tmp_path / "test_file.bed"

        mock_head_response = MagicMock()
        mock_head_response.is_redirect = False
        mock_head_response.raise_for_status = MagicMock()

        mock_stream_response = AsyncMock()
        mock_stream_response.raise_for_status = MagicMock()
        mock_stream_response.aiter_bytes = MagicMock(return_value=_async_iter([b"data"]))

        mock_client = AsyncMock()
        mock_client.head = AsyncMock(return_value=mock_head_response)
        mock_client.stream = MagicMock(return_value=_AsyncCtx(mock_stream_response))

        with patch("encode_connector.client.downloader.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _AsyncCtx(mock_client)
            await downloader._stream_download(
                "https://www.encodeproject.org/files/ENCFF001AAA/@@download/ENCFF001AAA.bed.gz",
                file_path,
            )

        mock_head_response.raise_for_status.assert_called_once()

    async def test_redirect_strips_auth_headers(self, authed_downloader, tmp_path):
        """When following a redirect, authorization headers are stripped for safety."""
        file_path = tmp_path / "test_file.bed"
        redirect_url = "https://encode-public.s3.amazonaws.com/files/test.bed.gz"

        mock_head_response = MagicMock()
        mock_head_response.is_redirect = True
        mock_head_response.headers = {"location": redirect_url}

        mock_stream_response = AsyncMock()
        mock_stream_response.raise_for_status = MagicMock()
        mock_stream_response.aiter_bytes = MagicMock(return_value=_async_iter([b"data"]))

        mock_client = AsyncMock()
        mock_client.head = AsyncMock(return_value=mock_head_response)
        mock_client.stream = MagicMock(return_value=_AsyncCtx(mock_stream_response))

        with patch("encode_connector.client.downloader.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _AsyncCtx(mock_client)
            await authed_downloader._stream_download(
                "https://www.encodeproject.org/files/test/@@download/test.bed.gz",
                file_path,
            )

        stream_call = mock_client.stream.call_args
        stream_headers = stream_call[1]["headers"]
        assert "Authorization" not in stream_headers
        assert "User-Agent" in stream_headers

    async def test_invalid_download_url_raises(self, downloader, tmp_path):
        """Invalid download host raises ValueError during URL validation."""
        file_path = tmp_path / "test_file.bed"
        with pytest.raises(ValueError, match="not allowed"):
            await downloader._stream_download("https://evil.com/malware.exe", file_path)

    async def test_belt_and_suspenders_revalidates_redirect_url(self, downloader, tmp_path):
        """Belt-and-suspenders: redirect URL is re-validated before GET."""
        file_path = tmp_path / "test_file.bed"
        redirect_url = "https://encode-public.s3.amazonaws.com/files/test.bed.gz"
        original_url = "https://www.encodeproject.org/files/test/@@download/test.bed.gz"

        mock_head_response = MagicMock()
        mock_head_response.is_redirect = True
        mock_head_response.headers = {"location": redirect_url}

        mock_stream_response = AsyncMock()
        mock_stream_response.raise_for_status = MagicMock()
        mock_stream_response.aiter_bytes = MagicMock(return_value=_async_iter([b"data"]))

        mock_client = AsyncMock()
        mock_client.head = AsyncMock(return_value=mock_head_response)
        mock_client.stream = MagicMock(return_value=_AsyncCtx(mock_stream_response))

        with (
            patch("encode_connector.client.downloader.httpx.AsyncClient") as mock_cls,
            patch("encode_connector.client.downloader.validate_redirect_url", wraps=_identity) as mock_validate,
        ):
            mock_cls.return_value = _AsyncCtx(mock_client)
            await downloader._stream_download(original_url, file_path)

        # validate_redirect_url should be called twice:
        # once for the initial redirect, once for belt-and-suspenders
        assert mock_validate.call_count == 2

    async def test_writes_streamed_chunks_to_file(self, downloader, tmp_path):
        """Streamed chunks are written correctly to the output file."""
        file_path = tmp_path / "test_output.bed"
        chunks = [b"chunk_one_", b"chunk_two_", b"chunk_three"]

        mock_head_response = MagicMock()
        mock_head_response.is_redirect = False
        mock_head_response.raise_for_status = MagicMock()

        mock_stream_response = AsyncMock()
        mock_stream_response.raise_for_status = MagicMock()
        mock_stream_response.aiter_bytes = MagicMock(return_value=_async_iter(chunks))

        mock_client = AsyncMock()
        mock_client.head = AsyncMock(return_value=mock_head_response)
        mock_client.stream = MagicMock(return_value=_AsyncCtx(mock_stream_response))

        with patch("encode_connector.client.downloader.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _AsyncCtx(mock_client)
            await downloader._stream_download(
                "https://www.encodeproject.org/files/test/@@download/test.bed.gz",
                file_path,
            )

        assert file_path.read_bytes() == b"chunk_one_chunk_two_chunk_three"


# ---------------------------------------------------------------------------
# TestComputeMd5
# ---------------------------------------------------------------------------


class TestComputeMd5:
    async def test_compute_md5_returns_correct_hash(self, downloader, tmp_path):
        """_compute_md5 returns the correct MD5 hex digest."""
        content = b"hello world"
        expected = hashlib.md5(content).hexdigest()

        file_path = tmp_path / "test.txt"
        file_path.write_bytes(content)

        result = await downloader._compute_md5(file_path)
        assert result == expected

    async def test_compute_md5_empty_file(self, downloader, tmp_path):
        """_compute_md5 works on empty files."""
        expected = hashlib.md5(b"").hexdigest()

        file_path = tmp_path / "empty.txt"
        file_path.write_bytes(b"")

        result = await downloader._compute_md5(file_path)
        assert result == expected

    async def test_compute_md5_large_content(self, downloader, tmp_path):
        """_compute_md5 correctly hashes content larger than chunk size."""
        # Create content larger than the 65536-byte chunk size
        content = b"x" * 200_000
        expected = hashlib.md5(content).hexdigest()

        file_path = tmp_path / "large.bin"
        file_path.write_bytes(content)

        result = await downloader._compute_md5(file_path)
        assert result == expected

    def test_md5_sync_returns_correct_hash(self, tmp_path):
        """_md5_sync (static method) returns correct MD5 hex digest."""
        content = b"test content for md5"
        expected = hashlib.md5(content).hexdigest()

        file_path = tmp_path / "sync_test.txt"
        file_path.write_bytes(content)

        result = FileDownloader._md5_sync(file_path)
        assert result == expected


# ---------------------------------------------------------------------------
# TestDownloadBatch
# ---------------------------------------------------------------------------


class TestDownloadBatch:
    async def test_batch_multiple_files(self, downloader, tmp_path):
        """download_batch processes multiple files and returns results for each."""
        files = [
            FileSummary(
                accession=f"ENCFF00{i}AAA",
                file_format="bed",
                download_url=f"https://www.encodeproject.org/files/ENCFF00{i}AAA/@@download/ENCFF00{i}AAA.bed.gz",
                md5sum="",
                file_size=100 * i,
            )
            for i in range(1, 4)
        ]

        with patch.object(downloader, "_stream_download", new_callable=AsyncMock) as mock_stream:
            mock_stream.side_effect = lambda url, path: path.write_bytes(b"content")
            results = await downloader.download_batch(files, tmp_path)

        assert len(results) == 3
        assert all(isinstance(r, DownloadResult) for r in results)
        assert all(r.success for r in results)

    async def test_batch_exception_in_one_task(self, downloader, tmp_path):
        """One failing download in a batch doesn't cancel others; returns DownloadResult with error."""
        files = [
            FileSummary(
                accession="ENCFF001AAA",
                file_format="bed",
                download_url="https://www.encodeproject.org/files/ENCFF001AAA/@@download/ENCFF001AAA.bed.gz",
                file_size=100,
            ),
            FileSummary(
                accession="ENCFF002BBB",
                file_format="bam",
                download_url="https://www.encodeproject.org/files/ENCFF002BBB/@@download/ENCFF002BBB.bam",
                file_size=200,
            ),
        ]

        call_count = 0

        async def mock_download(file_info, download_dir, organize_by="flat", verify_md5=True):
            nonlocal call_count
            call_count += 1
            if file_info.accession == "ENCFF001AAA":
                raise RuntimeError("Unexpected crash")
            result = DownloadResult(accession=file_info.accession)
            result.success = True
            return result

        with patch.object(downloader, "download_file", side_effect=mock_download):
            results = await downloader.download_batch(files, tmp_path)

        assert len(results) == 2
        # First result should be the error (from the exception wrapper)
        error_result = next(r for r in results if r.accession == "ENCFF001AAA")
        assert not error_result.success
        assert "Unexpected error" in error_result.error
        # Second result should succeed
        success_result = next(r for r in results if r.accession == "ENCFF002BBB")
        assert success_result.success

    async def test_batch_empty_list(self, downloader, tmp_path):
        """download_batch with empty file list returns empty results."""
        results = await downloader.download_batch([], tmp_path)
        assert results == []

    async def test_batch_respects_organize_by(self, downloader, tmp_path):
        """download_batch passes organize_by and verify_md5 through to download_file."""
        f = FileSummary(
            accession="ENCFF001AAA",
            file_format="bed",
            download_url="https://www.encodeproject.org/files/ENCFF001AAA/@@download/ENCFF001AAA.bed.gz",
            file_size=100,
        )

        with patch.object(downloader, "download_file", new_callable=AsyncMock) as mock_dl:
            mock_dl.return_value = DownloadResult(accession="ENCFF001AAA", success=True)
            await downloader.download_batch([f], tmp_path, organize_by="format", verify_md5=False)

        mock_dl.assert_called_once_with(f, tmp_path, "format", False)


# ---------------------------------------------------------------------------
# TestPreviewDownloads — preserved from original + new tests
# ---------------------------------------------------------------------------


class TestPreviewDownloads:
    def test_preview(self, downloader, sample_file, tmp_path):
        preview = downloader.preview_downloads([sample_file], tmp_path, "flat")
        assert preview["file_count"] == 1
        assert preview["total_size"] == 1024
        assert len(preview["files"]) == 1
        assert preview["files"][0]["accession"] == "ENCFF635JIA"

    def test_preview_empty(self, downloader, tmp_path):
        preview = downloader.preview_downloads([], tmp_path)
        assert preview["file_count"] == 0
        assert preview["total_size"] == 0

    def test_preview_multiple_files(self, downloader, tmp_path):
        files = [FileSummary(accession=f"ENCFF00{i}AAA", file_format="bed", file_size=1000 * i) for i in range(1, 4)]
        preview = downloader.preview_downloads(files, tmp_path)
        assert preview["file_count"] == 3
        assert preview["total_size"] == 1000 + 2000 + 3000
        assert len(preview["files"]) == 3

    def test_preview_shows_already_exists(self, downloader, sample_file, tmp_path):
        """Preview detects when a file already exists on disk."""
        file_path = downloader._resolve_path(tmp_path, sample_file, "flat")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(b"existing")

        preview = downloader.preview_downloads([sample_file], tmp_path, "flat")
        assert preview["files"][0]["already_exists"] is True

    def test_preview_shows_not_exists(self, downloader, sample_file, tmp_path):
        """Preview correctly reports when file does not exist."""
        preview = downloader.preview_downloads([sample_file], tmp_path, "flat")
        assert preview["files"][0]["already_exists"] is False

    def test_preview_with_experiment_organization(self, downloader, sample_file, tmp_path):
        preview = downloader.preview_downloads([sample_file], tmp_path, "experiment")
        assert "ENCSR133RZO" in preview["files"][0]["target_path"]

    def test_preview_with_format_organization(self, downloader, sample_file, tmp_path):
        preview = downloader.preview_downloads([sample_file], tmp_path, "format")
        assert "/bed/" in preview["files"][0]["target_path"]

    def test_preview_contains_all_fields(self, downloader, sample_file, tmp_path):
        """Each preview entry contains all expected fields."""
        preview = downloader.preview_downloads([sample_file], tmp_path, "flat")
        entry = preview["files"][0]
        assert "accession" in entry
        assert "file_format" in entry
        assert "output_type" in entry
        assert "file_size" in entry
        assert "file_size_human" in entry
        assert "target_path" in entry
        assert "already_exists" in entry

    def test_preview_total_size_human_readable(self, downloader, tmp_path):
        """Preview total_size_human is a human-readable string."""
        f = FileSummary(accession="ENCFF001AAA", file_format="bed", file_size=1_048_576)
        preview = downloader.preview_downloads([f], tmp_path)
        assert preview["total_size_human"] == "1.0 MB"


# ---------------------------------------------------------------------------
# TestInit
# ---------------------------------------------------------------------------


class TestInit:
    def test_default_initialization(self):
        """FileDownloader initializes with default parameters."""
        dl = FileDownloader()
        assert dl.base_url == "https://www.encodeproject.org"
        assert dl._max_concurrent == 3

    def test_custom_base_url_strips_trailing_slash(self):
        dl = FileDownloader(base_url="https://example.org/")
        assert dl.base_url == "https://example.org"

    def test_custom_max_concurrent(self):
        dl = FileDownloader(max_concurrent=10)
        assert dl._max_concurrent == 10

    def test_custom_credential_manager(self):
        cred_mgr = MagicMock()
        dl = FileDownloader(credential_manager=cred_mgr)
        assert dl._credential_manager is cred_mgr


# ---------------------------------------------------------------------------
# Async helper utilities for mocking httpx streaming
# ---------------------------------------------------------------------------


async def _async_iter(items):
    """Create an async iterator from a list of items."""
    for item in items:
        yield item


class _AsyncCtx:
    """Simple async context manager wrapper for mocking `async with` patterns."""

    def __init__(self, value):
        self._value = value

    async def __aenter__(self):
        return self._value

    def __aexit__(self, *args):
        return self._async_exit(*args)

    async def _async_exit(self, *args):
        pass

    # Also support synchronous context manager (for client.stream which uses `async with`)
    def __enter__(self):
        return self._value

    def __exit__(self, *args):
        pass


def _identity(value):
    """Identity function used as a wraps target for validation patches."""
    return value
