"""
Sub-Phase 2.2 — Auto-Link (The Librarian)

Computes embeddings for all wiki notes and auto-links related notes based on
cosine similarity. Adds bidirectional links to frontmatter links[] and
[[note-id]] wikilinks in body text.

Usage:
    python link.py                     # Link all unlinked / changed notes
    python link.py --dry-run           # Show what would be linked without writing
    python link.py --reprocess         # Re-link all notes (overwrite existing links)
    python link.py --threshold 0.80    # Use custom similarity threshold
"""

import datetime
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import numpy as np

# Ensure project root is on sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import config
from lib.embeddings import (
    cosine_similarity,
    embed_text,
    get_text_for_embedding,
    load_embeddings,
    save_embeddings,
    text_hash,
)
from lib.models import WikiNote
from lib.storage import (
    load_index,
    read_wiki_notes,
    save_index,
    write_wiki_note,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def build_note_embedding_key(note: WikiNote) -> str:
    """
    Build the text to embed for similarity comparison.

    Uses summary + body to create a rich semantic representation.

    Args:
        note: WikiNote object.

    Returns:
        Text string for embedding.
    """
    return get_text_for_embedding(note)


def compute_links_for_note(
    note_id: str,
    note_embedding: np.ndarray,
    all_ids: List[str],
    all_embeddings: np.ndarray,
    threshold: float,
) -> List[Tuple[str, float]]:
    """
    Compute all links for a single note against all other notes.

    Args:
        note_id: The note's ID (to exclude self-comparison).
        note_embedding: Embedding vector for this note.
        all_ids: List of all note IDs in the embedding index.
        all_embeddings: Matrix of all embedding vectors.
        threshold: Similarity threshold (0.0-1.0).

    Returns:
        List of (target_id, similarity) tuples above threshold.
    """
    links = []

    for i, other_id in enumerate(all_ids):
        if other_id == note_id:
            continue  # Skip self

        similarity = cosine_similarity(note_embedding, all_embeddings[i])

        if similarity >= threshold:
            links.append((other_id, float(similarity)))

    # Sort by similarity (highest first)
    links.sort(key=lambda x: x[1], reverse=True)
    return links


def update_note_links(
    note: WikiNote,
    new_links: List[Tuple[str, float]],
    all_notes_map: Dict[str, WikiNote],
) -> bool:
    """
    Update a wiki note with new links, avoiding duplicates.

    Adds to frontmatter links[] and appends [[other-id]] wikilinks in body.
    Maintains existing links that are not being replaced.

    Args:
        note: The WikiNote to update.
        new_links: List of (target_id, similarity) tuples.
        all_notes_map: Map of note_id -> WikiNote for all notes.

    Returns:
        True if the note was modified, False otherwise.
    """
    modified = False

    # Collect existing link IDs (from frontmatter)
    existing_links: Set[str] = set(note.links)

    # Also check body for [[id]] patterns
    import re
    body_wikilinks = set(re.findall(r'\[\[([^\]]+)\]\]', note.body))
    existing_links.update(body_wikilinks)

    # Add new links
    new_link_ids = []
    for target_id, similarity in new_links:
        if target_id not in existing_links:
            new_link_ids.append(target_id)
            existing_links.add(target_id)
            modified = True

    if not modified:
        return False

    # Update frontmatter links
    note.links = sorted(existing_links)

    # Append new wikilinks to body
    new_wikilinks_md = "\n\n## Related Notes\n"
    for target_id in new_link_ids:
        # Get target note info for context
        target_note = all_notes_map.get(target_id)
        if target_note:
            new_wikilinks_md += f"- [[{target_id}]] — {target_note.summary or '(no summary)'}\n"
        else:
            new_wikilinks_md += f"- [[{target_id}]]\n"

    # Check if "Related Notes" section already exists
    if "## Related Notes" in note.body:
        # Replace existing section
        import re
        note.body = re.sub(
            r"\n*## Related Notes\n.*?(?=\n## |\Z)",
            new_wikilinks_md.rstrip(),
            note.body,
            flags=re.DOTALL,
        )
    else:
        note.body += new_wikilinks_md

    return modified


def run(
    dry_run: bool = False,
    reprocess: bool = False,
    threshold: Optional[float] = None,
) -> int:
    """
    Main auto-link pipeline.

    Steps:
        1. Load all wiki notes
        2. Load existing embeddings
        3. For each note, compute or retrieve its embedding
        4. Compare all notes pairwise
        5. Add links for pairs above threshold
        6. Save updated notes and embeddings

    Args:
        dry_run: If True, show what would be linked without writing.
        reprocess: If True, re-link all notes (overwrite existing links).
        threshold: Custom similarity threshold (defaults to config.SIMILARITY_THRESHOLD).

    Returns:
        Number of new links created.
    """
    threshold = threshold or config.SIMILARITY_THRESHOLD
    logger.info(f"Auto-Link starting (threshold={threshold:.2f})")

    # Load all wiki notes
    notes = read_wiki_notes()
    if not notes:
        logger.warning("No wiki notes found to link.")
        return 0

    logger.info(f"Loaded {len(notes)} wiki notes from {config.WIKI_DIR}")

    # Build map of note_id -> note
    notes_map: Dict[str, WikiNote] = {note.id: note for note in notes}

    # Load existing embeddings
    embeddings_dict = load_embeddings()
    logger.info(f"Loaded {len(embeddings_dict)} existing embeddings from data/embeddings.pkl")

    # Compute embeddings for any notes that are missing or changed
    notes_to_embed = []
    for note in notes:
        text = build_note_embedding_key(note)
        h = text_hash(text)

        if reprocess:
            notes_to_embed.append(note)
        elif note.id not in embeddings_dict:
            notes_to_embed.append(note)
        elif embeddings_dict[note.id].get("text_hash") != h:
            notes_to_embed.append(note)

    if notes_to_embed:
        logger.info(f"Computing embeddings for {len(notes_to_embed)} notes...")
        for note in notes_to_embed:
            text = build_note_embedding_key(note)
            embedding = embed_text(text)
            embeddings_dict[note.id] = {
                "embedding": embedding,
                "text_hash": text_hash(text),
                "note_id": note.id,
            }
        logger.info(f"Embeddings computed and cached.")
    else:
        logger.info("All notes already embedded (no changes detected).")

    # Save embeddings (even if no new ones, to ensure persistence)
    if not dry_run:
        save_embeddings(embeddings_dict)

    # Build the full embedding matrix
    all_ids = list(embeddings_dict.keys())
    all_embeddings = np.array(
        [embeddings_dict[nid]["embedding"] for nid in all_ids],
        dtype=np.float32,
    )
    logger.info(f"Embedding matrix: {all_embeddings.shape}")

    # For each note, compute links to other notes
    total_links_added = 0
    linked_note_count = 0

    for note in notes:
        if note.id not in embeddings_dict:
            logger.warning(f"No embedding found for {note.id}, skipping.")
            continue

        note_embedding = embeddings_dict[note.id]["embedding"]

        # Compute links
        new_links = compute_links_for_note(
            note_id=note.id,
            note_embedding=note_embedding,
            all_ids=all_ids,
            all_embeddings=all_embeddings,
            threshold=threshold,
        )

        if not new_links:
            logger.debug(f"No links found for {note.id}")
            continue

        if dry_run:
            logger.info(
                f"[DRY RUN] {note.id} would link to {len(new_links)} notes: "
                + ", ".join(f"{tid} ({sim:.3f})" for tid, sim in new_links[:5])
            )
            total_links_added += len(new_links)
            continue

        # Update note with new links
        modified = update_note_links(note, new_links, notes_map)

        if modified:
            write_wiki_note(note)
            linked_note_count += 1
            total_links_added += len(new_links)
            logger.info(
                f"Linked {note.id} → {len(new_links)} notes "
                f"({', '.join(tid for tid, _ in new_links[:3])}{'...' if len(new_links) > 3 else ''})"
            )

    # Update index
    if not dry_run:
        index = load_index()
        index["last_link_build"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save_index(index)

    # Summary
    logger.info("=" * 50)
    logger.info(f"Auto-Link complete.")
    logger.info(f"  Notes scanned: {len(notes)}")
    logger.info(f"  Notes updated with new links: {linked_note_count}")
    logger.info(f"  Total links added: {total_links_added}")
    logger.info(f"  Threshold: {threshold:.2f}")
    if dry_run:
        logger.info("  [DRY RUN — No files were written]")

    return total_links_added


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Auto-link related wiki notes using embedding similarity."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be linked without writing any files.",
    )
    parser.add_argument(
        "--reprocess",
        action="store_true",
        help="Re-link all notes, overwriting existing link structures.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help=f"Similarity threshold (default: {config.SIMILARITY_THRESHOLD}). "
             f"Higher = fewer but more confident links.",
    )
    args = parser.parse_args()

    try:
        count = run(
            dry_run=args.dry_run,
            reprocess=args.reprocess,
            threshold=args.threshold,
        )
        if count == 0:
            print("No new links created. (All notes already linked or no matches above threshold.)")
        else:
            print(f"✓ Successfully created {count} link(s) between wiki notes.")
            print(f"  (threshold={args.threshold or config.SIMILARITY_THRESHOLD:.2f})")
    except Exception as e:
        logger.error(f"Auto-Link failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

