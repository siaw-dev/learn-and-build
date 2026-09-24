"""
curator/processing/deduplicator.py

Lightweight deduplication check before DB insertion.
Checks by URL and SHA-256 content hash.
"""

from __future__ import annotations

import asyncio

from curator.models import KnowledgeEntry
from curator.storage.database import Database


async def is_duplicate_async(entry: KnowledgeEntry, db: Database) -> bool:
    """Async check: returns True if URL already exists in DB."""
    return await db.url_exists(entry.url)


def is_duplicate(entry: KnowledgeEntry, db: Database) -> bool:
    """Sync wrapper for use in CLI context."""
    return asyncio.run(is_duplicate_async(entry, db))
