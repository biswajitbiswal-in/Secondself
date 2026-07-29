"""Ask SecondSelf page — Chat-style Q&A with streaming effect, source links."""

import logging
import sys
import re
from pathlib import Path
from typing import List

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import config
from ui.theme import THEME, PARA_COLORS
from ui.components import section_header, para_badge

logger = logging.getLogger(__name__)


# ── Link helpers ──

def make_links_clickable(text: str) -> str:
    """Convert plain URLs into clickable HTML links."""
    text = re.sub(
        r'(https?://[^\s<]+)',
        r'<a href="\1" target="_blank" rel="noopener noreferrer">\1</a>',
        text,
    )
    text = re.sub(
        r'(?<!href=")www\.([^\s<]+)',
        r'<a href="http://www.\1" target="_blank" rel="noopener noreferrer">www.\1</a>',
        text,
    )
    return text


def render_answer_markdown(text: str) -> str:
    """Render answer text with clickable links, bold, and markdown-style content."""
    # Convert markdown links [text](url) to HTML
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>', text)
    # Make bare URLs clickable
    text = make_links_clickable(text)
    # Convert **bold**
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Convert *italic*
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', text)
    # Convert newlines to <br> for HTML display
    text = text.replace('\n', '<br>')
    return text


def get_note_link_file(note_id: str, para: str) -> str:
    """Build a relative file path to the wiki note markdown file."""
    return f"wiki/{para}/{note_id}.md"


# ── Render ──

