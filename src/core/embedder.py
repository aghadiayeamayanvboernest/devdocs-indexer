"""Embedder module for generating OpenAI embeddings from markdown chunks."""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import frontmatter
from openai import AsyncOpenAI
from tqdm import tqdm

from src.config.settings import get_settings
from src.utils.chunker import SmartChunker
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Embedder:
    """
    Embedder that generates vector embeddings for markdown chunks.

    Workflow:
    1. Load parsed markdown files
    2. Chunk each document (1000 tokens, 200 overlap)
    3. Generate embeddings using OpenAI API (batch processing)
    4. Save chunks with embeddings to JSON files
    5. Generate statistics report
    """

    def __init__(
        self,
        run_dir: Path,
        chunk_size: int | None = None,
        overlap: int | None = None,
    ):
        """
        Initialize embedder.

        Args:
            run_dir: Directory containing parsed markdown
            chunk_size: Chunk size in tokens (defaults to settings)
            overlap: Overlap size in tokens (defaults to settings)
        """
        self.settings = get_settings()
        self.run_dir = Path(run_dir)
        self.markdown_dir = self.run_dir / "markdown"
        self.chunks_dir = self.run_dir / "chunks"
        self.logs_dir = self.run_dir / "logs"

        # Create directories
        self.chunks_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Initialize OpenAI client
        self.client = AsyncOpenAI(api_key=self.settings.openai_api_key)

        # Initialize chunker
        self.chunker = SmartChunker(
            chunk_size=chunk_size or self.settings.default_chunk_size,
            overlap=overlap or self.settings.default_overlap,
        )

        # Set up logging
        log_file = self.logs_dir / "embedder.jsonl"
        self.logger = get_logger("embedder", log_file)

        # Stats tracking
        self.stats: dict[str, Any] = {
            "total_files_processed": 0,
            "total_chunks_created": 0,
            "total_embeddings_generated": 0,
            "total_failures": 0,
            "start_time": None,
            "end_time": None,
        }

    async def embed(self) -> dict[str, Any]:
        """
        Run the complete embedding process.

        Returns:
            Statistics dictionary
        """
        self.stats["start_time"] = datetime.now().isoformat()
        self.logger.info(f"Starting embedding for run: {self.run_dir}")

        # Find all markdown files
        md_files = list(self.markdown_dir.rglob("*.md"))
        self.logger.info(f"Found {len(md_files)} markdown files")

        # Process each file
        all_chunks = []
        for md_file in tqdm(md_files, desc="Chunking files"):
            chunks = await self._process_file(md_file)
            all_chunks.extend(chunks)

        # Generate embeddings in batches
        await self._generate_embeddings_batch(all_chunks)

        # Save chunks to JSON
        self._save_chunks(all_chunks)

        self.stats["end_time"] = datetime.now().isoformat()
        self.logger.info(f"Embedding complete. Stats: {self.stats}")

        return self.stats

    async def _process_file(self, md_path: Path) -> list[dict]:
        """
        Process a markdown file into chunks.

        Args:
            md_path: Path to markdown file

        Returns:
            List of chunk dictionaries
        """
        try:
            # Parse frontmatter and content
            with open(md_path, encoding="utf-8") as f:
                post = frontmatter.load(f)

            metadata = post.metadata
            content = post.content

            # Get framework from path
            framework = md_path.parent.name

            # Chunk the content
            chunks = self.chunker.chunk_markdown(
                content,
                metadata={
                    "framework": framework,
                    "url": metadata.get("url", ""),
                    "title": metadata.get("title", ""),
                    "source_file": str(md_path.relative_to(self.run_dir)),
                },
                preserve_code_blocks=True,
            )

            self.stats["total_files_processed"] += 1
            self.stats["total_chunks_created"] += len(chunks)

            return chunks

        except Exception as e:
            self.logger.error(f"Failed to process {md_path}: {e}")
            self.stats["total_failures"] += 1
            return []

    async def _generate_embeddings_batch(
        self,
        chunks: list[dict],
        batch_size: int = 100,
    ) -> None:
        """
        Generate embeddings for chunks in batches.

        Args:
            chunks: List of chunk dictionaries
            batch_size: Number of chunks to embed per API call
        """
        self.logger.info(f"Generating embeddings for {len(chunks)} chunks")

        # Process in batches
        for i in tqdm(range(0, len(chunks), batch_size), desc="Embedding batches"):
            batch = chunks[i : i + batch_size]

            try:
                # Extract texts
                texts = [chunk["content"] for chunk in batch]

                # Call OpenAI API
                response = await self.client.embeddings.create(
                    model=self.settings.embedding_model,
                    input=texts,
                )

                # Attach embeddings to chunks
                for j, embedding_data in enumerate(response.data):
                    batch[j]["embedding"] = embedding_data.embedding

                self.stats["total_embeddings_generated"] += len(batch)

                # Rate limiting (avoid hitting API limits)
                await asyncio.sleep(0.5)

            except Exception as e:
                self.logger.error(f"Failed to generate embeddings for batch {i}: {e}")
                self.stats["total_failures"] += len(batch)

    def _save_chunks(self, chunks: list[dict]) -> None:
        """
        Save chunks with embeddings to JSON files (organized by framework).

        Args:
            chunks: List of chunk dictionaries with embeddings
        """
        # Group chunks by framework
        by_framework: dict[str, list[dict]] = {}
        for chunk in chunks:
            framework = chunk["metadata"]["framework"]
            if framework not in by_framework:
                by_framework[framework] = []
            by_framework[framework].append(chunk)

        # Save each framework's chunks
        for framework, framework_chunks in by_framework.items():
            framework_dir = self.chunks_dir / framework
            framework_dir.mkdir(parents=True, exist_ok=True)

            output_path = framework_dir / "chunks.json"

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(framework_chunks, f, indent=2)

            self.logger.info(
                f"Saved {len(framework_chunks)} chunks for {framework} to {output_path}"
            )
