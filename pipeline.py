"""
SecondSelf Pipeline — Orchestrates all phases

Coordinates classification, auto-linking, graph building, and Q&A into pipeline steps.

Usage:
    python pipeline.py classify     # Classify only (Sub-Phase 2.1)
    python pipeline.py link         # Link only (Sub-Phase 2.2)
    python pipeline.py graph        # Build graph only (Sub-Phase 3.1)
    python pipeline.py process      # Classify + Link + Build Graph (full pipeline)
    python pipeline.py process --dry-run   # Dry run (no files written)
    python pipeline.py ask          # Ask your brain (Sub-Phase 4.1)
    python pipeline.py ask "What are my career goals?" --top-k 5
"""

import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_classify(dry_run: bool = False, reprocess: bool = False) -> int:
    """
    Run the classification pipeline (Sub-Phase 2.1).

    Args:
        dry_run: If True, show what would be processed without writing.
        reprocess: If True, re-process all captures.

    Returns:
        Number of newly classified notes.
    """
    try:
        from classify import run as classify_run
        return classify_run(dry_run=dry_run, reprocess=reprocess)
    except Exception as e:
        logger.error(f"Classification failed: {e}")
        return 0


def run_link(dry_run: bool = False, reprocess: bool = False) -> int:
    """
    Run the auto-link pipeline (Sub-Phase 2.2).

    Args:
        dry_run: If True, show what would be linked without writing.
        reprocess: If True, re-link all notes.

    Returns:
        Number of new links created.
    """
    try:
        from link import run as link_run
        return link_run(dry_run=dry_run, reprocess=reprocess)
    except ImportError as e:
        logger.error(f"Auto-link module not available: {e}")
        logger.error("Run 'python pipeline.py classify' first to create wiki notes.")
        return 0
    except Exception as e:
        logger.error(f"Auto-link failed: {e}")
        return 0


def run_graph(dry_run: bool = False, pretty: bool = False) -> bool:
    """
    Build the knowledge graph from wiki notes (Sub-Phase 3.1).

    Args:
        dry_run: If True, show what would be done without writing.
        pretty: If True, pretty-print the JSON output.

    Returns:
        True if the graph was built successfully.
    """
    try:
        from build_graph import run as graph_run
        graph = graph_run(pretty=pretty)
        if graph and graph["metadata"]["node_count"] > 0:
            logger.info(f"Graph built: {graph['metadata']['node_count']} nodes, {graph['metadata']['edge_count']} edges")
            return True
        elif graph:
            logger.warning("Graph built but has no nodes (no wiki notes found).")
            return True
        return False
    except ImportError as e:
        logger.error(f"Graph build module not available: {e}")
        return False
    except Exception as e:
        logger.error(f"Graph build failed: {e}")
        return False


def run_process(dry_run: bool = False, reprocess: bool = False) -> bool:
    """
    Run the full pipeline: classify + link + build graph.

    Args:
        dry_run: If True, show what would happen without writing.
        reprocess: If True, re-process everything.

    Returns:
        True if the pipeline completed successfully.
    """
    logger.info("=" * 60)
    logger.info("  PIPELINE: PROCESS START")
    logger.info(f"  Dry-run: {dry_run}")
    logger.info("=" * 60)

    config.ensure_directories_exist()

    # Step 1: Classify
    logger.info("\nSTEP 1/3: Classification")
    logger.info("-" * 40)
    classified_count = run_classify(dry_run=dry_run, reprocess=reprocess)

    # Step 2: Link
    logger.info("\nSTEP 2/3: Auto-Link")
    logger.info("-" * 40)
    link_count = run_link(dry_run=dry_run, reprocess=reprocess)

    # Step 3: Build Graph
    logger.info("\nSTEP 3/3: Build Graph")
    logger.info("-" * 40)
    graph_success = run_graph(dry_run=dry_run)

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("  PIPELINE: PROCESS COMPLETE")
    logger.info("=" * 60)
    logger.info(f"  Classified: {classified_count} note(s)")
    logger.info(f"  Links created: {link_count}")
    logger.info(f"  Graph built: {'Yes' if graph_success else 'Failed'}")
    logger.info(f"  Wiki path: {config.WIKI_DIR}")
    logger.info(f"  Total wiki notes: {count_wiki_notes()}")
    if graph_success:
        logger.info(f"  Graph output: {config.GRAPH_PATH}")
    logger.info("=" * 60)

    return True


