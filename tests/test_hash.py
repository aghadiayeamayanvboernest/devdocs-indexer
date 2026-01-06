"""Tests for hash utilities."""

from src.utils.hash import compute_hash


def test_compute_hash_string():
    """Test hashing of string content."""
    content = "Hello, World!"
    hash_result = compute_hash(content)

    # Should return 64-character hex string
    assert len(hash_result) == 64
    assert all(c in "0123456789abcdef" for c in hash_result)

    # Should be deterministic
    assert compute_hash(content) == hash_result


def test_compute_hash_bytes():
    """Test hashing of bytes content."""
    content = b"Hello, World!"
    hash_result = compute_hash(content)

    # Should work the same as string
    assert compute_hash("Hello, World!") == hash_result


def test_compute_hash_different_content():
    """Test that different content produces different hashes."""
    hash1 = compute_hash("Content A")
    hash2 = compute_hash("Content B")

    assert hash1 != hash2


def test_compute_hash_empty():
    """Test hashing empty content."""
    hash_empty = compute_hash("")

    assert len(hash_empty) == 64
    # Empty string has known hash
    assert hash_empty == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
