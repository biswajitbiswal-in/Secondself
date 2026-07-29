"""SecondSelf UI package — premium dark-theme redesign.

All UI rendering lives here, organized by page.
Backend logic (storage, embeddings, LLM, pipeline) remains in the project root.
"""

# Import key components for easy access
from ui.theme import THEME, inject_custom_css, PARA_COLORS, PARA_EMOJIS

__all__ = ["THEME", "inject_custom_css", "PARA_COLORS", "PARA_EMOJIS"]

