"""
View all embeddings stored in data/embeddings.pkl.

Displays each note's embedding vector (first 8 dimensions preview),
vector shape, text hash, and the linked wiki note summary.

Usage:
    python view_embeddings.py              # Full view
    python view_embeddings.py --summary    # Compact summary only
    python view_embeddings.py --note 0ccfe113  # Single note
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import numpy as np
from lib.embeddings import load_embeddings, EMBEDDINGS_PATH
from lib.storage import read_wiki_notes


def view_all():
    """Display all stored embeddings with details."""
    embeddings_dict = load_embeddings()
    notes_map = {n.id: n for n in read_wiki_notes()}

    if not embeddings_dict:
        print("No embeddings found in data/embeddings.pkl")
        return

    print(f"Embeddings file: {EMBEDDINGS_PATH}")
    print(f"Total embeddings: {len(embeddings_dict)}")
    print("=" * 70)

    for note_id, data in embeddings_dict.items():
        embedding = data.get("embedding")
        text_hash = data.get("text_hash", "N/A")[:12] + "..."

        note = notes_map.get(note_id)
        summary = note.summary if note else "(no wiki note found)"
        para = note.para if note else "?"
        tags = note.tags if note else []

        print(f"\n[{para}] {note_id}")
        print(f"  Summary: {summary}")
        print(f"  Tags: {tags}")
        print(f"  Text hash: {text_hash}")

        if embedding is not None:
            vec = np.array(embedding)
            print(f"  Vector shape: {vec.shape}")
            print(f"  Vector dtype: {vec.dtype}")
            print(f"  Norm: {np.linalg.norm(vec):.6f}")
            print(f"  First 8 values: {vec[:8].tolist()}")
            print(f"  Min: {vec.min():.6f}  Max: {vec.max():.6f}  Mean: {vec.mean():.6f}")
        else:
            print("  Embedding: MISSING")

    print("\n" + "=" * 70)
    print(f"Total embeddings stored: {len(embeddings_dict)}")


def view_summary():
    """Compact view — just note ID and embedding stats."""
    embeddings_dict = load_embeddings()
    notes_map = {n.id: n for n in read_wiki_notes()}

    print(f"{'Note ID':<12} {'PARA':<12} {'Summary':<50} {'Dim':<6} {'Norm':<10}")
    print("-" * 90)

    for note_id, data in embeddings_dict.items():
        embedding = data.get("embedding")
        note = notes_map.get(note_id)
        summary = (note.summary[:47] + "...") if note and len(note.summary) > 47 else (note.summary if note else "?")
        para = note.para if note else "?"

        if embedding is not None:
            vec = np.array(embedding)
            dims = vec.shape[0]
            norm = f"{np.linalg.norm(vec):.4f}"
        else:
            dims = 0
            norm = "N/A"

        print(f"{note_id:<12} {para:<12} {summary:<50} {dims:<6} {norm:<10}")


def view_note(note_id: str):
    """View embedding for a specific note."""
    embeddings_dict = load_embeddings()
    notes_map = {n.id: n for n in read_wiki_notes()}

    data = embeddings_dict.get(note_id)
    if not data:
        print(f"Note '{note_id}' not found in embeddings.")
        print(f"Available IDs: {', '.join(sorted(embeddings_dict.keys()))}")
        return

    note = notes_map.get(note_id)

    print(f"Note: {note_id}")
    if note:
        print(f"  PARA: {note.para}")
        print(f"  Summary: {note.summary}")
        print(f"  Tags: {note.tags}")
        print(f"  Links: {note.links}")

    embedding = data.get("embedding")
    text_hash = data.get("text_hash", "N/A")

    print(f"\n  Text hash: {text_hash}")

    if embedding is not None:
        vec = np.array(embedding)
        print(f"  Dimensions: {vec.shape[0]}")
        print(f"  Norm: {np.linalg.norm(vec):.6f}")
        print(f"  Full vector ({vec.shape[0]} values):")
        # Print in rows of 16 for readability
        for i in range(0, len(vec), 16):
            row = vec[i:i+16]
            print(f"    [{i:3d}-{i+len(row)-1:3d}]: " + " ".join(f"{v:+.6f}" for v in row))


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="View embeddings stored in data/embeddings.pkl"
    )
    parser.add_argument("--summary", "-s", action="store_true",
                        help="Show compact summary table")
    parser.add_argument("--note", "-n", type=str, default=None,
                        help="Show full embedding for a specific note ID")

    args = parser.parse_args()

    if args.note:
        view_note(args.note)
    elif args.summary:
        view_summary()
    else:
        view_all()


if __name__ == "__main__":
    main()
