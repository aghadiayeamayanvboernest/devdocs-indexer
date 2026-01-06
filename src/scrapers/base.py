"""Base scraper class for framework documentation."""

import logging
from abc import ABC, abstractmethod
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from src.utils.crawl import fetch_url

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """
    Abstract base class for documentation scrapers.

    Each framework scraper inherits from this class and implements:
    - discover_urls(): How to find all documentation URLs
    - should_skip(): Which URLs to exclude

    The base class provides:
    - URL normalization and validation
    - Common crawling logic
    - Link extraction utilities
    """

    def __init__(self, config: dict):
        """
        Initialize scraper with framework configuration.

        Args:
            config: Framework config from frameworks.yaml
                   Should contain: name, base_url, start_urls, skip_patterns
        """
        self.config = config
        self.name = config["name"]
        self.base_url = config["base_url"]
        self.start_urls = config["start_urls"]
        self.skip_patterns = config.get("skip_patterns", [])
        self.selectors = config.get("selectors", {})

        # Track visited URLs to avoid duplicates
        self.visited_urls: set[str] = set()

    @abstractmethod
    async def discover_urls(self) -> list[str]:
        """
        Discover all documentation URLs for this framework.

        This is the main method each scraper must implement.
        Different frameworks have different doc structures:
        - Some have sitemap.xml
        - Some have navigation menus to crawl
        - Some have API endpoints
        - Some need to crawl recursively

        Returns:
            List of unique documentation URLs
        """
        pass

    def should_skip(self, url: str) -> bool:
        """
        Determine if a URL should be skipped.

        Args:
            url: URL to check

        Returns:
            True if URL should be skipped
        """
        # Skip if already visited
        if url in self.visited_urls:
            return True

        # Skip if not from base domain
        if not url.startswith(self.base_url):
            return True

        # Skip based on patterns
        for pattern in self.skip_patterns:
            if pattern in url:
                return True

        # Skip common non-doc patterns
        common_skips = [
            "#",  # Anchors
            "javascript:",
            "mailto:",
            ".pdf",
            ".zip",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".svg",
        ]

        for skip in common_skips:
            if skip in url.lower():
                return True

        return False

    def normalize_url(self, url: str, base: str | None = None) -> str:
        """
        Normalize URL to absolute form.

        Args:
            url: URL to normalize (can be relative)
            base: Base URL for resolving relative URLs (defaults to self.base_url)

        Returns:
            Absolute URL
        """
        base = base or self.base_url

        # Handle relative URLs
        if url.startswith("/"):
            parsed_base = urlparse(base)
            return f"{parsed_base.scheme}://{parsed_base.netloc}{url}"

        if not url.startswith("http"):
            return urljoin(base, url)

        # Remove fragments and trailing slashes for consistency
        url = url.split("#")[0].rstrip("/")

        return url

    async def extract_links_from_page(
        self,
        url: str,
        selector: str | None = None,
    ) -> list[str]:
        """
        Extract all links from a page.

        Args:
            url: Page URL to extract links from
            selector: Optional CSS selector to limit extraction

        Returns:
            List of absolute URLs
        """
        try:
            html = await fetch_url(url)
            soup = BeautifulSoup(html, "lxml")

            # Use selector if provided
            if selector:
                container = soup.select_one(selector)
                if not container:
                    logger.debug(f"Selector '{selector}' not found on {url}")
                    return []
                soup = container

            # Extract all links
            links = []
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                absolute_url = self.normalize_url(href, base=url)

                if not self.should_skip(absolute_url):
                    links.append(absolute_url)

            # Remove duplicates while preserving order
            seen = set()
            unique_links = []
            for link in links:
                if link not in seen:
                    seen.add(link)
                    unique_links.append(link)

            return unique_links

        except Exception as e:
            logger.debug(f"Failed to extract links from {url}: {e}")
            return []

    async def crawl_recursively(
        self,
        start_url: str,
        max_depth: int = 3,
        link_selector: str | None = None,
    ) -> list[str]:
        """
        Recursively crawl documentation starting from a URL.

        Args:
            start_url: Starting URL
            max_depth: Maximum recursion depth
            link_selector: CSS selector for navigation links

        Returns:
            List of all discovered URLs
        """
        all_urls: set[str] = set()
        to_visit: list[tuple[str, int]] = [(start_url, 0)]

        while to_visit:
            url, depth = to_visit.pop(0)

            # Skip if already visited or too deep
            if url in all_urls or depth > max_depth:
                continue

            all_urls.add(url)
            logger.info(f"Crawling {url} (depth {depth})")

            # Extract links from this page
            links = await self.extract_links_from_page(url, link_selector)

            # Add new links to visit queue
            for link in links:
                if link not in all_urls:
                    to_visit.append((link, depth + 1))

        return list(all_urls)

    def filter_urls(self, urls: list[str]) -> list[str]:
        """
        Filter and deduplicate URLs.

        Args:
            urls: List of URLs to filter

        Returns:
            Filtered list of unique URLs
        """
        filtered = []
        seen = set()

        for url in urls:
            # Normalize URL
            normalized = self.normalize_url(url)

            # Skip if should be excluded
            if self.should_skip(normalized):
                continue

            # Skip if duplicate
            if normalized in seen:
                continue

            seen.add(normalized)
            filtered.append(normalized)

        return filtered

    def get_url_hash(self, url: str) -> str:
        """
        Generate a short hash for a URL (for filenames).

        Args:
            url: URL to hash

        Returns:
            16-character hash string
        """
        from src.utils.hash import compute_hash

        return compute_hash(url)[:16]
