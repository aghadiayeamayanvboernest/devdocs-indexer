"""Content hashing utilities for change detection."""

import hashlib


def compute_hash(content: str | bytes) -> str:
    """
    Compute SHA-256 hash of content.

    Used for detecting changes in crawled documentation.
    If content hash matches previous hash, we can skip re-processing.

    Args:
        content: String or bytes content to hash

    Returns:
        Hexadecimal hash string (64 characters)

    Examples:
        >>> compute_hash("Hello, World!")
        'dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f'

        >>> compute_hash(b"Hello, World!")
        'dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f'
    """
    if isinstance(content, str):
        content = content.encode("utf-8")

    return hashlib.sha256(content).hexdigest()


def compute_file_hash(filepath: str) -> str:
    """
    Compute SHA-256 hash of file contents.

    Args:
        filepath: Path to file

    Returns:
        Hexadecimal hash string

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    with open(filepath, "rb") as f:
        content = f.read()
    return compute_hash(content)
