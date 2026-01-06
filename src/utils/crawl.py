"""Async web crawling utilities with Playwright and requests."""

import asyncio
import logging
from pathlib import Path
from typing import Any

import httpx
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


async def fetch_with_requests(
    url: str,
    timeout: int = 30,
    max_retries: int = 3,
) -> str:
    """
    Fetch URL content using httpx (fast, for static pages).

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts

    Returns:
        HTML content as string

    Raises:
        httpx.HTTPError: If request fails after all retries
    """
    retry_count = 0

    while retry_count < max_retries:
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.text

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                # 403 Forbidden - switch to Playwright
                logger.debug(f"Got 403 for {url}, will try Playwright")
                raise

            retry_count += 1
            if retry_count >= max_retries:
                logger.debug(f"Failed to fetch {url} after {max_retries} retries: {e}")
                raise

            # Exponential backoff
            await asyncio.sleep(2**retry_count)

        except httpx.RequestError as e:
            retry_count += 1
            if retry_count >= max_retries:
                logger.debug(f"Request error for {url} after {max_retries} retries: {e}")
                raise

            await asyncio.sleep(2**retry_count)

    # Should never reach here
    raise RuntimeError(f"Unexpected error fetching {url}")


async def fetch_with_playwright(
    url: str,
    timeout: int = 30,
    wait_for_selector: str | None = None,
) -> str:
    """
    Fetch URL content using Playwright (for JavaScript-rendered pages).

    Playwright launches a real browser, so it can handle:
    - JavaScript-rendered content
    - Dynamic loading
    - Complex SPAs (Single Page Apps)

    Args:
        url: URL to fetch
        timeout: Page load timeout in milliseconds
        wait_for_selector: Optional CSS selector to wait for before returning

    Returns:
        Fully-rendered HTML content

    Raises:
        Exception: If page fails to load
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()

            # Navigate to URL
            await page.goto(url, timeout=timeout * 1000, wait_until="networkidle")

            # Wait for specific element if requested
            if wait_for_selector:
                await page.wait_for_selector(wait_for_selector, timeout=timeout * 1000)

            # Get fully rendered HTML
            content = await page.content()
            return content

        finally:
            await browser.close()


async def fetch_url(
    url: str,
    timeout: int = 30,
    max_retries: int = 3,
    use_playwright: bool = False,
    wait_for_selector: str | None = None,
) -> str:
    """
    Smart fetch that tries requests first, falls back to Playwright.

    Args:
        url: URL to fetch
        timeout: Request timeout
        max_retries: Max retry attempts for requests
        use_playwright: Force use of Playwright
        wait_for_selector: CSS selector to wait for (Playwright only)

    Returns:
        HTML content

    Raises:
        Exception: If all attempts fail
    """
    if use_playwright:
        logger.info(f"Fetching {url} with Playwright")
        return await fetch_with_playwright(url, timeout, wait_for_selector)

    # Try requests first (faster)
    try:
        logger.info(f"Fetching {url} with httpx")
        return await fetch_with_requests(url, timeout, max_retries)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            # Fall back to Playwright
            logger.info(f"Falling back to Playwright for {url}")
            return await fetch_with_playwright(url, timeout, wait_for_selector)
        raise

    except Exception:
        # Last resort: try Playwright
        logger.info(f"httpx failed, trying Playwright for {url}")
        return await fetch_with_playwright(url, timeout, wait_for_selector)


async def save_content(
    content: str,
    filepath: Path,
) -> None:
    """
    Save content to file asynchronously.

    Args:
        content: Content to save
        filepath: Path to save to
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Use async file I/O for better performance
    async with asyncio.Lock():
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)


async def crawl_urls(
    urls: list[str],
    output_dir: Path,
    delay: float = 0.5,
    max_concurrent: int = 5,
    **fetch_kwargs: Any,
) -> dict[str, str]:
    """
    Crawl multiple URLs concurrently with rate limiting.

    Args:
        urls: List of URLs to crawl
        output_dir: Directory to save HTML files
        delay: Delay between requests (seconds)
        max_concurrent: Maximum concurrent requests
        **fetch_kwargs: Additional arguments for fetch_url

    Returns:
        Dictionary mapping URL to output filepath (or error message)
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    results = {}

    async def crawl_one(url: str) -> None:
        async with semaphore:
            try:
                # Fetch content
                content = await fetch_url(url, **fetch_kwargs)

                # Generate filename from URL hash
                from src.utils.hash import compute_hash

                url_hash = compute_hash(url)[:16]
                filepath = output_dir / f"{url_hash}.html"

                # Save to file
                await save_content(content, filepath)

                results[url] = str(filepath)
                logger.info(f"✓ Crawled {url} → {filepath.name}")

            except Exception as e:
                results[url] = f"ERROR: {str(e)}"
                logger.error(f"✗ Failed to crawl {url}: {e}")

            # Rate limiting
            await asyncio.sleep(delay)

    # Crawl all URLs
    await asyncio.gather(*[crawl_one(url) for url in urls])

    return results
