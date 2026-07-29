"""
Search across all wiki notes by keyword.

Usage:
    python search.py <keyword>
    python search.py "machine learning"
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from lib.storage import read_wiki_notes


def search(keyword: str):
    """Search all wiki notes for a keyword in summary, body, or tags."""
    notes = read_wiki_notes()
    keyword_lower = keyword.lower()
    results = []

    for n in notes:
        if (keyword_lower in n.summary.lower() or
            keyword_lower in n.body.lower() or
            keyword_lower in str(n.tags).lower() or
            keyword_lower in n.id.lower()):
            results.append(n)

    print(f"Searching wiki notes for: \"{keyword}\"")
    print(f"Found {len(results)} matching note(s)\n")

    for n in results:
        # Get a snippet of body where keyword appears
        body_lower = n.body.lower()
        idx = body_lower.find(keyword_lower)
        snippet = ""
        if idx >= 0:
            start = max(0, idx - 40)
            end = min(len(n.body), idx + len(keyword) + 40)
            snippet = n.body[start:end].replace('\n', ' ')
            if start > 0:
                snippet = "..." + snippet
            if end < len(n.body):
                snippet = snippet + "..."
        else:
            snippet = n.body[:80].replace('\n', ' ')

        print(f"[{n.para}] {n.id}")
        print(f"  Summary: {n.summary}")
        print(f"  Tags: {n.tags}")
        print(f"  Match: {snippet}")
        if n.links:
            print(f"  Links: {n.links}")
        print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python search.py <keyword>")
        print("Example: python search.py python")
        print("         python search.py \"machine learning\"")
        sys.exit(1)

    keyword = " ".join(sys.argv[1:])
    search(keyword)


if __name__ == "__main__":
    main()
