#!/usr/bin/env python3
"""
ingest.py — Knowledge Curator CLI

Entry point for both local development and GitHub Actions.

Local dev (SQLite):
  python3 ingest.py ingest --url <URL>
  python3 ingest.py render
  python3 ingest.py status

GitHub Actions / Online mode (JSON):
  python3 ingest.py ingest --url <URL> --store json
  python3 ingest.py render --store json
  python3 ingest.py status --store json

Other commands:
  python3 ingest.py seed [--store json] [--dry-run]
  python3 ingest.py publish                          # push to GitHub (local only)
"""

from __future__ import annotations

import asyncio
import sys
from urllib.parse import urlparse

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from curator.config import BLUEPRINTS_DIR, DB_PATH, JSON_STORE_PATH
from curator.ingestors import ingest_github_repo, ingest_youtube_video, ingest_webpage
from curator.models import KnowledgeEntry, SourceType
from curator.output import render_readme
from curator.processing import classify_entry, extract_blueprint, summarize_entry
from curator.storage import Database, JsonStore

console = Console()

SEED_URLS = [
    "https://github.com/topjohnwu/Magisk",
    "https://github.com/tiann/KernelSU",
    "https://github.com/bmax121/APatch",
    "https://github.com/LSPosed/LSPosed",
    "https://github.com/TeamWin/Team-Win-Recovery-Project",
    "https://github.com/topjohnwu/libsu",
    "https://github.com/RikkaApps/Shizuku",
    "https://github.com/awesome-android-root/awesome-android-root",
]


# ── Store factory ─────────────────────────────────────────────────────────────

def make_store(store_type: str):
    """Return the appropriate storage backend."""
    if store_type == "json":
        store = JsonStore(JSON_STORE_PATH)
        store.initialize()
        return store
    else:
        db = Database(DB_PATH)
        asyncio.run(db.initialize())
        return db


def _store_insert(store, entry: KnowledgeEntry) -> bool:
    if isinstance(store, JsonStore):
        return store.insert(entry)
    return asyncio.run(store.insert(entry))


def _store_stats(store) -> dict:
    if isinstance(store, JsonStore):
        return store.stats()
    return asyncio.run(store.stats())


def _store_url_exists(store, url: str) -> bool:
    if isinstance(store, JsonStore):
        return store.url_exists(url)
    return asyncio.run(store.url_exists(url))


# ── Source type detection ─────────────────────────────────────────────────────

