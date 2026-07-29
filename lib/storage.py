"""
Filesystem storage helpers for SecondSelf.

Provides read/write operations for raw captures, wiki notes, and index state.
All paths are derived from the central config module.
"""

import hashlib
import json
import logging
import re
import uuid
from pathlib import Path
from typing import List, Optional

import yaml

import config
from lib.models import WikiNote

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ID Generation
# ---------------------------------------------------------------------------

def generate_capture_id() -> str:
    """Generate a short unique ID: first 8 hex chars of UUID4."""
    return uuid.uuid4().hex[:8]


def folder_name_from_id(capture_id: str, timestamp_str: str = "") -> str:
    """
    Build folder name: {YYYY-MM-DD}_{short_id}
    If timestamp_str is provided, parse date from it.
    """
    if timestamp_str:
        # Extract date portion from ISO timestamp
        date_part = timestamp_str[:10]  # "2026-07-24"
    else:
        import datetime
        date_part = datetime.date.today().isoformat()
    return f"{date_part}_{capture_id}"


# ---------------------------------------------------------------------------
# Content Hashing
# ---------------------------------------------------------------------------

def content_hash(data: str) -> str:
    """Return SHA-256 hex digest of the given string."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Index (data/index.json)
# ---------------------------------------------------------------------------

def load_index() -> dict:
    """Load the processing index from data/index.json."""
    index_path = config.BASE_DIR / "data" / "index.json"
    if index_path.exists():
        try:
            return json.loads(index_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load index, starting fresh: {e}")
    return {
        "raw_processed": {},
        "embeddings_version": config.EMBEDDING_MODEL,
        "last_graph_build": None,
    }


def save_index(index: dict):
    """Save the processing index to data/index.json."""
    index_path = config.BASE_DIR / "data" / "index.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.debug("Index saved.")


# ---------------------------------------------------------------------------
# Raw Capture Operations
# ---------------------------------------------------------------------------

def read_raw_captures() -> List[dict]:
    """
    List all raw capture directories and return their metadata + content.

    Returns a list of dicts:
        { "id": str, "meta": dict, "content": str, "dir": Path }
    """
    captures = []
    if not config.RAW_DIR.exists():
        return captures

    for item in sorted(config.RAW_DIR.iterdir()):
        if not item.is_dir():
            continue

        meta_path = item / "metadata.json"
        content_path = item / "content.md"

        if not meta_path.exists() or not content_path.exists():
            continue

        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            content = content_path.read_text(encoding="utf-8")
            captures.append({
                "id": meta.get("id", item.name),
                "meta": meta,
                "content": content,
                "dir": item,
            })
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to read capture {item.name}: {e}")
            continue

    return captures


# ---------------------------------------------------------------------------
# Wiki Note Operations
# ---------------------------------------------------------------------------

def write_wiki_note(note: WikiNote):
    """
    Write a WikiNote to wiki/{para}/{id}.md with YAML frontmatter.

    Frontmatter fields:
        id, raw_id, para, tags, summary, created, links, source_url
    Body: note.body (cleaned content)
    """
    para_dir = config.WIKI_DIR / note.para
    para_dir.mkdir(parents=True, exist_ok=True)

    note_path = para_dir / f"{note.id}.md"

    frontmatter = {
        "id": note.id,
        "raw_id": note.raw_id,
        "para": note.para,
        "tags": note.tags,
        "summary": note.summary,
        "created": note.created,
        "links": note.links,
        "source_url": note.source_url,
    }

    # Build markdown with YAML frontmatter
    yaml_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True, sort_keys=False)
    full_content = f"---\n{yaml_str}---\n\n{note.body}"

    note_path.write_text(full_content, encoding="utf-8")
    logger.info(f"Written wiki note: {note_path}")


def read_wiki_notes() -> List[WikiNote]:
    """
    Parse all wiki markdown files from wiki/{para}/*.md.

    Returns a list of WikiNote objects.
    """
    notes = []
    if not config.WIKI_DIR.exists():
        return notes

    for para in config.PARA_CATEGORIES:
        para_dir = config.WIKI_DIR / para
        if not para_dir.exists():
            continue
        for md_file in para_dir.glob("*.md"):
            try:
                note = parse_wiki_md(md_file)
                if note:
                    notes.append(note)
            except Exception as e:
                logger.warning(f"Failed to parse {md_file}: {e}")
                continue

    return notes


def parse_wiki_md(md_path: Path) -> Optional[WikiNote]:
    """
    Parse a single wiki markdown file with YAML frontmatter.
    Returns a WikiNote or None on failure.
    """
    content = md_path.read_text(encoding="utf-8")

    # Split frontmatter and body
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", content, re.DOTALL)
    if not match:
        logger.warning(f"No valid frontmatter in {md_path}")
        return None

    yaml_str = match.group(1)
    body = match.group(2).strip()

    try:
        fm = yaml.safe_load(yaml_str)
    except yaml.YAMLError as e:
        logger.warning(f"YAML parse error in {md_path}: {e}")
        return None

    if not isinstance(fm, dict):
        return None

    return WikiNote(
        id=fm.get("id", md_path.stem),
        raw_id=fm.get("raw_id", ""),
        para=fm.get("para", "Resources"),
        tags=fm.get("tags", []),
        summary=fm.get("summary", ""),
        created=fm.get("created", ""),
        links=fm.get("links", []),
        body=body,
        source_url=fm.get("source_url", ""),
    )


def get_wiki_path(note_id: str) -> Optional[Path]:
    """Find the wiki file path for a given note ID across all PARA categories."""
    for para in config.PARA_CATEGORIES:
        para_dir = config.WIKI_DIR / para
        note_path = para_dir / f"{note_id}.md"
        if note_path.exists():
            return note_path
    return None