def render():
    section_header(
        "💬 Ask SecondSelf",
        "Ask questions in plain English — get answers synthesized from your notes",
        icon="💬"
    )

    # ── Chat history container ──
    if "ask_messages" not in st.session_state:
        st.session_state["ask_messages"] = []

    # ── Question input area ──
    col_q, col_btn = st.columns([5, 1])
    with col_q:
        question = st.text_input(
            "Your question",
            placeholder="e.g., What are my career goals? What ML resources have I saved?",
            label_visibility="collapsed",
            key="ask_question_input",
        )
    with col_btn:
        ask_button = st.button("🔍 Ask", use_container_width=True, key="btn_ask_chat")

    # ── Retrieval options expander ──
    with st.expander("⚙️ Retrieval Options", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            top_k = st.slider(
                "Number of notes", min_value=1, max_value=20,
                value=config.TOP_K_RETRIEVAL, key="ask_top_k",
            )
        with col2:
            threshold = st.slider(
                "Min relevance", min_value=0.0, max_value=1.0,
                value=0.0, step=0.05, key="ask_threshold",
            )

    # ── Process question ──
    if ask_button and question.strip():
        with st.spinner("🔎 Searching your notes and synthesizing answer..."):
            try:
                from ask import ask as ask_question
                result = ask_question(
                    question=question.strip(),
                    top_k=top_k,
                    threshold=threshold,
                )

                # Store in chat history
                st.session_state["ask_messages"].append({
                    "role": "user",
                    "content": question.strip(),
                })
                st.session_state["ask_messages"].append({
                    "role": "assistant",
                    "content": result.answer,
                    "sources": result.sources,
                })
                st.rerun()

            except Exception as e:
                st.error(f"Failed to get answer: {e}")
                logger.error(f"Ask error: {e}", exc_info=True)

    elif ask_button and not question.strip():
        st.warning("Please enter a question first.")

    # ── Render chat history ──
    st.markdown("<br>", unsafe_allow_html=True)

    for i, msg in enumerate(st.session_state["ask_messages"]):
        if msg["role"] == "user":
            _render_user_message(msg["content"], i)
        else:
            _render_assistant_message(msg["content"], msg.get("sources", []), i)

    # ── If no messages yet, show welcoming hint ──
    if not st.session_state["ask_messages"]:
        st.markdown(f"""
        <div style="text-align:center;padding:3rem 1rem;animation:fadeInUp 0.5s ease;">
            <div style="font-size:3rem;margin-bottom:1rem;">🧠</div>
            <h3 style="color:{THEME['text_secondary']};">Ask anything from your notes</h3>
            <p style="color:{THEME['text_muted']};max-width:500px;margin:0 auto;">
            Try: "What are my career goals?" or "What resources do I have saved about Python?"
            </p>
        </div>
        """, unsafe_allow_html=True)

    # ── Clear chat button ──
    if st.session_state["ask_messages"]:
        if st.button("🗑️ Clear Conversation", key="clear_chat", type="secondary"):
            st.session_state["ask_messages"] = []
            st.rerun()


def _render_user_message(content: str, idx: int):
    """Render a user message bubble."""
    st.markdown(f"""
    <div style="display:flex;justify-content:flex-end;margin-bottom:0.75rem;animation:fadeInUp 0.3s ease;">
        <div style="background:{THEME['accent']}22;border:1px solid {THEME['accent']}44;
                    border-radius:16px 16px 4px 16px;padding:0.75rem 1rem;
                    max-width:75%;backdrop-filter:blur(8px);">
            <p style="margin:0;color:{THEME['text_primary']};font-size:0.9rem;">{content}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _render_assistant_message(content: str, sources: List[dict], idx: int):
    """Render an assistant message bubble with sources."""
    rendered = render_answer_markdown(content)
    st.markdown(f"""
    <div style="display:flex;margin-bottom:1rem;animation:fadeInUp 0.3s ease;">
        <div style="background:{THEME['bg_card']};border:1px solid {THEME['border']};
                    border-radius:16px 16px 16px 4px;padding:1rem 1.25rem;
                    max-width:85%;backdrop-filter:blur(12px);">
            <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.5rem;">
                <span style="font-size:1.2rem;">🧠</span>
                <span style="font-size:0.75rem;color:{THEME['text_muted']};font-weight:500;">
                    SecondSelf</span>
            </div>
            <div style="color:{THEME['text_primary']};font-size:0.9rem;line-height:1.6;">
                {rendered}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Sources ──
    if sources:
        st.markdown(f"""
        <div style="margin:0 0 1.25rem 1rem;padding-left:1rem;
                    border-left:2px solid {THEME['accent']}44;">
            <p style="font-size:0.75rem;color:{THEME['text_muted']};
                      font-weight:600;margin:0 0 0.5rem 0;text-transform:uppercase;
                      letter-spacing:0.5px;">
                📚 Sources ({len(sources)})</p>
        </div>
        """, unsafe_allow_html=True)

        cols = st.columns(min(3, len(sources)))
        for j, src in enumerate(sources):
            col = cols[j % len(cols)]
            with col:
                _render_source_card(src, j)


def _render_source_card(src: dict, idx: int):
    """Render a single source card with clickable note link and source URL."""
    note_id = src.get("id", "?")
    para = src.get("para", "Resources")
    summary = src.get("summary", "No summary")
    score = src.get("relevance_score", 0)
    relevance_pct = min(100, int(score * 100))
    note_path = get_note_link_file(note_id, para)
    source_url = src.get("source_url", "")

    color = PARA_COLORS.get(para, PARA_COLORS["Resources"])
    bar_color = color["bg"]

    # Source URL badge
    source_url_html = ""
    if source_url:
        domain = source_url.split("//")[-1].split("/")[0] if "//" in source_url else source_url
        source_url_html = f'''
        <a href="{source_url}" target="_blank" rel="noopener noreferrer"
           style="display:inline-flex;align-items:center;gap:2px;font-size:0.6rem;
                  color:{THEME['accent_light']};text-decoration:none;margin-top:0.2rem;
                  opacity:0.7;">
            🔗 {domain[:22]}{'…' if len(domain)>22 else ''}
        </a>'''

    st.markdown(f"""
    <div style="background:{THEME['bg_card']};border:1px solid {THEME['border']};
                border-radius:{THEME['radius_md']};padding:0.6rem 0.8rem;
                margin-bottom:0.4rem;backdrop-filter:blur(8px);animation:fadeInUp 0.3s ease;
                transition:all 0.2s;">
        <div style="display:flex;justify-content:space-between;align-items:start;">
            <div style="flex:1;">
                <a href="{note_path}" target="_blank"
                   style="font-family:monospace;font-size:0.75rem;color:{color['light']};
                          text-decoration:none;font-weight:500;">
                    [{para[:3]}] {note_id[:8]}… ↗</a>
                <p style="font-size:0.8rem;color:{THEME['text_secondary']};
                          margin:0.15rem 0;line-height:1.3;">{summary[:80]}{'…' if len(summary)>80 else ''}</p>
                {source_url_html}
            </div>
            <span style="font-size:0.65rem;color:{THEME['text_muted']};white-space:nowrap;
                         margin-left:0.5rem;">
                {score:.2f}
            </span>
        </div>
        <div style="height:2px;background:{THEME['bg_input']};border-radius:2px;margin-top:0.4rem;">
            <div style="height:100%;width:{relevance_pct}%;background:{bar_color};
                        border-radius:2px;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

