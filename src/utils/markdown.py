"""HTML cleaning and markdown conversion utilities."""

import re

from bs4 import BeautifulSoup
from markdownify import markdownify


def clean_html(html: str, selectors: dict | None = None) -> BeautifulSoup:
    """
    Clean HTML by removing navigation, scripts, and other non-content elements.

    Args:
        html: Raw HTML string
        selectors: Optional dict with 'content' and 'remove' CSS selectors
                  Example: {'content': 'main', 'remove': ['nav', 'footer']}

    Returns:
        Cleaned BeautifulSoup object
    """
    soup = BeautifulSoup(html, "lxml")

    # Extract main content if selector provided
    if selectors and "content" in selectors:
        content_element = soup.select_one(selectors["content"])
        if content_element:
            soup = BeautifulSoup(str(content_element), "lxml")

    # Remove unwanted elements
    elements_to_remove = [
        "script",
        "style",
        "nav",
        "footer",
        "header",
        "aside",
        "iframe",
        "noscript",
    ]

    # Add custom selectors to remove
    if selectors and "remove" in selectors:
        elements_to_remove.extend(selectors["remove"])

    for selector in elements_to_remove:
        for element in soup.select(selector):
            element.decompose()

    # Remove elements with common navigation/menu classes
    navigation_patterns = [
        '[class*="nav"]',
        '[class*="menu"]',
        '[class*="sidebar"]',
        '[class*="breadcrumb"]',
        '[class*="footer"]',
        '[class*="header"]',
        '[aria-label*="Navigation"]',
        '[aria-label*="Menu"]',
    ]

    for pattern in navigation_patterns:
        for element in soup.select(pattern):
            element.decompose()

    return soup


def html_to_markdown(html: str, selectors: dict | None = None) -> str:
    """
    Convert HTML to clean markdown.

    Process:
    1. Clean HTML (remove nav, scripts, etc.)
    2. Convert to markdown
    3. Clean up markdown artifacts

    Args:
        html: Raw HTML string
        selectors: Optional CSS selectors for cleaning

    Returns:
        Clean markdown string
    """
    # Clean HTML first
    soup = clean_html(html, selectors)

    # Convert to markdown
    markdown = markdownify(
        str(soup),
        heading_style="ATX",  # Use # for headings
        bullets="-",  # Use - for bullets
        code_language="",  # Don't add language to code blocks by default
        strip=["a"],  # Keep link text but you can strip tags
    )

    # Clean up markdown
    markdown = clean_markdown(markdown)

    return markdown


def clean_markdown(text: str) -> str:
    """
    Clean up markdown artifacts and formatting issues.

    Args:
        text: Markdown text

    Returns:
        Cleaned markdown
    """
    # Remove markdown code fence artifacts
    text = re.sub(r"```markdown\n?", "", text)
    text = re.sub(r"```\n?$", "", text, flags=re.MULTILINE)

    # Remove excessive backticks
    text = re.sub(r"`{3,}", "```", text)

    # Remove repeated URLs/links
    text = re.sub(r"(?:(https?://[^\s]+)\s+){2,}", r"\1 ", text)

    # Remove empty links
    text = re.sub(r"\[\s*\]\([^)]*\)", "", text)

    # Clean up whitespace
    # Remove leading/trailing whitespace from lines
    lines = [line.rstrip() for line in text.split("\n")]

    # Remove more than 2 consecutive blank lines
    cleaned_lines = []
    blank_count = 0

    for line in lines:
        if line.strip() == "":
            blank_count += 1
            if blank_count <= 2:
                cleaned_lines.append(line)
        else:
            blank_count = 0
            cleaned_lines.append(line)

    text = "\n".join(cleaned_lines)

    # Remove leading and trailing whitespace
    text = text.strip()

    return text


def extract_headings(markdown: str) -> list[str]:
    """
    Extract all headings from markdown.

    Args:
        markdown: Markdown text

    Returns:
        List of heading texts (without # markers)
    """
    headings = []
    pattern = r"^#{1,6}\s+(.+)$"

    for line in markdown.split("\n"):
        match = re.match(pattern, line.strip())
        if match:
            headings.append(match.group(1).strip())

    return headings


def add_frontmatter(markdown: str, metadata: dict) -> str:
    """
    Add YAML frontmatter to markdown document.

    Args:
        markdown: Markdown content
        metadata: Dictionary of metadata fields

    Returns:
        Markdown with YAML frontmatter

    Example:
        >>> add_frontmatter("# Hello", {"url": "https://example.com", "title": "Test"})
        ---
        url: https://example.com
        title: Test
        ---

        # Hello
    """
    import yaml

    yaml_content = yaml.dump(metadata, allow_unicode=True, sort_keys=False)
    return f"---\n{yaml_content}---\n\n{markdown}"
