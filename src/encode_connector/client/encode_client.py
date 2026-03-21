"""Async HTTP client for the ENCODE Project REST API.

All requests go over HTTPS to encodeproject.org only.
No data is sent to any other server. No telemetry or analytics.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from encode_connector.client.auth import CredentialManager
from encode_connector.client.constants import (
    BASE_URL,
    DEFAULT_LIMIT,
    DEFAULT_TIMEOUT,
    EXPERIMENT_FILTER_MAP,
    FILE_FILTER_MAP,
    MAX_REQUESTS_PER_SECOND,
    METADATA_MAP,
    USER_AGENT,
)
from encode_connector.client.models import (
    ExperimentDetail,
    ExperimentSummary,
    FileSummary,
)
from encode_connector.client.validation import (
    clamp_limit,
    validate_accession,
    validate_date,
)

logger = logging.getLogger(__name__)

# Retry configuration for transient failures
MAX_RETRIES = 3
RETRY_BACKOFF = [1.0, 2.0, 4.0]
RETRYABLE_STATUS_CODES = frozenset({429, 502, 503, 504})


class EncodeClient:
    """Async client for the ENCODE Project REST API.

    Usage:
        async with EncodeClient() as client:
            experiments = await client.search_experiments(
                assay_title="Histone ChIP-seq",
                organism="Homo sapiens",
                organ="pancreas",
                biosample_type="tissue",
            )
    """

    def __init__(
        self,
        access_key: str | None = None,
        secret_key: str | None = None,
        base_url: str = BASE_URL,
        credential_manager: CredentialManager | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._credential_manager = credential_manager or CredentialManager()

        # If explicit credentials provided, store them
        if access_key and secret_key:
            self._credential_manager.store_credentials(access_key, secret_key)

        self._client: httpx.AsyncClient | None = None
        self._client_lock = asyncio.Lock()

        # TTL cache for metadata and facets (avoids repeated identical API calls)
        self._cache: dict[str, tuple[Any, float]] = {}
        self._cache_ttl = 3600  # 1 hour

        # Rate limiter: token bucket
        self._rate_limit = MAX_REQUESTS_PER_SECOND
        self._semaphore = asyncio.Semaphore(MAX_REQUESTS_PER_SECOND)
        self._last_request_time = 0.0
        self._rate_lock = asyncio.Lock()

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client.

        Uses an asyncio.Lock to prevent concurrent coroutines from
        creating duplicate clients (race condition on _client is None check).
        """
        async with self._client_lock:
            if self._client is None or self._client.is_closed:
                headers = {
                    "Accept": "application/json",
                    "User-Agent": USER_AGENT,
                }
                # Add auth headers if credentials available
                auth_headers = self._credential_manager.get_auth_header()
                if auth_headers:
                    headers.update(auth_headers)

                self._client = httpx.AsyncClient(
                    base_url=self.base_url,
                    headers=headers,
                    timeout=DEFAULT_TIMEOUT,
                    follow_redirects=True,
                    # HTTPS certificate verification enforced (default)
                    # Note: httpx strips auth headers on cross-origin redirects by default
                )
            return self._client

    async def _request(self, path: str, params: dict[str, Any] | None = None) -> dict:
        """Make a rate-limited GET request to the ENCODE API with retry on transient failures."""
        last_exception: Exception | None = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                async with self._semaphore:
                    # Enforce rate limiting with lock to prevent race conditions
                    async with self._rate_lock:
                        now = time.monotonic()
                        min_interval = 1.0 / self._rate_limit
                        elapsed = now - self._last_request_time
                        if elapsed < min_interval:
                            await asyncio.sleep(min_interval - elapsed)
                        self._last_request_time = time.monotonic()

                    client = await self._ensure_client()
                    response = await client.get(path, params=params)

                    # Retry on transient server errors
                    if response.status_code in RETRYABLE_STATUS_CODES:
                        if attempt < MAX_RETRIES:
                            delay = RETRY_BACKOFF[attempt]
                            logger.warning(
                                "ENCODE API returned %d for %s, retrying in %.1fs (attempt %d/%d)",
                                response.status_code,
                                path,
                                delay,
                                attempt + 1,
                                MAX_RETRIES,
                            )
                            await asyncio.sleep(delay)
                            continue
                        # Final attempt — let raise_for_status handle it
                    response.raise_for_status()
                    return response.json()

            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as e:
                last_exception = e
                if attempt < MAX_RETRIES:
                    delay = RETRY_BACKOFF[attempt]
                    logger.warning(
                        "Connection error for %s: %s, retrying in %.1fs (attempt %d/%d)",
                        path,
                        type(e).__name__,
                        delay,
                        attempt + 1,
                        MAX_RETRIES,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise

        # Should not reach here, but just in case
        if last_exception:
            raise last_exception
        raise RuntimeError("Unexpected retry exhaustion")

    async def get_json(self, path: str, params: dict[str, Any] | None = None) -> dict:
        """Public method to fetch JSON from an ENCODE API path.

        Use this instead of calling _request directly from outside the client.
        """
        return await self._request(path, params)

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> EncodeClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # TTL cache helpers
    # ------------------------------------------------------------------

    def _get_cached(self, key: str) -> Any | None:
        """Return cached value if still within TTL, else None."""
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < self._cache_ttl:
                return value
        return None

    def _set_cached(self, key: str, value: Any) -> None:
        """Store a value in the TTL cache."""
        self._cache[key] = (value, time.time())

    # ------------------------------------------------------------------
    # Experiment queries
    # ------------------------------------------------------------------

    async def search_experiments(
        self,
        assay_title: str | None = None,
        organism: str | None = None,
        organ: str | None = None,
        biosample_type: str | None = None,
        biosample_term_name: str | None = None,
        target: str | None = None,
        status: str | None = None,
        lab: str | None = None,
        award: str | None = None,
        assembly: str | None = None,
        replication_type: str | None = None,
        life_stage: str | None = None,
        sex: str | None = None,
        treatment: str | None = None,
        genetic_modification: str | None = None,
        perturbed: bool | None = None,
        search_term: str | None = None,
        date_released_from: str | None = None,
        date_released_to: str | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Search ENCODE experiments with comprehensive filters.

        Returns dict with 'results' (list of ExperimentSummary) and 'total' count.
        """
        limit = clamp_limit(limit)
        params: dict[str, Any] = {
            "type": "Experiment",
            "format": "json",
            "frame": "object",
            "limit": limit,
        }
        if offset > 0:
            params["from"] = offset

        # Map user-friendly params to API params
        filter_values = {
            "assay_title": assay_title,
            "organism": organism,
            "organ": organ,
            "biosample_type": biosample_type,
            "biosample_term_name": biosample_term_name,
            "target": target,
            "status": status,
            "lab": lab,
            "award": award,
            "assembly": assembly,
            "replication_type": replication_type,
            "life_stage": life_stage,
            "sex": sex,
            "treatment": treatment,
            "genetic_modification": genetic_modification,
            "searchTerm": search_term,
        }

        for key, value in filter_values.items():
            if value is not None:
                api_param = EXPERIMENT_FILTER_MAP.get(key, key)
                params[api_param] = value

        if perturbed is not None:
            params[EXPERIMENT_FILTER_MAP["perturbed"]] = str(perturbed).lower()

        # Date range filtering (sanitize inputs to prevent Lucene injection)
        if date_released_from:
            validate_date(date_released_from)
        if date_released_to:
            validate_date(date_released_to)
        if date_released_from or date_released_to:
            from_date = date_released_from or "*"
            to_date = date_released_to or "*"
            existing = params.get("advancedQuery", "").strip()
            date_clause = f"date_released:[{from_date} TO {to_date}]"
            params["advancedQuery"] = f"{existing} {date_clause}".strip()

        data = await self._request("/search/", params)

        results = [ExperimentSummary.from_api(exp) for exp in data.get("@graph", [])]

        return {
            "results": results,
            "total": data.get("total", len(results)),
            "limit": limit,
            "offset": offset,
        }

    async def get_experiment_raw(self, accession: str) -> dict:
        """Get raw experiment data with embedded frame."""
        validate_accession(accession)
        return await self._request(
            f"/experiments/{accession}/",
            {"format": "json", "frame": "embedded"},
        )

    async def get_experiment(self, accession: str) -> ExperimentDetail:
        """Get full details for a single experiment including its files."""
        validate_accession(accession)
        # Get experiment data
        exp_data = await self._request(
            f"/experiments/{accession}/",
            {"format": "json", "frame": "embedded"},
        )

        # Get files for this experiment
        files_data = await self._request(
            "/search/",
            {
                "type": "File",
                "dataset": f"/experiments/{accession}/",
                "format": "json",
                "frame": "object",
                "limit": "all",
            },
        )

        files = files_data.get("@graph", [])
        return ExperimentDetail.from_api(exp_data, files)

    # ------------------------------------------------------------------
    # File queries
    # ------------------------------------------------------------------

    async def list_files(
        self,
        experiment_accession: str,
        file_format: str | None = None,
        file_type: str | None = None,
        output_type: str | None = None,
        output_category: str | None = None,
        assembly: str | None = None,
        status: str | None = None,
        preferred_default: bool | None = None,
        limit: int = 200,
    ) -> list[FileSummary]:
        """List files for a specific experiment with optional filters."""
        validate_accession(experiment_accession)
        limit = clamp_limit(limit)
        params: dict[str, Any] = {
            "type": "File",
            "dataset": f"/experiments/{experiment_accession}/",
            "format": "json",
            "frame": "object",
            "limit": limit,
        }

        filter_values = {
            "file_format": file_format,
            "file_type": file_type,
            "output_type": output_type,
            "output_category": output_category,
            "assembly": assembly,
            "status": status,
        }

        for key, value in filter_values.items():
            if value is not None:
                api_param = FILE_FILTER_MAP.get(key, key)
                params[api_param] = value

        if preferred_default is not None:
            params["preferred_default"] = str(preferred_default).lower()

        data = await self._request("/search/", params)
        return [FileSummary.from_api(f) for f in data.get("@graph", [])]

    async def search_files(
        self,
        file_format: str | None = None,
        file_type: str | None = None,
        output_type: str | None = None,
        output_category: str | None = None,
        assembly: str | None = None,
        assay_title: str | None = None,
        organism: str | None = None,
        organ: str | None = None,
        biosample_type: str | None = None,
        target: str | None = None,
        status: str | None = None,
        preferred_default: bool | None = None,
        search_term: str | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Search files across all experiments with combined filters."""
        limit = clamp_limit(limit)
        params: dict[str, Any] = {
            "type": "File",
            "format": "json",
            "frame": "object",
            "limit": limit,
        }
        if offset > 0:
            params["from"] = offset

        # File-level filters
        file_filters = {
            "file_format": file_format,
            "file_type": file_type,
            "output_type": output_type,
            "output_category": output_category,
            "assembly": assembly,
            "status": status,
        }
        for key, value in file_filters.items():
            if value is not None:
                api_param = FILE_FILTER_MAP.get(key, key)
                params[api_param] = value

        if preferred_default is not None:
            params["preferred_default"] = str(preferred_default).lower()

        # Experiment-level filters available on File search
        if assay_title:
            params["assay_title"] = assay_title
        if organ:
            params["biosample_ontology.organ_slims"] = organ
        if biosample_type:
            params["biosample_ontology.classification"] = biosample_type
        if target:
            params["target.label"] = target

        # For organism filtering on files, we need a two-step approach:
        # search experiments first, then get files from matching experiments
        if organism:
            # For non-human organisms, do a two-step search
            exp_result = await self.search_experiments(
                assay_title=assay_title,
                organism=organism,
                organ=organ,
                biosample_type=biosample_type,
                target=target,
                status=status or "released",
                search_term=search_term,
                limit=200,
            )
            if not exp_result["results"]:
                return {"results": [], "total": 0, "limit": limit, "offset": offset}

            # Get files from matching experiments
            all_files = []
            for exp in exp_result["results"]:
                exp_files = await self.list_files(
                    experiment_accession=exp.accession,
                    file_format=file_format,
                    file_type=file_type,
                    output_type=output_type,
                    output_category=output_category,
                    assembly=assembly,
                    status=status,
                    preferred_default=preferred_default,
                )
                all_files.extend(exp_files)
                if len(all_files) >= limit:
                    break

            return {
                "results": all_files[:limit],
                "total": len(all_files),
                "total_note": "Approximate — based on files collected from matching experiments",
                "limit": limit,
                "offset": offset,
            }

        if search_term:
            params["searchTerm"] = search_term

        data = await self._request("/search/", params)
        results = [FileSummary.from_api(f) for f in data.get("@graph", [])]

        return {
            "results": results,
            "total": data.get("total", len(results)),
            "limit": limit,
            "offset": offset,
        }

    async def get_file_info(self, accession: str) -> FileSummary:
        """Get details for a single file by accession."""
        validate_accession(accession)
        data = await self._request(
            f"/files/{accession}/",
            {"format": "json", "frame": "object"},
        )
        return FileSummary.from_api(data)

    # ------------------------------------------------------------------
    # Metadata / schema queries
    # ------------------------------------------------------------------

    def get_metadata(self, metadata_type: str) -> list[str]:
        """Get known values for a filter type (cached, no API call).

        Args:
            metadata_type: One of: assays, organisms, organs, biosample_types,
                file_formats, output_types, output_categories, assemblies,
                life_stages, replication_types, statuses, file_statuses

        Returns:
            List of valid filter values.
        """
        cache_key = f"metadata:{metadata_type}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        values = METADATA_MAP.get(metadata_type)
        if values is None:
            available = ", ".join(sorted(METADATA_MAP.keys()))
            raise ValueError(f"Unknown metadata type: {metadata_type}. Available: {available}")
        result = list(values)
        self._set_cached(cache_key, result)
        return result

    async def search_facets(
        self,
        search_type: str = "Experiment",
        **filters: str,
    ) -> dict[str, list[dict[str, Any]]]:
        """Get live facet counts from ENCODE for dynamic filter discovery.

        Returns facet name -> list of {term, count} for each available filter.
        Results are cached for 1 hour to reduce redundant API calls.
        """
        # Build a stable cache key from search_type + sorted filters
        filter_key = "|".join(f"{k}={v}" for k, v in sorted(filters.items()))
        cache_key = f"facets:{search_type}:{filter_key}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        params: dict[str, Any] = {
            "type": search_type,
            "format": "json",
            "limit": 0,  # We only want facets, not results
        }
        params.update(filters)

        data = await self._request("/search/", params)

        facets = {}
        for facet in data.get("facets", []):
            field = facet.get("field", "")
            terms = [
                {"term": t.get("key", ""), "count": t.get("doc_count", 0)}
                for t in facet.get("terms", [])
                if t.get("doc_count", 0) > 0
            ]
            if terms:
                facets[field] = terms

        self._set_cached(cache_key, facets)
        return facets

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @property
    def has_credentials(self) -> bool:
        """Check if authentication credentials are configured."""
        return self._credential_manager.has_credentials

    def store_credentials(self, access_key: str, secret_key: str) -> str:
        """Store ENCODE credentials securely. Returns storage location description."""
        result = self._credential_manager.store_credentials(access_key, secret_key)
        # Mark client for reset so next request uses new credentials
        self._client = None
        return result

    def clear_credentials(self) -> None:
        """Remove stored credentials."""
        self._credential_manager.clear_credentials()
        # Mark client for reset
        self._client = None
