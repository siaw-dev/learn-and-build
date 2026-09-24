"""
curator/config.py — Taxonomy definitions, constants, and environment loading.
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env from project root
_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env")

# ── API Keys ────────────────────────────────────────────────────────────────
# Single key (local dev / backward compat)
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
GITHUB_USERNAME: str = os.getenv("GITHUB_USERNAME", "")
GITHUB_REPO_NAME: str = os.getenv("GITHUB_REPO_NAME", "awesome-android-root-kernel")

# Multi-key pool: reads GEMINI_KEY_1 … GEMINI_KEY_8 (set as GitHub Secrets)
GEMINI_API_KEYS: list[str] = [
    v for k, v in sorted(os.environ.items())
    if k.startswith("GEMINI_KEY_") and v.strip()
]
# Fall back to single key for local dev
if not GEMINI_API_KEYS and GEMINI_API_KEY:
    GEMINI_API_KEYS = [GEMINI_API_KEY]

# ── Paths ───────────────────────────────────────────────────────────────────
DB_PATH: Path = _ROOT / "data" / "knowledge.db"
JSON_STORE_PATH: Path = _ROOT / "data" / "knowledge.json"
BLUEPRINTS_DIR: Path = _ROOT / "blueprints"
README_PATH: Path = _ROOT / "README.md"
TEMPLATE_PATH: Path = _ROOT / "templates" / "awesome_readme.md.j2"

# ── Models ──────────────────────────────────────────────────────────────────
GEMINI_MODEL: str = "gemini-3.8-flash"




# ── Taxonomy (Domain Adaptive) ──────────────────────────────────────────────
TAXONOMY: dict[str, list[str]] = {
    # System-Level & Android Internals
    "Root Solutions": [
        "Magisk", "KernelSU", "APatch", "SuperSU", "Systemless Root",
    ],
    "Kernel & Low-Level Systems": [
        "GKI", "Linux Kernel", "Drivers", "eBPF", "Kprobes", "AOSP Kernel", "Custom Kernels",
    ],
    "Runtime Injection & Hooks": [
        "Zygisk", "LSPosed", "Xposed", "Frida", "Dobby", "PLT/GOT Hooking", "Inline Hooks",
    ],
    "Bootloaders & Partitions": [
        "Bootloader Unlock", "Fastboot", "AVB (Android Verified Boot)", "EDL", "Partition Tables",
    ],
    "Security & Reverse Engineering": [
        "Play Integrity / SafetyNet", "Anti-Cheat", "Binary Analysis", "Ghidra", "Memory Patching",
    ],
    # General Engineering Domains
    "AI, Agents & Machine Learning": [
        "Autonomous Agents", "LLM Pipelines", "Inference Engines", "Vector Stores", "MCP Servers",
    ],
    "Compilers & Language Runtimes": [
        "Bytecode VMs", "JIT Compilers", "AST Analyzers", "Parser Generators", "Linkers",
    ],
    "Distributed Systems & Storage": [
        "Databases", "Consensus Protocols", "Message Brokers", "Storage Engines", "Cache Systems",
    ],
    "Web Architecture & Protocols": [
        "HTTP/3", "WebSockets", "gRPC", "API Gateways", "High-Performance Servers",
    ],
    "Embedded & Firmware": [
        "Microcontrollers", "RTOS", "Hardware Protocols (SPI/I2C/UART)", "IoT Security",
    ],
    "Modules & Extensions": [
        "Magisk Modules", "KernelSU Modules", "System Overlays", "Plugins",
    ],
    "Tools, CLI & Utilities": [
        "ADB Scripts", "Payload Dumpers", "Build Systems", "Developer Tooling",
    ],
    "Tutorials & Deep Dives": [
        "Architecture Walkthroughs", "Technical Video Breakdowns", "Explorations",
    ],
}

ALL_CATEGORIES: list[str] = list(TAXONOMY.keys())


# ── Status emoji map ────────────────────────────────────────────────────────
STATUS_EMOJI: dict[str, str] = {
    "active": "🟢 Active",
    "archived": "🔴 Archived",
    "deprecated": "🟡 Deprecated",
    "experimental": "🔵 Experimental",
}