def count_wiki_notes() -> int:
    """Count total wiki markdown files across all PARA categories."""
    count = 0
    for para in config.PARA_CATEGORIES:
        para_dir = config.WIKI_DIR / para
        if para_dir.exists():
            count += len(list(para_dir.glob("*.md")))
    return count


def run_ask(question: str = None, top_k: int = 5, threshold: float = 0.35, json_output: bool = False):
    """
    Run the Q&A pipeline (Sub-Phase 4.1).

    Args:
        question: The question string. If None, enters interactive mode.
        top_k: Number of notes to retrieve.
        threshold: Minimum similarity threshold.
        json_output: If True, print JSON output.
    """
    try:
        from ask import ask as ask_func, print_result

        if question:
            logger.info(f"Asking: \"{question}\"")
            result = ask_func(question=question, top_k=top_k, threshold=threshold)
            print_result(result, json_output=json_output)
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
                    result = ask_func(question=q, top_k=top_k, threshold=threshold)
                    print_result(result, json_output=json_output)
                    print()
                except KeyboardInterrupt:
                    print("\nGoodbye!")
                    break
    except ImportError as e:
        logger.error(f"Ask module not available: {e}")
        logger.error("Run 'python pipeline.py process' first to build wiki notes and embeddings.")
    except Exception as e:
        logger.error(f"Ask failed: {e}", exc_info=True)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="SecondSelf Pipeline — Classify, link, build graph, and ask your brain."
    )
    parser.add_argument(
        "command",
        choices=["classify", "link", "graph", "process", "ask"],
        help="Pipeline command to execute.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without writing any files.",
    )
    parser.add_argument(
        "--reprocess",
        action="store_true",
        help="Re-process all items, overwriting existing data.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=config.TOP_K_RETRIEVAL,
        help=f"Number of notes to retrieve (default: {config.TOP_K_RETRIEVAL}). Used with 'ask' command.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.0,
        help="Minimum similarity threshold (0.0-1.0). Used with 'ask' command.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON. Used with 'ask' command.",
    )

    args, remaining = parser.parse_known_args()

    # For 'ask' command, capture the question from remaining args
    question = " ".join(remaining) if remaining else None

    try:
        if args.command == "classify":
            logger.info("Running classification pipeline...")
            count = run_classify(dry_run=args.dry_run, reprocess=args.reprocess)
            print(f"✓ Classification complete. {count} capture(s) classified.")

        elif args.command == "link":
            logger.info("Running auto-link pipeline...")
            count = run_link(dry_run=args.dry_run, reprocess=args.reprocess)
            print(f"✓ Auto-link complete. {count} link(s) created.")

        elif args.command == "graph":
            logger.info("Building knowledge graph...")
            success = run_graph(dry_run=args.dry_run, pretty=True)
            if success:
                print(f"✓ Graph built successfully!")
                print(f"  → {config.GRAPH_PATH}")
            else:
                print("Graph build failed. Check logs above.")

        elif args.command == "process":
            success = run_process(dry_run=args.dry_run, reprocess=args.reprocess)
            if success:
                print(f"✓ Pipeline complete!")
                print(f"  {count_wiki_notes()} notes across {len(config.PARA_CATEGORIES)} PARA categories")
                print(f"  Graph: {config.GRAPH_PATH}")
            else:
                print("Pipeline completed with errors. Check logs above.")

        elif args.command == "ask":
            run_ask(
                question=question,
                top_k=args.top_k,
                threshold=args.threshold,
                json_output=args.json,
            )

    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

