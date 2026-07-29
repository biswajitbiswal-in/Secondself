"""
Text extraction helpers for SecondSelf.

Extracts clean text from different capture types (note, link, file)
so it can be classified by the LLM.
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

import config

logger = logging.getLogger(__name__)

# Timeout for URL fetching
REQUEST_TIMEOUT = 15
MAX_EXTRACT_CHARS = 8000  # Truncate extracted text to this many characters


def extract_text(raw_dir: Path) -> str:
    """
    Main dispatcher: detect the capture type from metadata.json and extract text accordingly.

    Args:
        raw_dir: Path to the raw capture directory (raw/{id}/)

    Returns:
        Extracted plain text string, or empty string on failure.
    """
    meta_path = raw_dir / "metadata.json"
    if not meta_path.exists():
        logger.warning(f"No metadata.json in {raw_dir}")
        return ""

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to read metadata.json in {raw_dir}: {e}")
        return ""

    capture_type = meta.get("type", "note")

    if capture_type == "note":
        return extract_note_text(raw_dir)
    elif capture_type == "link":
        return extract_link_text(raw_dir, meta)
    elif capture_type == "file":
        return extract_file_text(raw_dir, meta)
    else:
        logger.warning(f"Unknown capture type '{capture_type}' in {raw_dir}")
        return ""


def strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter (--- ... ---) from the start of a markdown file."""
    match = re.match(r"^---\s*\n.*?\n---\s*\n", text, re.DOTALL)
    if match:
        return text[match.end():]
    return text


def extract_note_text(raw_dir: Path) -> str:
    """
    Extract text from a note capture — read content.md directly.

    Strips any leading YAML frontmatter that may be present.

    Returns:
        Clean text from content.md
    """
    content_path = raw_dir / "content.md"
    if not content_path.exists():
        logger.warning(f"No content.md in {raw_dir}")
        return ""

    try:
        text = content_path.read_text(encoding="utf-8")
        text = strip_frontmatter(text)
        return truncate(text.strip())
    except OSError as e:
        logger.warning(f"Failed to read content.md in {raw_dir}: {e}")
        return ""


def extract_link_text(raw_dir: Path, meta: dict) -> str:
    """
    Extract text from a link capture — fetch the URL and strip HTML.

    Falls back to the URL string itself if fetching fails.

    Returns:
        Plain text from the webpage, or URL string as fallback.
    """
    url = meta.get("url", "")
    if not url:
        # Try reading content.md as fallback
        content_path = raw_dir / "content.md"
        if content_path.exists():
            return truncate(content_path.read_text(encoding="utf-8"))
        return ""

    # Try to fetch and extract the webpage
    try:
        headers = {
            "User-Agent": "SecondSelf-Extract/1.0 (+https://github.com/secondself)"
        }
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        # Determine encoding
        encoding = response.encoding or "utf-8"
        response.encoding = encoding

        # Parse HTML and extract text
        soup = BeautifulSoup(response.text, "html.parser")

        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()

        # Get text and clean it up
        text = soup.get_text(separator=" ", strip=True)

        if text:
            return truncate(text)

        # If extraction yielded empty, use raw content
        content_path = raw_dir / "content.md"
        if content_path.exists():
            return truncate(content_path.read_text(encoding="utf-8"))

        return url

    except requests.RequestException as e:
        logger.warning(f"Failed to fetch URL '{url}': {e}")
        # Fallback to stored content
        content_path = raw_dir / "content.md"
        if content_path.exists():
            return truncate(content_path.read_text(encoding="utf-8"))
        return url

    except Exception as e:
        logger.warning(f"Error extracting link text from '{url}': {e}")
        return url


def extract_file_text(raw_dir: Path, meta: dict) -> str:
    """
    Extract text from a file capture.

    Supports PDF via pypdf. Falls back to original_filename or content.md.

    Returns:
        Extracted text or fallback string.
    """
    # Try content.md first (for text files that were captured directly)
    content_path = raw_dir / "content.md"
    if content_path.exists():
        text = content_path.read_text(encoding="utf-8")
        if text.strip():
            return truncate(text)

    # Check if there's a PDF in the directory
    pdf_files = list(raw_dir.glob("*.pdf"))
    if pdf_files:
        try:
            from pypdf import PdfReader
            reader = PdfReader(pdf_files[0])
            text_parts = []
            for page in reader.pages:
                page_text = page.extract_text() or ""
                text_parts.append(page_text)
            full_text = "\n".join(text_parts)
            if full_text.strip():
                return truncate(full_text)
        except Exception as e:
            logger.warning(f"Failed to extract PDF text from {pdf_files[0]}: {e}")

    # Fallback: return filename as minimal content
    original_filename = meta.get("original_filename", "unknown_file")
    return truncate(f"[File: {original_filename}]")


def truncate(text: str, max_chars: int = MAX_EXTRACT_CHARS) -> str:
    """Truncate text to a maximum number of characters, keeping whole words."""
    if len(text) <= max_chars:
        return text
    # Truncate at word boundary
    truncated = text[:max_chars]
    last_space = truncated.rfind(" ")
    if last_space > max_chars // 2:
        truncated = truncated[:last_space]
    return truncated + "\n\n[Content truncated...]"

