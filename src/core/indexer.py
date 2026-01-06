"""Indexer module for uploading embeddings to Pinecone."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from pinecone import Pinecone, ServerlessSpec
from tqdm import tqdm

from src.config.settings import get_settings
from src.utils.hash import compute_hash
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Indexer:
    """
    Indexer that uploads vector embeddings to Pinecone.

    Workflow:
    1. Initialize Pinecone client and index
    2. Load chunks with embeddings from JSON files
    3. Upload to Pinecone using namespace-per-framework strategy
    4. Generate statistics report
    """

    def __init__(
        self,
        run_dir: Path,
        create_index: bool = False,
    ):
        """
        Initialize indexer.

        Args:
            run_dir: Directory containing chunks with embeddings
            create_index: If True, create index if it doesn't exist
        """
        self.settings = get_settings()
        self.run_dir = Path(run_dir)
        self.chunks_dir = self.run_dir / "chunks"
        self.logs_dir = self.run_dir / "logs"

        # Create logs directory
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Pinecone
        self.pc = Pinecone(api_key=self.settings.pinecone_api_key)

        # Get or create index
        self.index_name = self.settings.pinecone_index_name
        self._setup_index(create_index)

        # Set up logging
        log_file = self.logs_dir / "indexer.jsonl"
        self.logger = get_logger("indexer", log_file)

        # Stats tracking
        self.stats: dict[str, Any] = {
            "total_chunks_uploaded": 0,
            "total_failures": 0,
            "frameworks_indexed": 0,
            "start_time": None,
            "end_time": None,
        }

    def _setup_index(self, create_if_missing: bool) -> None:
        """
        Set up Pinecone index.

        Args:
            create_if_missing: Create index if it doesn't exist
        """
        # Check if index exists
        existing_indexes = self.pc.list_indexes()
        index_names = [idx["name"] for idx in existing_indexes]

        if self.index_name not in index_names:
            if create_if_missing:
                logger.info(f"Creating Pinecone index: {self.index_name}")

                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.settings.embedding_dimensions,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region=self.settings.pinecone_environment,
                    ),
                )
                logger.info(f"Index {self.index_name} created successfully")
            else:
                raise ValueError(
                    f"Index {self.index_name} does not exist. "
                    "Set create_index=True to create it."
                )

        # Connect to index
        self.index = self.pc.Index(self.index_name)

    async def index_all(self) -> dict[str, Any]:
        """
        Run the complete indexing process.

        Returns:
            Statistics dictionary
        """
        self.stats["start_time"] = datetime.now().isoformat()
        self.logger.info(f"Starting indexing for run: {self.run_dir}")

        # Find all chunk files
        chunk_files = list(self.chunks_dir.rglob("chunks.json"))
        self.logger.info(f"Found {len(chunk_files)} chunk files")

        # Upload each framework's chunks
        for chunk_file in chunk_files:
            framework = chunk_file.parent.name
            await self._index_framework(framework, chunk_file)
            self.stats["frameworks_indexed"] += 1

        self.stats["end_time"] = datetime.now().isoformat()
        self.logger.info(f"Indexing complete. Stats: {self.stats}")

        return self.stats

    async def _index_framework(self, framework: str, chunk_file: Path) -> None:
        """
        Index all chunks for a framework.

        Args:
            framework: Framework name (used as namespace)
            chunk_file: Path to chunks.json file
        """
        self.logger.info(f"Indexing {framework} from {chunk_file}")

        # Load chunks
        with open(chunk_file, encoding="utf-8") as f:
            chunks = json.load(f)

        # Filter chunks that have embeddings
        chunks_with_embeddings = [c for c in chunks if "embedding" in c]

        if len(chunks_with_embeddings) < len(chunks):
            missing = len(chunks) - len(chunks_with_embeddings)
            self.logger.warning(
                f"{missing} chunks missing embeddings for {framework}"
            )

        self.logger.info(
            f"Uploading {len(chunks_with_embeddings)} chunks to namespace '{framework}'"
        )

        # Prepare vectors for Pinecone
        vectors = []
        for i, chunk in enumerate(chunks_with_embeddings):
            # Generate unique ID
            chunk_id = self._generate_chunk_id(chunk, i)

            # Prepare metadata (Pinecone has size limits, keep it small)
            metadata = {
                "framework": framework,
                "url": chunk["metadata"].get("url", "")[:500],  # Limit URL length
                "title": chunk["metadata"].get("title", "")[:200],
                "chunk_index": chunk["metadata"].get("chunk_index", i),
                "tokens": chunk.get("tokens", 0),
                "content": chunk["content"][:1000],  # First 1000 chars for preview
            }

            vectors.append(
                {
                    "id": chunk_id,
                    "values": chunk["embedding"],
                    "metadata": metadata,
                }
            )

        # Upload in batches (Pinecone limit: 100 vectors per upsert)
        batch_size = 100

        for i in tqdm(
            range(0, len(vectors), batch_size),
            desc=f"Uploading {framework}",
        ):
            batch = vectors[i : i + batch_size]

            try:
                # Upsert to Pinecone with framework namespace
                self.index.upsert(
                    vectors=batch,
                    namespace=framework,
                )

                self.stats["total_chunks_uploaded"] += len(batch)

            except Exception as e:
                self.logger.error(f"Failed to upload batch for {framework}: {e}")
                self.stats["total_failures"] += len(batch)

        self.logger.info(
            f"Successfully indexed {len(chunks_with_embeddings)} chunks for {framework}"
        )

    def _generate_chunk_id(self, chunk: dict, index: int) -> str:
        """
        Generate a unique ID for a chunk.

        Args:
            chunk: Chunk dictionary
            index: Chunk index

        Returns:
            Unique chunk ID
        """
        # Use URL + chunk index for stable IDs
        url = chunk["metadata"].get("url", "unknown")
        chunk_index = chunk["metadata"].get("chunk_index", index)

        # Hash for uniqueness
        id_string = f"{url}#{chunk_index}"
        hash_suffix = compute_hash(id_string)[:8]

        return f"{chunk_index}_{hash_suffix}"
