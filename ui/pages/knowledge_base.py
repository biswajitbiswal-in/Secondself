"""Knowledge Base page — Browse, search, filter notes with card grid view."""

import logging
import sys
from pathlib import Path
from typing import List

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import config
from ui.theme import THEME, PARA_COLORS
from ui.components import section_header, empty_state, para_badge

logger = logging.getLogger(__name__)


@st.cache_data(ttl=60)
def _load_notes():
    """Load all wiki notes with caching."""
    from lib.storage import read_wiki_notes
    return read_wiki_notes()


def render():
    section_header(
        "📖 Knowledge Base",
        "Browse, search, and filter all your notes",
        icon="📖"
    )

    notes = _load_notes()

    if not notes:
        empty_state(
            icon="📭",
            title="No notes yet",
            description="Capture some notes and run the classification pipeline to build your knowledge base.",
            action_label="📥 Go to Capture",
            action_key="kb_goto_capture",
        )
        if st.session_state.get("kb_goto_capture"):
            st.session_state["nav"] = "capture"
            st.rerun()
        return

    # ── Search and Filters ──
    col1, col2, col3 = st.columns([3, 2, 2])
    with col1:
        search_query = st.text_input(
            "Search notes",
            placeholder="🔍 Search by title, summary, or tags...",
            label_visibility="collapsed",
            key="kb_search",
        ).strip().lower()
    with col2:
        selected_para = st.selectbox(
            "Category",
            options=["All"] + config.PARA_CATEGORIES,
            key="kb_para_filter",
            label_visibility="collapsed",
        )
    with col3:
        sort_by = st.selectbox(
            "Sort by",
            options=["Newest First", "Oldest First", "Title A-Z", "Title Z-A"],
            key="kb_sort",
            label_visibility="collapsed",
        )

    # ── Filter notes ──
    filtered = notes[:]
    if selected_para != "All":
        filtered = [n for n in filtered if n.para == selected_para]
    if search_query:
        filtered = [
            n for n in filtered
            if search_query in n.summary.lower()
            or search_query in n.body.lower()
            or any(search_query in t.lower() for t in n.tags)
            or search_query in n.id.lower()
        ]

    # Sort
    if sort_by == "Newest First":
        filtered.sort(key=lambda n: n.created, reverse=True)
    elif sort_by == "Oldest First":
        filtered.sort(key=lambda n: n.created)
    elif sort_by == "Title A-Z":
        filtered.sort(key=lambda n: n.summary.lower())
    elif sort_by == "Title Z-A":
        filtered.sort(key=lambda n: n.summary.lower(), reverse=True)

    # ── Results count ──
    st.markdown(f"""
    <p style="color:{THEME['text_muted']};font-size:0.85rem;margin-bottom:0.75rem;">
        Showing {len(filtered)} of {len(notes)} notes</p>
    """, unsafe_allow_html=True)

    # ── Note Cards Grid ──
    if not filtered:
        st.markdown(f"""
        <div style="text-align:center;padding:3rem 1rem;">
            <div style="font-size:2.5rem;margin-bottom:0.75rem;">🔍</div>
            <p style="color:{THEME['text_muted']};">No notes match your search criteria.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    # Display in columns
    cols_per_row = 3
    for i in range(0, len(filtered), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, note in enumerate(filtered[i:i + cols_per_row]):
            with cols[j]:
                _render_note_card(note)


def _render_note_card(note):
    """Render a single note card."""
    note_path = f"wiki/{note.para}/{note.id}.md"
    color = PARA_COLORS.get(note.para, PARA_COLORS["Resources"])
    tag_html = " ".join(
        f'<span style="display:inline-block;background:rgba(255,255,255,0.04);'
        f'padding:1px 6px;border-radius:3px;font-size:0.65rem;color:{THEME["text_muted"]};'
        f'margin-right:3px;">{t}</span>'
        for t in note.tags[:4]
    )
    if len(note.tags) > 4:
        tag_html += f'<span style="font-size:0.65rem;color:{THEME["text_dim"]};">+{len(note.tags)-4}</span>'

    body_preview = (note.body or "")[:120].strip()
    if len(body_preview) >= 120:
        body_preview += "…"

    # Source URL badge/link (if available)
    source_url_html = ""
    if note.source_url:
        domain = note.source_url.split("//")[-1].split("/")[0] if "//" in note.source_url else note.source_url
        source_url_html = f'''
        <a href="{note.source_url}" target="_blank" rel="noopener noreferrer"
           style="display:inline-flex;align-items:center;gap:3px;font-size:0.65rem;
                  color:{THEME['accent_light']};text-decoration:none;margin-top:0.3rem;
                  border:1px solid rgba(167,139,250,0.15);border-radius:4px;
                  padding:1px 6px;transition:all 0.2s;">
            🔗 {domain[:25]}{'…' if len(domain)>25 else ''}
        </a>'''

    st.markdown(f"""
    <a href="{note_path}" target="_blank" style="text-decoration:none;display:block;">
    <div style="background:{THEME['bg_card']};border:1px solid {THEME['border']};
                border-left:3px solid {color['bg']};
                border-radius:{THEME['radius_md']};padding:1rem;
                backdrop-filter:blur(12px);transition:all 0.25s;
                margin-bottom:0.75rem;min-height:140px;
                animation:fadeInUp 0.3s ease;">
        <div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:0.4rem;">
            <span style="font-size:0.65rem;font-family:monospace;color:{THEME['text_dim']};">{note.id[:10]}…</span>
            {para_badge(note.para, size="sm")}
        </div>
        <p style="font-size:0.85rem;color:{THEME['text_primary']};font-weight:500;
                  margin:0 0 0.35rem 0;line-height:1.3;">
            {note.summary[:90]}{'…' if len(note.summary)>90 else ''}</p>
        {f'<p style="font-size:0.75rem;color:{THEME["text_muted"]};margin:0 0 0.4rem 0;line-height:1.3;">{body_preview}</p>' if body_preview else ''}
        {f'<div style="margin-top:0.4rem;">{tag_html}</div>' if tag_html else ''}
        {source_url_html}
    </div>
    </a>
    """, unsafe_allow_html=True)

