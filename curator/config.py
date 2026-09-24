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
README_PATH: Path = _ROOT / "README.md"
TEMPLATE_PATH: Path = _ROOT / "templates" / "awesome_readme.md.j2"

# ── Models ──────────────────────────────────────────────────────────────────
GEMINI_MODEL: str = "gemini-2.0-flash"


# ── Taxonomy ────────────────────────────────────────────────────────────────
TAXONOMY: dict[str, list[str]] = {
    "Root Solutions": [
        "Magisk",
        "KernelSU",
        "APatch",
        "SuperSU",
        "Systemless Root",
    ],
    "Bootloader & Fastboot": [
        "Bootloader Unlock",
        "Fastboot / Fastbootd",
        "OEM Unlock",
        "Relock",
        "EDL Mode",
    ],
    "Kernel (GKI & Custom)": [
        "GKI (Generic Kernel Image)",
        "Custom Kernels",
        "Kernel Patches",
        "AOSP Kernel",
        "KernelSU Integration",
        "APatch Integration",
    ],
    "Zygote & Hook Frameworks": [
        "Zygisk",
        "LSPosed",
        "Xposed Framework",
        "Riru",
        "Hook APIs",
    ],
    "Modules & Overlays": [
        "Magisk Modules",
        "KernelSU Modules",
        "APatch Modules",
        "Systemless Overlays",
    ],
    "Recovery": [
        "TWRP",
        "OrangeFox",
        "SHRP",
        "Custom Recovery",
        "A/B Partition Recovery",
    ],
    "Forensics & Anti-Detection": [
        "SafetyNet / Play Integrity",
        "Root Detection Bypass",
        "Banking App Bypass",
        "Anti-Cheat Bypass",
        "Forensic Analysis",
    ],
    "Tutorials & Learning": [
        "Step-by-Step Guides",
        "Video Tutorials",
        "Beginner Guides",
        "Deep Dives",
        "Development Guides",
    ],
    "Tools & Utilities": [
        "ADB & Fastboot Scripts",
        "Payload Dumper",
        "Partition Tools",
        "Flashing Tools",
        "Analysis Tools",
    ],
    "Device-Specific": [
        "Samsung (Exynos / Qualcomm)",
        "Qualcomm Snapdragon",
        "MediaTek (MTK)",
        "Google Pixel",
        "OnePlus / OPPO",
        "Xiaomi / MIUI",
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
