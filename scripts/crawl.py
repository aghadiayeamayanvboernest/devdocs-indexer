"""Run only the crawling stage."""

import argparse
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.crawler import Crawler


async def main():
    """Run the crawler."""
    parser = argparse.ArgumentParser(description="Crawl documentation websites")
    parser.add_argument(
        "--frameworks",
        nargs="+",
        help="Frameworks to crawl (default: all)",
        choices=["react", "nextjs", "typescript", "tailwind", "fastapi", "django", "postgresql"],
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory (default: timestamped dir in data/runs)",
    )

    args = parser.parse_args()

    print("Starting crawler...")
    crawler = Crawler(
        frameworks=args.frameworks,
        output_dir=args.output_dir,
    )

    stats = await crawler.crawl()

    print("\n✓ Crawling complete!")
    print(f"  Frameworks: {stats['frameworks_crawled']}")
    print(f"  URLs: {stats['total_urls_discovered']}")
    print(f"  Downloaded: {stats['total_files_downloaded']}")
    print(f"  Output: {crawler.output_dir}")


if __name__ == "__main__":
    asyncio.run(main())
