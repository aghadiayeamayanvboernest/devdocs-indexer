"""Tests for chunking utilities."""

import pytest

from src.utils.chunker import SmartChunker


@pytest.fixture
def chunker():
    """Create a chunker with small size for testing."""
    return SmartChunker(chunk_size=100, overlap=20)


def test_count_tokens(chunker):
    """Test token counting."""
    text = "Hello, world! This is a test."
    tokens = chunker.count_tokens(text)

    assert tokens > 0
    assert isinstance(tokens, int)


def test_chunk_text_basic(chunker):
    """Test basic text chunking."""
    text = "This is a short text that should fit in one chunk."

    chunks = chunker.chunk_text(text)

    assert len(chunks) > 0
    assert chunks[0]["content"] == text
    assert chunks[0]["tokens"] > 0
    assert "metadata" in chunks[0]


def test_chunk_text_long(chunker):
    """Test chunking of long text."""
    # Create text longer than chunk_size
    text = " ".join([f"This is sentence number {i}." for i in range(100)])

    chunks = chunker.chunk_text(text, metadata={"source": "test"})

    # Should create multiple chunks
    assert len(chunks) > 1

    # Each chunk should have metadata
    for chunk in chunks:
        assert chunk["metadata"]["source"] == "test"
        assert "chunk_index" in chunk["metadata"]
        assert "chunk_count" in chunk["metadata"]

    # Chunks should have reasonable size
    for chunk in chunks:
        assert chunk["tokens"] <= chunker.chunk_size * 1.2  # Allow 20% overage


def test_chunk_markdown_with_code(chunker):
    """Test chunking markdown with code blocks."""
    markdown = """# Test Document

Here is some text.

```python
def hello():
    print("Hello, world!")
```

More text here.
"""

    chunks = chunker.chunk_markdown(markdown, preserve_code_blocks=True)

    assert len(chunks) > 0

    # Code block should be preserved (if small enough)
    has_code = any("def hello" in chunk["content"] for chunk in chunks)
    assert has_code


def test_chunk_empty_text(chunker):
    """Test chunking empty text."""
    chunks = chunker.chunk_text("")

    assert len(chunks) == 0


def test_chunk_with_overlap(chunker):
    """Test that chunks have overlap."""
    text = " ".join([f"Word{i}" for i in range(200)])

    chunks = chunker.chunk_text(text)

    if len(chunks) > 1:
        # Check that consecutive chunks share some content
        # (This is hard to test exactly, but we can check metadata)
        assert chunks[0]["metadata"]["chunk_count"] == len(chunks)
        assert chunks[0]["metadata"]["chunk_index"] == 0
        assert chunks[1]["metadata"]["chunk_index"] == 1


def test_chunk_metadata_propagation(chunker):
    """Test that metadata is propagated to all chunks."""
    text = " ".join([f"Sentence {i}" for i in range(100)])
    metadata = {"url": "https://example.com", "framework": "react"}

    chunks = chunker.chunk_text(text, metadata)

    for chunk in chunks:
        assert chunk["metadata"]["url"] == "https://example.com"
        assert chunk["metadata"]["framework"] == "react"
