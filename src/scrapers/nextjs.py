"""Next.js documentation scraper."""

import logging

from src.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class NextJSScraper(BaseScraper):
    """
    Scraper for Next.js documentation (nextjs.org/docs).

    Strategy:
    - Similar to React, uses sidebar navigation
    - Single main docs section
    - Recursive crawling of docs area
    """

    async def discover_urls(self) -> list[str]:
        """
        Discover all Next.js documentation URLs.

        Returns:
            List of Next.js documentation URLs
        """
        logger.info(f"Discovering URLs for {self.name}")

        all_urls: set[str] = set()

        # Next.js has a single main docs section
        for start_url in self.start_urls:
            logger.info(f"Crawling from {start_url}")

            # Crawl recursively from docs root
            section_urls = await self.crawl_recursively(
                start_url=start_url,
                max_depth=4,  # Deeper crawl for comprehensive coverage
                link_selector="main",
            )

            all_urls.update(section_urls)

        urls = self.filter_urls(list(all_urls))

        logger.info(f"Discovered {len(urls)} total URLs for {self.name}")

        return urls
