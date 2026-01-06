"""Parser module for converting HTML to markdown with metadata."""

import csv
from datetime import datetime
from pathlib import Path
from typing import Any

from tqdm import tqdm

from src.config.settings import get_settings
from src.utils.hash import compute_hash
from src.utils.logger import get_logger
from src.utils.markdown import add_frontmatter, extract_headings, html_to_markdown

logger = get_logger(__name__)


class Parser:
    """
    Parser that converts raw HTML to clean markdown with metadata.

    Workflow:
    1. Load crawled HTML files
    2. Convert each to markdown using framework-specific selectors
    3. Add YAML frontmatter with metadata (URL, framework, headings, etc.)
    4. Save to markdown directory
    5. Generate CSV report
    """

    def __init__(
        self,
        run_dir: Path,
        force: bool = False,
    ):
        """
        Initialize parser.

        Args:
            run_dir: Directory containing crawled data
            force: If True, reparse even if content hash hasn't changed
        """
        self.settings = get_settings()
        self.run_dir = Path(run_dir)
        self.raw_dir = self.run_dir / "raw"
        self.markdown_dir = self.run_dir / "markdown"
        self.logs_dir = self.run_dir / "logs"
        self.force = force

        # Create directories
        self.markdown_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Set up logging
        log_file = self.logs_dir / "parser.jsonl"
        self.logger = get_logger("parser", log_file)

        # Stats tracking
        self.stats: dict[str, Any] = {
            "total_files_processed": 0,
            "total_files_skipped": 0,
            "total_failures": 0,
            "start_time": None,
            "end_time": None,
        }

    async def parse(self) -> dict[str, Any]:
        """
        Run the complete parsing process.

        Returns:
            Statistics dictionary
        """
        self.stats["start_time"] = datetime.now().isoformat()
        self.logger.info(f"Starting parsing for run: {self.run_dir}")

        # Load crawl report
        report_path = self.run_dir / "crawl_report.csv"
        if not report_path.exists():
            raise FileNotFoundError(f"Crawl report not found: {report_path}")

        files_to_parse = self._load_crawl_report(report_path)

        # Parse each file
        parsed_files = []
        for file_data in tqdm(files_to_parse, desc="Parsing files"):
            result = await self._parse_file(file_data)
            if result:
                parsed_files.append(result)

        # Generate report
        self._generate_report(parsed_files)

        self.stats["end_time"] = datetime.now().isoformat()
        self.logger.info(f"Parsing complete. Stats: {self.stats}")

        return self.stats

    def _load_crawl_report(self, report_path: Path) -> list[dict]:
        """
        Load crawl report and filter successful downloads.

        Args:
            report_path: Path to crawl_report.csv

        Returns:
            List of file metadata dicts
        """
        files = []

        with open(report_path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Only process successful downloads
                if row["status"] == "success":
                    files.append(row)

        self.logger.info(f"Loaded {len(files)} files from crawl report")
        return files

    async def _parse_file(self, file_data: dict) -> dict | None:
        """
        Parse a single HTML file to markdown.

        Args:
            file_data: File metadata from crawl report

        Returns:
            Parsed file metadata or None if failed
        """
        try:
            framework = file_data["framework"]
            html_path = self.run_dir / file_data["filepath"]
            url = file_data["url"]

            # Read HTML content
            with open(html_path, encoding="utf-8") as f:
                html_content = f.read()

            # Load framework config for selectors
            from src.config.settings import load_framework_config

            framework_configs = load_framework_config()["frameworks"]
            selectors = framework_configs[framework].get("selectors")

            # Convert to markdown
            markdown = html_to_markdown(html_content, selectors)

            # Extract headings for metadata
            headings = extract_headings(markdown)
            main_heading = headings[0] if headings else "Untitled"

            # Create metadata
            metadata = {
                "framework": framework,
                "url": url,
                "title": main_heading,
                "headings": headings[:5],  # First 5 headings
                "source_file": file_data["filepath"],
                "parsed_at": datetime.now().isoformat(),
            }

            # Add frontmatter
            markdown_with_frontmatter = add_frontmatter(markdown, metadata)

            # Save to markdown directory
            framework_md_dir = self.markdown_dir / framework
            framework_md_dir.mkdir(parents=True, exist_ok=True)

            md_filename = f"{file_data['url_hash']}.md"
            md_path = framework_md_dir / md_filename

            with open(md_path, "w", encoding="utf-8") as f:
                f.write(markdown_with_frontmatter)

            # Compute markdown hash
            md_hash = compute_hash(markdown_with_frontmatter)

            self.stats["total_files_processed"] += 1

            return {
                **file_data,
                "markdown_path": str(md_path.relative_to(self.run_dir)),
                "markdown_hash": md_hash,
                "title": main_heading,
                "headings_count": len(headings),
                "parse_status": "success",
            }

        except Exception as e:
            self.logger.error(f"Failed to parse {file_data.get('url', 'unknown')}: {e}")
            self.stats["total_failures"] += 1

            return {
                **file_data,
                "parse_status": "failed",
                "error": str(e),
            }

    def _generate_report(self, parsed_files: list[dict]) -> None:
        """
        Generate CSV report of parsed files.

        Args:
            parsed_files: List of parsed file metadata
        """
        report_path = self.run_dir / "parse_report.csv"

        with open(report_path, "w", newline="") as f:
            fieldnames = [
                "framework",
                "url",
                "url_hash",
                "title",
                "filepath",
                "markdown_path",
                "content_hash",
                "markdown_hash",
                "headings_count",
                "parse_status",
                "error",
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for file_data in parsed_files:
                row = {field: file_data.get(field, "") for field in fieldnames}
                writer.writerow(row)

        self.logger.info(f"Parse report written to {report_path}")
