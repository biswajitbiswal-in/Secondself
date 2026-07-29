"""Capture page — Three distinct cards for Note, URL, and File capture."""

import logging
import sys
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ui.theme import THEME
from ui.components import section_header, toast_message

logger = logging.getLogger(__name__)


def render():
    section_header("📥 Capture", "Add new knowledge to your second brain", icon="📥")

    # ── Three-column card layout ──
    col1, col2, col3 = st.columns(3)

    with col1:
        _render_note_card()
    with col2:
        _render_link_card()
    with col3:
        _render_file_card()

    # ── Pipeline quick actions ──
    st.markdown("<br><hr>", unsafe_allow_html=True)
    section_header("🔄 Pipeline", "Process captures → classify → link → build graph", icon="🔄")

    col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
    with col1:
        process_all = st.button("⚡ Process All", use_container_width=True, key="cap_process_all",
                                help="Classify + Link + Build Graph")
    with col2:
        classify_btn = st.button("🏷️ Classify", use_container_width=True, key="cap_classify",
                                 help="Classify unprocessed captures")
    with col3:
        refresh_btn = st.button("🔄 Refresh Graph", use_container_width=True, key="cap_refresh",
                                help="Rebuild knowledge graph")
    with col4:
        st.markdown("")  # Spacer

    # ── Handle pipeline buttons ──
    if process_all:
        _process_pipeline()

    if classify_btn:
        _run_classify()

    if refresh_btn:
        _run_refresh_graph()


# ── Card renderers ──

def _render_card(icon: str, title: str, description: str, accent_color: str = THEME["accent"]):
    """Render the top of a capture card."""
    st.markdown(f"""
    <div style="background:{THEME['bg_card']};border:1px solid {THEME['border']};
                border-radius:{THEME['radius_lg']};padding:1.5rem;
                backdrop-filter:blur(16px);text-align:center;
                border-top:3px solid {accent_color};
                transition:all 0.25s;margin-bottom:1rem;
                animation:fadeInUp 0.3s ease;">
        <div style="font-size:2.5rem;margin-bottom:0.75rem;">{icon}</div>
        <h3 style="margin:0 0 0.25rem 0;font-size:1.1rem;">{title}</h3>
        <p style="color:{THEME['text_muted']};font-size:0.8rem;margin:0 0 1rem 0;">{description}</p>
    </div>
    """, unsafe_allow_html=True)


def _render_note_card():
    _render_card("📝", "Note", "Write a quick note or thought")
    note_text = st.text_area(
        "Note content",
        placeholder="Write your note here...",
        height=130,
        label_visibility="collapsed",
        key="cap_note_input",
    )
    if st.button("📝 Capture Note", use_container_width=True, key="btn_cap_note"):
        if note_text.strip():
            with st.spinner("Capturing note..."):
                try:
                    from capture import capture_note
                    cid, cap_dir, md_path, json_path = capture_note(note_text)
                    st.success(f"✅ Note captured! ID: {cid[:8]}…")
                    st.session_state["cap_note_input"] = ""
                    st.rerun()
                except Exception as e:
                    st.error(f"Capture failed: {e}")
        else:
            st.warning("Please enter some note content.")


def _render_link_card():
    _render_card("🔗", "URL", "Save a webpage or article", accent_color="#06B6D4")
    link_url = st.text_input(
        "URL",
        placeholder="https://example.com/article",
        label_visibility="collapsed",
        key="cap_link_input",
    )
    if st.button("🔗 Capture Link", use_container_width=True, key="btn_cap_link",
                 type="secondary"):
        if link_url.strip():
            with st.spinner("Fetching URL..."):
                try:
                    from capture import capture_link
                    cid, cap_dir, md_path, json_path = capture_link(link_url)
                    st.success(f"✅ Link captured! ID: {cid[:8]}…")
                    st.session_state["cap_link_input"] = ""
                    st.rerun()
                except Exception as e:
                    st.error(f"Link capture failed: {e}")
        else:
            st.warning("Please enter a valid URL.")


def _render_file_card():
    _render_card("📄", "File", "Upload a document or code file", accent_color="#10B981")
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["txt", "md", "pdf", "py", "js", "html", "css", "json", "yaml", "yml", "toml", "cfg", "ini"],
        label_visibility="collapsed",
        key="cap_file_input",
    )
    if uploaded_file is not None:
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:0.5rem;padding:0.5rem 0.75rem;
                    background:{THEME['success_bg']};border:1px solid rgba(16,185,129,0.2);
                    border-radius:{THEME['radius_sm']};margin:0.25rem 0;">
            <span style="font-size:1.2rem;">📎</span>
            <span style="font-size:0.85rem;color:{THEME['success']};">{uploaded_file.name}</span>
            <span style="font-size:0.75rem;color:{THEME['text_muted']};">
                ({_format_size(len(uploaded_file.getvalue()))})</span>
        </div>
        """, unsafe_allow_html=True)

        if st.button("📄 Capture File", use_container_width=True, key="btn_cap_file"):
            with st.spinner("Capturing file..."):
                try:
                    temp_dir = BASE_DIR / "data" / "temp"
                    temp_dir.mkdir(parents=True, exist_ok=True)
                    temp_path = temp_dir / uploaded_file.name
                    temp_path.write_bytes(uploaded_file.getvalue())

                    from capture import capture_file
                    cid, cap_dir, md_path, json_path = capture_file(str(temp_path))
                    temp_path.unlink(missing_ok=True)
                    st.success(f"✅ File captured! ID: {cid[:8]}…")
                    st.rerun()
                except Exception as e:
                    st.error(f"File capture failed: {e}")


# ── Pipeline actions ──

def _process_pipeline():
    with st.spinner("Running full pipeline (classify → link → graph)..."):
        try:
            from pipeline import run_process
            success = run_process(dry_run=False, reprocess=False)
            if success:
                st.success("✅ Pipeline complete! Graph rebuilt.")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Pipeline encountered errors.")
        except Exception as e:
            st.error(f"Pipeline failed: {e}")


def _run_classify():
    with st.spinner("Classifying unprocessed captures..."):
        try:
            from pipeline import run_classify
            count = run_classify(dry_run=False, reprocess=False)
            st.success(f"✅ Classified {count} capture(s)")
            st.cache_data.clear()
        except Exception as e:
            st.error(f"Classification failed: {e}")


def _run_refresh_graph():
    with st.spinner("Rebuilding knowledge graph..."):
        try:
            from build_graph import run as build_graph_run
            graph = build_graph_run(pretty=True)
            if graph and graph["metadata"]["node_count"] > 0:
                st.success(f"✅ Graph rebuilt: {graph['metadata']['node_count']} nodes, "
                           f"{graph['metadata']['edge_count']} edges")
                st.cache_data.clear()
                st.rerun()
            else:
                st.warning("Graph built but no nodes found.")
        except Exception as e:
            st.error(f"Graph build failed: {e}")


def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable form."""
    for unit in ["B", "KB", "MB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} GB"

