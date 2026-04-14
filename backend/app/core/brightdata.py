"""
Brightdata Web Unlocker API Client
Fetches any URL through Brightdata's Web Unlocker (zone: web_unlocker1).
This is the REST API approach — not a proxy; every request is a POST
to https://api.brightdata.com/request.

Usage:
    from app.core.brightdata import fetch_via_unlocker

    html = await fetch_via_unlocker("https://www.linkedin.com/jobs/...")
"""
from __future__ import annotations

import asyncio
import httpx
import structlog
from typing import Optional

from app.core.config import settings

log = structlog.get_logger()

# Retry config
MAX_RETRIES = 3
RETRY_BACKOFF = 2.0  # seconds, doubled each attempt


async def fetch_via_unlocker(
    url: str,
    *,
    format: str = "raw",
    country: Optional[str] = None,
    extra_payload: Optional[dict] = None,
    timeout: float = 60.0,
) -> str:
    """
    Fetch a URL through the Brightdata Web Unlocker REST API.

    Args:
        url:            Target URL to fetch.
        format:         Response format — 'raw' (default) or 'json'.
        country:        Optional 2-letter country code for geo-targeting (e.g. 'us').
        extra_payload:  Any additional fields to merge into the request body.
        timeout:        HTTP timeout in seconds.

    Returns:
        Response body as a string.

    Raises:
        RuntimeError: If Brightdata is not configured or all retries fail.
    """
    if not settings.brightdata_configured:
        raise RuntimeError(
            "Brightdata Web Unlocker is not configured. "
            "Set BRIGHTDATA_API_KEY in your .env file."
        )

    payload: dict = {
        "zone": settings.BRIGHTDATA_ZONE,
        "url": url,
        "format": format,
    }
    if country:
        payload["country"] = country
    if extra_payload:
        payload.update(extra_payload)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.BRIGHTDATA_API_KEY}",
    }

    last_error: Exception | None = None

    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                log.debug(
                    "Brightdata Web Unlocker request",
                    url=url,
                    attempt=attempt,
                    zone=settings.BRIGHTDATA_ZONE,
                )
                response = await client.post(
                    settings.BRIGHTDATA_API_URL,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                log.debug("Brightdata fetch success", url=url, status=response.status_code)
                return response.text

            except httpx.HTTPStatusError as exc:
                log.warning(
                    "Brightdata HTTP error",
                    url=url,
                    status=exc.response.status_code,
                    attempt=attempt,
                )
                last_error = exc
                # 4xx errors won't improve on retry — fail fast
                if 400 <= exc.response.status_code < 500:
                    break

            except (httpx.RequestError, asyncio.TimeoutError) as exc:
                log.warning("Brightdata request error", url=url, error=str(exc), attempt=attempt)
                last_error = exc

            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF * attempt
                log.info("Retrying Brightdata request", wait_s=wait, attempt=attempt)
                await asyncio.sleep(wait)

    raise RuntimeError(
        f"Brightdata Web Unlocker failed for {url} after {MAX_RETRIES} attempts. "
        f"Last error: {last_error}"
    )


async def test_connection() -> dict:
    """
    Quick connectivity test — fetches the Brightdata geo test URL.
    Returns a dict with 'ok', 'body', and 'error' fields.
    """
    test_url = "https://geo.brdtest.com/welcome.txt?product=unlocker&method=api"
    try:
        body = await fetch_via_unlocker(test_url)
        return {"ok": True, "body": body.strip(), "error": None}
    except Exception as exc:
        return {"ok": False, "body": None, "error": str(exc)}
