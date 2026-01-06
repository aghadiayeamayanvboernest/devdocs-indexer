"""Utility functions for crawling, parsing, and processing."""

from src.utils.chunker import SmartChunker
from src.utils.crawl import fetch_with_playwright, fetch_with_requests
from src.utils.hash import compute_hash
from src.utils.logger import get_logger
from src.utils.markdown import clean_html, html_to_markdown

__all__ = [
    "fetch_with_playwright",
    "fetch_with_requests",
    "clean_html",
    "html_to_markdown",
    "SmartChunker",
    "compute_hash",
    "get_logger",
]
