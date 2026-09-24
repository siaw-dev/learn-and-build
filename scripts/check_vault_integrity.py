#!/usr/bin/env python3
"""
scripts/check_vault_integrity.py

Automated vault integrity and quality gate validator.
Validates schemas, blueprint file existence, markdown section completeness, and facts integrity.
Run locally or in GitHub Actions CI.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import re

REQUIRED_BP_PATTERNS = [
    (r"# Blueprint:", "Blueprint Header (# Blueprint:)"),
    (r"## 1\.\s+Architectural\s+(Topology|Layout)", "Section 1: Architectural Topology / Layout"),
    (r"## 2\.\s+(Core Mechanisms|Low-Level Mechanics)", "Section 2: Core Mechanisms / Mechanics"),
    (r"## 3\.\s+(Data Contracts|Core API)", "Section 3: Data Contracts / Core APIs"),
    (r"## 4\.\s+(Production-Ready|Copy-Paste)", "Section 4: Production Scaffolding / Code Recipes"),
    (r"## 5\.\s+(Engineering Invariants|Compatibility Matrix)", "Section 5: Engineering Invariants / Gotchas"),
]

def main() -> int:
    root = Path(__file__).resolve().parent.parent
    knowledge_path = root / "data" / "knowledge.json"
    facts_path = root / "data" / "facts.json"
    blueprints_dir = root / "blueprints"

    errors: list[str] = []
    warnings: list[str] = []

    print("🔍 Validating Learn & Build Vault Integrity...")

    # 1. Validate knowledge.json
    if not knowledge_path.exists():
        errors.append(f"Missing {knowledge_path}")
    else:
        try:
            entries = json.loads(knowledge_path.read_text(encoding="utf-8"))
            if not isinstance(entries, list):
                errors.append(f"{knowledge_path} is not a JSON array")
            else:
                print(f"  ✓ {knowledge_path.name}: {len(entries)} entries parsed")
                for i, e in enumerate(entries):
                    title = e.get("title", f"Entry #{i}")
                    bp_file = e.get("blueprint_file")
                    bp_status = e.get("blueprint_status", "stub")

                    if not bp_file:
                        errors.append(f"[{title}] missing blueprint_file")
                        continue

                    full_bp = root / bp_file
                    if not full_bp.exists():
                        errors.append(f"[{title}] referenced blueprint does not exist: {bp_file}")
                        continue

                    content = full_bp.read_text(encoding="utf-8")
                    if bp_status == "verified":
                        if len(content) < 2000:
                            errors.append(f"[{title}] marked verified but file is only {len(content)} bytes")
                        for pattern, label in REQUIRED_BP_PATTERNS:
                            if not re.search(pattern, content, re.MULTILINE):
                                errors.append(f"[{title}] verified blueprint missing {label}")
                    else:
                        warnings.append(f"[{title}] blueprint is a baseline stub ({len(content)} bytes)")
        except Exception as ex:
            errors.append(f"Failed to parse {knowledge_path}: {ex}")

    # 2. Validate facts.json
    if facts_path.exists():
        try:
            facts = json.loads(facts_path.read_text(encoding="utf-8"))
            if not isinstance(facts, list):
                errors.append(f"{facts_path} is not a JSON array")
            else:
                print(f"  ✓ {facts_path.name}: {len(facts)} facts parsed")
                for i, f in enumerate(facts):
                    if not f.get("fact"):
                        errors.append(f"Fact #{i} missing 'fact' field")
                    if not f.get("domain"):
                        warnings.append(f"Fact #{i} missing 'domain' field")
        except Exception as ex:
            errors.append(f"Failed to parse {facts_path}: {ex}")

    # 3. Report
    print("\n--- Integrity Summary ---")
    if warnings:
        print(f"⚠️  {len(warnings)} Warning(s):")
        for w in warnings:
            print(f"   • {w}")

    if errors:
        print(f"\n❌ {len(errors)} Error(s) encountered:")
        for err in errors:
            print(f"   ✖ {err}")
        return 1

    print("✅ All vault assets, blueprints, and schemas are 100% valid!\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
