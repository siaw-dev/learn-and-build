"""
curator/processing/summarizer.py

Uses Gemini (with automatic key rotation) to produce a concise 1-2 sentence
description for each entry. Falls back to the existing description if all
keys are exhausted or the call fails.

API: google-genai SDK >= 2.3.0 — uses client.interactions.create()
"""

from __future__ import annotations

from curator.config import GEMINI_API_KEYS, GEMINI_MODEL
from curator.models import KnowledgeEntry, SourceType
from curator.processing.key_rotator import get_rotator

_SUMMARIZE_PROMPT = """\
You are a skilled technical writer and software engineering analyst.

Write a concise, accurate 1-2 sentence description of the following technical
tool, project, library, article, or video suitable for an engineering knowledge base.
Be specific about what it does and why it matters. Do NOT start with "This is".

SOURCE TYPE: {source_type}
TITLE: {title}
CONTENT:
{content}

Respond with ONLY the description text (no quotes, no markdown).
"""

_PLACEHOLDERS = {
    "A GitHub repository.",
    "A web resource.",
}


def _call_summarize(client, prompt: str) -> str:
    """Inner function passed to rotator.with_retry(). Uses interactions.create()."""
    interaction = client.interactions.create(
        model=GEMINI_MODEL,
        input=prompt,
        generation_config={"temperature": 0.3, "max_output_tokens": 150},
    )
    return (interaction.output_text or "").strip().strip('"\'')


def summarize_entry(entry: KnowledgeEntry) -> KnowledgeEntry:
    """
    Generate a clean 1-2 sentence description using Gemini with key rotation.
    If no API keys available or all fail, retains the existing description.
    """
    # Skip if description already looks good
    if (entry.description
            and entry.description not in _PLACEHOLDERS
            and len(entry.description) > 40
            and entry.source_type != SourceType.YOUTUBE):
        return entry

    if not GEMINI_API_KEYS:
        # Graceful degradation: extract from raw content
        if entry.raw_content:
            lines = [l.strip() for l in entry.raw_content.splitlines() if l.strip()]
            text_lines = [l for l in lines if not any(
                l.startswith(p) for p in
                ("Name:", "Title:", "URL:", "Author:", "Stars:", "Language:")
            )]
            entry.description = " ".join(text_lines)[:220].strip() or entry.description
        return entry

    content_for_ai = (entry.raw_content or entry.description or entry.title)[:4000]
    prompt = _SUMMARIZE_PROMPT.format(
        source_type=entry.source_type.value,
        title=entry.title,
        content=content_for_ai,
    )

    try:
        rotator = get_rotator()
        summary = rotator.with_retry(_call_summarize, prompt)
        if summary:
            entry.description = summary
    except Exception as e:
        print(f"  ⚠️  Summarizer error ({type(e).__name__}). Keeping original description.")

    return entry
