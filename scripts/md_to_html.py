#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown to HTML converter for reread-yijing GitHub Pages.

Usage:
    python scripts/md_to_html.py

This script converts Markdown files under docs/ into HTML files for GitHub Pages,
using the shared template in assets/css/style.css.
"""

import re
import sys
from pathlib import Path
from typing import Optional

try:
    import markdown
    from markdown.extensions import Extension
    from markdown.treeprocessors import Treeprocessor
except ImportError:
    print("Error: 'markdown' package is required.")
    print("Install it with: pip install -r requirements.txt")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = PROJECT_ROOT / "docs"
OUTPUT_DIR = PROJECT_ROOT
README_PATH = PROJECT_ROOT / "README.md"
INDEX_PATH = PROJECT_ROOT / "index.html"

# Files and directories to skip during batch conversion
SKIP_NAMES = {"README.md", "LICENSE", "CONTRIBUTING.md"}


# ---------------------------------------------------------------------------
# Template
# ---------------------------------------------------------------------------
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} · 重读易经</title>
  <link rel="stylesheet" href="{css_prefix}assets/css/style.css">
</head>
<body>
  <nav class="site-nav">
    <div class="site-nav-inner">
      <a href="{home_prefix}index.html" class="site-title">重读易经</a>
      <div class="site-links">
        <a href="{home_prefix}index.html">总览</a>
        <a href="{home_prefix}hexagrams/01-qian.html">乾卦</a>
        <a href="{home_prefix}hexagrams/02-kun.html">坤卦</a>
      </div>
    </div>
  </nav>

  <main class="container">
{body}
  </main>

  <footer class="site-footer">
    <p>重读易经 · Reread Yijing · 以现代方法重读中国古代经典</p>
  </footer>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def extract_title(md_text: str) -> str:
    """Extract the first H1 title from Markdown text."""
    match = re.search(r"^#\s+(.+)$", md_text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return "重读易经"


def rewrite_md_links(html: str, source_dir: Path, output_dir: Path) -> str:
    """
    Rewrite relative .md links to .html links.

    Handles links like:
      - ./other.md
      - docs/hexagrams/01-qian.md
      - ../README.md
    """

    def replace_link(match: re.Match) -> str:
        before = match.group(1)
        url = match.group(2)
        after = match.group(3)

        # Skip external links, anchors-only, and non-md files
        if (
            "://" in url
            or url.startswith("#")
            or url.startswith("mailto:")
            or not url.endswith(".md")
        ):
            return match.group(0)

        new_url = url[:-3] + ".html"

        # README.md -> index.html
        if Path(url).name == "README.md":
            new_url = str(Path(new_url).parent / "index.html")
            if new_url == "./index.html" or new_url == ".\\index.html":
                new_url = "index.html"

        return f'{before}"{new_url}"{after}'

    # Match href="..." or src="..."
    pattern = re.compile(r'((?:href|src)=")([^"]+)(")')
    return pattern.sub(replace_link, html)


def convert_markdown(md_text: str) -> str:
    """Convert Markdown text to HTML body."""
    md = markdown.Markdown(
        extensions=[
            "tables",
            "fenced_code",
            "toc",
        ]
    )
    html = md.convert(md_text)
    return html


def build_html(title: str, body: str, relative_depth: int) -> str:
    """Wrap HTML body in the shared template."""
    css_prefix = "../" * relative_depth if relative_depth > 0 else ""
    home_prefix = "../" * relative_depth if relative_depth > 0 else ""

    return HTML_TEMPLATE.format(
        title=title,
        body=body,
        css_prefix=css_prefix,
        home_prefix=home_prefix,
    )


def generate_index_cards() -> str:
    """Generate a card grid for the index page based on existing hexagram HTML files."""
    hex_dir = OUTPUT_DIR / "hexagrams"
    if not hex_dir.exists():
        return ""

    cards = []
    # Sort by filename to keep hexagram order
    for html_file in sorted(hex_dir.glob("*.html")):
        name = html_file.stem
        # Try to extract a short subtitle from the file content
        content = html_file.read_text(encoding="utf-8")
        subtitle = "单卦报告"
        if "乾卦" in content:
            subtitle = "天行健，君子以自强不息。"
        elif "坤卦" in content:
            subtitle = "地势坤，君子以厚德载物。"

        display_name = name.replace("-", " ").upper()
        cards.append(
            f'      <a href="hexagrams/{html_file.name}" class="card">\n'
            f"        <h3>{display_name}</h3>\n"
            f"        <p>{subtitle}</p>\n"
            f"      </a>"
        )

    if not cards:
        return ""

    return '\n    <div class="card-grid">\n' + "\n".join(cards) + '\n    </div>'


def process_file(source_path: Path, output_path: Path) -> None:
    """Convert a single Markdown file to HTML."""
    md_text = source_path.read_text(encoding="utf-8")
    title = extract_title(md_text)
    body = convert_markdown(md_text)
    body = rewrite_md_links(body, SOURCE_DIR, OUTPUT_DIR)

    # Calculate relative depth from output file to project root
    try:
        relative_depth = len(output_path.relative_to(PROJECT_ROOT).parent.parts)
    except ValueError:
        relative_depth = 0

    html = build_html(title, body, relative_depth)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    print(f"Generated: {output_path.relative_to(PROJECT_ROOT)}")


def process_readme() -> None:
    """Convert README.md to index.html and append card grid."""
    md_text = README_PATH.read_text(encoding="utf-8")
    title = extract_title(md_text)
    body = convert_markdown(md_text)
    body = rewrite_md_links(body, PROJECT_ROOT, OUTPUT_DIR)

    # Append generated card grid if not already present
    if "card-grid" not in body:
        cards_html = generate_index_cards()
        if cards_html:
            body = body.rstrip() + "\n\n" + cards_html + "\n"

    html = build_html(title, body, relative_depth=0)
    INDEX_PATH.write_text(html, encoding="utf-8")
    print(f"Generated: {INDEX_PATH.relative_to(PROJECT_ROOT)}")


def main() -> None:
    """Batch convert all Markdown files under docs/."""
    if not SOURCE_DIR.exists():
        print(f"Source directory not found: {SOURCE_DIR}")
        sys.exit(1)

    # Convert README.md to index.html first
    if README_PATH.exists():
        process_readme()

    # Convert all Markdown files under docs/
    for md_file in sorted(SOURCE_DIR.rglob("*.md")):
        if md_file.name in SKIP_NAMES:
            continue

        # Compute output path: docs/foo/bar.md -> foo/bar.html
        rel_path = md_file.relative_to(SOURCE_DIR)
        output_path = OUTPUT_DIR / rel_path.with_suffix(".html")
        process_file(md_file, output_path)

    print("\nDone. Open index.html in a browser to preview.")


if __name__ == "__main__":
    main()
