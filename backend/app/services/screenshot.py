"""Screenshot service — capture webpage screenshots using Playwright headless browser.

Inspired by competitorsmart's screenshot_tool.py. Provides visual evidence
for competitive analysis reports (competitor homepages, pricing pages, etc.).
"""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Default output directory relative to project root
SCREENSHOTS_DIR = os.environ.get("COMPETA_SCREENSHOTS_DIR", "screenshots")

# Internal/unsafe URL patterns (reuse logic from search.py)
_BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
_BLOCKED_SCHEMES = {"file", "ftp"}


def _is_url_safe(url: str) -> bool:
    """Reject internal / unsafe URLs to prevent SSRF."""
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme in _BLOCKED_SCHEMES:
        return False
    if parsed.hostname in _BLOCKED_HOSTS:
        return False
    if parsed.hostname and parsed.hostname.endswith(".local"):
        return False
    return True


def _url_to_filename(url: str) -> str:
    """Generate a deterministic filename from a URL using SHA-256 hash."""
    h = hashlib.sha256(url.encode()).hexdigest()[:16]
    # Add a short human-readable prefix from the domain
    try:
        domain = urlparse(url).netloc.replace("www.", "")[:20]
    except Exception:
        domain = "unknown"
    # Sanitize domain for filename
    safe_domain = "".join(c if c.isalnum() or c in "-_" else "_" for c in domain)
    return f"{safe_domain}_{h}.png"


async def screenshot_webpage(
    url: str,
    task_id: str,
    *,
    full_page: bool = False,
    width: int = 1280,
    height: int = 800,
    timeout_ms: int = 20000,
) -> dict[str, str | None]:
    """Capture a screenshot of a webpage using Playwright.

    Args:
        url: The URL to screenshot.
        task_id: Task ID for organizing output directory.
        full_page: If True, capture the entire scrollable page.
        width: Viewport width.
        height: Viewport height.
        timeout_ms: Navigation timeout in milliseconds.

    Returns:
        Dict with keys: url, path (relative), error (or None).
        If Playwright is not installed, returns error message.
    """
    if not _is_url_safe(url):
        return {"url": url, "path": None, "error": "URL blocked (internal/unsafe)"}

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.warning("playwright not installed; screenshot skipped for %s", url)
        return {"url": url, "path": None, "error": "playwright not installed"}

    # Prepare output directory
    output_dir = Path(SCREENSHOTS_DIR) / task_id
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = _url_to_filename(url)
    filepath = output_dir / filename
    relative_path = f"{task_id}/{filename}"

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": width, "height": height},
            )
            page = await context.new_page()

            await page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")

            await page.screenshot(
                path=str(filepath),
                full_page=full_page,
            )

            await browser.close()

        logger.info("Screenshot saved: %s → %s", url, relative_path)
        return {"url": url, "path": relative_path, "error": None}

    except Exception as exc:
        logger.warning("Screenshot failed for %s: %s", url, exc)
        return {"url": url, "path": None, "error": str(exc)}


async def screenshot_webpages(
    urls: list[str],
    task_id: str,
    **kwargs: Any,
) -> list[dict[str, str | None]]:
    """Capture screenshots for multiple URLs sequentially (browser reuse would be more complex)."""
    results: list[dict[str, str | None]] = []
    for url in urls:
        result = await screenshot_webpage(url, task_id, **kwargs)
        results.append(result)
    return results
