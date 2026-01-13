"""Django documentation scraper."""

import logging

from src.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class DjangoScraper(BaseScraper):
    """Scraper for Django documentation."""

    async def discover_urls(self) -> list[str]:
        """Discover all Django documentation URLs."""
        logger.info(f"Discovering URLs for {self.name}")

        all_urls: set[str] = set()

        for start_url in self.start_urls:
            # Django docs are extensive, use shallow depth to avoid exponential crawl
            section_urls = await self.crawl_recursively(
                start_url=start_url,
                max_depth=2,  # Reduced from 3 to prevent link explosion
                link_selector="main",  # Main content area contains all doc links
            )
            all_urls.update(section_urls)

        urls = self.filter_urls(list(all_urls))
        logger.info(f"Discovered {len(urls)} total URLs for {self.name}")

        return urls
