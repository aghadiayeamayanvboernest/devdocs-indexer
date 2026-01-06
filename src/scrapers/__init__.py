"""Framework-specific scrapers."""

from src.scrapers.base import BaseScraper
from src.scrapers.django import DjangoScraper
from src.scrapers.fastapi import FastAPIScraper
from src.scrapers.nextjs import NextJSScraper
from src.scrapers.postgresql import PostgreSQLScraper
from src.scrapers.react import ReactScraper
from src.scrapers.tailwind import TailwindScraper
from src.scrapers.typescript import TypeScriptScraper

__all__ = [
    "BaseScraper",
    "ReactScraper",
    "NextJSScraper",
    "TypeScriptScraper",
    "TailwindScraper",
    "FastAPIScraper",
    "DjangoScraper",
    "PostgreSQLScraper",
]
