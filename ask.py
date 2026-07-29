"""
Sub-Phase 4.1 — Ask Your Brain (The Oracle)

RAG (Retrieval-Augmented Generation) Q&A engine for SecondSelf.
Answers questions in plain English by retrieving relevant notes from the
personal knowledge base and synthesizing them via Groq LLM.

Pipeline:
  1. Embed the question (lib/embeddings.py)
  2. Retrieve top-K notes by cosine similarity from embeddings.pkl
  3. Load full wiki bodies for retrieved IDs
  4. Build RAG prompt with note context
  5. Call synthesize_answer() via lib/llm.py
  6. Return AskResult with answer + sources

Usage:
    python ask.py "What are my career goals?"
    python ask.py "What ML resources have I saved?" --top-k 3
    python ask.py "Summarize my active projects" --json
    python ask.py "What's in my archives?" --threshold 0.6
"""

import json
import logging
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

# Ensure project root is on sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import config
from lib.embeddings import (
    cosine_similarity,
    embed_text,
    get_all_embedding_vectors,
    load_embeddings,
)
from lib.llm import synthesize_answer
from lib.models import AskResult
from lib.storage import get_wiki_path, parse_wiki_md, read_wiki_notes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core RAG Pipeline
# ---------------------------------------------------------------------------

def retrieve_notes(
    question: str,
    top_k: int = 5,
    threshold: float = 0.35,
) -> List[dict]:
    """
    Retrieve the top-K most relevant notes for a question using embedding similarity.

    Steps:
        1. Embed the question
        2. Load all note embeddings
        3. Compute cosine similarity against all notes
        4. Sort by similarity and return top-K

    Args:
        question: The user's question as plain text.
        top_k: Number of top notes to retrieve (default: 5).
        threshold: Minimum similarity score (0.0 = no minimum).

    Returns:
        List of dicts with keys:
            - id: note ID
            - summary: note summary
            - para: PARA category
            - relevance_score: cosine similarity (0.0 to 1.0)
            - body: full note body content
    """
    # Embed the question
    logger.info(f"Embedding question: \"{question}\"")
    question_embedding = embed_text(question)

    # Get all note IDs and embeddings
    note_ids, embedding_matrix = get_all_embedding_vectors()

    if len(note_ids) == 0:
        logger.warning("No embeddings found. Run 'python pipeline.py link' first.")
        return []

    logger.info(f"Comparing against {len(note_ids)} notes...")

    # Compute cosine similarity against all notes
    similarities = []
    for i, note_id in enumerate(note_ids):
        sim = cosine_similarity(question_embedding, embedding_matrix[i])
        if sim >= threshold:
            similarities.append((note_id, sim))

    # Sort by similarity (highest first)
    similarities.sort(key=lambda x: x[1], reverse=True)

    # Take top-K
    top_results = similarities[:top_k]

    if not top_results:
        logger.info("No notes above threshold.")
        return []

    logger.info(f"Top {len(top_results)} results: "
                f"{', '.join(f'{nid} ({sim:.3f})' for nid, sim in top_results)}")

    # Load full note bodies
    notes_map = {}
    all_notes = read_wiki_notes()
    for note in all_notes:
        notes_map[note.id] = note

    # Build result list
    retrieved = []
    for note_id, sim_score in top_results:
        note = notes_map.get(note_id)
        if note is None:
            # Fallback: try to load from file directly
            note_path = get_wiki_path(note_id)
            if note_path:
                note = parse_wiki_md(note_path)

        if note is None:
            logger.warning(f"Could not load note '{note_id}', skipping.")
            continue

        retrieved.append({
            "id": note.id,
            "summary": note.summary,
            "para": note.para,
            "relevance_score": round(float(sim_score), 4),
            "body": note.body,
            "source_url": note.source_url,
        })

    logger.info(f"Successfully loaded {len(retrieved)} notes.")
    return retrieved


def build_rag_context(retrieved_notes: List[dict], max_chars: int = 6000) -> str:
    """
    Build the RAG context string from retrieved notes.

    Formats each note with its ID, summary, PARA category, and body.
    Truncates total context to avoid token limits.

    Args:
        retrieved_notes: List of note dicts from retrieve_notes().
        max_chars: Maximum total characters for the context (default: 6000).

    Returns:
        Formatted context string for the LLM prompt.
    """
    if not retrieved_notes:
        return ""

    context_parts = []
    total_chars = 0

    for i, note in enumerate(retrieved_notes):
        # Format note header with relevance score
        score = note.get("relevance_score", 0)
        relevance_label = "HIGH" if score >= 0.6 else ("MEDIUM" if score >= 0.35 else "LOW")
        header = (
            f"[Note {i + 1}] ID: {note['id']} | Category: {note['para']} "
            f"| Relevance: {relevance_label} ({score:.2f}) | Summary: {note['summary']}"
        )
        body = note.get("body", "").strip()

        # Truncate body if needed — keep first 1500 chars per note
        body_truncated = body[:1500]
        if len(body) > 1500:
            body_truncated += "\n[...]"

        note_block = f"{header}\n{body_truncated}"

        # Check if adding this note would exceed max_chars
        if total_chars + len(note_block) > max_chars:
            remaining = max_chars - total_chars
            if remaining > 200:
                # Add as much as we can
                note_block = note_block[:remaining] + "\n[...truncated]"
                context_parts.append(note_block)
            break

        context_parts.append(note_block)
        total_chars += len(note_block)

    return "\n\n---\n\n".join(context_parts)


