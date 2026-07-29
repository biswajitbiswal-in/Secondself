"""Settings page — Configuration, Danger Zone, manual actions."""

import logging
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


def render():
    section_header("⚙️ Settings", "Configure your SecondSelf system", icon="⚙️")

    # ── Configuration Section ──
    st.markdown("### 🧠 Model Configuration")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div style="background:{THEME['bg_card']};border:1px solid {THEME['border']};
                    border-radius:{THEME['radius_md']};padding:1rem;margin-bottom:0.75rem;">
            <p style="font-size:0.7rem;text-transform:uppercase;letter-spacing:0.5px;
                      color:{THEME['text_muted']};margin:0 0 0.25rem 0;">Embedding Model</p>
            <p style="font-size:0.95rem;color:{THEME['text_primary']};margin:0;
                      font-family:monospace;">{config.EMBEDDING_MODEL}</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style="background:{THEME['bg_card']};border:1px solid {THEME['border']};
                    border-radius:{THEME['radius_md']};padding:1rem;margin-bottom:0.75rem;">
            <p style="font-size:0.7rem;text-transform:uppercase;letter-spacing:0.5px;
                      color:{THEME['text_muted']};margin:0 0 0.25rem 0;">LLM Model</p>
            <p style="font-size:0.95rem;color:{THEME['text_primary']};margin:0;
                      font-family:monospace;">{config.GROQ_MODEL}</p>
        </div>
        """, unsafe_allow_html=True)

    # ── Threshold sliders ──
    st.markdown("### 🎯 Retrieval Settings")

    col1, col2 = st.columns(2)
    with col1:
        st.slider(
            "Similarity Threshold (auto-link)",
            min_value=0.0,
            max_value=1.0,
            value=config.SIMILARITY_THRESHOLD,
            step=0.05,
            disabled=True,
            help="Configured in config.py — edit file to change",
            key="settings_sim",
        )
    with col2:
        st.slider(
            "Top-K Retrieval (RAG)",
            min_value=1,
            max_value=20,
            value=config.TOP_K_RETRIEVAL,
            disabled=True,
            help="Configured in config.py — edit file to change",
            key="settings_topk",
        )

    # ── API Key Status ──
    st.markdown("### 🔑 API Keys")
    api_status = "✅ Configured" if config.GROQ_API_KEY else "❌ Not Set"
    st.markdown(f"""
    <div style="background:{THEME['bg_card']};border:1px solid {THEME['border']};
                border-radius:{THEME['radius_md']};padding:1rem;margin-bottom:0.75rem;
                display:flex;justify-content:space-between;align-items:center;">
        <div>
            <p style="font-size:0.85rem;color:{THEME['text_primary']};margin:0;font-weight:500;">
                Groq API Key</p>
            <p style="font-size:0.75rem;color:{THEME['text_muted']};margin:0;
                      font-family:monospace;">
                {config.GROQ_API_KEY[:8] + '…' if config.GROQ_API_KEY else '(empty)'}</p>
        </div>
        <span style="font-size:0.85rem;font-weight:600;color:{THEME['success'] if config.GROQ_API_KEY else THEME['error']};">
            {api_status}</span>
    </div>
    """, unsafe_allow_html=True)

    # ── System Info ──
    st.markdown("### 💾 Storage")
    col1, col2, col3 = st.columns(3)
    with col1:
        _render_info_card("Wiki Notes", str(config.WIKI_DIR))
    with col2:
        _render_info_card("Raw Captures", str(config.RAW_DIR))
    with col3:
        _render_info_card("Embeddings", str(config.EMBEDDINGS_DIR))

    # ── Manual Actions ──
    st.markdown("### 🔧 Manual Actions")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🔨 Rebuild Graph", use_container_width=True, key="set_rebuild"):
            _rebuild_graph()
    with col2:
        if st.button("🧬 Recompute Embeddings", use_container_width=True, key="set_embeddings"):
            _recompute_embeddings()
    with col3:
        if st.button("🗑️ Clear Cache", use_container_width=True, key="set_cache"):
            st.cache_data.clear()
            st.success("✅ Cache cleared!")
    with col4:
        if st.button("📤 Export Data", use_container_width=True, key="set_export"):
            _export_data()

    # ── Danger Zone ──
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style="background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.2);
                border-radius:{THEME['radius_lg']};padding:1.5rem;margin-bottom:1rem;">
        <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.75rem;">
            <span style="font-size:1.2rem;">⚠️</span>
            <h3 style="color:#FCA5A5;margin:0;font-size:1.1rem;">Danger Zone</h3>
        </div>
        <p style="color:{THEME['text_muted']};font-size:0.85rem;margin-bottom:1rem;">
            Destructive actions that cannot be undone.</p>
        <div style="display:flex;gap:0.75rem;flex-wrap:wrap;">
            {_danger_button("Reset All Data", "set_reset", "Are you sure you want to reset ALL data?")}
            {_danger_button("Clear All Captures", "set_clear_captures", "This will delete all raw captures.")}
            {_danger_button("Delete All Notes", "set_delete_notes", "This will delete all wiki notes.")}
        </div>
        <div style="margin-top:1rem;">
            {_danger_button("⚠️ RESET EVERYTHING (Full Wipe)", "set_full_wipe",
                           "This will delete ALL data including captures, notes, embeddings, and graph!")}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Handle danger zone actions
    _handle_danger_actions()


def _render_info_card(label: str, value: str):
    """Render a small info card."""
    st.markdown(f"""
    <div style="background:{THEME['bg_card']};border:1px solid {THEME['border']};
                border-radius:{THEME['radius_md']};padding:0.75rem;margin-bottom:0.5rem;">
        <p style="font-size:0.7rem;text-transform:uppercase;color:{THEME['text_muted']};
                  margin:0 0 0.15rem 0;">{label}</p>
        <p style="font-size:0.75rem;color:{THEME['text_secondary']};margin:0;
                  font-family:monospace;word-break:break-all;">{value}</p>
    </div>
    """, unsafe_allow_html=True)


def _danger_button(label: str, key: str, confirm_msg: str) -> str:
    """Return a danger button that requires confirmation."""
    return (
        f'<button onclick="if(confirm(\'{confirm_msg}\')){{}};" '
        f'style="padding:0.5rem 1rem;border-radius:{THEME["radius_md"]};'
        f'background:rgba(239,68,68,0.15);border:1px solid rgba(239,68,68,0.3);'
        f'color:#FCA5A5;font-weight:600;font-size:0.85rem;cursor:pointer;'
        f'transition:all 0.2s;">{label}</button>'
    )


def _handle_danger_actions():
    """Handle danger zone button clicks."""
    import os, shutil
    from pathlib import Path

    if st.session_state.get("set_reset"):
        if st.button("⚠️ Confirm Reset All Data", key="confirm_reset"):
            try:
                shutil.rmtree(config.RAW_DIR, ignore_errors=True)
                shutil.rmtree(config.WIKI_DIR, ignore_errors=True)
                config.ensure_directories_exist()
                st.success("✅ All data has been reset.")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Reset failed: {e}")

    if st.session_state.get("set_full_wipe"):
        if st.button("💀 Confirm FULL WIPE", key="confirm_wipe", type="secondary"):
            try:
                paths = [config.RAW_DIR, config.WIKI_DIR, config.EMBEDDINGS_DIR,
                         config.BASE_DIR / "data" / "graph.json",
                         config.BASE_DIR / "data" / "embeddings.pkl",
                         config.BASE_DIR / "data" / "index.json"]
                for p in paths:
                    p = Path(p)
                    if p.exists():
                        if p.is_dir():
                            shutil.rmtree(p)
                        else:
                            p.unlink()
                config.ensure_directories_exist()
                st.success("✅ Full wipe complete.")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Wipe failed: {e}")


def _rebuild_graph():
    """Rebuild the knowledge graph."""
    with st.spinner("Rebuilding graph..."):
        try:
            from build_graph import run as build_graph_run
            graph = build_graph_run(pretty=True)
            if graph:
                st.success(f"✅ Graph rebuilt: {graph['metadata']['node_count']} nodes")
                st.cache_data.clear()
            else:
                st.error("Graph build failed.")
        except Exception as e:
            st.error(f"Error: {e}")


def _recompute_embeddings():
    """Recompute all embeddings."""
    with st.spinner("Recomputing embeddings..."):
        try:
            from link import run as link_run
            count = link_run(dry_run=False, reprocess=True)
            st.success(f"✅ Recomputed embeddings for {count} notes")
            st.cache_data.clear()
        except Exception as e:
            st.error(f"Error: {e}")


def _export_data():
    """Export notes data as JSON."""
    import json, datetime
    try:
        from lib.storage import read_wiki_notes
        notes = read_wiki_notes()
        export = []
        for n in notes:
            export.append({
                "id": n.id,
                "para": n.para,
                "summary": n.summary,
                "tags": n.tags,
                "created": n.created,
                "body": n.body[:500] if n.body else "",
            })
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        export_path = config.BASE_DIR / "data" / f"export_{ts}.json"
        export_path.write_text(
            json.dumps(export, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        st.success(f"✅ Exported {len(export)} notes to {export_path.name}")
    except Exception as e:
        st.error(f"Export failed: {e}")

