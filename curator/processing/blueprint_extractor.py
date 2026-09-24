"""
curator/processing/blueprint_extractor.py

Generates deep engineering blueprints from ingested sources (GitHub repos,
video transcripts, technical articles).

Unlike a 1-sentence catalog summary, a blueprint contains:
1. Architecture & Component Layout
2. Low-Level Mechanics & Hooking Techniques
3. Core API Signatures & Data Structures
4. Production-Ready Code Recipes & Boilerplate
5. Compatibility Gotchas & Version Matrix
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from google.genai import types

from curator.config import GEMINI_API_KEYS, GEMINI_MODEL
from curator.models import KnowledgeEntry
from curator.processing.key_rotator import get_rotator

_BLUEPRINT_PROMPT = """\
You are an expert Principal Systems Engineer specializing in Android Internals, Linux Kernel, \
Root Solutions (Magisk, KernelSU, APatch), and Hook Frameworks (Zygisk, LSPosed).

Your goal is to extract a DEEP TECHNICAL BLUEPRINT from the following resource so that \
an autonomous AI agent or software engineer can build real software using these exact fundamentals.

SOURCE TITLE: {title}
SOURCE URL: {url}
SOURCE TYPE: {source_type}
CATEGORY: {category}

SOURCE RAW CONTENT / EXCERPTS:
{content}

Generate a comprehensive, production-grade technical blueprint formatted in clear Markdown.
Follow this EXACT structure:

# Blueprint: {title}

> **Source**: [{url}]({url})  
> **Category**: {category}  
> **Role in Ecosystem**: 1-2 sentences explaining what this does at the low-level architecture.

---

## 1. Architectural Layout & Entry Points
- Breakdown of core components and directories (e.g., kernel driver, daemon, JNI, manager app).
- Where the execution starts and how control is handed off.

## 2. Low-Level Mechanics & Hooking Techniques
- Exact hooking mechanisms used (e.g., `kprobes`, `fops` hijacking, `execve` interception, sepolicy injection, mount namespace unsharing).
- How it interacts with SELinux, Zygote, or the Android runtime.
- Detection evasion or systemless mounting strategies (overlayfs, tmpfs loop mounts).

## 3. Core API Signatures & Data Structures
- Key C/C++ or Kotlin/Rust structs, ioctl definitions, header definitions, or function signatures needed to interface with this system.
- Include code blocks with valid type signatures.

## 4. Copy-Paste Code Recipes & Boilerplate
- Provide at least ONE complete, functional, compilable minimal boilerplate template that an engineer can copy to build a module, driver patch, or client for this tool.
- Include proper headers, error checking, and comments.

## 5. Compatibility Matrix & Engineering Gotchas
- Android OS versions supported (e.g., Android 12 through Android 15).
- Kernel requirements (e.g., GKI 5.10+, Kprobes enabled, non-GKI backports).
- Known pitfalls, bootloop risks, or SELinux denials to watch out for.

---
Produce dense, accurate, highly technical content. Do NOT include hand-waving or generic filler.
"""


def _slugify(text: str) -> str:
    """Create a safe file slug from title/url."""
    # Remove protocol and owner if repo URL
    cleaned = text.split("/")[-1].lower()
    cleaned = re.sub(r"[^a-z0-9_-]", "_", cleaned)
    return cleaned.strip("_") or "blueprint"


def _call_extract_blueprint(client, prompt: str) -> str:
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=3000,
        ),
    )
    return response.text.strip()


def extract_blueprint(
    entry: KnowledgeEntry,
    blueprints_dir: Path,
) -> Optional[Path]:
    """
    Extract a technical blueprint and save it to blueprints/<slug>.md.
    Returns the Path to the written file, or None if extraction failed.
    """
    blueprints_dir.mkdir(parents=True, exist_ok=True)
    slug = _slugify(entry.title or entry.url)
    blueprint_file = blueprints_dir / f"{slug}.md"

    # If keys are available, use Gemini
    if GEMINI_API_KEYS:
        content_for_ai = (entry.raw_content or entry.description or entry.title)[:7000]
        prompt = _BLUEPRINT_PROMPT.format(
            title=entry.title,
            url=entry.url,
            source_type=entry.source_type.value,
            category=entry.category,
            content=content_for_ai,
        )

        try:
            rotator = get_rotator()
            markdown_content = rotator.with_retry(_call_extract_blueprint, prompt)
            blueprint_file.write_text(markdown_content, encoding="utf-8")
            print(f"  📄 Blueprint generated: {blueprint_file.name}")
            return blueprint_file
        except Exception as e:
            print(f"  ⚠️ Blueprint AI extraction error: {e}. Generating baseline template.")

    # Fallback: Generate structured baseline blueprint template
    baseline = f"""# Blueprint: {entry.title}

> **Source**: [{entry.url}]({entry.url})  
> **Category**: {entry.category}  
> **Status**: {entry.status.value}

---

## 1. Architectural Layout & Entry Points
- **Primary Source**: [{entry.url}]({entry.url})
- **Author/Maintainer**: {entry.author or 'Unknown'}
- **Tags**: {', '.join(f'`{t}`' for t in entry.tags)}

## 2. Low-Level Mechanics & Hooking Techniques
{entry.description}

## 3. Core API Signatures & Data Structures
*(Extracted from repository metadata and topics: {', '.join(entry.tags)})*

## 4. Copy-Paste Code Recipes & Boilerplate
```bash
# Clone and explore core fundamentals:
git clone {entry.url}
cd $(basename {entry.url})
```

## 5. Compatibility Matrix & Engineering Gotchas
- **Target OS**: {', '.join(entry.android_versions) if entry.android_versions else 'Android 9.0+'}
- **Supported Hardware**: {', '.join(entry.devices) if entry.devices else 'Generic ARM64'}
"""
    blueprint_file.write_text(baseline, encoding="utf-8")
    print(f"  📄 Baseline blueprint generated: {blueprint_file.name}")
    return blueprint_file
