"""Knowledge Graph page — Interactive vis-network with larger canvas."""

import json
import logging
import re
import sys
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import config
from ui.theme import THEME
from ui.components import section_header

logger = logging.getLogger(__name__)


@st.cache_data(ttl=300)
def _load_graph_data() -> dict:
    """Load graph.json data with caching."""
    if config.GRAPH_PATH.exists():
        try:
            return json.loads(config.GRAPH_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"nodes": [], "edges": [], "metadata": {}}
    return {"nodes": [], "edges": [], "metadata": {}}


def _get_graph_html() -> str:
    """Get graph.html content with inline graph data injected."""
    graph_html_path = BASE_DIR / "static" / "graph.html"
    if not graph_html_path.exists():
        logger.warning("graph.html not found in static/")
        return "<p style='color:#555;text-align:center;padding:2rem;'>Graph viewer not available.</p>"

    html_content = graph_html_path.read_text(encoding="utf-8")
    graph_data = _load_graph_data()
    data_json = json.dumps(graph_data)

    # Inject data by replacing INLINE_GRAPH_DATA
    pattern = r'const\s+INLINE_GRAPH_DATA\s*=\s*[^;]+;'
    new_html, count = re.subn(
        pattern,
        lambda m: f'const INLINE_GRAPH_DATA = {data_json};',
        html_content,
        count=1,
    )

    if count == 0:
        new_html = html_content.replace(
            '</script>',
            f'\nconst INLINE_GRAPH_DATA = {data_json};\n</script>',
            1,
        )

    return new_html


def render():
    section_header(
        "🕸️ Knowledge Graph",
        "Explore connections between your notes — hover for details, click for full info",
        icon="🕸️"
    )

    graph_data = _load_graph_data()
    node_count = graph_data.get("metadata", {}).get("node_count", len(graph_data.get("nodes", [])))
    edge_count = graph_data.get("metadata", {}).get("edge_count", len(graph_data.get("edges", [])))

    # ── Graph controls row ──
    col1, col2, col3, col4 = st.columns([2, 2, 2, 6])
    with col1:
        st.markdown(
            f"<p style='color:{THEME['text_secondary']};font-size:0.9rem;'>"
            f"<strong>{node_count}</strong> nodes · <strong>{edge_count}</strong> edges</p>",
            unsafe_allow_html=True,
        )
    with col2:
        if st.button("🔄 Refresh Graph", key="graph_refresh", use_container_width=True):
            _rebuild_graph()
    with col3:
        if st.button("⛶ Fullscreen", key="graph_fullscreen", use_container_width=True):
            st.markdown(
                "<script>document.documentElement.requestFullscreen()</script>",
                unsafe_allow_html=True,
            )
    with col4:
        st.markdown("")

    # ── Graph canvas ──
    if node_count == 0:
        st.markdown(f"""
        <div style="text-align:center;padding:4rem 1rem;">
            <div style="font-size:3rem;margin-bottom:1rem;">🕸️</div>
            <h3 style="color:{THEME['text_secondary']};">No graph data yet</h3>
            <p style="color:{THEME['text_muted']};max-width:400px;margin:0 auto 1.5rem;">
            Capture some notes and run the pipeline to build your knowledge graph.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    try:
        graph_html = _get_graph_html()
        # Larger canvas than the original — 650px height
        st.components.v1.html(
            graph_html,
            height=650,
            scrolling=False,
        )
    except Exception as e:
        st.error(f"Failed to render graph: {e}")
        logger.error(f"Graph render error: {e}", exc_info=True)

    # ── Graph metadata ──
    with st.expander("📊 Graph Metadata", expanded=False):
        meta = graph_data.get("metadata", {})
        cols = st.columns(4)
        with cols[0]:
            st.metric("Total Nodes", meta.get("node_count", node_count))
        with cols[1]:
            st.metric("Total Edges", meta.get("edge_count", edge_count))
        with cols[2]:
            cats = meta.get("para_categories", {})
            st.metric("Categories", len(cats))
        with cols[3]:
            gtime = meta.get("generated_at", "N/A")[:19] if meta.get("generated_at") else "N/A"
            st.metric("Last Built", gtime)

        if meta.get("para_categories"):
            st.markdown("**Nodes by Category**")
            for cat, count in meta["para_categories"].items():
                st.markdown(f"- {cat}: {count}")


def _rebuild_graph():
    """Rebuild the knowledge graph from wiki notes."""
    with st.spinner("Rebuilding knowledge graph..."):
        try:
            from build_graph import run as build_graph_run
            graph = build_graph_run(pretty=True)
            if graph and graph["metadata"]["node_count"] > 0:
                st.success(f"✅ Graph rebuilt: {graph['metadata']['node_count']} notes, "
                           f"{graph['metadata']['edge_count']} connections")
                st.cache_data.clear()
                st.rerun()
            else:
                st.warning("Graph built but no nodes found.")
        except Exception as e:
            st.error(f"Graph build failed: {e}")

