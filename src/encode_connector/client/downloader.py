"""File download manager for ENCODE data files.

Downloads are always to user-specified local directories.
Supports MD5 verification, concurrent downloads with rate limiting,
and organization by experiment or file format.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from pathlib import Path
from typing import Any

import httpx

from encode_connector.client.auth import CredentialManager
from encode_connector.client.constants import (
    BASE_URL,
    DOWNLOAD_CONCURRENCY,
    DOWNLOAD_TIMEOUT,
    USER_AGENT,
)
from encode_connector.client.models import DownloadResult, FileSummary, _human_size
from encode_connector.client.validation import (
    safe_path_component,
    validate_download_url,
    validate_organize_by,
    validate_redirect_url,
)

logger = logging.getLogger(__name__)


class FileDownloader:
    """Manages file downloads from ENCODE with concurrency and verification."""

    def __init__(
        self,
        credential_manager: CredentialManager | None = None,
        base_url: str = BASE_URL,
        max_concurrent: int = DOWNLOAD_CONCURRENCY,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._credential_manager = credential_manager or CredentialManager()
        self._max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)

    def _get_headers(self) -> dict[str, str]:
        """Build request headers including optional auth."""
        headers = {
            "User-Agent": USER_AGENT,
        }
        auth = self._credential_manager.get_auth_header()
        if auth:
            headers.update(auth)
        return headers

    def _resolve_path(
        self,
        download_dir: str | Path,
        file_info: FileSummary,
        organize_by: str = "flat",
    ) -> Path:
        """Determine the local file path for a download.

        Args:
            download_dir: Base download directory.
            file_info: File metadata.
            organize_by: How to organize files:
                - "flat": all files in download_dir
                - "experiment": download_dir/ENCSR.../filename
                - "format": download_dir/bed/filename
                - "experiment_format": download_dir/ENCSR.../bed/filename
        """
        validate_organize_by(organize_by)
        base = Path(download_dir).resolve()

        # Determine filename from the download URL (sanitize to prevent path traversal)
        if file_info.download_url:
            url_path = Path(file_info.download_url.split("?")[0]).name
        else:
            url_path = ""
        filename = url_path or f"{file_info.accession}.{file_info.file_format}"
        # Extra safety: strip any remaining path separators
        filename = Path(filename).name

        # Sanitize subdirectory components to prevent path traversal
        if organize_by == "experiment" and file_info.experiment_accession:
            subdir = safe_path_component(file_info.experiment_accession)
            return base / subdir / filename
        elif organize_by == "format" and file_info.file_format:
            subdir = safe_path_component(file_info.file_format)
            return base / subdir / filename
        elif organize_by == "experiment_format" and file_info.experiment_accession:
            exp_dir = safe_path_component(file_info.experiment_accession)
            fmt_dir = safe_path_component(file_info.file_format)
            return base / exp_dir / fmt_dir / filename
        else:
            return base / filename

    async def download_file(
        self,
        file_info: FileSummary,
        download_dir: str | Path,
        organize_by: str = "flat",
        verify_md5: bool = True,
    ) -> DownloadResult:
        """Download a single file with rate limiting and optional MD5 verification."""
        result = DownloadResult(accession=file_info.accession)

        if not file_info.download_url:
            result.error = "No download URL available"
            return result

        file_path = self._resolve_path(download_dir, file_info, organize_by)
        result.file_path = str(file_path)

        # Skip if already downloaded and MD5 matches
        if file_path.exists() and verify_md5 and file_info.md5sum:
            existing_md5 = await self._compute_md5(file_path)
            if existing_md5 == file_info.md5sum:
                result.success = True
                result.md5_verified = True
                result.file_size = file_path.stat().st_size
                result.file_size_human = _human_size(result.file_size)
                logger.info("Skipping %s (already downloaded, MD5 verified)", file_info.accession)
                return result

        # Create parent directories
        file_path.parent.mkdir(parents=True, exist_ok=True)

        async with self._semaphore:
            try:
                await self._stream_download(file_info.download_url, file_path)

                result.file_size = file_path.stat().st_size
                result.file_size_human = _human_size(result.file_size)
                result.success = True

                # Verify MD5 if available
                if verify_md5 and file_info.md5sum:
                    computed_md5 = await self._compute_md5(file_path)
                    if computed_md5 == file_info.md5sum:
                        result.md5_verified = True
                    else:
                        result.success = False
                        result.error = f"MD5 mismatch: expected {file_info.md5sum}, got {computed_md5}"
                        # Remove corrupted file
                        file_path.unlink(missing_ok=True)

                if result.success:
                    logger.info(
                        "Downloaded %s (%s) -> %s",
                        file_info.accession,
                        result.file_size_human,
                        file_path,
                    )

            except httpx.HTTPStatusError as e:
                result.error = f"HTTP {e.response.status_code}: {e.response.reason_phrase}"
                logger.error("Failed to download %s: %s", file_info.accession, result.error)
                file_path.unlink(missing_ok=True)
            except httpx.TimeoutException:
                result.error = "Download timed out"
                logger.error("Timeout downloading %s", file_info.accession)
                file_path.unlink(missing_ok=True)
            except BaseException as e:
                # Catch BaseException (including asyncio.CancelledError) to ensure
                # partial files are cleaned up on cancellation or any other error
                result.error = str(e)
                logger.error("Error downloading %s: %s", file_info.accession, e)
                file_path.unlink(missing_ok=True)
                if isinstance(e, (KeyboardInterrupt, asyncio.CancelledError)):
                    raise

        return result

    async def _stream_download(self, url: str, file_path: Path) -> None:
        """Stream download a file to disk.

        Validates download URL against allowed hosts. Uses a HEAD request to
        detect redirects, then streams the response in all cases to avoid
        loading large files (BAM/FASTQ can be 50+ GB) into memory.
        """
        # Ensure absolute URL
        if url.startswith("/"):
            url = f"{self.base_url}{url}"

        # Validate the URL is to an allowed ENCODE host
        validate_download_url(url)

        headers = self._get_headers()

        async with httpx.AsyncClient(
            follow_redirects=False,
            timeout=DOWNLOAD_TIMEOUT,
        ) as client:
            # Use HEAD to detect redirects without downloading the body
            head_response = await client.head(url, headers=headers)

            if head_response.is_redirect:
                redirect_url = str(head_response.headers.get("location", ""))
                if redirect_url:
                    validate_redirect_url(redirect_url)
                    # For S3/CDN redirects, strip auth headers
                    safe_headers = {"User-Agent": headers.get("User-Agent", USER_AGENT)}
                    stream_url = redirect_url
                    stream_headers = safe_headers
                else:
                    stream_url = url
                    stream_headers = headers
            else:
                head_response.raise_for_status()
                stream_url = url
                stream_headers = headers

            # Belt-and-suspenders: re-validate stream_url before the GET
            # to guard against any code path that might set it without validation
            if stream_url != url:
                validate_redirect_url(stream_url)
            else:
                validate_download_url(stream_url)

            # Always stream the download to avoid loading entire file into memory
            async with client.stream("GET", stream_url, headers=stream_headers) as response:
                response.raise_for_status()
                with open(file_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=65536):
                        f.write(chunk)

    async def _compute_md5(self, file_path: Path) -> str:
        """Compute MD5 hash of a file asynchronously."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._md5_sync, file_path)

    @staticmethod
    def _md5_sync(file_path: Path) -> str:
        """Compute MD5 hash synchronously."""
        md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                md5.update(chunk)
        return md5.hexdigest()

    async def download_batch(
        self,
        files: list[FileSummary],
        download_dir: str | Path,
        organize_by: str = "flat",
        verify_md5: bool = True,
    ) -> list[DownloadResult]:
        """Download multiple files concurrently.

        Returns list of DownloadResult for each file.
        """
        tasks = [self.download_file(f, download_dir, organize_by, verify_md5) for f in files]
        # Use return_exceptions=True so one failed download doesn't cancel the rest
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # Convert any unexpected exceptions into failed DownloadResult objects
        final: list[DownloadResult] = []
        for i, result in enumerate(results):
            if isinstance(result, BaseException):
                dr = DownloadResult(accession=files[i].accession)
                dr.error = f"Unexpected error: {result}"
                final.append(dr)
            else:
                final.append(result)
        return final

    def preview_downloads(
        self,
        files: list[FileSummary],
        download_dir: str | Path,
        organize_by: str = "flat",
    ) -> dict[str, Any]:
        """Preview what would be downloaded without actually downloading.

        Returns summary with file list, total size, and paths.
        """
        previews = []
        total_size = 0

        for f in files:
            path = self._resolve_path(download_dir, f, organize_by)
            total_size += f.file_size
            previews.append(
                {
                    "accession": f.accession,
                    "file_format": f.file_format,
                    "output_type": f.output_type,
                    "file_size": f.file_size,
                    "file_size_human": f.file_size_human,
                    "target_path": str(path),
                    "already_exists": path.exists(),
                }
            )

        return {
            "file_count": len(files),
            "total_size": total_size,
            "total_size_human": _human_size(total_size),
            "files": previews,
        }
