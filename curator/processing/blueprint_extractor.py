"""
curator/processing/blueprint_extractor.py

Universal Engineering Blueprint Extractor.

Extracts deep, production-grade architectural and algorithmic fundamentals
from ANY technical resource (GitHub repo, YouTube lecture/tutorial, technical doc)
across any domain:
  - Systems, Kernels, Drivers & Low-Level Engineering
  - Security, Reverse Engineering & Exploit Development
  - Distributed Systems, Databases & Concurrency
  - Compilers, Bytecode VMs & Language Runtimes
  - AI/ML Infrastructure & Autonomous Agent Frameworks
  - Web Platforms, API Protocols & Network Stacks
  - Embedded, Firmware & Hardware Interfacing

Outputs dense, complete blueprints so an autonomous AI agent or software engineer
can build production software adhering to those exact fundamentals.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from curator.config import GEMINI_API_KEYS, GEMINI_MODEL
from curator.models import KnowledgeEntry
from curator.processing.key_rotator import get_rotator

_UNIVERSAL_BLUEPRINT_PROMPT = """\
You are a Principal Software Architect, Systems Engineer, and Low-Level Specialist.

Your task is to extract a DEEP, UNCONSTRAINED TECHNICAL BLUEPRINT from the following technical resource \
so that an autonomous software engineering agent can directly build production software based on these exact fundamentals.

SOURCE METADATA:
Title: {title}
URL: {url}
Source Type: {source_type}
Assigned Category: {category}

SOURCE RAW EXTRACTS / TREE / CODE / CONTENT:
{content}

---

Generate a comprehensive, dense, zero-handwaving Markdown technical blueprint.
Do NOT limit the scope to any single platform unless the source itself is platform-specific.
Analyze whatever domain this resource belongs to (Linux/Unix, Android, Windows, Web, Embedded, Distributed, AI, Compiler, etc.).

Format the blueprint using this EXACT comprehensive specification:

# Blueprint: {title}

> **Source**: [{url}]({url})  
> **Domain / Category**: {category}  
> **Core Architectural Purpose**: 2-3 precise sentences defining what problem this system solves and its exact architectural mechanism.

---

## 1. Architectural Topology & Entry Points
- **System Boundaries**: How components communicate (IPC, FFI, syscalls, REST/gRPC, shared memory, event loops).
- **Directory & Component Map**: Where core logic, drivers, engines, state stores, and entrypoints live.
- **Lifecycle & Execution Flow**: Step-by-step trace from initialization/startup to active state and termination.

## 2. Core Mechanisms, Algorithms & Low-Level Techniques
- **Fundamental Invariants**: The core algorithms, state machines, protocol handshakes, memory management strategies, or hook mechanisms.
- **Subsystem Interfacing**: How it interfaces with the OS kernel, hardware, runtime, or network (e.g. syscalls, memory mapping, interrupts, zero-copy buffers, seccomp/selinux, JNI).
- **Security & Integrity Model**: Permissions, privilege boundaries, isolation, cryptography, or anti-detection / bypass mechanics if applicable.

## 3. Data Contracts, Structs & Core API Signatures
- Exact schemas, C/Rust structs, Go interfaces, Kotlin/TypeScript types, or protocol headers needed to interface with or extend this system.
- Include complete code blocks with valid type signatures.

## 4. Production-Ready Scaffolding Boilerplate (Copy-Paste)
- Provide at least ONE complete, functional, compilable/runnable minimal template that an engineer or AI can copy to build a compatible module, plugin, client, driver, or service.
- Must contain real imports, error handling, configuration, and execution logic.
- NEVER use lazy comments like `// implement your logic here`. Write out working fundamental logic.

## 5. Engineering Invariants, Tradeoffs & Gotchas
- **Performance & Concurrency Characteristics**: Locking strategies, lock-free queues, cache locality, async models, or overhead.
- **Failure Modes & Edge Cases**: Race conditions, memory leaks, compatibility cliffs across OS/library versions.
- **Hard Prerequisites**: Compilers, toolchains, kernel configs, or environment capabilities required.

---
Produce dense, accurate, highly technical content. Focus purely on engineering reality.
"""


def _slugify(text: str) -> str:
    """Create a safe file slug from title/url."""
    cleaned = text.split("/")[-1].lower()
    cleaned = re.sub(r"[^a-z0-9_-]", "_", cleaned)
    return cleaned.strip("_") or "blueprint"


def _call_extract_blueprint(client, prompt: str) -> str:
    """Inner function passed to rotator.with_retry(). Uses interactions.create()."""
    interaction = client.interactions.create(
        model=GEMINI_MODEL,
        input=prompt,
        generation_config={"temperature": 0.2, "max_output_tokens": 3000},
    )
    return (interaction.output_text or "").strip()


def extract_blueprint(
    entry: KnowledgeEntry,
    blueprints_dir: Path,
) -> Optional[Path]:
    """
    Extract an unconstrained, domain-adaptive technical blueprint and save it to blueprints/<slug>.md.
    Returns the Path to the written file, or None if extraction failed.
    """
    blueprints_dir.mkdir(parents=True, exist_ok=True)
    slug = _slugify(entry.title or entry.url)
    blueprint_file = blueprints_dir / f"{slug}.md"

    if GEMINI_API_KEYS:
        content_for_ai = (entry.raw_content or entry.description or entry.title)[:8000]
        prompt = _UNIVERSAL_BLUEPRINT_PROMPT.format(
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
            entry.blueprint_status = "verified"
            print(f"  📄 Blueprint generated (verified): {blueprint_file.name}")
            return blueprint_file
        except Exception as e:
            print(f"  ⚠️ Blueprint AI extraction error ({type(e).__name__}: {e}). Generating baseline stub.")

    # Universal fallback template (marked explicitly as stub)
    entry.blueprint_status = "stub"
    baseline = f"""# Blueprint: {entry.title}

> **Source**: [{entry.url}]({entry.url})  
> **Domain / Category**: {entry.category}  
> **Status**: {entry.status.value} (Baseline Stub)

---

## 1. Architectural Topology & Entry Points
- **Primary Source**: [{entry.url}]({entry.url})
- **Author/Organization**: {entry.author or 'Unknown'}
- **Tags & Specializations**: {', '.join(f'`{t}`' for t in entry.tags)}

## 2. Core Mechanisms, Algorithms & Low-Level Techniques
{entry.description}

## 3. Data Contracts, Structs & Core API Signatures
*(Derived from repository topics: {', '.join(entry.tags)})*

## 4. Production-Ready Scaffolding Boilerplate
```bash
# Clone source repository to inspect implementation fundamentals:
git clone {entry.url}
cd $(basename {entry.url})
```

## 5. Engineering Invariants, Tradeoffs & Gotchas
- **Target Environments**: {', '.join(entry.android_versions) if entry.android_versions else 'Cross-platform / POSIX'}
- **Target Architectures / Platforms**: {', '.join(entry.devices) if entry.devices else 'Any'}
"""
    blueprint_file.write_text(baseline, encoding="utf-8")
    print(f"  📄 Baseline stub blueprint generated: {blueprint_file.name}")
    return blueprint_file