def ask(question: str, top_k: int = 5, threshold: float = 0.35) -> AskResult:
    """
    Answer a question using the RAG pipeline.

    Full pipeline:
        1. Retrieve top-K relevant notes
        2. Build RAG context string
        3. Call LLM to synthesize answer
        4. Return structured AskResult with answer + sources

    Args:
        question: The user's question in plain English.
        top_k: Number of notes to retrieve (default: 5).
        threshold: Minimum similarity threshold (0.0 = no minimum).

    Returns:
        AskResult with answer text and list of source dicts.
    """
    if not question or not question.strip():
        return AskResult(
            answer="Please ask a question.",
            sources=[],
        )

    logger.info(f"=" * 60)
    logger.info(f"  ASK YOUR BRAIN")
    logger.info(f"  Question: \"{question}\"")
    logger.info(f"  top_k={top_k}, threshold={threshold}")
    logger.info(f"=" * 60)

    # Step 1 & 2: Retrieve relevant notes
    retrieved_notes = retrieve_notes(question, top_k=top_k, threshold=threshold)

    # Step 3: Build RAG context
    if retrieved_notes:
        context = build_rag_context(retrieved_notes, max_chars=6000)

        logger.info(f"Building RAG context ({len(context)} chars)...")
        logger.info(f"Notes in context: {len(retrieved_notes)}")

        # Step 4: Call LLM to synthesize answer
        logger.info("Calling LLM to synthesize answer...")
        answer_text = synthesize_answer(context=context, question=question)
    else:
        logger.info("No relevant notes found.")
        answer_text = "I don't have any notes about that."

    # Step 5: Build source list
    sources = []
    for note in retrieved_notes:
        sources.append({
            "id": note["id"],
            "summary": note["summary"],
            "relevance_score": note["relevance_score"],
            "para": note["para"],
            "source_url": note.get("source_url", ""),
        })

    result = AskResult(answer=answer_text, sources=sources)

    logger.info(f"=" * 60)
    logger.info(f"  ANSWER GENERATED")
    logger.info(f"  Sources: {len(sources)}")
    logger.info(f"  Answer: {answer_text[:150]}...")
    logger.info(f"=" * 60)

    return result


# ---------------------------------------------------------------------------
# CLI Interface
# ---------------------------------------------------------------------------

def print_result(result: AskResult, json_output: bool = False):
    """
    Print the AskResult to stdout in human-readable or JSON format.

    Args:
        result: The AskResult to display.
        json_output: If True, print as JSON instead of formatted text.
    """
    if json_output:
        print(json.dumps({
            "answer": result.answer,
            "sources": result.sources,
        }, indent=2, ensure_ascii=False))
        return

    # Human-readable output
    print()
    print("=" * 70)
    print("  🧠  ANSWER")
    print("=" * 70)
    print()
    print(result.answer)
    print()

    if result.sources:
        print("-" * 70)
        print(f"  SOURCES ({len(result.sources)})")
        print("-" * 70)
        for i, src in enumerate(result.sources):
            relevance_label = "⭐ HIGH" if src.get("relevance_score", 0) >= 0.6 else ("📌 MEDIUM" if src.get("relevance_score", 0) >= 0.35 else "🔹 LOW")
            print(f"  [{i + 1}] {src['id']}  [{src['para']}]  {relevance_label}")
            print(f"       {src['summary']}")
            print(f"       Relevance: {src['relevance_score']:.3f}")
            print()
    else:
        print("(No sources — answer was generated without reference notes)")
        print()

    print("=" * 70)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Ask your SecondSelf knowledge brain a question in plain English.",
    )
    parser.add_argument(
        "question",
        type=str,
        nargs="?",
        help="Your question (in quotes). If omitted, enters interactive mode.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=config.TOP_K_RETRIEVAL,
        help=f"Number of notes to retrieve (default: {config.TOP_K_RETRIEVAL}).",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.0,
        help="Minimum similarity threshold (0.0-1.0, default: 0.0 = no minimum).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON.",
    )

    args = parser.parse_args()

    try:
        if args.question:
            # Single question mode
            result = ask(
                question=args.question,
                top_k=args.top_k,
                threshold=args.threshold,
            )
            print_result(result, json_output=args.json)
        else:
            # Interactive mode
            print("🧠  SecondSelf — Ask Your Brain")
            print("Type your questions or 'quit' to exit.\n")
            while True:
                try:
                    q = input("❓ ").strip()
                    if not q:
                        continue
                    if q.lower() in ("quit", "exit", "q"):
                        print("Goodbye!")
                        break
                    result = ask(question=q, top_k=args.top_k, threshold=args.threshold)
                    print_result(result, json_output=args.json)
                    print()
                except KeyboardInterrupt:
                    print("\nGoodbye!")
                    break

    except Exception as e:
        logger.error(f"Ask failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

