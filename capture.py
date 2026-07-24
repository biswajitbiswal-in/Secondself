"""
Capture Module (Phase 1 — The Archivist)

Provides CLI and python API to capture notes, URLs, and local files,
attaching UUIDs, ISO 8601 timestamps, and metadata.
Each capture creates a dedicated folder under `raw/{folder_name}/` containing:
  - `content.md`   (Raw content body only — no frontmatter)
  - `metadata.json` (Structured JSON metadata and content)
"""

import sys
from pathlib import Path

# Auto-detect virtual environment if third-party modules are missing when invoked via system python
try:
    import frontmatter
except ImportError:
    base_dir = Path(__file__).resolve().parent
    venv_python = base_dir / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists() and sys.executable != str(venv_python):
        import subprocess
        result = subprocess.run([str(venv_python), *sys.argv])
        sys.exit(result.returncode)
    else:
        print("ERROR: Dependencies not found. Please activate the virtual environment (.venv) or run: pip install -r requirements.txt")
        sys.exit(1)

import argparse
import datetime
import json
import logging
import os
import re
import shutil
import uuid
from urllib.parse import urlparse

import requests

import config

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s capture: %(message)s")

# Restricted file extensions (executables and binary binaries)
RESTRICTED_EXTENSIONS = {
    ".exe",
    ".dll",
    ".bat",
    ".cmd",
    ".ps1",
    ".sh",
    ".msi",
    ".sys",
    ".bin",
    ".so",
    ".dylib",
    ".com",
    ".scr",
}

# Configuration caps
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_LINK_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
DEFAULT_TIMEOUT_SECONDS = 10


def generate_id() -> str:
    """Generate a UUID4 string ID."""
    return str(uuid.uuid4())


def generate_timestamp() -> tuple[str, datetime.datetime]:
    """Return ISO 8601 timezone-aware timestamp string and datetime object."""
    now = datetime.datetime.now(datetime.timezone.utc).astimezone()
    return now.isoformat(), now


def build_folder_name(id_str: str, dt: datetime.datetime) -> str:
    """
    Build folder name following the convention: {YYYYMMDD}_{HHMMSS}_{short_id}
    """
    date_str = dt.strftime("%Y%m%d")
    time_str = dt.strftime("%H%M%S")
    short_id = id_str.split("-")[0]
    return f"{date_str}_{time_str}_{short_id}"


def write_capture(content: str, metadata: dict, dt: datetime.datetime) -> tuple[str, Path, Path, Path]:
    """
    Create a subfolder in `raw/{folder_name}/` and save:
      1. `content.md`   (Raw content body only — no frontmatter)
      2. `metadata.json` (Structured JSON sidecar)

    Returns:
        tuple[str, Path, Path, Path]: (capture_id, capture_dir, md_path, json_path)
    """
    config.ensure_directories_exist()
    id_str = metadata["id"]
    folder_name = build_folder_name(id_str, dt)
    capture_dir = config.RAW_DIR / folder_name
    capture_dir.mkdir(parents=True, exist_ok=True)

    target_md_path = capture_dir / "content.md"
    target_json_path = capture_dir / "metadata.json"

    # Add cross-reference pointers in metadata
    metadata["metadata_file"] = "metadata.json"

    # 1. Write content.md — raw content only (no frontmatter, metadata is in metadata.json)
    target_md_path.write_text(content, encoding="utf-8")

    # 2. Write metadata.json
    json_record = {
        "id": metadata.get("id"),
        "timestamp": metadata.get("timestamp"),
        "type": metadata.get("type"),
        "source": metadata.get("source"),
        "content_file": "content.md",
        "metadata_file": "metadata.json",
        "url": metadata.get("url"),
        "original_filename": metadata.get("original_filename"),
        "content": content,
    }
    target_json_path.write_text(json.dumps(json_record, indent=2, ensure_ascii=False), encoding="utf-8")

    logging.info(f"Saved capture to {capture_dir}")
    return id_str, capture_dir, target_md_path, target_json_path


