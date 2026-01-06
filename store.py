"""Store embeddings to Pinecone vector database.

Just run: uv run python store.py
(Automatically finds the latest run and uploads to Pinecone)
"""

import asyncio
from pathlib import Path

from src.config.settings import get_settings
from src.core.indexer import Indexer


def find_latest_run() -> Path | None:
    """Find the most recent run directory."""
    settings = get_settings()
    data_dir = settings.data_dir

    if not data_dir.exists():
        return None

    # Get all run directories (sorted by name, which is timestamp-based)
    run_dirs = sorted([d for d in data_dir.iterdir() if d.is_dir()], reverse=True)

    if not run_dirs:
        return None

    return run_dirs[0]  # Most recent


async def main():
    """Upload embeddings to Pinecone."""
    print("=" * 80)
    print("DevDocs AI - Pinecone Upload")
    print("=" * 80)

    # Find latest run automatically
    run_dir = find_latest_run()

    if not run_dir:
        print("\nERROR: No run directory found!")
        print("Please run main.py first to generate embeddings.")
        return

    print(f"\nFound latest run: {run_dir.name}")

    # Validate chunks exist
    chunks_dir = run_dir / "chunks"
    if not chunks_dir.exists():
        print(f"\nERROR: No chunks directory found in {run_dir}")
        print("Make sure you've run main.py first to generate embeddings")
        return

    # Count chunks
    chunk_files = list(chunks_dir.rglob("chunks.json"))
    if not chunk_files:
        print(f"\nERROR: No chunk files found in {chunks_dir}")
        return

    print(f"Chunk files found: {len(chunk_files)}")
    print("\nFrameworks to upload:")
    for chunk_file in chunk_files:
        framework = chunk_file.parent.name
        print(f"  • {framework}")

    print("\n" + "-" * 80)
    print("Uploading to Pinecone...")
    print("-" * 80)

    # Initialize indexer and upload
    # create_index=False - you must create the index manually in Pinecone dashboard
    indexer = Indexer(run_dir=run_dir, create_index=False)

    index_stats = await indexer.index_all()

    # Summary
    print("\n" + "=" * 80)
    print("UPLOAD COMPLETE!")
    print("=" * 80)
    print(f"\n✓ Frameworks indexed: {index_stats['frameworks_indexed']}")
    print(f"✓ Chunks uploaded: {index_stats['total_chunks_uploaded']}")
    print(f"✗ Failures: {index_stats['total_failures']}")

    if index_stats["total_failures"] > 0:
        print(f"\nCheck logs: {run_dir}/logs/indexer.jsonl")


if __name__ == "__main__":
    asyncio.run(main())
