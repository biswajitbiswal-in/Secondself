"""Dashboard page — Animated stat cards, system status, PARA breakdown."""

import logging
import sys
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import config
from ui.theme import THEME, PARA_COLORS, PARA_EMOJIS
from ui.components import section_header, stat_card

logger = logging.getLogger(__name__)


# ── Cached data getters ──

@st.cache_data(ttl=60)
def _get_wiki_stats():
    from lib.storage import read_wiki_notes
    notes = read_wiki_notes()
    stats = {"total": len(notes), "by_para": {}}
    for para in config.PARA_CATEGORIES:
        stats["by_para"][para] = sum(1 for n in notes if n.para == para)
    return stats


@st.cache_data(ttl=60)
def _get_embedding_stats():
    from lib.embeddings import load_embeddings
    embs = load_embeddings()
    return {"total": len(embs), "model": config.EMBEDDING_MODEL}


@st.cache_data(ttl=60)
def _get_graph_data():
    import json
    if config.GRAPH_PATH.exists():
        try:
            return json.loads(config.GRAPH_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {"nodes": [], "edges": [], "metadata": {}}
    return {"nodes": [], "edges": [], "metadata": {}}


# ── Render ──

def render():
    section_header("📊 Dashboard", "Overview of your SecondSelf knowledge base")

    # Collect stats
    try:
        wiki = _get_wiki_stats()
        emb = _get_embedding_stats()
        graph = _get_graph_data()
        graph_nodes = graph.get("metadata", {}).get("node_count", len(graph.get("nodes", [])))
        graph_edges = graph.get("metadata", {}).get("edge_count", len(graph.get("edges", [])))
    except Exception as e:
        logger.warning(f"Dashboard stat load failed: {e}")
        st.warning("Could not load stats. Ensure the pipeline has been run.")
        return

    # ── Stat cards row 1 ──
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        stat_card("Total Notes", wiki["total"], "📝")
    with col2:
        stat_card("Embeddings", emb["total"], "🧬")
    with col3:
        stat_card("Graph Nodes", graph_nodes, "🕸️")
    with col4:
        stat_card("Connections", graph_edges, "🔗")

    # ── Stat cards row 2 ──
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        stat_card("Projects", wiki["by_para"].get("Projects", 0), PARA_EMOJIS.get("Projects", "🎯"),
                  color=PARA_COLORS["Projects"]["bg"])
    with col2:
        stat_card("Areas", wiki["by_para"].get("Areas", 0), PARA_EMOJIS.get("Areas", "🔑"),
                  color=PARA_COLORS["Areas"]["bg"])
    with col3:
        stat_card("Resources", wiki["by_para"].get("Resources", 0), PARA_EMOJIS.get("Resources", "📚"),
                  color=PARA_COLORS["Resources"]["bg"])
    with col4:
        stat_card("Archives", wiki["by_para"].get("Archives", 0), PARA_EMOJIS.get("Archives", "🗄️"),
                  color=PARA_COLORS["Archives"]["bg"])

    st.markdown("<br>", unsafe_allow_html=True)

    # ── PARA Distribution Bars ──
    st.markdown("### 📊 PARA Distribution")
    total = max(wiki["total"], 1)
    for para in config.PARA_CATEGORIES:
        count = wiki["by_para"].get(para, 0)
        pct = count / total * 100
        color = PARA_COLORS[para]
        st.markdown(f"""
        <div style="margin-bottom:0.75rem;animation:fadeInUp 0.3s ease;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                <span style="color:{THEME['text_secondary']};font-size:0.85rem;">
                    {PARA_EMOJIS[para]} {para}</span>
                <span style="color:{THEME['text_muted']};font-size:0.85rem;">
                    {count} ({pct:.1f}%)</span>
            </div>
            <div style="height:8px;background:{THEME['bg_input']};border-radius:4px;overflow:hidden;">
                <div style="height:100%;width:{pct}%;background:linear-gradient(90deg,{color['bg']},{color['light']});
                            border-radius:4px;transition:width 0.6s ease;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── System Info ──
    st.markdown("### ⚙️ System Status")
    col1, col2 = st.columns(2)
    with col1:
        _info_row("Embedding Model", emb["model"])
        _info_row("LLM Model", config.GROQ_MODEL)
        _info_row("Similarity Threshold", str(config.SIMILARITY_THRESHOLD))
    with col2:
        gtime = graph.get("metadata", {}).get("generated_at", "N/A")[:19] if graph.get("metadata", {}).get("generated_at") else "N/A"
        _info_row("Graph Last Built", gtime)
        _info_row("Top-K Retrieval", str(config.TOP_K_RETRIEVAL))
        _info_row("API Status", "✅ Connected" if config.GROQ_API_KEY else "⚠️ No API Key")

    # ── Quick Actions ──
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 🚀 Quick Actions")
    ac1, ac2, ac3, ac4 = st.columns(4)
    with ac1:
        if st.button("📥 Capture Note", use_container_width=True, key="dash_capture"):
            st.session_state["nav"] = "capture"
            st.rerun()
    with ac2:
        if st.button("💬 Ask Question", use_container_width=True, key="dash_ask"):
            st.session_state["nav"] = "ask"
            st.rerun()
    with ac3:
        if st.button("🕸️ View Graph", use_container_width=True, key="dash_graph"):
            st.session_state["nav"] = "graph"
            st.rerun()
    with ac4:
        if st.button("⚡ Run Pipeline", use_container_width=True, key="dash_pipeline"):
            st.session_state["nav"] = "capture"
            st.rerun()


def _info_row(label: str, value: str):
    """Render a label-value info row."""
    st.markdown(
        f"""<div style="display:flex;justify-content:space-between;
            padding:0.4rem 0;border-bottom:1px solid {THEME['border']};
            font-size:0.85rem;">
            <span style="color:{THEME['text_muted']};">{label}</span>
            <span style="color:{THEME['text_secondary']};">{value}</span>
        </div>""",
        unsafe_allow_html=True,
    )