def sync_captures_to_folder_structure() -> int:
    """
    Migrate any flat captures in `raw/` into dedicated subfolders `raw/{folder_name}/`
    containing `content.md` and `metadata.json`.
    """
    config.ensure_directories_exist()

    # Delete legacy aggregated JSON if present
    legacy_json = config.RAW_DIR / "captures.json"
    if legacy_json.exists():
        legacy_json.unlink()

    count = 0
    # Process any flat .md files in raw/
    flat_md_files = [f for f in config.RAW_DIR.glob("*.md") if f.is_file()]
    for md_path in flat_md_files:
        folder_name = md_path.stem
        capture_dir = config.RAW_DIR / folder_name
        capture_dir.mkdir(parents=True, exist_ok=True)

        target_md = capture_dir / "content.md"
        target_json = capture_dir / "metadata.json"

        try:
            post = frontmatter.load(md_path)
            post.metadata["metadata_file"] = "metadata.json"
            # Write only the raw content body to content.md (no frontmatter)
            target_md.write_text(post.content, encoding="utf-8")

            record = {
                "id": post.metadata.get("id"),
                "timestamp": str(post.metadata.get("timestamp")),
                "type": post.metadata.get("type"),
                "source": post.metadata.get("source"),
                "content_file": "content.md",
                "metadata_file": "metadata.json",
                "url": post.metadata.get("url"),
                "original_filename": post.metadata.get("original_filename"),
                "content": post.content,
            }
            target_json.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")

            # Remove old flat files
            md_path.unlink()
            old_flat_json = md_path.with_suffix(".json")
            if old_flat_json.exists():
                old_flat_json.unlink()

            count += 1
        except Exception as e:
            logging.warning(f"Failed to migrate flat capture {md_path.name}: {e}")

    # Count all subdirectories in raw/
    total_subdirs = len([d for d in config.RAW_DIR.iterdir() if d.is_dir()])
    logging.info(f"Synchronized folder structure for {total_subdirs} captures in raw/.")
    return total_subdirs


def capture_note(text: str) -> tuple[str, Path, Path, Path]:
    """
    Capture plain text note and save to raw/{folder_name}/ (content.md & metadata.json).

    Returns:
        tuple[str, Path, Path, Path]: (capture_id, capture_dir, md_path, json_path)
    """
    text = text.strip()
    if not text:
        raise ValueError("Note content cannot be empty.")

    capture_id = generate_id()
    iso_timestamp, dt = generate_timestamp()

    metadata = {
        "id": capture_id,
        "timestamp": iso_timestamp,
        "type": "note",
        "source": "cli",
    }

    return write_capture(text, metadata, dt)


def capture_link(url: str) -> tuple[str, Path, Path, Path]:
    """
    Fetch URL web page content and save to raw/{folder_name}/ (content.md & metadata.json).

    Returns:
        tuple[str, Path, Path, Path]: (capture_id, capture_dir, md_path, json_path)
    """
    url = url.strip()
    parsed = urlparse(url)
    if not parsed.scheme or parsed.scheme not in ("http", "https"):
        raise ValueError(f"Invalid URL scheme: '{url}'. Must start with http:// or https://")

    capture_id = generate_id()
    iso_timestamp, dt = generate_timestamp()

    headers = {
        "User-Agent": "SecondSelf-Capture/1.0 (+https://github.com/secondself)"
    }

    try:
        response = requests.get(
            url, headers=headers, timeout=DEFAULT_TIMEOUT_SECONDS, stream=True
        )
        response.raise_for_status()

        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > MAX_LINK_SIZE_BYTES:
            raise ValueError(
                f"URL content size ({content_length} bytes) exceeds maximum limit ({MAX_LINK_SIZE_BYTES} bytes)."
            )

        content_bytes = bytearray()
        for chunk in response.iter_content(chunk_size=8192):
            content_bytes.extend(chunk)
            if len(content_bytes) > MAX_LINK_SIZE_BYTES:
                raise ValueError(
                    f"Downloaded content from '{url}' exceeded maximum size limit of {MAX_LINK_SIZE_BYTES} bytes."
                )

        encoding = response.encoding or "utf-8"
        try:
            page_text = content_bytes.decode(encoding, errors="replace")
        except Exception:
            page_text = content_bytes.decode("utf-8", errors="replace")

    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch URL '{url}': {e}") from e

    metadata = {
        "id": capture_id,
        "timestamp": iso_timestamp,
        "type": "link",
        "source": "url",
        "url": url,
    }

    return write_capture(page_text, metadata, dt)


