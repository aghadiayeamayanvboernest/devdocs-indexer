"""Main pipeline script: Crawl, Parse, and Embed documentation.

Just run: uv run python main.py
"""

import asyncio
import os
import sys
from contextlib import contextmanager

from src.core.crawler import Crawler
from src.core.embedder import Embedder
from src.core.parser import Parser


@contextmanager
def suppress_stderr():
    """Temporarily suppress stderr to hide noisy library warnings."""
    devnull = open(os.devnull, 'w')
    old_stderr = sys.stderr
    sys.stderr = devnull
    try:
        yield
    finally:
        sys.stderr = old_stderr
        devnull.close()


async def main():
    """Run crawling, parsing, and embedding (everything except Pinecone upload)."""
    print("=" * 80)
    print("DevDocs AI - Documentation Processing Pipeline")
    print("=" * 80)
    print("\nThis will:")
    print("  1. Crawl all 7 framework documentation sites")
    print("  2. Convert HTML to Markdown")
    print("  3. Generate embeddings with OpenAI")
    print("\nThen run store.py to upload to Pinecone")
    print("=" * 80)

    # Step 1: Crawl (all frameworks by default)
    print("\n[1/3] CRAWLING - Discovering and downloading documentation...")
    print("-" * 80)
    crawler = Crawler()  # No arguments = all frameworks
    with suppress_stderr():
        crawl_stats = await crawler.crawl()

    print("\n✓ Crawling complete!")
    print(f"  • Frameworks: {crawl_stats['frameworks_crawled']}")
    print(f"  • URLs discovered: {crawl_stats['total_urls_discovered']}")
    print(f"  • Files downloaded: {crawl_stats['total_files_downloaded']}")
    print(f"  • Failures: {crawl_stats['total_failures']}")

    # Step 2: Parse
    print("\n[2/3] PARSING - Converting HTML to Markdown...")
    print("-" * 80)
    parser_instance = Parser(run_dir=crawler.output_dir)
    parse_stats = await parser_instance.parse()

    print("\n✓ Parsing complete!")
    print(f"  • Files processed: {parse_stats['total_files_processed']}")
    print(f"  • Failures: {parse_stats['total_failures']}")

    # Step 3: Embed
    print("\n[3/3] EMBEDDING - Generating vector embeddings...")
    print("-" * 80)
    embedder = Embedder(run_dir=crawler.output_dir)
    embed_stats = await embedder.embed()

    print("\n✓ Embedding complete!")
    print(f"  • Files processed: {embed_stats['total_files_processed']}")
    print(f"  • Chunks created: {embed_stats['total_chunks_created']}")
    print(f"  • Embeddings generated: {embed_stats['total_embeddings_generated']}")
    print(f"  • Failures: {embed_stats['total_failures']}")

    # Final summary
    print("\n" + "=" * 80)
    print("PROCESSING COMPLETE!")
    print("=" * 80)
    print(f"\nOutput directory: {crawler.output_dir}")
    print(f"Total chunks with embeddings: {embed_stats['total_embeddings_generated']}")
    print("\nNext step:")
    print("  Run: uv run python store.py")
    print("  (This will automatically find and upload your chunks to Pinecone)")


if __name__ == "__main__":
    asyncio.run(main())
