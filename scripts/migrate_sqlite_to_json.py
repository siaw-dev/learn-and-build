#!/usr/bin/env python3
"""
scripts/migrate_sqlite_to_json.py

One-shot migration: exports all entries from the SQLite database
into data/knowledge.json (the new cloud-compatible store).

Run once after the v2 upgrade:
    python3 scripts/migrate_sqlite_to_json.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from curator.config import DB_PATH, JSON_STORE_PATH
from curator.storage.database import Database
from curator.storage.json_store import JsonStore


async def main():
    print("🔄 Migrating SQLite → knowledge.json...")

    if not DB_PATH.exists():
        print(f"  ℹ️  SQLite DB not found at {DB_PATH}. Nothing to migrate.")
        # Still create an empty knowledge.json
        store = JsonStore(JSON_STORE_PATH)
        store.initialize()
        print(f"  ✅ Created empty {JSON_STORE_PATH}")
        return

    db = Database(DB_PATH)
    await db.initialize()
    entries = await db.get_all()

    if not entries:
        print("  ℹ️  SQLite DB is empty. Creating empty knowledge.json.")
        store = JsonStore(JSON_STORE_PATH)
        store.initialize()
        return

    store = JsonStore(JSON_STORE_PATH)
    store.initialize()

    migrated = 0
    skipped = 0
    for entry in entries:
        inserted = store.insert(entry)
        if inserted:
            migrated += 1
            print(f"  ✅ Migrated: {entry.title} [{entry.category}]")
        else:
            skipped += 1
            print(f"  ⏭️  Skipped (duplicate): {entry.title}")

    print(f"\n✅ Migration complete: {migrated} migrated, {skipped} skipped.")
    print(f"   Output: {JSON_STORE_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