def _detect_source_type(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if "github.com" in host:
        return "github"
    if "youtube.com" in host or "youtu.be" in host:
        return "youtube"
    return "web"


# ── Core ingestion pipeline ───────────────────────────────────────────────────

def _process_url(url: str, store) -> bool:
    """
    Full pipeline: ingest → classify → summarize → deduplicate → store.
    Returns True if a new entry was saved, False if duplicate or failed.
    """
    source_type = _detect_source_type(url)

    console.rule(f"[bold cyan]Ingesting {source_type.upper()}[/bold cyan]")
    console.print(f"  📥 URL: [link={url}]{url}[/link]")

    # Step 1: Ingest
    try:
        with console.status("  Fetching content...", spinner="dots"):
            if source_type == "github":
                entry = ingest_github_repo(url)
            elif source_type == "youtube":
                entry = ingest_youtube_video(url)
            else:
                entry = ingest_webpage(url)
        console.print(f"  ✅ Fetched: [bold]{entry.title}[/bold]")
    except Exception as e:
        console.print(f"  [bold red]❌ Ingestion failed:[/bold red] {e}")
        return False

    # Step 2: Classify
    with console.status("  Classifying...", spinner="dots"):
        entry = classify_entry(entry)
    console.print(f"  🏷️  Category: [green]{entry.category}[/green] | Tags: {entry.tags[:5]}")

    # Step 3: Summarize
    with console.status("  Summarizing...", spinner="dots"):
        entry = summarize_entry(entry)
    console.print(f"  📝 {entry.description[:120]}")

    # Step 4: Extract Deep Blueprint
    with console.status("  Extracting technical blueprint...", spinner="dots"):
        bp_path = extract_blueprint(entry, BLUEPRINTS_DIR)
        if bp_path:
            entry.blueprint_file = f"blueprints/{bp_path.name}"
            console.print(f"  📐 Blueprint: [cyan]blueprints/{bp_path.name}[/cyan]")

    # Step 5: Store
    inserted = _store_insert(store, entry)
    if inserted:
        console.print(f"  [bold green]✅ Saved to knowledge base.[/bold green]")
        return True
    else:
        console.print(f"  [yellow]⚠️  Duplicate — already in database. Skipped.[/yellow]")
        return False



# ── CLI ───────────────────────────────────────────────────────────────────────

_STORE_OPTION = click.option(
    "--store",
    type=click.Choice(["json", "sqlite"]),
    default="json",
    show_default=True,
    help="Storage backend: 'json' for online/GitHub Actions, 'sqlite' for local dev.",
)


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """🤖 Knowledge Curator — Android Root & Kernel Intelligence System"""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()
@click.option("--url", "-u", required=True, help="URL to ingest (GitHub, YouTube, or webpage)")
@_STORE_OPTION
def ingest(url: str, store: str):
    """Ingest a single URL into the knowledge base."""
    store_obj = make_store(store)
    success = _process_url(url.strip(), store_obj)
    if not success:
        sys.exit(1)


@cli.command()
@_STORE_OPTION
def render(store: str):
    """Regenerate README.md from the full database."""
    store_obj = make_store(store)

    with console.status("Rendering awesome list README.md...", spinner="dots"):
        total = render_readme(store_obj)

    console.print(Panel(
        f"[bold green]✅ README.md generated![/bold green]\n"
        f"   {total} entries rendered across all categories.",
        title="Render Complete",
        expand=False,
    ))


@cli.command()
@click.option("--message", "-m", default="chore: update curated knowledge base",
              help="Git commit message")
def publish(message: str):
    """Commit and push README.md to the private GitHub repo (local use)."""
    from curator.git_publisher import publish as git_publish
    try:
        git_publish(commit_message=message)
        console.print("[bold green]✅ Published successfully![/bold green]")
    except EnvironmentError as e:
        console.print(f"[bold red]❌ Config error:[/bold red] {e}")
        sys.exit(1)


@cli.command()
@_STORE_OPTION
def status(store: str):
    """Show database statistics."""
    store_obj = make_store(store)
    stats = _store_stats(store_obj)

    console.print(Panel(
        f"[bold]Total entries:[/bold] {stats['total']}",
        title="📊 Knowledge Base Status",
        expand=False,
    ))

    if stats["by_category"]:
        table = Table(title="Entries by Category", show_header=True)
        table.add_column("Category", style="cyan")
        table.add_column("Count", justify="right", style="green")
        for cat, count in stats["by_category"].items():
            table.add_row(cat, str(count))
        console.print(table)

    if stats["by_source"]:
        table2 = Table(title="Entries by Source", show_header=True)
        table2.add_column("Source", style="magenta")
        table2.add_column("Count", justify="right", style="green")
        for src, count in stats["by_source"].items():
            table2.add_row(src, str(count))
        console.print(table2)


@cli.command()
@click.option("--dry-run", is_flag=True, help="List seed URLs without ingesting")
@_STORE_OPTION
def seed(dry_run: bool, store: str):
    """Seed the knowledge base with starter Android root/kernel resources."""
    if dry_run:
        console.print("[bold]Seed URLs:[/bold]")
        for url in SEED_URLS:
            console.print(f"  • {url}")
        return

    store_obj = make_store(store)
    console.print(f"[bold]Seeding {len(SEED_URLS)} starter resources (store={store})...[/bold]\n")
    saved = 0
    for url in SEED_URLS:
        if _process_url(url, store_obj):
            saved += 1
        console.print()

    console.print(
        f"[bold green]✅ Seed complete![/bold green] "
        f"{saved}/{len(SEED_URLS)} new entries saved.\n"
        f"Run [cyan]python3 ingest.py render --store {store}[/cyan] to generate the README."
    )


@cli.command()
@click.argument("name", required=False)
def blueprint(name: str | None):
    """List all available blueprints or read a specific one."""
    if not BLUEPRINTS_DIR.exists():
        console.print("[yellow]No blueprints directory found.[/yellow]")
        return

    files = sorted(BLUEPRINTS_DIR.glob("*.md"))
    if not files:
        console.print("[yellow]No blueprints generated yet.[/yellow]")
        return

    if not name:
        console.print(Panel(f"[bold cyan]Available Blueprints ({len(files)}):[/bold cyan]"))
        for f in files:
            console.print(f"  📐 [bold]{f.stem}[/bold] -> [dim]{f}[/dim]")
        console.print("\n[dim]Run: python3 ingest.py blueprint <name> to view.[/dim]")
        return

    target = BLUEPRINTS_DIR / f"{name}.md"
    if not target.exists():
        matches = [f for f in files if name.lower() in f.stem.lower()]
        if matches:
            target = matches[0]
        else:
            console.print(f"[red]No blueprint found matching '{name}'.[/red]")
            return

    from rich.markdown import Markdown
    console.print(Panel(f"[bold green]Blueprint: {target.stem}[/bold green]"))
    console.print(Markdown(target.read_text(encoding="utf-8")))


@cli.command()
@_STORE_OPTION
@click.option("--only-stubs/--all", default=True, help="Only backfill entries that are stubs")
def backfill_blueprints(store: str, only_stubs: bool):
    """Generate missing or upgrade stub blueprints for existing entries."""
    from pathlib import Path
    store_obj = make_store(store)
    if isinstance(store_obj, JsonStore):
        entries = store_obj.get_all()
    else:
        entries = asyncio.run(store_obj.get_all())

    console.print(f"[bold]Checking {len(entries)} entries for blueprints (only_stubs={only_stubs})...[/bold]")
    updated = 0
    for entry in entries:
        bp_name = Path(entry.blueprint_file).name if entry.blueprint_file else ""
        existing_file = BLUEPRINTS_DIR / bp_name if bp_name else None

        # Check if already verified with substantial content
        if existing_file and existing_file.exists():
            file_text = existing_file.read_text(encoding="utf-8")
            if len(file_text) > 2500 and "## 1. Architectural Topology" in file_text:
                if entry.blueprint_status != "verified":
                    entry.blueprint_status = "verified"
                    console.print(f"  [green]✓ {entry.title} already has verified blueprint ({len(file_text)} bytes). Updated status.[/green]")
                    updated += 1
                if only_stubs:
                    continue

        console.print(f"\n[bold cyan]Backfilling blueprint for:[/bold cyan] {entry.title}")
        # Fetch fresh raw content + code snippets if missing
        if not entry.raw_content:
            with console.status("  Fetching source code / content...", spinner="dots"):
                try:
                    if entry.source_type == SourceType.GITHUB:
                        fresh = ingest_github_repo(entry.url)
                        entry.raw_content = fresh.raw_content
                    elif entry.source_type == SourceType.WEB:
                        fresh = ingest_webpage(entry.url)
                        entry.raw_content = fresh.raw_content
                except Exception as e:
                    console.print(f"  [yellow]Failed to fetch raw content: {e}[/yellow]")

        with console.status("  Extracting technical blueprint...", spinner="dots"):
            bp_path = extract_blueprint(entry, BLUEPRINTS_DIR)
            if bp_path:
                entry.blueprint_file = f"blueprints/{bp_path.name}"
                updated += 1

    if isinstance(store_obj, JsonStore):
        store_obj.save(entries)
    console.print(f"\n[bold green]✅ Finished backfill! Updated {updated} blueprints.[/bold green]")



if __name__ == "__main__":
    cli()
