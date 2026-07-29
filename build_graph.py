"""
Sub-Phase 3.1 — Graph Data Model (The Cartographer)

Converts the linked wiki notes into a structured graph.json with nodes, edges,
and metadata. This powers the interactive vis-network visualization in Phase 3.2.

Logic:
  - Parse nodes: One node per wiki/**/*.md note
  - Parse edges: From links[] frontmatter + [[id]] wikilinks in body
  - Deduplicate: Edge key = (min(source,target), max(source,target))
  - Enrich nodes: label = summary, group = para, content_preview = first 200 chars
  - Export: Write data/graph.json and update static/graph.html

Usage:
    python build_graph.py                      # Build graph from all wiki notes
    python build_graph.py --pretty              # Pretty-print JSON (larger file)
    python build_graph.py --min-weight 0.5      # Only include edges with weight >= 0.5
    python build_graph.py --para Projects       # Filter nodes by PARA category
"""

import datetime
import json
import logging
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Ensure project root is on sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import config
from lib.models import GraphNode, GraphEdge, WikiNote
from lib.storage import load_index, read_wiki_notes, save_index

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def extract_wikilinks_from_body(body: str) -> List[str]:
    """
    Extract all [[note-id]] wikilinks from markdown body text.

    Args:
        body: The markdown body content of a wiki note.

    Returns:
        List of unique note IDs referenced in wikilinks.
    """
    return list(set(re.findall(r'\[\[([^\]]+)\]\]', body)))


def build_graph(
    notes: List[WikiNote],
    min_weight: float = 0.0,
    para_filter: str = None,
) -> dict:
    """
    Build the full graph data structure from a list of WikiNote objects.

    Steps:
        1. Parse each note into a GraphNode
        2. Extract edges from frontmatter links[] + body [[wikilinks]]
        3. Deduplicate edges using (min(source,target), max(source,target))
        4. Build metadata summary

    Args:
        notes: List of WikiNote objects to build the graph from.
        min_weight: Minimum edge weight to include (0.0 = all edges).
        para_filter: If set, only include notes from this PARA category.

    Returns:
        dict with 'nodes', 'edges', and 'metadata' keys, ready for JSON export.
    """
    # Filter by PARA category if specified
    if para_filter:
        if para_filter not in config.PARA_CATEGORIES:
            logger.warning(f"Invalid PARA filter '{para_filter}', ignoring.")
        else:
            notes = [n for n in notes if n.para == para_filter]
            logger.info(f"Filtered to PARA={para_filter}: {len(notes)} notes")

    # Build a map for quick lookup: note_id -> WikiNote
    notes_map: Dict[str, WikiNote] = {note.id: note for note in notes}

    # -----------------------------------------------------------------------
    # Step 1: Parse nodes
    # -----------------------------------------------------------------------
    nodes: List[dict] = []
    seen_node_ids: Set[str] = set()

    for note in notes:
        if note.id in seen_node_ids:
            logger.warning(f"Duplicate node ID '{note.id}', skipping.")
            continue

        seen_node_ids.add(note.id)

        # Build content_preview: first 200 chars of body (strip markdown-like syntax)
        content_preview = note.body[:200].strip().replace("\n", " ")
        if len(note.body) > 200:
            content_preview += "..."

        # label = summary if available, otherwise use ID as fallback
        label = note.summary.strip() if note.summary.strip() else note.id

        node = GraphNode(
            id=note.id,
            label=label,
            para=note.para,
            tags=note.tags,
            summary=note.summary,
            content_preview=content_preview,
            group=note.para,  # group = PARA category for coloring
        )

        nodes.append({
            "id": node.id,
            "label": node.label,
            "para": node.para,
            "tags": node.tags,
            "summary": node.summary,
            "content_preview": node.content_preview,
            "group": node.group,
            "source_url": note.source_url,
        })

    logger.info(f"Parsed {len(nodes)} nodes from {len(notes)} wiki notes.")

    if not nodes:
        logger.warning("No nodes to build graph from.")
        return {
            "nodes": [],
            "edges": [],
            "metadata": {
                "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "node_count": 0,
                "edge_count": 0,
            },
        }

    # -----------------------------------------------------------------------
    # Step 2: Parse edges
    # -----------------------------------------------------------------------
    edges: List[dict] = []
    seen_edges: Set[Tuple[str, str]] = set()

    for note in notes:
        source_id = note.id

        # Collect all target IDs: from frontmatter links[] and body [[wikilinks]]
        target_ids: Set[str] = set()

        # From frontmatter links[]
        for link_id in note.links:
            target_ids.add(link_id)

        # From body [[wikilinks]]
        body_links = extract_wikilinks_from_body(note.body)
        for link_id in body_links:
            target_ids.add(link_id)

        for target_id in target_ids:
            if target_id == source_id:
                continue

            if target_id not in notes_map:
                logger.debug(f"Edge target '{target_id}' (from '{source_id}') not found, skipping.")
                continue

            # Deduplicate: edge key = (min(source, target), max(source, target))
            edge_key = tuple(sorted([source_id, target_id]))
            if edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)

            # Calculate weight
            in_frontmatter = target_id in note.links
            in_body = target_id in body_links

            if in_frontmatter and in_body:
                weight = 1.0
            elif in_frontmatter or in_body:
                weight = 0.8
            else:
                weight = 0.5

            if weight < min_weight:
                continue

            edge = GraphEdge(
                source=edge_key[0],
                target=edge_key[1],
                weight=weight,
                type="semantic",
            )

            edges.append({
                "source": edge.source,
                "target": edge.target,
                "weight": edge.weight,
                "type": edge.type,
            })

    logger.info(f"Parsed {len(edges)} edges (deduplicated).")

    # -----------------------------------------------------------------------
    # Step 3: Build metadata
    # -----------------------------------------------------------------------
    metadata = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "para_categories": {},
        "model_version": config.EMBEDDING_MODEL,
    }

    for para in config.PARA_CATEGORIES:
        count = sum(1 for n in notes if n.para == para)
        metadata["para_categories"][para] = count

    # -----------------------------------------------------------------------
    # Step 4: Assemble graph
    # -----------------------------------------------------------------------
    graph = {
        "nodes": nodes,
        "edges": edges,
        "metadata": metadata,
    }

    return graph


