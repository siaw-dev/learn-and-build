"""
curator/storage/json_store.py

JSON-backed knowledge store for cloud/GitHub Actions use.
Reads/writes a flat JSON array committed to the repository.
This gives human-readable git diffs, no binary blobs, and works
perfectly in stateless CI environments.

Shares the same interface as Database so ingest.py can swap stores
with a single --store flag.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from curator.models import EntryStatus, KnowledgeEntry, SourceType


class JsonStore:
    """Synchronous JSON-file-backed knowledge store."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    # ── Internal I/O ────────────────────────────────────────────────────────

    def _load_raw(self) -> list[dict]:
        if not self.path.exists():
            return []
        text = self.path.read_text(encoding="utf-8").strip()
        if not text:
            return []
        return json.loads(text)

    def _save_raw(self, rows: list[dict]) -> None:
        # Sort by category then title for stable, readable diffs
        rows.sort(key=lambda r: (r.get("category", ""), r.get("title", "").lower()))
        self.path.write_text(
            json.dumps(rows, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

    def _to_row(self, entry: KnowledgeEntry) -> dict:
        return {
            "url": entry.url,
            "title": entry.title,
            "description": entry.description,
            "source_type": entry.source_type.value,
            "category": entry.category,
            "subcategory": entry.subcategory,
            "tags": entry.tags,
            "status": entry.status.value,
            "author": entry.author,
            "stars": entry.stars,
            "android_versions": entry.android_versions,
            "devices": entry.devices,
            "content_hash": entry.content_hash,
            "ingested_at": entry.ingested_at.isoformat(),
        }

    def _from_row(self, row: dict) -> KnowledgeEntry:
        return KnowledgeEntry(
            url=row["url"],
            title=row["title"],
            description=row["description"],
            source_type=SourceType(row["source_type"]),
            category=row.get("category", "Uncategorized"),
            subcategory=row.get("subcategory"),
            tags=row.get("tags", []),
            status=EntryStatus(row.get("status", "active")),
            author=row.get("author"),
            stars=row.get("stars"),
            android_versions=row.get("android_versions", []),
            devices=row.get("devices", []),
            content_hash=row.get("content_hash", ""),
            ingested_at=datetime.fromisoformat(
                row.get("ingested_at", datetime.now().isoformat())
            ),
        )

    # ── Public API (mirrors Database interface) ──────────────────────────────

    def initialize(self) -> None:
        """Ensure the JSON file exists (create empty array if missing)."""
        if not self.path.exists():
            self._save_raw([])

    def insert(self, entry: KnowledgeEntry) -> bool:
        """
        Insert a new entry. Returns True if inserted, False if duplicate.
        Checks both URL and content_hash for deduplication.
        """
        rows = self._load_raw()
        existing_urls = {r["url"] for r in rows}
        existing_hashes = {r.get("content_hash", "") for r in rows}

        if entry.url in existing_urls or entry.content_hash in existing_hashes:
            return False

        rows.append(self._to_row(entry))
        self._save_raw(rows)
        return True

    def get_all(
        self,
        category: Optional[str] = None,
        source_type: Optional[SourceType] = None,
        status: Optional[EntryStatus] = None,
    ) -> list[KnowledgeEntry]:
        """Retrieve entries with optional filters."""
        rows = self._load_raw()
        entries = [self._from_row(r) for r in rows]

        if category:
            entries = [e for e in entries if e.category == category]
        if source_type:
            entries = [e for e in entries if e.source_type == source_type]
        if status:
            entries = [e for e in entries if e.status == status]

        return entries

    def url_exists(self, url: str) -> bool:
        rows = self._load_raw()
        return any(r["url"] == url for r in rows)

    def stats(self) -> dict:
        """Return aggregated stats matching Database.stats() shape."""
        rows = self._load_raw()
        by_category: dict[str, int] = {}
        by_source: dict[str, int] = {}

        for r in rows:
            cat = r.get("category", "Uncategorized")
            src = r.get("source_type", "unknown")
            by_category[cat] = by_category.get(cat, 0) + 1
            by_source[src] = by_source.get(src, 0) + 1

        # Sort by count descending
        by_category = dict(sorted(by_category.items(), key=lambda x: -x[1]))
        by_source = dict(sorted(by_source.items(), key=lambda x: -x[1]))

        return {
            "total": len(rows),
            "by_category": by_category,
            "by_source": by_source,
        }

    # ── Async compatibility shim (so render pipeline works unchanged) ────────

    async def initialize_async(self) -> None:
        self.initialize()

    async def insert_async(self, entry: KnowledgeEntry) -> bool:
        return self.insert(entry)

    async def get_all_async(self, **kwargs) -> list[KnowledgeEntry]:
        return self.get_all(**kwargs)

    async def stats_async(self) -> dict:
        return self.stats()

    async def url_exists_async(self, url: str) -> bool:
        return self.url_exists(url)
