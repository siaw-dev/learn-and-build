"""
curator/models.py — Core Pydantic data models for knowledge entries.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, field_validator


class SourceType(str, Enum):
    GITHUB = "github"
    YOUTUBE = "youtube"
    WEB = "web"


class EntryStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"


class KnowledgeEntry(BaseModel):
    """A single curated knowledge entry from any source."""

    url: str
    title: str
    description: str                    # AI-summarized, 1-2 sentences
    source_type: SourceType
    category: str                       # Maps to taxonomy in config.py
    subcategory: Optional[str] = None
    tags: list[str] = []
    status: EntryStatus = EntryStatus.ACTIVE
    author: Optional[str] = None
    stars: Optional[int] = None         # GitHub only
    android_versions: list[str] = []    # e.g. ["Android 13", "Android 14"]
    devices: list[str] = []             # e.g. ["Qualcomm", "Samsung"]
    raw_content: Optional[str] = None   # Full text (stored in DB, not README)
    content_hash: str = ""              # SHA256 for deduplication
    ingested_at: datetime = datetime.now()

    @field_validator("content_hash", mode="before")
    @classmethod
    def compute_hash(cls, v: str, info) -> str:
        """Auto-compute SHA256 hash from URL if not provided."""
        if v:
            return v
        # Get url from the data being validated
        url = info.data.get("url", "")
        raw = info.data.get("raw_content", "")
        return hashlib.sha256(f"{url}{raw}".encode()).hexdigest()

    @field_validator("tags", "android_versions", "devices", mode="before")
    @classmethod
    def parse_csv_or_list(cls, v) -> list[str]:
        """Accept either a list or a comma-separated string (from SQLite)."""
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v or []

    def to_db_dict(self) -> dict:
        """Flatten for SQLite storage (lists become CSV strings)."""
        return {
            "url": self.url,
            "title": self.title,
            "description": self.description,
            "source_type": self.source_type.value,
            "category": self.category,
            "subcategory": self.subcategory or "",
            "tags": ",".join(self.tags),
            "status": self.status.value,
            "author": self.author or "",
            "stars": self.stars,
            "android_versions": ",".join(self.android_versions),
            "devices": ",".join(self.devices),
            "raw_content": self.raw_content or "",
            "content_hash": self.content_hash,
            "ingested_at": self.ingested_at.isoformat(),
        }

    @classmethod
    def from_db_row(cls, row: dict) -> "KnowledgeEntry":
        """Reconstruct from a SQLite row dict."""
        return cls(
            url=row["url"],
            title=row["title"],
            description=row["description"],
            source_type=SourceType(row["source_type"]),
            category=row["category"],
            subcategory=row.get("subcategory") or None,
            tags=row.get("tags", ""),
            status=EntryStatus(row.get("status", "active")),
            author=row.get("author") or None,
            stars=row.get("stars"),
            android_versions=row.get("android_versions", ""),
            devices=row.get("devices", ""),
            raw_content=row.get("raw_content") or None,
            content_hash=row.get("content_hash", ""),
            ingested_at=datetime.fromisoformat(
                row.get("ingested_at", datetime.now().isoformat())
            ),
        )