def capture_file(file_path: str) -> tuple[str, Path, Path, Path]:
    """
    Read local file content and save to raw/{folder_name}/ (content.md & metadata.json).

    Returns:
        tuple[str, Path, Path, Path]: (capture_id, capture_dir, md_path, json_path)
    """
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    if not path.is_file():
        raise ValueError(f"Path is not a regular file: {file_path}")

    ext = path.suffix.lower()
    if ext in RESTRICTED_EXTENSIONS:
        raise ValueError(f"Executable/binary extension '{ext}' is not allowed for capture.")

    file_size = path.stat().st_size
    if file_size > MAX_FILE_SIZE_BYTES:
        raise ValueError(
            f"File size ({file_size} bytes) exceeds maximum limit of {MAX_FILE_SIZE_BYTES} bytes (10 MB)."
        )

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        raise RuntimeError(f"Failed to read file '{path}': {e}") from e

    capture_id = generate_id()
    iso_timestamp, dt = generate_timestamp()

    metadata = {
        "id": capture_id,
        "timestamp": iso_timestamp,
        "type": "file",
        "source": "filepath",
        "original_filename": path.name,
    }

    return write_capture(content, metadata, dt)


def show_capture(query_id: str):
    """Find and display capture details for a given capture ID or short ID prefix."""
    config.ensure_directories_exist()
    query_id = query_id.strip().lower()

    matched_dir = None
    for item in config.RAW_DIR.iterdir():
        if item.is_dir():
            if query_id in item.name.lower():
                matched_dir = item
                break
            meta_json = item / "metadata.json"
            if meta_json.exists():
                try:
                    data = json.loads(meta_json.read_text(encoding="utf-8"))
                    if str(data.get("id", "")).lower().startswith(query_id):
                        matched_dir = item
                        break
                except Exception:
                    continue

    if not matched_dir:
        print(f"No capture found matching ID: '{query_id}'")
        return

    target_md = matched_dir / "content.md"
    target_json = matched_dir / "metadata.json"

    print("=" * 60)
    print(f"CAPTURE DETAILS [Folder: {matched_dir.name}]")
    print("=" * 60)
    print(f"Folder        : {matched_dir}")
    print(f"Content (.md) : {target_md}")
    print(f"JSON (.json)  : {target_json}")

    if target_json.exists():
        try:
            data = json.loads(target_json.read_text(encoding="utf-8"))
            print("-" * 60)
            print(f"ID       : {data.get('id')}")
            print(f"Type     : {data.get('type')}")
            print(f"Source   : {data.get('source')}")
            print(f"Created  : {data.get('timestamp')}")
            if data.get("url"):
                print(f"URL      : {data.get('url')}")
            if data.get("original_filename"):
                print(f"File     : {data.get('original_filename')}")
            print("-" * 60)
            print("CONTENT PREVIEW:")
            print(data.get("content", "")[:300])
        except Exception as e:
            print(f"Error reading JSON: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="SecondSelf Capture CLI — Ingest text notes, URLs, or local files into raw/"
    )
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument("text", nargs="?", help="Text note content to capture")
    group.add_argument("--link", help="URL of webpage to fetch and capture")
    group.add_argument("--file", help="Path of local file to capture")
    group.add_argument("--show", help="Display content.md and metadata.json file paths for a capture ID")
    parser.add_argument("--sync-json", action="store_true", help="Organize raw captures into subfolders")

    args = parser.parse_args()

    try:
        if args.show:
            show_capture(args.show)
        elif args.sync_json:
            count = sync_captures_to_folder_structure()
            print(f"Organized folder structure for {count} captures.")
        elif args.link:
            cid, cap_dir, md_path, json_path = capture_link(args.link)
            print(f"Captured link successfully!")
            print(f"ID       : {cid}")
            print(f"Folder   : {cap_dir}")
            print(f"Markdown : {md_path}")
            print(f"JSON     : {json_path}")
        elif args.file:
            cid, cap_dir, md_path, json_path = capture_file(args.file)
            print(f"Captured file successfully!")
            print(f"ID       : {cid}")
            print(f"Folder   : {cap_dir}")
            print(f"Markdown : {md_path}")
            print(f"JSON     : {json_path}")
        elif args.text:
            cid, cap_dir, md_path, json_path = capture_note(args.text)
            print(f"Captured note successfully!")
            print(f"ID       : {cid}")
            print(f"Folder   : {cap_dir}")
            print(f"Markdown : {md_path}")
            print(f"JSON     : {json_path}")
        else:
            count = sync_captures_to_folder_structure()
            print(f"Organized folder structure for {count} captures.")
    except Exception as e:
        logging.error(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
