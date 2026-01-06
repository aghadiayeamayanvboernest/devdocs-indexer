# DevDocs Indexer

Documentation indexer pipeline for DevDocs AI - an intelligent documentation assistant with code generation capabilities.

## Overview

This pipeline crawls, processes, and indexes documentation from 7 major frameworks into a Pinecone vector database for semantic search:

- **React** - react.dev
- **Next.js** - nextjs.org
- **TypeScript** - typescriptlang.org
- **Tailwind CSS** - tailwindcss.com
- **FastAPI** - fastapi.tiangolo.com
- **Django** - docs.djangoproject.com
- **PostgreSQL** - postgresql.org/docs

## Architecture

```
Web Docs → Crawl (Playwright) → Parse (HTML→MD) → Chunk (1000 tokens) → Embed (OpenAI) → Index (Pinecone)
```

### Pipeline Stages

1. **Crawl** - Async Playwright-based scraping with retry logic
2. **Parse** - HTML cleaning and markdown conversion with metadata
3. **Chunk** - Smart semantic chunking (1000 tokens, 200 overlap)
4. **Embed** - OpenAI text-embedding-3-small (1536 dimensions)
5. **Index** - Pinecone upload with framework namespaces

## Setup

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager
- OpenAI API key
- Pinecone API key

### Installation

```bash
# Clone the repository
git clone https://github.com/aghadiayeamayanvboernest/devdocs-indexer.git
cd devdocs-indexer

# Install dependencies with uv
uv sync

# Install Playwright browsers
uv run playwright install chromium

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

### Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=...
PINECONE_INDEX_NAME=devdocs-index

# Optional
LOG_LEVEL=INFO
DATA_DIR=data/runs
```

## Usage

### Two-Step Workflow (Recommended)

**Step 1: Process documentation (crawl, parse, embed)**
```bash
# Process all frameworks
uv run python main.py

# Or specific frameworks only
uv run python main.py --frameworks react nextjs typescript
```

This creates chunks with embeddings in `data/runs/YYYY_MM_DD_HH_MM/chunks/`

**Step 2: Upload to Pinecone**
```bash
# Review chunks first, then upload
uv run python store.py --run-dir data/runs/YYYY_MM_DD_HH_MM

# Create index if it doesn't exist
uv run python store.py --run-dir data/runs/YYYY_MM_DD_HH_MM --create-index
```

### Run Individual Stages

```bash
# 1. Crawl only (downloads HTML)
uv run python scripts/crawl.py --frameworks react nextjs

# 2. Parse only (HTML → Markdown)
uv run python scripts/parse.py --run-dir data/runs/2025_01_06_10_00

# 3. Embed only (generate embeddings)
uv run python scripts/embed.py --run-dir data/runs/2025_01_06_10_00

# 4. Index only (upload to Pinecone)
uv run python scripts/index.py --run-dir data/runs/2025_01_06_10_00
```

## Project Structure

```
devdocs-indexer/
├── src/
│   ├── core/              # Core pipeline orchestration
│   ├── scrapers/          # Framework-specific scrapers
│   ├── utils/             # Utilities (crawl, parse, chunk, hash)
│   └── config/            # Configuration files
├── scripts/               # Entry point scripts
├── tests/                 # pytest tests
├── notebooks/             # Jupyter notebooks for exploration
└── data/                  # Gitignored data directory
    └── runs/              # Timestamped pipeline runs
```

## Development

### Run Tests

```bash
# Run all tests with coverage
uv run pytest

# Run specific test file
uv run pytest tests/test_scrapers.py

# Run with verbose output
uv run pytest -v
```

### Code Quality

```bash
# Run linter
uv run ruff check .

# Run formatter
uv run ruff format .

# Type checking
uv run mypy src/
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
uv run pre-commit install

# Run manually
uv run pre-commit run --all-files
```

## Data Output

Each pipeline run creates a timestamped directory:

```
data/runs/YYYY_MM_DD_HH_MM/
├── raw/                  # Downloaded HTML files
├── markdown/             # Converted markdown with frontmatter
├── chunks/               # Chunked documents (JSON)
└── logs/                 # Pipeline logs (JSONL)
```

## Configuration

Framework configurations are in [`src/config/frameworks.yaml`](src/config/frameworks.yaml):

```yaml
frameworks:
  react:
    name: "React"
    base_url: "https://react.dev"
    start_urls: [...]
    skip_patterns: [...]
    chunk_size: 1000
    overlap: 200
```

## Performance

- **Crawl time**: ~2-3 hours for all 7 frameworks
- **Parse time**: ~10-15 minutes
- **Embedding time**: ~5-10 minutes (depends on chunk count)
- **Total chunks**: ~20-25K across all frameworks
- **Embedding cost**: ~$0.50 per full run

## License

MIT

## Author

Aghadiaye Ernest
