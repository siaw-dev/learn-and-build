"""
curator/storage/database.py — SQLite persistence via aiosqlite.

Handles:
- Schema creation
- Insert with deduplication
- Query by category, status, source type
- Stats aggregation
"""

from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path
from typing import Optional

import aiosqlite

from curator.models import EntryStatus, KnowledgeEntry, SourceType

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS entries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    url             TEXT NOT NULL UNIQUE,
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    source_type     TEXT NOT NULL,
    category        TEXT NOT NULL,
    subcategory     TEXT DEFAULT '',
    tags            TEXT DEFAULT '',
    status          TEXT DEFAULT 'active',
    author          TEXT DEFAULT '',
    stars           INTEGER,
    android_versions TEXT DEFAULT '',
    devices         TEXT DEFAULT '',
    raw_content     TEXT DEFAULT '',
    content_hash    TEXT NOT NULL,
    ingested_at     TEXT NOT NULL
);
"""

_CREATE_HASH_INDEX = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_content_hash ON entries (content_hash);
"""


class Database:
    """Async SQLite database wrapper for the knowledge curator."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def initialize(self) -> None:
        """Create tables and indexes if they don't exist."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(_CREATE_TABLE)
            await db.execute(_CREATE_HASH_INDEX)
            await db.commit()

    async def insert(self, entry: KnowledgeEntry) -> bool:
        """
        Insert a new entry. Returns True if inserted, False if duplicate.
        Checks both URL (UNIQUE constraint) and content_hash index.
        """
        async with aiosqlite.connect(self.db_path) as db:
            # Check for existing URL or hash
            async with db.execute(
                "SELECT id FROM entries WHERE url = ? OR content_hash = ?",
                (entry.url, entry.content_hash),
            ) as cursor:
                if await cursor.fetchone():
                    return False  # Duplicate

            row = entry.to_db_dict()
            await db.execute(
                """INSERT INTO entries
                   (url, title, description, source_type, category, subcategory,
                    tags, status, author, stars, android_versions, devices,
                    raw_content, content_hash, ingested_at)
                   VALUES
                   (:url, :title, :description, :source_type, :category, :subcategory,
                    :tags, :status, :author, :stars, :android_versions, :devices,
                    :raw_content, :content_hash, :ingested_at)
                """,
                row,
            )
            await db.commit()
            return True

    async def get_all(
        self,
        category: Optional[str] = None,
        source_type: Optional[SourceType] = None,
        status: Optional[EntryStatus] = None,
    ) -> list[KnowledgeEntry]:
        """Retrieve entries with optional filters."""
        clauses: list[str] = []
        params: list = []

        if category:
            clauses.append("category = ?")
            params.append(category)
        if source_type:
            clauses.append("source_type = ?")
            params.append(source_type.value)
        if status:
            clauses.append("status = ?")
            params.append(status.value)

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        query = f"SELECT * FROM entries {where} ORDER BY category, title"

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [KnowledgeEntry.from_db_row(dict(row)) for row in rows]

    async def stats(self) -> dict:
        """Return aggregated stats for the --status CLI command."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM entries") as cur:
                total = (await cur.fetchone())[0]

            async with db.execute(
                "SELECT category, COUNT(*) as c FROM entries GROUP BY category ORDER BY c DESC"
            ) as cur:
                by_category = {row[0]: row[1] for row in await cur.fetchall()}

            async with db.execute(
                "SELECT source_type, COUNT(*) as c FROM entries GROUP BY source_type"
            ) as cur:
                by_source = {row[0]: row[1] for row in await cur.fetchall()}

        return {"total": total, "by_category": by_category, "by_source": by_source}

    async def url_exists(self, url: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT id FROM entries WHERE url = ?", (url,)) as cur:
                return (await cur.fetchone()) is not None
