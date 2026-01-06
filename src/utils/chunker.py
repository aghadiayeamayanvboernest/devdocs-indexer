"""Smart text chunking utilities for embeddings."""

import re

import tiktoken
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import Document, TextNode


class SmartChunker:
    """
    Smart document chunker that splits text at semantic boundaries.

    Features:
    - Sentence-aware splitting (doesn't break mid-sentence)
    - Configurable chunk size and overlap
    - Preserves code blocks within single chunks when possible
    - Maintains context through overlap
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        overlap: int = 200,
        encoding_model: str = "cl100k_base",
    ):
        """
        Initialize chunker.

        Args:
            chunk_size: Target chunk size in tokens
            overlap: Number of tokens to overlap between chunks
            encoding_model: Tiktoken encoding model name
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.encoding = tiktoken.get_encoding(encoding_model)

        # LlamaIndex sentence splitter
        self.splitter = SentenceSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            paragraph_separator="\n\n",
            secondary_chunking_regex="[^,.;。]+[,.;。]?",
        )

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        return len(self.encoding.encode(text))

    def chunk_text(self, text: str, metadata: dict | None = None) -> list[dict]:
        """
        Chunk text into semantic chunks.

        Args:
            text: Text to chunk
            metadata: Optional metadata to attach to each chunk

        Returns:
            List of chunk dictionaries with 'content', 'metadata', and 'tokens'
        """
        if not text.strip():
            return []

        metadata = metadata or {}

        # Create LlamaIndex document
        doc = Document(text=text, metadata=metadata)

        # Split into nodes
        nodes = self.splitter.get_nodes_from_documents([doc])

        # Convert to simple dict format
        chunks = []
        for i, node in enumerate(nodes):
            chunk_text = node.get_content()
            chunk_metadata = {
                **metadata,
                "chunk_index": i,
                "chunk_count": len(nodes),
            }

            chunks.append(
                {
                    "content": chunk_text,
                    "metadata": chunk_metadata,
                    "tokens": self.count_tokens(chunk_text),
                }
            )

        return chunks

    def chunk_markdown(
        self,
        markdown: str,
        metadata: dict | None = None,
        preserve_code_blocks: bool = True,
    ) -> list[dict]:
        """
        Chunk markdown with special handling for code blocks.

        Args:
            markdown: Markdown text
            metadata: Metadata to attach
            preserve_code_blocks: If True, try to keep code blocks intact

        Returns:
            List of chunks
        """
        if preserve_code_blocks:
            # Split by code blocks
            parts = self._split_preserving_code_blocks(markdown)

            all_chunks = []
            for part_text, is_code in parts:
                if is_code:
                    # Keep code block as single chunk if possible
                    tokens = self.count_tokens(part_text)
                    if tokens <= self.chunk_size:
                        all_chunks.append(
                            {
                                "content": part_text,
                                "metadata": {**(metadata or {}), "is_code_block": True},
                                "tokens": tokens,
                            }
                        )
                    else:
                        # Code block too large, split it
                        chunks = self.chunk_text(part_text, metadata)
                        all_chunks.extend(chunks)
                else:
                    # Regular text, chunk normally
                    chunks = self.chunk_text(part_text, metadata)
                    all_chunks.extend(chunks)

            return all_chunks

        else:
            return self.chunk_text(markdown, metadata)

    def _split_preserving_code_blocks(self, markdown: str) -> list[tuple[str, bool]]:
        """
        Split markdown into code blocks and text blocks.

        Args:
            markdown: Markdown text

        Returns:
            List of (text, is_code_block) tuples
        """
        parts = []
        current_text = []
        in_code_block = False
        code_fence_pattern = re.compile(r"^```.*$", re.MULTILINE)

        lines = markdown.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i]

            if code_fence_pattern.match(line):
                # Found code fence
                if in_code_block:
                    # End of code block
                    current_text.append(line)
                    parts.append(("\n".join(current_text), True))
                    current_text = []
                    in_code_block = False
                else:
                    # Start of code block
                    if current_text:
                        parts.append(("\n".join(current_text), False))
                        current_text = []
                    current_text.append(line)
                    in_code_block = True
            else:
                current_text.append(line)

            i += 1

        # Add remaining text
        if current_text:
            parts.append(("\n".join(current_text), in_code_block))

        return parts

    def chunk_document_with_context(
        self,
        markdown: str,
        metadata: dict | None = None,
    ) -> list[TextNode]:
        """
        Chunk document and add contextual metadata (headers, surrounding chunks).

        This is useful for RAG systems where you want each chunk to have
        context about where it came from.

        Args:
            markdown: Markdown text
            metadata: Base metadata

        Returns:
            List of LlamaIndex TextNode objects with rich metadata
        """
        # Extract headers for context
        headers = self._extract_headers_with_positions(markdown)

        # Chunk the text
        chunks = self.chunk_markdown(markdown, metadata)

        # Create TextNode objects with enhanced metadata
        nodes = []
        for i, chunk in enumerate(chunks):
            # Find which header this chunk falls under
            chunk_content = chunk["content"]
            chunk_position = markdown.find(chunk_content)

            current_headers = self._get_headers_for_position(chunk_position, headers)

            node_metadata = {
                **chunk["metadata"],
                "headers": current_headers,
                "previous_chunk": chunks[i - 1]["content"][:100] if i > 0 else None,
                "next_chunk": chunks[i + 1]["content"][:100] if i < len(chunks) - 1 else None,
            }

            node = TextNode(
                text=chunk_content,
                metadata=node_metadata,
            )

            nodes.append(node)

        return nodes

    def _extract_headers_with_positions(self, markdown: str) -> list[dict]:
        """Extract headers with their positions in text."""
        headers = []
        pattern = r"^(#{1,6})\s+(.+)$"

        for match in re.finditer(pattern, markdown, re.MULTILINE):
            level = len(match.group(1))
            text = match.group(2).strip()
            position = match.start()

            headers.append({"level": level, "text": text, "position": position})

        return headers

    def _get_headers_for_position(
        self,
        position: int,
        headers: list[dict],
    ) -> dict[str, str]:
        """Get active headers at a given position in the document."""
        active_headers = {}

        for header in headers:
            if header["position"] <= position:
                # This header is before our position
                level = header["level"]
                active_headers[f"h{level}"] = header["text"]

                # Clear any lower-level headers (higher number = lower level)
                for i in range(level + 1, 7):
                    active_headers.pop(f"h{i}", None)

        return active_headers
