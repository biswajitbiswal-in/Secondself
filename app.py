"""
Sub-Phase 4.2 — Streamlit App (The Oracle)

Single-page Streamlit application that brings together all SecondSelf features:
  - Ask bar: Ask questions in plain English, get answers from your notes (RAG)
  - Knowledge Graph: Interactive vis-network visualization of note relationships
  - Capture form: Quickly capture new notes via the sidebar
  - Pipeline control: Process captures → classify → link → rebuild graph
  - Stats sidebar: Node/edge counts, PARA distribution

Usage:
    streamlit run app.py

Deployment (Streamlit Community Cloud):
    - Push to GitHub
    - Connect at https://share.streamlit.io
    - Set main file: app.py
    - Add secret: GROQ_API_KEY
    - Pre-commit wiki/, data/graph.json, data/embeddings.pkl for demo
"""

import json
import logging
import sys
import os
from pathlib import Path
from typing import Optional

# Ensure project root is on sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Configure logging before any other imports
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

import streamlit as st

# Streamlit must be configured before any other app imports
st.set_page_config(
    page_title="SecondSelf — Personal AI Second Brain",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

import config
from lib.models import AskResult

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------

APP_TITLE = "🧠 SecondSelf"
APP_SUBTITLE = "Your Personal AI Second Brain"
APP_DESCRIPTION = (
    "Ask questions, explore connections, and capture knowledge — "
    "all powered by your personal notes."
)

# Color scheme matching the graph theme
THEME = {
    "bg_dark": "#0a0a14",
    "bg_card": "#12122a",
    "bg_input": "rgba(255,255,255,0.04)",
    "border": "rgba(255,255,255,0.08)",
    "border_focus": "#7c3aed",
    "text_primary": "#e0e0e0",
    "text_secondary": "#888",
    "text_muted": "#555",
    "accent": "#7c3aed",
    "accent_light": "#a78bfa",
    "success": "#10b981",
    "warning": "#f59e0b",
    "error": "#ef4444",
}

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------

def inject_custom_css():
    """Inject dark-themed custom CSS for the Streamlit app."""
    st.markdown(f"""
    <style>
        /* Main container */
        .stApp {{
            background: {THEME['bg_dark']};
            color: {THEME['text_primary']};
        }}

        /* Remove default Streamlit padding */
        .block-container {{
            padding-top: 1rem;
            padding-bottom: 1rem;
        }}

        /* Sidebar */
        section[data-testid="stSidebar"] {{
            background: {THEME['bg_card']};
            border-right: 1px solid {THEME['border']};
        }}
        section[data-testid="stSidebar"] .stMarkdown {{
            color: {THEME['text_secondary']};
        }}

        /* Headers */
        h1, h2, h3 {{
            color: {THEME['text_primary']} !important;
        }}

        /* Gradient header accent */
        h1::after {{
            content: '';
            display: block;
            width: 60px;
            height: 3px;
            background: linear-gradient(90deg, {THEME['accent']}, {THEME['accent_light']}, transparent);
            border-radius: 2px;
            margin-top: 4px;
        }}
        h2::after {{
            content: '';
            display: block;
            width: 40px;
            height: 2px;
            background: linear-gradient(90deg, {THEME['accent_light']}, transparent);
            border-radius: 2px;
            margin-top: 3px;
        }}

        /* Text inputs */
        .stTextInput > div > div {{
            background: {THEME['bg_input']} !important;
            border: 1px solid {THEME['border']} !important;
            border-radius: 8px !important;
            color: {THEME['text_primary']} !important;
            transition: border-color 0.3s, box-shadow 0.3s !important;
        }}
        .stTextInput > div > div:focus-within {{
            border-color: {THEME['border_focus']} !important;
            box-shadow: 0 0 0 3px rgba(124,58,237,0.15) !important;
        }}
        .stTextInput input {{
            color: {THEME['text_primary']} !important;
        }}

        /* Text area */
        .stTextArea > div > div {{
            background: {THEME['bg_input']} !important;
            border: 1px solid {THEME['border']} !important;
            border-radius: 8px !important;
            color: {THEME['text_primary']} !important;
            transition: border-color 0.3s, box-shadow 0.3s !important;
        }}
        .stTextArea > div > div:focus-within {{
            border-color: {THEME['border_focus']} !important;
            box-shadow: 0 0 0 3px rgba(124,58,237,0.15) !important;
        }}
        .stTextArea textarea {{
            color: {THEME['text_primary']} !important;
        }}

        /* Buttons */
        .stButton > button {{
            background: {THEME['accent']} !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 0.5rem 1.5rem !important;
            font-weight: 600 !important;
            transition: all 0.2s !important;
        }}
        .stButton > button:hover {{
            background: {THEME['accent_light']} !important;
            box-shadow: 0 4px 20px rgba(124,58,237,0.3) !important;
        }}
        .stButton > button:disabled {{
            background: rgba(124,58,237,0.3) !important;
            cursor: not-allowed !important;
        }}

        /* Secondary buttons */
        .stButton > button.secondary {{
            background: transparent !important;
            border: 1px solid {THEME['border']} !important;
            color: {THEME['text_secondary']} !important;
        }}
        .stButton > button.secondary:hover {{
            border-color: {THEME['accent']} !important;
            color: {THEME['accent_light']} !important;
        }}

        /* Success/info/error messages */
        .stAlert {{
            background: {THEME['bg_card']} !important;
            border: 1px solid {THEME['border']} !important;
            border-radius: 8px !important;
        }}
        .stAlert > div {{
            color: {THEME['text_primary']} !important;
        }}

        /* Expander */
        .st-expander {{
            background: {THEME['bg_card']} !important;
            border: 1px solid {THEME['border']} !important;
            border-radius: 8px !important;
        }}
        .st-expander-header {{
            color: {THEME['text_primary']} !important;
        }}

        /* Metric cards */
        [data-testid="stMetric"] {{
            background: {THEME['bg_card']} !important;
            border: 1px solid {THEME['border']} !important;
            border-radius: 8px !important;
            padding: 1rem !important;
        }}
        [data-testid="stMetric"] label {{
            color: {THEME['text_secondary']} !important;
        }}
        [data-testid="stMetric"] [data-testid="stMetricValue"] {{
            color: {THEME['accent_light']} !important;
        }}

        /* Divider */
        hr {{
            border-color: {THEME['border']} !important;
        }}

        /* Spinner */
        .stSpinner > div {{
            border-color: {THEME['accent']} {THEME['accent']} transparent transparent !important;
        }}

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {{
            border-bottom: 1px solid {THEME['border']} !important;
        }}
        .stTabs [data-baseweb="tab"] {{
            color: {THEME['text_secondary']} !important;
        }}
        .stTabs [aria-selected="true"] {{
            color: {THEME['accent_light']} !important;
        }}

        /* Select box */
        .stSelectbox > div > div {{
            background: {THEME['bg_input']} !important;
            border: 1px solid {THEME['border']} !important;
            color: {THEME['text_primary']} !important;
        }}

        /* Graph container */
        .graph-container {{
            width: 100%;
            height: 550px;
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid {THEME['border']};
            background: {THEME['bg_dark']};
        }}

        /* Answer box */
        .answer-box {{
            background: {THEME['bg_card']};
            border: 1px solid {THEME['border']};
            border-radius: 12px;
            padding: 1.25rem;
            margin: 1rem 0;
            line-height: 1.6;
            animation: fadeInUp 0.3s ease;
        }}
        .answer-box a {{
            color: {THEME['accent_light']} !important;
            text-decoration: none !important;
            border-bottom: 1px solid rgba(167,139,250,0.3);
            transition: border-color 0.2s, color 0.2s;
            font-weight: 500;
        }}
        .answer-box a:hover {{
            color: #c4b5fd !important;
            border-bottom-color: #c4b5fd;
        }}
        .answer-box code {{
            background: rgba(124,58,237,0.15);
            color: {THEME['accent_light']};
            padding: 0.1rem 0.3rem;
            border-radius: 4px;
            font-size: 0.85rem;
        }}
        .answer-box ul {{ padding-left: 1.25rem; margin: 0.5rem 0; }}
        .answer-box li {{ margin-bottom: 0.25rem; }}
        .answer-box strong {{ color: #fff; }}

        /* Capture success toast */
        .capture-success {{
            padding: 0.75rem;
            border-radius: 8px;
            background: rgba(16,185,129,0.1);
            border: 1px solid rgba(16,185,129,0.2);
            color: {THEME['success']};
            font-size: 0.9rem;
            margin: 0.5rem 0;
        }}

        /* Pipeline status */
        .pipeline-status {{
            padding: 0.5rem;
            border-radius: 6px;
            background: rgba(124,58,237,0.08);
            border: 1px solid rgba(124,58,237,0.15);
            color: {THEME['accent_light']};
            font-size: 0.85rem;
            margin: 0.25rem 0;
        }}

        /* Title area */
        .app-title {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 0.25rem;
        }}
        .app-title h1 {{
            font-size: 1.8rem !important;
            font-weight: 700;
            margin: 0 !important;
        }}
        .app-subtitle {{
            color: {THEME['text_muted']};
            font-size: 0.9rem;
            margin-bottom: 1.5rem;
        }}

        /* Status badges */
        .status-badge {{
            display: inline-block;
            padding: 0.15rem 0.5rem;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .status-badge.active {{
            background: rgba(16,185,129,0.15);
            color: #6ee7b7;
        }}
        .status-badge.inactive {{
            background: rgba(239,68,68,0.15);
            color: #fca5a5;
        }}

        /* ── ANSWER FADE-IN ANIMATION ── */
        @keyframes fadeInUp {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
    </style>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Graph HTML embedding
# ---------------------------------------------------------------------------

def get_graph_html() -> str:
    """
    Get the graph.html content with inline graph data injected.

    Reads the current graph.json and injects it into the HTML template
    so the vis-network renders correctly within Streamlit's iframe.

    Returns:
        HTML string for embedding via st.components.v1.html().
    """
    graph_path = config.GRAPH_PATH

    # Read the base graph HTML template
    graph_html_path = BASE_DIR / "static" / "graph.html"
    if not graph_html_path.exists():
        logger.warning("graph.html not found in static/")
        return "<p style='color:#555;text-align:center;padding:2rem;'>Graph viewer not available.</p>"

    html_content = graph_html_path.read_text(encoding="utf-8")

    # Load current graph data
    if graph_path.exists():
        try:
            graph_data = json.loads(graph_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load graph.json: {e}")
            graph_data = {"nodes": [], "edges": [], "metadata": {}}
    else:
        graph_data = {"nodes": [], "edges": [], "metadata": {}}

    # Inject graph data into the HTML by replacing INLINE_GRAPH_DATA
    data_json = json.dumps(graph_data)
    import re
    pattern = r'const\s+INLINE_GRAPH_DATA\s*=\s*[^;]+;'
    new_html, count = re.subn(
        pattern,
        lambda m: f'const INLINE_GRAPH_DATA = {data_json};',
        html_content,
        count=1
    )

    if count == 0:
        # Fallback: append before closing </script>
        new_html = html_content.replace(
            '</script>',
            f'\nconst INLINE_GRAPH_DATA = {data_json};\n</script>',
            1
        )

    return new_html


# ---------------------------------------------------------------------------
# Cached resources
# ---------------------------------------------------------------------------

@st.cache_resource
def load_embedding_model():
    """Load the sentence-transformers model (cached in memory)."""
    from lib.embeddings import load_model
    return load_model()


@st.cache_data(ttl=300)  # 5-minute cache
def load_graph_data() -> dict:
    """Load graph.json data with caching."""
    graph_path = config.GRAPH_PATH
    if graph_path.exists():
        try:
            return json.loads(graph_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"nodes": [], "edges": [], "metadata": {}}
    return {"nodes": [], "edges": [], "metadata": {}}


@st.cache_data(ttl=60)
def get_wiki_stats() -> dict:
    """Get statistics about the wiki notes."""
    from lib.storage import read_wiki_notes
    notes = read_wiki_notes()
    stats = {
        "total": len(notes),
        "by_para": {},
    }
    for para in config.PARA_CATEGORIES:
        count = sum(1 for n in notes if n.para == para)
        stats["by_para"][para] = count
    return stats


@st.cache_data(ttl=300)
def get_embedding_stats() -> dict:
    """Get statistics about the embedding index."""
    from lib.embeddings import load_embeddings
    embeddings = load_embeddings()
    return {
        "total": len(embeddings),
        "model": config.EMBEDDING_MODEL,
    }


# ---------------------------------------------------------------------------
# Link helpers for rendering
# ---------------------------------------------------------------------------

def make_links_clickable(text: str) -> str:
    """
    Convert plain URLs in text into clickable HTML <a> links.

    Handles: https://, http://, and bare www. URLs.
    """
    import re
    # Pattern for http/https URLs
    text = re.sub(
        r'(https?://[^\s<]+)',
        r'<a href="\1" target="_blank" rel="noopener noreferrer">\1</a>',
        text,
    )
    # Pattern for bare www. URLs (that aren't already linked)
    text = re.sub(
        r'(?<!href=")www\.([^\s<]+)',
        r'<a href="http://www.\1" target="_blank" rel="noopener noreferrer">www.\1</a>',
        text,
    )
    return text


def get_wiki_link_url(note_id: str, para: str) -> str:
    """
    Build a human-readable wiki note link.

    Since wiki notes are local markdown files, we generate a file:// path
    that can be opened from the browser. The path is relative to the project root.
    """
    path = config.WIKI_DIR / para / f"{note_id}.md"
    wiki_path_relative = path.relative_to(config.BASE_DIR) if path.exists() else f"wiki/{para}/{note_id}.md"
    return str(wiki_path_relative)


def render_answer_with_links(answer_text: str) -> str:
    """
    Render the answer text with:
      - URLs converted to clickable links
      - Newlines converted to <br> for HTML display
      - Basic Markdown-like bold (**text**) converted to <strong>
    """
    import re
    # First convert URLs to clickable links
    html = make_links_clickable(answer_text)

    # Convert **bold** to <strong>
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)

    # Convert markdown links [text](url) to HTML links
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>', html)

    # Convert newlines to <br>
    html = html.replace('\n', '<br>')

    return html


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def render_sidebar():
    """Render the sidebar with capture form, pipeline control, and stats."""
    with st.sidebar:
        st.markdown("## 📥 Quick Capture")
        st.markdown(
            "<p style='color:#888;font-size:0.85rem;'>Capture a new note, link, or file</p>",
            unsafe_allow_html=True,
        )

        # Capture type selector
        capture_type = st.selectbox(
            "Capture type",
            options=["Note", "Link", "File"],
            label_visibility="collapsed",
            key="capture_type",
        )

        # Capture input based on type
        if capture_type == "Note":
            note_text = st.text_area(
                "Note content",
                placeholder="Write your note here...",
                height=120,
                label_visibility="collapsed",
                key="note_input",
            )
            capture_button = st.button("📝 Capture Note", use_container_width=True, key="btn_capture_note")

            if capture_button:
                if note_text.strip():
                    with st.spinner("Capturing note..."):
                        try:
                            from capture import capture_note
                            cid, cap_dir, md_path, json_path = capture_note(note_text)
                            st.markdown(
                                f"<div class='capture-success'>✅ Note captured<br>"
                                f"<span style='font-size:0.8rem;'>ID: {cid[:8]}... | 📁 {cap_dir.name}</span></div>",
                                unsafe_allow_html=True,
                            )
                            # Clear the input by rerunning
                            st.session_state["note_input"] = ""
                            st.rerun()
                        except Exception as e:
                            st.error(f"Capture failed: {e}")
                else:
                    st.warning("Please enter some note content.")

        elif capture_type == "Link":
            link_url = st.text_input(
                "URL",
                placeholder="https://example.com/article",
                label_visibility="collapsed",
                key="link_input",
            )
            capture_button = st.button("🔗 Capture Link", use_container_width=True, key="btn_capture_link")

            if capture_button:
                if link_url.strip():
                    with st.spinner("Fetching URL..."):
                        try:
                            from capture import capture_link
                            cid, cap_dir, md_path, json_path = capture_link(link_url)
                            st.markdown(
                                f"<div class='capture-success'>✅ Link captured<br>"
                                f"<span style='font-size:0.8rem;'>ID: {cid[:8]}... | 📁 {cap_dir.name}</span></div>",
                                unsafe_allow_html=True,
                            )
                            st.session_state["link_input"] = ""
                            st.rerun()
                        except Exception as e:
                            st.error(f"Link capture failed: {e}")
                else:
                    st.warning("Please enter a valid URL.")

        elif capture_type == "File":
            uploaded_file = st.file_uploader(
                "Choose a file",
                type=["txt", "md", "pdf", "py", "js", "html", "css", "json", "yaml", "yml", "toml", "cfg", "ini"],
                label_visibility="collapsed",
                key="file_input",
            )
            if uploaded_file is not None:
                if st.button("📄 Capture File", use_container_width=True, key="btn_capture_file"):
                    with st.spinner("Capturing file..."):
                        try:
                            # Save uploaded file temporarily
                            temp_dir = BASE_DIR / "data" / "temp"
                            temp_dir.mkdir(parents=True, exist_ok=True)
                            temp_path = temp_dir / uploaded_file.name
                            temp_path.write_bytes(uploaded_file.getvalue())

                            from capture import capture_file
                            cid, cap_dir, md_path, json_path = capture_file(str(temp_path))
                            st.markdown(
                                f"<div class='capture-success'>✅ File captured<br>"
                                f"<span style='font-size:0.8rem;'>ID: {cid[:8]}... | 📁 {cap_dir.name}</span></div>",
                                unsafe_allow_html=True,
                            )
                            # Clean up temp file
                            temp_path.unlink(missing_ok=True)
                            st.rerun()
                        except Exception as e:
                            st.error(f"File capture failed: {e}")

        # Divider
        st.markdown("<hr>", unsafe_allow_html=True)

        # Pipeline section
        st.markdown("## 🔄 Pipeline")
        st.markdown(
            "<p style='color:#888;font-size:0.85rem;'>Process captures → classify → link → build graph</p>",
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns(2)
        with col1:
            process_all = st.button(
                "⚡ Process All",
                use_container_width=True,
                key="btn_process_all",
                help="Classify + Link + Build Graph",
            )
        with col2:
            refresh_graph = st.button(
                "🔄 Refresh Graph",
                use_container_width=True,
                key="btn_refresh_graph",
                help="Rebuild the knowledge graph from wiki notes",
            )

        # Individual steps
        with st.expander("Individual Steps", expanded=False):
            classify_btn = st.button("🏷️ Classify Only", use_container_width=True, key="btn_classify")
            link_btn = st.button("🔗 Link Only", use_container_width=True, key="btn_link")
            graph_btn = st.button("📊 Build Graph Only", use_container_width=True, key="btn_graph")

        # Handle pipeline buttons
        if process_all:
            with st.spinner("Running full pipeline (classify → link → graph)..."):
                from pipeline import run_process
                success = run_process(dry_run=False, reprocess=False)
                if success:
                    st.markdown(
                        "<div class='pipeline-status'>✅ Pipeline complete! Graph rebuilt.</div>",
                        unsafe_allow_html=True,
                    )
                    # Clear caches so stats update
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Pipeline encountered errors. Check logs.")

        if refresh_graph:
            with st.spinner("Rebuilding knowledge graph..."):
                from build_graph import run as build_graph_run
                try:
                    graph = build_graph_run(pretty=True)
                    if graph and graph["metadata"]["node_count"] > 0:
                        st.markdown(
                            f"<div class='pipeline-status'>✅ Graph rebuilt: "
                            f"{graph['metadata']['node_count']} nodes, {graph['metadata']['edge_count']} edges</div>",
                            unsafe_allow_html=True,
                        )
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.warning("Graph built but no nodes found.")
                except Exception as e:
                    st.error(f"Graph build failed: {e}")

        if classify_btn:
            with st.spinner("Classifying unprocessed captures..."):
                from pipeline import run_classify
                count = run_classify(dry_run=False, reprocess=False)
                st.markdown(
                    f"<div class='pipeline-status'>✅ Classified {count} capture(s)</div>",
                    unsafe_allow_html=True,
                )
                st.cache_data.clear()

        if link_btn:
            with st.spinner("Auto-linking wiki notes..."):
                from pipeline import run_link
                count = run_link(dry_run=False, reprocess=False)
                st.markdown(
                    f"<div class='pipeline-status'>✅ Created {count} link(s)</div>",
                    unsafe_allow_html=True,
                )
                st.cache_data.clear()

        if graph_btn:
            with st.spinner("Building knowledge graph..."):
                from pipeline import run_graph
                success = run_graph(dry_run=False, pretty=True)
                if success:
                    st.markdown(
                        "<div class='pipeline-status'>✅ Graph rebuilt</div>",
                        unsafe_allow_html=True,
                    )
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Graph build failed.")

        # Divider
        st.markdown("<hr>", unsafe_allow_html=True)

        # Stats section
        st.markdown("## 📊 Stats")

        # Wiki stats
        try:
            wiki_stats = get_wiki_stats()
            embedding_stats = get_embedding_stats()
            graph_data = load_graph_data()

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Notes", wiki_stats["total"])
            with col2:
                st.metric("Embeddings", embedding_stats["total"])

            col1, col2 = st.columns(2)
            with col1:
                graph_nodes = graph_data.get("metadata", {}).get("node_count", len(graph_data.get("nodes", [])))
                st.metric("Graph Nodes", graph_nodes)
            with col2:
                graph_edges = graph_data.get("metadata", {}).get("edge_count", len(graph_data.get("edges", [])))
                st.metric("Connections", graph_edges)

            # PARA breakdown
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("**Notes by PARA**")
            for para in config.PARA_CATEGORIES:
                count = wiki_stats["by_para"].get(para, 0)
                bar_width = max(2, count * 10)
                st.markdown(
                    f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:4px;'>"
                    f"<span style='width:80px;font-size:0.8rem;color:#888;'>{para}</span>"
                    f"<span style='font-size:0.8rem;color:#aaa;'>{count}</span>"
                    f"<div style='flex:1;height:6px;background:rgba(255,255,255,0.06);border-radius:3px;'>"
                    f"<div style='width:{min(bar_width, 100)}%;height:100%;border-radius:3px;"
                    f"background:{['#7c3aed','#06b6d4','#10b981','#f59e0b'][config.PARA_CATEGORIES.index(para)]};'></div>"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )

            # Model info
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(
                f"<p style='color:#555;font-size:0.75rem;'>"
                f"Embedding model: {embedding_stats['model']}<br>"
                f"Similarity threshold: {config.SIMILARITY_THRESHOLD}<br>"
                f"Graph last built: {graph_data.get('metadata', {}).get('generated_at', 'N/A')[:19] or 'N/A'}"
                f"</p>",
                unsafe_allow_html=True,
            )

        except Exception as e:
            st.warning(f"Could not load stats: {e}")

        # Footer
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown(
            f"<p style='color:#444;font-size:0.7rem;text-align:center;'>"
            f"SecondSelf v2.0 · Built with Streamlit + Groq + sentence-transformers"
            f"</p>",
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Main panel
# ---------------------------------------------------------------------------

def render_main_panel():
    """Render the main content area with ask bar and knowledge graph."""
    # Title area
    st.markdown(
        f"""
        <div class="app-title">
            <h1>{APP_TITLE}</h1>
            <span class="status-badge active">● Online</span>
        </div>
        <p class="app-subtitle">{APP_SUBTITLE} — {APP_DESCRIPTION}</p>
        """,
        unsafe_allow_html=True,
    )

    # ── Ask Section ──
    st.markdown("### 💬 Ask Your Brain")
    st.markdown(
        "<p style='color:#888;font-size:0.85rem;'>Ask questions in plain English — get answers synthesized from your notes</p>",
        unsafe_allow_html=True,
    )

    # Question input
    col_q, col_btn = st.columns([5, 1])
    with col_q:
        question = st.text_input(
            "Your question",
            placeholder="e.g., What are my career goals? What ML resources have I saved?",
            label_visibility="collapsed",
            key="question_input",
        )
    with col_btn:
        ask_button = st.button("🔍 Ask", use_container_width=True, key="btn_ask")

    # Advanced options in expander
    with st.expander("⚙️ Retrieval Options", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            top_k = st.slider(
                "Number of notes to retrieve",
                min_value=1,
                max_value=20,
                value=config.TOP_K_RETRIEVAL,
                help="More notes = broader context, fewer = more focused",
            )
        with col2:
            threshold = st.slider(
                "Minimum relevance threshold",
                min_value=0.0,
                max_value=1.0,
                value=0.0,
                step=0.05,
                help="Higher values = only highly relevant notes",
            )

    # Process answer
    if ask_button and question.strip():
        with st.spinner("🔎 Searching your notes and synthesizing answer..."):
            try:
                from ask import ask as ask_question
                result: AskResult = ask_question(
                    question=question.strip(),
                    top_k=top_k,
                    threshold=threshold,
                )

                # Display the answer with clickable links — clean and minimal
                rendered_answer = render_answer_with_links(result.answer)
                st.markdown(
                    f"""<div class="answer-box">{rendered_answer}</div>""",
                    unsafe_allow_html=True,
                )

            except Exception as e:
                st.error(f"Failed to get answer: {e}")
                logger.error(f"Ask error: {e}", exc_info=True)

    elif ask_button and not question.strip():
        st.warning("Please enter a question first.")

    # Separator
    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Graph Section ──
    st.markdown("### 🕸️ Knowledge Graph")
    st.markdown(
        "<p style='color:#888;font-size:0.85rem;'>Explore connections between your notes — hover for details, click for full info</p>",
        unsafe_allow_html=True,
    )

    # Load the graph data for stats display
    graph_data = load_graph_data()
    node_count = graph_data.get("metadata", {}).get("node_count", len(graph_data.get("nodes", [])))
    edge_count = graph_data.get("metadata", {}).get("edge_count", len(graph_data.get("edges", [])))

    # Show graph stats
    if node_count > 0:
        st.markdown(
            f"<p style='color:#555;font-size:0.8rem;'>{node_count} nodes · {edge_count} connections</p>",
            unsafe_allow_html=True,
        )
    else:
        st.info("No graph data yet. Capture some notes and run the pipeline to build your knowledge graph.")

    # Embed the graph HTML
    try:
        graph_html = get_graph_html()
        # Use a container with a border
        st.components.v1.html(
            graph_html,
            height=580,
            scrolling=False,
        )
    except Exception as e:
        st.error(f"Failed to render graph: {e}")
        logger.error(f"Graph render error: {e}", exc_info=True)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def check_api_key():
    """Show a warning banner if GROQ_API_KEY is not configured."""
    if not config.GROQ_API_KEY:
        st.warning(
            "⚠️ **GROQ_API_KEY not configured.** "
            "The Ask and Pipeline (classify/link) features require a Groq API key. "
            "Set it via `.env` file locally or **Streamlit Secrets** in deployment.\n\n"
            "To set up locally:\n"
            "```\n"
            "echo GROQ_API_KEY=gsk_your_key_here > .env\n"
            "```\n\n"
            "The Knowledge Graph, Capture, and Stats will still work without it.",
            icon="🔑",
        )


def main():
    """Main entry point for the Streamlit app."""
    # Inject custom CSS
    inject_custom_css()

    # Check API key on startup
    check_api_key()

    # Pre-load embedding model in background (cached)
    try:
        load_embedding_model()
    except Exception as e:
        logger.warning(f"Could not pre-load embedding model: {e}")

    # Render sidebar
    render_sidebar()

    # Render main panel
    render_main_panel()


if __name__ == "__main__":
    main()

