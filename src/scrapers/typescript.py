"""TypeScript documentation scraper."""

import logging

from src.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class TypeScriptScraper(BaseScraper):
    """
    Scraper for TypeScript documentation (typescriptlang.org/docs).

    Strategy:
    - Crawl main docs section
    - TypeScript docs are well-structured with clear navigation
    """

    async def discover_urls(self) -> list[str]:
        """
        Discover all TypeScript documentation URLs.

        Returns:
            List of TypeScript documentation URLs
        """
        logger.info(f"Discovering URLs for {self.name}")

        all_urls: set[str] = set()

        for start_url in self.start_urls:
            logger.info(f"Crawling from {start_url}")

            # Crawl TypeScript docs
            section_urls = await self.crawl_recursively(
                start_url=start_url,
                max_depth=4,  # Deeper crawl for comprehensive coverage
                link_selector="#sidebar",  # TypeScript uses sidebar for navigation
            )

            all_urls.update(section_urls)

        urls = self.filter_urls(list(all_urls))

        logger.info(f"Discovered {len(urls)} total URLs for {self.name}")

        return urls
