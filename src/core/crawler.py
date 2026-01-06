"""Main crawler orchestrator for discovering and downloading documentation."""

import asyncio
import csv
from datetime import datetime
from pathlib import Path
from typing import Any

from tqdm import tqdm

from src.config.settings import get_settings, load_framework_config
from src.scrapers import (
    DjangoScraper,
    FastAPIScraper,
    NextJSScraper,
    PostgreSQLScraper,
    ReactScraper,
    TailwindScraper,
    TypeScriptScraper,
)
from src.utils.crawl import fetch_url, save_content
from src.utils.hash import compute_hash
from src.utils.logger import get_logger

logger = get_logger(__name__)


# Map framework names to scraper classes
SCRAPER_MAP = {
    "react": ReactScraper,
    "nextjs": NextJSScraper,
    "typescript": TypeScriptScraper,
    "tailwind": TailwindScraper,
    "fastapi": FastAPIScraper,
    "django": DjangoScraper,
    "postgresql": PostgreSQLScraper,
}


class Crawler:
    """
    Main crawler that discovers and downloads documentation.

    Workflow:
    1. Load framework configurations
    2. For each framework, use appropriate scraper to discover URLs
    3. Download HTML content for each URL
    4. Save to disk with metadata tracking
    5. Generate CSV report of all crawled files
    """

    def __init__(
        self,
        frameworks: list[str] | None = None,
        output_dir: Path | None = None,
    ):
        """
        Initialize crawler.

        Args:
            frameworks: List of framework names to crawl (None = all)
            output_dir: Output directory (defaults to timestamped dir in data/runs)
        """
        self.settings = get_settings()
        self.framework_configs = load_framework_config()["frameworks"]

        # Determine which frameworks to crawl
        if frameworks:
            self.frameworks = frameworks
        else:
            self.frameworks = list(self.framework_configs.keys())

        # Set up output directory
        if output_dir:
            self.output_dir = output_dir
        else:
            # Use date only (no time) for cleaner directory names
            date_stamp = datetime.now().strftime("%Y_%m_%d")
            self.output_dir = self.settings.data_dir / date_stamp

        self.raw_dir = self.output_dir / "raw"
        self.logs_dir = self.output_dir / "logs"

        # Create directories
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Set up logging
        log_file = self.logs_dir / "crawler.jsonl"
        self.logger = get_logger("crawler", log_file)

        # Stats tracking
        self.stats: dict[str, Any] = {
            "frameworks_crawled": 0,
            "total_urls_discovered": 0,
            "total_files_downloaded": 0,
            "total_failures": 0,
            "start_time": None,
            "end_time": None,
        }

    async def crawl(self) -> dict[str, Any]:
        """
        Run the complete crawling process.

        Returns:
            Statistics dictionary
        """
        self.stats["start_time"] = datetime.now().isoformat()
        self.logger.info(f"Starting crawl for frameworks: {self.frameworks}")

        all_urls: dict[str, list[dict]] = {}

        # Step 1: Discover URLs for each framework
        for framework in self.frameworks:
            self.logger.info(f"Discovering URLs for {framework}")

            urls = await self._discover_framework_urls(framework)
            all_urls[framework] = urls

            self.stats["total_urls_discovered"] += len(urls)
            self.logger.info(f"Discovered {len(urls)} URLs for {framework}")

        # Step 2: Download all discovered URLs
        for framework, urls in all_urls.items():
            self.logger.info(f"Downloading {len(urls)} URLs for {framework}")

            await self._download_urls(framework, urls)

            self.stats["frameworks_crawled"] += 1

        # Step 3: Generate CSV report
        self._generate_report(all_urls)

        self.stats["end_time"] = datetime.now().isoformat()
        self.logger.info(f"Crawl complete. Stats: {self.stats}")

        return self.stats

    async def _discover_framework_urls(self, framework: str) -> list[dict]:
        """
        Discover all URLs for a framework.

        Args:
            framework: Framework name

        Returns:
            List of URL metadata dicts
        """
        config = self.framework_configs[framework]
        scraper_class = SCRAPER_MAP.get(framework)

        if not scraper_class:
            self.logger.error(f"No scraper found for {framework}")
            return []

        try:
            scraper = scraper_class(config)
            urls = await scraper.discover_urls()

            # Add metadata to each URL
            url_data = []
            for url in urls:
                url_hash = compute_hash(url)[:16]
                url_data.append(
                    {
                        "framework": framework,
                        "url": url,
                        "url_hash": url_hash,
                        "filename": f"{url_hash}.html",
                    }
                )

            return url_data

        except Exception as e:
            self.logger.error(f"Error discovering URLs for {framework}: {e}")
            return []

    async def _download_urls(self, framework: str, urls: list[dict]) -> None:
        """
        Download HTML content for all URLs.

        Args:
            framework: Framework name
            urls: List of URL metadata dicts
        """
        # Create framework subdirectory
        framework_dir = self.raw_dir / framework
        framework_dir.mkdir(parents=True, exist_ok=True)

        # Download with progress bar
        self.logger.info(f"Downloading {len(urls)} files for {framework}")

        # Limit concurrent downloads
        semaphore = asyncio.Semaphore(5)

        async def download_one(url_data: dict) -> None:
            async with semaphore:
                try:
                    # Fetch content
                    content = await fetch_url(
                        url_data["url"],
                        timeout=self.settings.timeout_seconds,
                    )

                    # Save to file
                    filepath = framework_dir / url_data["filename"]
                    await save_content(content, filepath)

                    # Compute content hash
                    url_data["content_hash"] = compute_hash(content)
                    url_data["status"] = "success"
                    url_data["filepath"] = str(filepath.relative_to(self.output_dir))

                    self.stats["total_files_downloaded"] += 1

                except Exception as e:
                    self.logger.error(f"Failed to download {url_data['url']}: {e}")
                    url_data["status"] = "failed"
                    url_data["error"] = str(e)
                    self.stats["total_failures"] += 1

                # Rate limiting
                await asyncio.sleep(self.settings.delay_between_requests)

        # Download all URLs
        tasks = [download_one(url_data) for url_data in urls]

        # Use tqdm for progress bar
        for coro in tqdm(
            asyncio.as_completed(tasks),
            total=len(tasks),
            desc=f"Downloading {framework}",
        ):
            await coro

    def _generate_report(self, all_urls: dict[str, list[dict]]) -> None:
        """
        Generate CSV report of all crawled files.

        Args:
            all_urls: Dictionary mapping framework to list of URL data
        """
        report_path = self.output_dir / "crawl_report.csv"

        with open(report_path, "w", newline="") as f:
            fieldnames = [
                "framework",
                "url",
                "url_hash",
                "filename",
                "filepath",
                "content_hash",
                "status",
                "error",
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for _framework, urls in all_urls.items():
                for url_data in urls:
                    # Add None for missing fields
                    row = {field: url_data.get(field, "") for field in fieldnames}
                    writer.writerow(row)

        self.logger.info(f"Report written to {report_path}")
