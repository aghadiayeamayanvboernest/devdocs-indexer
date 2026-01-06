"""Tests for markdown utilities."""

from src.utils.markdown import (
    add_frontmatter,
    clean_html,
    clean_markdown,
    extract_headings,
    html_to_markdown,
)


def test_clean_html_basic(sample_html):
    """Test basic HTML cleaning."""
    soup = clean_html(sample_html)

    # Should remove nav and footer
    assert soup.find("nav") is None
    assert soup.find("footer") is None

    # Should keep main content
    assert "Main Heading" in soup.get_text()
    assert "test paragraph" in soup.get_text()


def test_clean_html_with_selectors(sample_html):
    """Test HTML cleaning with custom selectors."""
    selectors = {"content": "main", "remove": ["nav", "footer"]}

    soup = clean_html(sample_html, selectors)

    assert "Main Heading" in soup.get_text()
    assert soup.find("nav") is None


def test_html_to_markdown(sample_html):
    """Test HTML to markdown conversion."""
    markdown = html_to_markdown(sample_html)

    # Should contain heading
    assert "# Main Heading" in markdown

    # Should contain paragraph text
    assert "test paragraph" in markdown

    # Should contain code (either as code fence or plain text from <code>)
    assert "function test()" in markdown
    assert "return true" in markdown


def test_clean_markdown():
    """Test markdown cleaning."""
    dirty_markdown = """```markdown
# Test


[](https://empty.com)

https://example.com https://example.com

```
"""

    cleaned = clean_markdown(dirty_markdown)

    # Should remove markdown fence artifacts
    assert "```markdown" not in cleaned

    # Should remove empty links (the original empty.com link)
    assert "empty.com" not in cleaned

    # Should remove repeated URLs (keep only one)
    assert cleaned.count("https://example.com") == 1


def test_extract_headings():
    """Test heading extraction."""
    markdown = """# Heading 1

Some text

## Heading 2

### Heading 3
"""

    headings = extract_headings(markdown)

    assert len(headings) == 3
    assert "Heading 1" in headings
    assert "Heading 2" in headings
    assert "Heading 3" in headings


def test_add_frontmatter():
    """Test adding YAML frontmatter."""
    markdown = "# Test Content"
    metadata = {"url": "https://example.com", "title": "Test", "framework": "react"}

    result = add_frontmatter(markdown, metadata)

    # Should start with ---
    assert result.startswith("---\n")

    # Should contain metadata
    assert "url: https://example.com" in result
    assert "title: Test" in result
    assert "framework: react" in result

    # Should end with original content
    assert result.endswith("# Test Content")
