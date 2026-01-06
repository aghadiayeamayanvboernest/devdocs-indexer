"""Pytest configuration and fixtures."""

from pathlib import Path

import pytest


@pytest.fixture
def test_data_dir(tmp_path: Path) -> Path:
    """Create a temporary data directory for tests."""
    data_dir = tmp_path / "test_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


@pytest.fixture
def sample_html() -> str:
    """Sample HTML content for testing."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Test Page</title></head>
    <body>
        <nav>Navigation</nav>
        <main>
            <h1>Main Heading</h1>
            <p>This is a test paragraph with <code>code</code> example.</p>
            <pre><code>function test() {
    return true;
}</code></pre>
        </main>
        <footer>Footer content</footer>
    </body>
    </html>
    """


@pytest.fixture
def sample_markdown() -> str:
    """Sample markdown content for testing."""
    return """---
url: https://example.com/test
framework: react
title: Test Page
---

# Main Heading

This is a test paragraph with `code` example.

```javascript
function test() {
    return true;
}
```
"""


@pytest.fixture
def mock_framework_config() -> dict:
    """Mock framework configuration."""
    return {
        "react": {
            "name": "React",
            "base_url": "https://react.dev",
            "start_urls": ["https://react.dev/learn"],
            "skip_patterns": ["/blog", "/community"],
            "selectors": {
                "content": "main",
                "remove": ["nav", "footer"],
            },
            "chunk_size": 1000,
            "overlap": 200,
        }
    }
