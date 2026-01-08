"""FastAPI documentation scraper."""

import logging

from src.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class FastAPIScraper(BaseScraper):
    """Scraper for FastAPI documentation."""

    async def discover_urls(self) -> list[str]:
        """Discover all FastAPI documentation URLs."""
        logger.info(f"Discovering URLs for {self.name}")

        all_urls: set[str] = set()

        for start_url in self.start_urls:
            section_urls = await self.crawl_recursively(
                start_url=start_url,
                max_depth=4,  # Deeper crawl for comprehensive coverage
                link_selector=".md-sidebar--primary",  # Material for MkDocs sidebar with all docs links
            )
            all_urls.update(section_urls)

        urls = self.filter_urls(list(all_urls))
        logger.info(f"Discovered {len(urls)} total URLs for {self.name}")

        return urls