def run(
    pretty: bool = False,
    min_weight: float = 0.0,
    para_filter: str = None,
) -> dict:
    """
    Main graph build pipeline.

    Steps:
        1. Load all wiki notes
        2. Build the graph (nodes + edges + metadata)
        3. Export to data/graph.json + update static/graph.html
        4. Update index with build timestamp

    Args:
        pretty: If True, pretty-print JSON with indentation.
        min_weight: Minimum edge weight to include.
        para_filter: If set, filter nodes by this PARA category.

    Returns:
        The graph dict (for inspection or further processing).
    """
    logger.info("=" * 50)
    logger.info("  BUILD GRAPH — Sub-Phase 3.1")
    logger.info("=" * 50)

    config.ensure_directories_exist()
    config.GRAPH_PATH.parent.mkdir(parents=True, exist_ok=True)

    notes = read_wiki_notes()
    if not notes:
        logger.warning("No wiki notes found to build graph.")
        empty_graph = {
            "nodes": [],
            "edges": [],
            "metadata": {
                "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "node_count": 0,
                "edge_count": 0,
                "para_categories": {p: 0 for p in config.PARA_CATEGORIES},
            },
        }
        write_graph(empty_graph, pretty=pretty)
        return empty_graph

    logger.info(f"Loaded {len(notes)} wiki notes from {config.WIKI_DIR}")

    graph = build_graph(
        notes=notes,
        min_weight=min_weight,
        para_filter=para_filter,
    )

    write_graph(graph, pretty=pretty)

    index = load_index()
    index["last_graph_build"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    save_index(index)

    logger.info("=" * 50)
    logger.info("  GRAPH BUILD COMPLETE")
    logger.info("=" * 50)
    logger.info(f"  Nodes:  {graph['metadata']['node_count']}")
    logger.info(f"  Edges:  {graph['metadata']['edge_count']}")
    for para, count in graph['metadata']['para_categories'].items():
        if count > 0:
            logger.info(f"    {para}: {count} nodes")
    logger.info(f"  Output: {config.GRAPH_PATH}")
    logger.info("=" * 50)

    return graph


def inject_inline_data(html_content: str, graph_data: dict) -> str:
    """
    Inject graph data into the HTML by replacing the INLINE_GRAPH_DATA assignment.
    Uses regex to handle both initial (null) and subsequent (existing data) states.

    Args:
        html_content: The current HTML content.
        graph_data: The graph dict to inject.

    Returns:
        Updated HTML content with injected graph data.
    """
    import re
    data_json = json.dumps(graph_data)
    pattern = r'const\s+INLINE_GRAPH_DATA\s*=\s*[^;]+;'
    # Use a lambda to avoid escape-sequence interpretation in replacement string
    new_html, count = re.subn(
        pattern,
        lambda m: f'const INLINE_GRAPH_DATA = {data_json};',
        html_content,
        count=1
    )
    if count == 0:
        logger.warning("Could not find INLINE_GRAPH_DATA assignment in HTML. Appending fallback.")
        # Append the inline data before closing </script>
        new_html = html_content.replace(
            '</script>',
            f'\nconst INLINE_GRAPH_DATA = {data_json};\n</script>',
            1
        )
    return new_html


def write_graph(graph: dict, pretty: bool = False):
    """
    Write the graph dict to data/graph.json and update static/graph.html.

    Args:
        graph: The graph dict with 'nodes', 'edges', 'metadata'.
        pretty: If True, indent JSON for human readability.
    """
    config.GRAPH_PATH.parent.mkdir(parents=True, exist_ok=True)

    if pretty:
        json_str = json.dumps(graph, indent=2, ensure_ascii=False)
    else:
        json_str = json.dumps(graph, ensure_ascii=False)

    config.GRAPH_PATH.write_text(json_str, encoding="utf-8")
    logger.info(f"Graph written to {config.GRAPH_PATH} ({len(json_str)} bytes)")

    # Also update static/graph.html with inline graph data
    graph_html_path = config.BASE_DIR / "static" / "graph.html"
    if graph_html_path.exists():
        try:
            html_content = graph_html_path.read_text(encoding="utf-8")
            new_html = inject_inline_data(html_content, graph)
            graph_html_path.write_text(new_html, encoding="utf-8")
            logger.info(f"Graph HTML updated: {graph_html_path}")
        except Exception as e:
            logger.warning(f"Failed to update graph HTML: {e}")


def print_graph_summary(graph: dict):
    """Print a human-readable summary of the graph to stdout."""
    meta = graph["metadata"]
    print(f"\n{'=' * 60}")
    print(f"  KNOWLEDGE GRAPH SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Generated:  {meta['generated_at']}")
    print(f"  Nodes:      {meta['node_count']}")
    print(f"  Edges:      {meta['edge_count']}")
    print(f"  Model:      {meta.get('model_version', 'N/A')}")
    print(f"{'-' * 60}")
    print(f"  Notes by PARA category:")
    for para, count in meta.get("para_categories", {}).items():
        bar = "█" * count if count > 0 else ""
        print(f"    {para:12s} : {count:2d}  {bar}")
    print(f"{'=' * 60}")

    if graph["nodes"]:
        connection_count = {}
        for edge in graph["edges"]:
            connection_count[edge["source"]] = connection_count.get(edge["source"], 0) + 1
            connection_count[edge["target"]] = connection_count.get(edge["target"], 0) + 1

        sorted_nodes = sorted(connection_count.items(), key=lambda x: x[1], reverse=True)

        if sorted_nodes:
            print(f"\n  Most connected nodes:")
            for node_id, count in sorted_nodes[:5]:
                node_info = next((n for n in graph["nodes"] if n["id"] == node_id), None)
                label = node_info["label"] if node_info else node_id
                print(f"    {label[:50]:50s} — {count} connections")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Build graph.json from wiki notes for knowledge graph visualization."
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print the JSON output (human-readable but larger file).",
    )
    parser.add_argument(
        "--min-weight",
        type=float,
        default=0.0,
        help="Minimum edge weight to include (0.0 = all edges).",
    )
    parser.add_argument(
        "--para",
        type=str,
        default=None,
        choices=config.PARA_CATEGORIES,
        help="Filter nodes by PARA category (default: all categories).",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print a human-readable summary after building.",
    )

    args = parser.parse_args()

    try:
        graph = run(
            pretty=args.pretty,
            min_weight=args.min_weight,
            para_filter=args.para,
        )

        if args.summary:
            print_graph_summary(graph)

        node_count = graph["metadata"]["node_count"]
        edge_count = graph["metadata"]["edge_count"]
        print(f"\n✓ Graph built successfully!")
        print(f"  → {config.GRAPH_PATH}")
        print(f"  → {node_count} nodes, {edge_count} edges")

    except Exception as e:
        logger.error(f"Graph build failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
