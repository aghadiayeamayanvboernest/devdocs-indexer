"""React documentation scraper."""

import logging

from src.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class ReactScraper(BaseScraper):
    """
    Scraper for React documentation (react.dev).

    Strategy:
    - Start from main docs sections (/learn, /reference)
    - Recursively crawl navigation links
    - React docs have a clear sidebar navigation structure
    """

    async def discover_urls(self) -> list[str]:
        """
        Discover all React documentation URLs.

        Approach:
        1. Start from configured start_urls (learn, reference sections)
        2. Recursively crawl each section
        3. Extract all links from main content navigation
        4. Filter and deduplicate

        Returns:
            List of React documentation URLs
        """
        logger.info(f"Discovering URLs for {self.name}")

        all_urls: set[str] = set()

        # Crawl each start URL recursively
        for start_url in self.start_urls:
            logger.info(f"Crawling from {start_url}")

            # React docs have navigation in main content area
            # We'll use recursive crawling with moderate depth
            section_urls = await self.crawl_recursively(
                start_url=start_url,
                max_depth=4,  # Deeper crawl to capture all nested documentation
                link_selector="main",  # Links in main content
            )

            all_urls.update(section_urls)
            logger.info(f"Found {len(section_urls)} URLs in section")

        # Convert to list and filter
        urls = self.filter_urls(list(all_urls))

        logger.info(f"Discovered {len(urls)} total URLs for {self.name}")

        return urls
