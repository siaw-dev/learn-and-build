"""
curator/output/awesome_renderer.py

Renders the full knowledge base as a GitHub-style Awesome List README.md.
Uses Jinja2 template from templates/awesome_readme.md.j2.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from curator.config import ALL_CATEGORIES, README_PATH, STATUS_EMOJI, TEMPLATE_PATH
from curator.models import EntryStatus, KnowledgeEntry
from curator.storage.database import Database
from curator.storage.json_store import JsonStore


def _source_badge(source_type: str) -> str:
    badges = {
        "github": "![GitHub](https://img.shields.io/badge/-GitHub-181717?logo=github&logoColor=white&style=flat-square)",
        "youtube": "![YouTube](https://img.shields.io/badge/-YouTube-FF0000?logo=youtube&logoColor=white&style=flat-square)",
        "web": "![Web](https://img.shields.io/badge/-Article-0A66C2?logo=googlechrome&logoColor=white&style=flat-square)",
    }
    return badges.get(source_type, "")


def _load_all_entries(store) -> dict[str, list[KnowledgeEntry]]:
    """Load all entries grouped by category, supporting both JsonStore and Database."""
    if isinstance(store, JsonStore):
        all_entries = store.get_all()
    else:
        all_entries = asyncio.run(store.get_all())

    grouped: dict[str, list[KnowledgeEntry]] = {cat: [] for cat in ALL_CATEGORIES}
    grouped["Other"] = []

    for entry in all_entries:
        if entry.category in grouped:
            grouped[entry.category].append(entry)
        else:
            grouped["Other"].append(entry)

    return {k: v for k, v in grouped.items() if v}



def render_readme(db: Database, output_path: Path = README_PATH) -> int:
    """
    Render the awesome-list README.md from all DB entries.

    Args:
        db:          Database instance
        output_path: Where to write the README (default: project root README.md)

    Returns:
        Total number of entries rendered.
    """
    grouped = _load_all_entries(db)
    total = sum(len(v) for v in grouped.values())

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_PATH.parent)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.globals["source_badge"] = _source_badge
    env.globals["status_emoji"] = STATUS_EMOJI

    template = env.get_template(TEMPLATE_PATH.name)
    rendered = template.render(
        grouped=grouped,
        categories=list(grouped.keys()),
        total=total,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    return total
