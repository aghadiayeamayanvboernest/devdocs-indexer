"""PostgreSQL documentation scraper."""

import logging

from src.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class PostgreSQLScraper(BaseScraper):
    """Scraper for PostgreSQL documentation."""

    async def discover_urls(self) -> list[str]:
        """Discover all PostgreSQL documentation URLs."""
        logger.info(f"Discovering URLs for {self.name}")

        all_urls: set[str] = set()

        for start_url in self.start_urls:
            # PostgreSQL docs are very extensive
            section_urls = await self.crawl_recursively(
                start_url=start_url,
                max_depth=3,  # Moderate depth for PostgreSQL's extensive docs
                link_selector="body",  # Use full page - PostgreSQL has simple structure
            )
            all_urls.update(section_urls)

        urls = self.filter_urls(list(all_urls))
        logger.info(f"Discovered {len(urls)} total URLs for {self.name}")

        return urls
