"""
curator/processing/classifier.py

Uses the Gemini API (with automatic key rotation across up to 8 keys)
to classify a raw KnowledgeEntry into the domain taxonomy.

Falls back to keyword-based heuristic classification if all API keys
are exhausted or unavailable.

API: google-genai SDK >= 2.3.0 — uses client.interactions.create()
"""

from __future__ import annotations

import json
import re

from curator.config import ALL_CATEGORIES, GEMINI_API_KEYS, GEMINI_MODEL, TAXONOMY
from curator.models import EntryStatus, KnowledgeEntry
from curator.processing.key_rotator import get_rotator

_CLASSIFICATION_PROMPT = """\
You are an expert software engineering analyst.

Given the content below about a technical tool, project, video, or article,
classify it using ONLY the taxonomy provided. The resource may be from any
engineering domain (systems, AI, web, compilers, embedded, databases, etc.).

TAXONOMY (categories and example subcategories):
{taxonomy}

CONTENT:
{content}

Respond with ONLY a valid JSON object (no markdown fences) containing:
{{
  "category": "<one of the category names above>",
  "subcategory": "<optional subcategory, or empty string>",
  "tags": ["<tag1>", "<tag2>", ...],
  "android_versions": ["<e.g. Android 13>", "<Android 14>"],
  "devices": ["<e.g. Qualcomm>", "<Samsung>", "<all>"],
  "status": "<active|archived|deprecated|experimental>"
}}

Rules:
- category MUST be exactly one of the listed category names.
- tags should be lowercase, specific, and useful for search (3-8 tags).
- android_versions: list only if explicitly relevant; otherwise use [].
- devices: list chipset families or manufacturers if relevant; otherwise ["all"].
- status: use "archived" only if the content explicitly says it's discontinued.
"""


def _build_taxonomy_text() -> str:
    lines = []
    for cat, examples in TAXONOMY.items():
        lines.append(f"- {cat}: {', '.join(examples[:3])}, ...")
    return "\n".join(lines)


def _call_classify(client, prompt: str) -> dict:
    """Inner function passed to rotator.with_retry(). Uses interactions.create()."""
    interaction = client.interactions.create(
        model=GEMINI_MODEL,
        input=prompt,
        generation_config={"temperature": 0.1, "max_output_tokens": 512},
    )
    raw = (interaction.output_text or "").strip()
    raw = re.sub(r"^```[a-z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw)


def classify_entry(entry: KnowledgeEntry) -> KnowledgeEntry:
    """
    Classify a raw entry using Gemini with automatic key rotation.
    Falls back to keyword heuristics if no API keys are available.
    """
    if not GEMINI_API_KEYS:
        return _heuristic_classify(entry)

    taxonomy_text = _build_taxonomy_text()
    content_for_ai = (entry.raw_content or f"{entry.title}\n{entry.description}")[:5000]
    prompt = _CLASSIFICATION_PROMPT.format(taxonomy=taxonomy_text, content=content_for_ai)

    try:
        rotator = get_rotator()
        data = rotator.with_retry(_call_classify, prompt)

        entry.category = data.get("category", "Uncategorized")
        if entry.category not in ALL_CATEGORIES:
            entry.category = _best_category_match(entry.category)

        entry.subcategory = data.get("subcategory") or None
        entry.tags = data.get("tags", entry.tags)
        entry.android_versions = data.get("android_versions", [])
        entry.devices = data.get("devices", [])

        raw_status = data.get("status", "active").lower()
        try:
            entry.status = EntryStatus(raw_status)
        except ValueError:
            entry.status = EntryStatus.ACTIVE

    except Exception as e:
        print(f"  ⚠️  Classifier error ({type(e).__name__}). Using heuristic fallback.")
        entry = _heuristic_classify(entry)

    return entry


def _best_category_match(raw: str) -> str:
    raw_lower = raw.lower()
    for cat in ALL_CATEGORIES:
        if any(word in raw_lower for word in cat.lower().split()):
            return cat
    return "Tools, CLI & Utilities"


def _heuristic_classify(entry: KnowledgeEntry) -> KnowledgeEntry:
    """Keyword-based fallback when Gemini is unavailable."""
    combined = (entry.title + " " + " ".join(entry.tags) + " " +
                (entry.description or "")).lower()

    rules = [
        (["magisk", "kernelsu", "apatch", "supersu", "root solution"], "Root Solutions"),
        (["bootloader", "fastboot", "oem unlock", "edl", "9008"], "Bootloaders & Partitions"),
        (["kernel", "gki", "kprobes", "lkm", "ebpf", "driver"], "Kernel & Low-Level Systems"),
        (["zygisk", "lsposed", "xposed", "riru", "frida", "hook"], "Runtime Injection & Hooks"),
        (["module", "overlay", "systemless", "plugin"], "Modules & Extensions"),
        (["safetynet", "play integrity", "detection", "bypass", "ghidra", "reverse"], "Security & Reverse Engineering"),
        (["llm", "agent", "ml", "ai", "inference", "vector", "embedding"], "AI, Agents & Machine Learning"),
        (["compiler", "jit", "bytecode", "ast", "linker", "runtime"], "Compilers & Language Runtimes"),
        (["database", "storage", "raft", "kafka", "queue", "cache"], "Distributed Systems & Storage"),
        (["http", "grpc", "websocket", "server", "api", "protocol"], "Web Architecture & Protocols"),
        (["rtos", "microcontroller", "firmware", "embedded", "spi", "i2c"], "Embedded & Firmware"),
        (["tutorial", "guide", "how to", "learn", "walkthrough"], "Tutorials & Deep Dives"),
        (["tool", "cli", "adb", "script", "utility"], "Tools, CLI & Utilities"),
    ]

    for keywords, category in rules:
        if any(kw in combined for kw in keywords):
            entry.category = category
            return entry

    entry.category = "Tools, CLI & Utilities"
    return entry
