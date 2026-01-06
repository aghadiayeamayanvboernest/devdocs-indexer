"""Run the complete indexing pipeline from start to finish."""

import argparse
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.crawler import Crawler
from src.core.embedder import Embedder
from src.core.indexer import Indexer
from src.core.parser import Parser


async def main():
    """Run the complete pipeline."""
    parser = argparse.ArgumentParser(
        description="Run the complete DevDocs indexing pipeline"
    )
    parser.add_argument(
        "--frameworks",
        nargs="+",
        help="Frameworks to index (default: all)",
        choices=["react", "nextjs", "typescript", "tailwind", "fastapi", "django", "postgresql"],
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory (default: timestamped dir in data/runs)",
    )
    parser.add_argument(
        "--create-index",
        action="store_true",
        help="Create Pinecone index if it doesn't exist",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("DevDocs AI - Full Indexing Pipeline")
    print("=" * 80)

    # Step 1: Crawl
    print("\n[1/4] CRAWLING - Discovering and downloading documentation...")
    crawler = Crawler(
        frameworks=args.frameworks,
        output_dir=args.output_dir,
    )
    crawl_stats = await crawler.crawl()

    print("\n✓ Crawling complete!")
    print(f"  - Frameworks: {crawl_stats['frameworks_crawled']}")
    print(f"  - URLs discovered: {crawl_stats['total_urls_discovered']}")
    print(f"  - Files downloaded: {crawl_stats['total_files_downloaded']}")
    print(f"  - Failures: {crawl_stats['total_failures']}")

    # Step 2: Parse
    print("\n[2/4] PARSING - Converting HTML to Markdown...")
    parser_instance = Parser(run_dir=crawler.output_dir)
    parse_stats = await parser_instance.parse()

    print("\n✓ Parsing complete!")
    print(f"  - Files processed: {parse_stats['total_files_processed']}")
    print(f"  - Failures: {parse_stats['total_failures']}")

    # Step 3: Embed
    print("\n[3/4] EMBEDDING - Generating vector embeddings...")
    embedder = Embedder(run_dir=crawler.output_dir)
    embed_stats = await embedder.embed()

    print("\n✓ Embedding complete!")
    print(f"  - Files processed: {embed_stats['total_files_processed']}")
    print(f"  - Chunks created: {embed_stats['total_chunks_created']}")
    print(f"  - Embeddings generated: {embed_stats['total_embeddings_generated']}")
    print(f"  - Failures: {embed_stats['total_failures']}")

    # Step 4: Index
    print("\n[4/4] INDEXING - Uploading to Pinecone...")
    indexer = Indexer(
        run_dir=crawler.output_dir,
        create_index=args.create_index,
    )
    index_stats = await indexer.index_all()

    print("\n✓ Indexing complete!")
    print(f"  - Frameworks indexed: {index_stats['frameworks_indexed']}")
    print(f"  - Chunks uploaded: {index_stats['total_chunks_uploaded']}")
    print(f"  - Failures: {index_stats['total_failures']}")

    print("\n" + "=" * 80)
    print("PIPELINE COMPLETE!")
    print("=" * 80)
    print(f"\nOutput directory: {crawler.output_dir}")
    print(f"\nTotal chunks indexed: {index_stats['total_chunks_uploaded']}")


if __name__ == "__main__":
    asyncio.run(main())
