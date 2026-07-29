"""
Groq LLM API wrapper for SecondSelf.

Provides:
  - call_llm(): Generic Groq API call with retry + backoff
  - classify_content(): Returns {para, tags[], summary} for a given text
  - synthesize_answer(): RAG answer synthesis (used in Phase 4)
"""

import json
import logging
import time
from typing import Optional

from groq import Groq

import config

logger = logging.getLogger(__name__)

# Maximum retries for API calls
MAX_RETRIES = 3
# Base delay in seconds for exponential backoff
RETRY_BASE_DELAY = 2.0

# System prompts
CLASSIFY_SYSTEM_PROMPT = """You are a personal knowledge librarian using the PARA method.
Given a piece of content (personal note, bookmark, or file), classify it into exactly one PARA category, generate relevant tags, and provide a one-line summary.

PARA Categories:
- Projects: Active work items with a specific outcome or deadline. Things I'm actively working on.
- Areas: Ongoing responsibilities or domains of interest with no fixed deadline. Things I'm responsible for over time.
- Resources: Reference material, learning resources, articles, papers, or information I want to keep. Topics or interests.
- Archives: Completed projects, inactive items, or things no longer relevant.

Return ONLY valid JSON with exactly these fields:
{
  "para": "Projects|Areas|Resources|Archives",
  "tags": ["tag1", "tag2", "tag3"],
  "summary": "One concise sentence summarizing what this is about."
}

Be specific with tags (2-4 tags). The summary should be clear and descriptive."""


def _get_client() -> Groq:
    """Initialize and return the Groq client."""
    api_key = config.GROQ_API_KEY
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. "
            "Add it to your .env file: GROQ_API_KEY=gsk_your_key_here"
        )
    return Groq(api_key=api_key)


def call_llm(
    prompt: str,
    system: str = "",
    model: str = "",
    temperature: float = 0.3,
    max_tokens: int = 1024,
) -> str:
    """
    Call the Groq LLM with the given prompt and system message.

    Args:
        prompt: The user prompt / question.
        system: Optional system prompt to set context.
        model: Model name (defaults to config.GROQ_MODEL).
        temperature: LLM temperature (0.0 = deterministic, 1.0 = creative).
        max_tokens: Maximum tokens in the response.

    Returns:
        The LLM response text.

    Raises:
        RuntimeError: If all retries fail.
    """
    model = model or config.GROQ_MODEL
    client = _get_client()

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            logger.debug(f"LLM call (attempt {attempt + 1}/{MAX_RETRIES}) to {model}")
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            last_error = e
            logger.warning(f"LLM call failed (attempt {attempt + 1}): {e}")
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                logger.info(f"Retrying in {delay:.1f}s...")
                time.sleep(delay)

    raise RuntimeError(f"LLM call failed after {MAX_RETRIES} attempts: {last_error}")


def classify_content(text: str) -> dict:
    """
    Classify a piece of text into PARA category + tags + summary.

    Args:
        text: The extracted text content to classify.

    Returns:
        dict with keys: para, tags (list), summary (str)
        Falls back to {"para": "Resources", "tags": [], "summary": ""} on failure.
    """
    if not text or not text.strip():
        logger.warning("Empty text provided for classification.")
        return {"para": "Resources", "tags": [], "summary": "Empty content"}

    # Truncate text to avoid token limits
    max_chars = config.MAX_CONTENT_CHARS
    truncated_text = text[:max_chars]
    if len(text) > max_chars:
        truncated_text += "\n\n[...content truncated]"

    prompt = f"""Given this captured content, classify it using the PARA method.

Content:
---
{truncated_text}
---

Return ONLY valid JSON: {{
  "para": "Projects|Areas|Resources|Archives",
  "tags": ["tag1", "tag2", ...],
  "summary": "One-line summary"
}}"""

    try:
        response = call_llm(
            prompt=prompt,
            system=CLASSIFY_SYSTEM_PROMPT,
            temperature=0.1,  # Lower temperature for classification
        )

        # Try to parse JSON from the response
        result = _parse_json_response(response)
        if result and "para" in result:
            # Validate PARA category
            para = result["para"]
            if para not in config.PARA_CATEGORIES:
                logger.warning(f"Invalid PARA category '{para}', defaulting to 'Resources'")
                result["para"] = "Resources"

            # Ensure tags is a list
            if not isinstance(result.get("tags"), list):
                result["tags"] = []

            # Ensure summary is a string
            if not isinstance(result.get("summary"), str):
                result["summary"] = ""

            return result

    except Exception as e:
        logger.error(f"Classification failed: {e}")

    # Fallback
    return {"para": "Resources", "tags": [], "summary": ""}


def _parse_json_response(response: str) -> Optional[dict]:
    """
    Attempt to parse JSON from an LLM response.

    Handles:
      - Raw JSON output
      - JSON wrapped in markdown code blocks
    """
    # Try direct JSON parsing first
    text = response.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting JSON from markdown code blocks
    import re
    json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try finding JSON-like structure with regex
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    logger.warning(f"Could not parse JSON from LLM response: {text[:200]}...")
    return None


def synthesize_answer(context: str, question: str) -> str:
    """
    Synthesize an answer from retrieved note context.

    This is used in Phase 4 (The Oracle) for RAG-based Q&A.

    Args:
        context: Concatenated note content for RAG context.
        question: The user's question.

    Returns:
        Synthesized answer string.
    """
    system_prompt = """You are SecondSelf, an AI assistant answering from the user's personal knowledge base.
Use ONLY the provided notes to answer. If the answer isn't in the notes, say so clearly.

IMPORTANT RULES:
1. Each note has a relevance label (HIGH, MEDIUM, or LOW). Prioritize HIGH relevance notes.
2. Ignore LOW relevance notes unless they contain information not found in HIGH/MEDIUM notes.
3. Cite sources using [note-id] notation only when referencing specific information from a note.
4. If only LOW relevance notes are available and they don't actually answer the question, say "I don't have specific notes about that."
5. Be concise and precise — do not include information from irrelevant notes just because they are provided.
6. LINK FORMATTING: When you mention URLs (like python.org, github.com, linkedin.com etc.), ALWAYS format them as complete clickable markdown links: [text](url). For example, write [python.org](https://python.org) instead of just python.org. This ensures links are clickable in the final HTML output.
7. STRUCTURE: Use sections with **bold headers** where appropriate. Use bullet points for lists. Keep paragraphs short and scannable."""

    prompt = f"""Here are the relevant notes from my personal knowledge base:

{context}

Question: {question}

Answer using ONLY the information in these notes. If the notes don't contain the answer, say "I don't have any notes about that."""

    return call_llm(
        prompt=prompt,
        system=system_prompt,
        temperature=0.3,
        max_tokens=2048,
    )

