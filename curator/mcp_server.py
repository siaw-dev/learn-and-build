"""
curator/mcp_server.py

Model Context Protocol (MCP) server for Learn & Build Knowledge Vault.
Implements the JSON-RPC 2.0 stdio protocol with zero external dependencies.
Exposes tools and resources to Antigravity, Claude Code, and autonomous AI agents.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
_JSON_PATH = _ROOT / "data" / "knowledge.json"
_FACTS_PATH = _ROOT / "data" / "facts.json"
_BLUEPRINTS_DIR = _ROOT / "blueprints"

TOOLS_SCHEMA = [
    {
        "name": "search_blueprints",
        "description": "Search the Learn & Build vault for architectural blueprints matching a technology, keyword, syscall, or pattern.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search keyword, technology name, or pattern (e.g. 'retrofit', 'ebpf', 'kprobe', 'http')"},
                "category": {"type": "string", "description": "Optional category filter (e.g. 'Root Solutions', 'Web Architecture & Protocols')"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_blueprint",
        "description": "Retrieve the full verified architectural blueprint and production code recipes for a given technology or slug.",
        "parameters": {
            "type": "object",
            "properties": {
                "slug": {"type": "string", "description": "Slug or technology name (e.g. 'retrofit', 'guava', 'kernelsu')"},
            },
            "required": ["slug"],
        },
    },
    {
        "name": "record_field_note",
        "description": "Append a battle-tested runtime gotcha or production field note directly into a blueprint's Section 5.",
        "parameters": {
            "type": "object",
            "properties": {
                "slug": {"type": "string", "description": "Blueprint slug (e.g. 'retrofit', 'kernelsu')"},
                "note": {"type": "string", "description": "Field note or gotcha description"},
                "tag": {"type": "string", "description": "Optional tag (e.g. 'proguard', 'android14', 'performance')"},
                "author": {"type": "string", "description": "Optional author or agent name"},
            },
            "required": ["slug", "note"],
        },
    },
    {
        "name": "record_fact",
        "description": "Record an unattached architectural invariant or engineering discovery into data/facts.json.",
        "parameters": {
            "type": "object",
            "properties": {
                "fact": {"type": "string", "description": "The architectural discovery or runtime invariant"},
                "domain": {"type": "string", "description": "Architecture domain (e.g. 'Kernel & Low-Level Systems', 'Concurrency & Event Loops')"},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of tags associated with this fact",
                },
            },
            "required": ["fact", "domain"],
        },
    },
    {
        "name": "list_vault",
        "description": "List all technologies and blueprints curated in the Learn & Build vault.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Optional category filter"},
                "verified_only": {"type": "boolean", "description": "Show only verified AI blueprints (exclude baseline stubs)"},
            },
        },
    },
    {
        "name": "scaffold_blueprint",
        "description": "Extract compilable Section 4 starter source files from a blueprint and emit them into a target directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "slug": {"type": "string", "description": "Blueprint slug to scaffold (e.g. 'retrofit', 'guava')"},
                "output_dir": {"type": "string", "description": "Destination directory path for generated files"},
            },
            "required": ["slug", "output_dir"],
        },
    },
]


def _load_entries() -> list[dict]:
    if _JSON_PATH.exists():
        try:
            return json.loads(_JSON_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _load_facts() -> list[dict]:
    if _FACTS_PATH.exists():
        try:
            return json.loads(_FACTS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def handle_tool_call(name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name == "search_blueprints":
        query = args.get("query", "").lower()
        category = args.get("category")
        entries = _load_entries()
        matches = []
        for e in entries:
            if category and e.get("category", "").lower() != category.lower():
                continue
            haystack = " ".join([
                e.get("title", ""),
                e.get("description", ""),
                e.get("category", ""),
                " ".join(e.get("tags", [])),
            ]).lower()
            if query in haystack:
                matches.append({
                    "title": e.get("title"),
                    "category": e.get("category"),
                    "blueprint_status": e.get("blueprint_status"),
                    "blueprint_file": e.get("blueprint_file"),
                    "description": e.get("description"),
                    "url": e.get("url"),
                })
        return {"matches": matches, "count": len(matches)}

    elif name == "get_blueprint":
        slug = args.get("slug", "").removesuffix(".md").replace("blueprints/", "")
        candidate = _BLUEPRINTS_DIR / f"{slug}.md"
        if not candidate.exists():
            found = list(_BLUEPRINTS_DIR.glob(f"*{slug}*.md"))
            if found:
                candidate = found[0]
        if not candidate.exists():
            return {"error": f"Blueprint '{slug}' not found locally."}
        text = candidate.read_text(encoding="utf-8")
        return {
            "slug": candidate.stem,
            "filename": candidate.name,
            "content": text,
        }

    elif name == "record_field_note":
        slug = args.get("slug", "").removesuffix(".md").replace("blueprints/", "")
        note_text = args.get("note", "")
        tag = args.get("tag")
        author = args.get("author")

        candidate = _BLUEPRINTS_DIR / f"{slug}.md"
        if not candidate.exists():
            found = list(_BLUEPRINTS_DIR.glob(f"*{slug}*.md"))
            if found:
                candidate = found[0]
        if not candidate.exists():
            return {"error": f"Blueprint '{slug}' not found."}

        text = candidate.read_text(encoding="utf-8")
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        author_str = f" (by `{author}`)" if author else ""
        tag_str = f" `[{tag}]`" if tag else ""
        note_entry = f"- **Field Note ({timestamp})**{tag_str}: {note_text}{author_str}"

        header = "### Battle-Tested Field Notes & Production Gotchas"
        if header not in text:
            text += f"\n\n{header}\n"
        text += f"{note_entry}\n"
        candidate.write_text(text, encoding="utf-8")
        return {"success": True, "file": candidate.name, "entry": note_entry}

    elif name == "record_fact":
        fact_text = args.get("fact", "")
        domain = args.get("domain", "General")
        tags = args.get("tags") or []
        facts = _load_facts()
        entry = {
            "fact": fact_text,
            "domain": domain,
            "tags": tags,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        facts.append(entry)
        _FACTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        _FACTS_PATH.write_text(json.dumps(facts, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return {"success": True, "fact": entry}

    elif name == "list_vault":
        category = args.get("category")
        verified_only = args.get("verified_only", False)
        entries = _load_entries()
        if category:
            entries = [e for e in entries if e.get("category", "").lower() == category.lower()]
        if verified_only:
            entries = [e for e in entries if e.get("blueprint_status") == "verified"]
        return {"entries": entries, "total": len(entries)}

    elif name == "scaffold_blueprint":
        from curator.scaffolder import scaffold_blueprint
        slug = args.get("slug", "").removesuffix(".md").replace("blueprints/", "")
        output_dir = Path(args.get("output_dir", f"./{slug}-scaffold"))
        candidate = _BLUEPRINTS_DIR / f"{slug}.md"
        if not candidate.exists():
            found = list(_BLUEPRINTS_DIR.glob(f"*{slug}*.md"))
            if found:
                candidate = found[0]
        if not candidate.exists():
            return {"error": f"Blueprint '{slug}' not found."}
        try:
            res = scaffold_blueprint(candidate, output_dir)
            return {
                "success": True,
                "slug": res.slug,
                "target_dir": str(res.target_dir.resolve()),
                "files": [f.filename for f in res.files],
            }
        except Exception as ex:
            return {"error": str(ex)}

    return {"error": f"Unknown tool: {name}"}


def run_stdio_server():
    """Run JSON-RPC 2.0 stdio loop for MCP clients."""
    sys.stderr.write("[Learn & Build] MCP Server running on stdio...\n")
    sys.stderr.flush()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue

        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        # Handle MCP Lifecycle
        if method == "initialize":
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "resources": {"subscribe": False, "listChanged": False},
                    },
                    "serverInfo": {
                        "name": "learn-and-build",
                        "version": "1.0.0",
                    },
                },
            }
        elif method == "tools/list":
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": TOOLS_SCHEMA,
                },
            }
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            tool_result = handle_tool_call(tool_name, tool_args)
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(tool_result, indent=2, ensure_ascii=False),
                        }
                    ],
                },
            }
        elif method == "resources/list":
            resources = [
                {
                    "uri": "vault://facts",
                    "name": "Engineering Facts & Invariants",
                    "description": "Recorded runtime discoveries and engineering facts",
                    "mimeType": "application/json",
                }
            ]
            for bp in _BLUEPRINTS_DIR.glob("*.md"):
                resources.append({
                    "uri": f"vault://blueprints/{bp.stem}",
                    "name": f"Blueprint: {bp.stem}",
                    "description": f"Architectural blueprint for {bp.stem}",
                    "mimeType": "text/markdown",
                })
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"resources": resources},
            }
        elif method == "resources/read":
            uri = params.get("uri", "")
            if uri == "vault://facts":
                content = json.dumps(_load_facts(), indent=2, ensure_ascii=False)
                mime = "application/json"
            elif uri.startswith("vault://blueprints/"):
                slug = uri.replace("vault://blueprints/", "")
                bp_file = _BLUEPRINTS_DIR / f"{slug}.md"
                content = bp_file.read_text(encoding="utf-8") if bp_file.exists() else "# Not Found"
                mime = "text/markdown"
            else:
                content = "# Resource Not Found"
                mime = "text/plain"
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "contents": [{"uri": uri, "mimeType": mime, "text": content}]
                },
            }
        elif method == "notifications/initialized":
            continue
        else:
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }

        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    run_stdio_server()
