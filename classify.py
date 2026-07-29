"""
Sub-Phase 2.1 — Auto-Classify (The Librarian)

Transforms unprocessed raw/ captures into structured wiki/ notes with
PARA categorization, tags, and summary using the Groq LLM.

Usage:
    python classify.py                 # Classify all unprocessed captures
    python classify.py --dry-run       # Show what would be processed without writing
    python classify.py --reprocess     # Re-process all captures (overwrite existing)
"""

import datetime
import logging
import sys
from pathlib import Path

# Ensure the project root is on sys.path for imports
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import config
from lib.extract import extract_text
from lib.llm import classify_content
from lib.models import WikiNote
from lib.storage import (
    load_index,
    read_raw_captures,
    save_index,
    write_wiki_note,
    content_hash,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def classify_capture(raw_item: dict) -> WikiNote:
    """
    Classify a single raw capture into a WikiNote.

    Steps:
        1. Extract text from the raw capture
        2. Call LLM to get PARA category, tags, and summary
        3. Build and return a WikiNote

    Args:
        raw_item: dict with keys 'id', 'meta', 'content', 'dir'

    Returns:
        WikiNote object ready to be written
    """
    raw_dir = raw_item["dir"]
    meta = raw_item["meta"]
    capture_id = meta.get("id", "")

    logger.info(f"Extracting text from: {raw_dir.name}")

    # Extract text for LLM classification
    extracted_text = extract_text(raw_dir)

    if not extracted_text or not extracted_text.strip():
        logger.warning(f"No extractable text in {raw_dir.name}, using minimal content")
        extracted_text = raw_item.get("content", "")

    if not extracted_text.strip():
        logger.warning(f"Empty content in {raw_dir.name}, skipping")
        return None

    # Call LLM to classify
    logger.info(f"Classifying: {raw_dir.name} ({len(extracted_text)} chars)")
    classification = classify_content(extracted_text)

    para = classification.get("para", "Resources")
    tags = classification.get("tags", [])
    summary = classification.get("summary", "")

    # Generate a short wiki ID from the full capture UUID
    wiki_id = capture_id.split("-")[0] if capture_id else raw_dir.name[-8:]

    # Get timestamp from metadata
    created = meta.get("timestamp", datetime.datetime.now(datetime.timezone.utc).isoformat())

    # Body is the extracted text (cleaned)
    body = extracted_text.strip()

    # Extract source URL from raw capture metadata (for link/web captures)
    source_url = meta.get("url", "")

    note = WikiNote(
        id=wiki_id,
        raw_id=raw_dir.name,
        para=para,
        tags=tags,
        summary=summary,
        created=created,
        links=[],
        body=body,
        source_url=source_url,
    )

    logger.info(f"  → {para} | tags: {tags} | summary: {summary[:80]}...")
    return note


def run(dry_run: bool = False, reprocess: bool = False) -> int:
    """
    Main classification pipeline.

    Args:
        dry_run: If True, show what would be processed without writing files.
        reprocess: If True, re-process all captures even if already processed.

    Returns:
        Number of newly classified notes.
    """
    config.ensure_directories_exist()
    index = load_index()
    raw_captures = read_raw_captures()

    if not raw_captures:
        logger.info("No raw captures found in raw/ directory.")
        return 0

    processed_count = 0
    skipped_count = 0

    # Get set of already processed raw IDs
    raw_processed = index.get("raw_processed", {})

    for raw_item in raw_captures:
        raw_dir_name = raw_item["dir"].name
        meta = raw_item["meta"]
        capture_id = meta.get("id", "")

        # Check if already processed
        already_processed = raw_dir_name in raw_processed or capture_id in raw_processed

        if already_processed and not reprocess:
            logger.debug(f"Skipping already processed: {raw_dir_name}")
            skipped_count += 1
            continue

        # Classify
        note = classify_capture(raw_item)
        if note is None:
            skipped_count += 1
            continue

        if dry_run:
            logger.info(f"[DRY RUN] Would write: wiki/{note.para}/{note.id}.md")
            logger.info(f"  Summary: {note.summary}")
            logger.info(f"  Tags: {note.tags}")
        else:
            # Write the wiki note
            write_wiki_note(note)

            # Update index
            raw_processed[raw_dir_name] = {
                "wiki_id": note.id,
                "classified_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "content_hash": content_hash(note.body),
            }
            # Also index by the full capture UUID
            if capture_id and capture_id != raw_dir_name:
                raw_processed[capture_id] = raw_processed[raw_dir_name]

        processed_count += 1

    # Save updated index
    if not dry_run and processed_count > 0:
        index["raw_processed"] = raw_processed
        save_index(index)

    # Summary
    logger.info("=" * 50)
    logger.info(f"Classification complete.")
    logger.info(f"  Total raw captures found: {len(raw_captures)}")
    logger.info(f"  Newly classified: {processed_count}")
    logger.info(f"  Skipped (already processed): {skipped_count}")
    if dry_run:
        logger.info(f"  [DRY RUN — No files were written]")

    return processed_count


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Classify raw captures into organized wiki notes with PARA categories."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without writing any files.",
    )
    parser.add_argument(
        "--reprocess",
        action="store_true",
        help="Re-process all captures, overwriting existing wiki notes.",
    )
    args = parser.parse_args()

    try:
        count = run(dry_run=args.dry_run, reprocess=args.reprocess)
        if count == 0:
            print("No new captures to classify.")
        else:
            print(f"✓ Successfully classified {count} capture(s).")
            print(f"  → wiki/ organized by PARA: {', '.join(config.PARA_CATEGORIES)}")
    except Exception as e:
        logger.error(f"Classification failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

