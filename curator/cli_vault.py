"""
curator/cli_vault.py

Fast, native CLI query tool for the Learn & Build Knowledge Vault.
Designed for autonomous AI agents and engineers working in Antigravity.

Commands:
  python3 -m curator.cli_vault list [--verified-only]
  python3 -m curator.cli_vault search <query> [--category <cat>]
  python3 -m curator.cli_vault blueprint <slug_or_name> [--copy]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.request import urlopen

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

_ROOT = Path(__file__).resolve().parent.parent
_JSON_PATH = _ROOT / "data" / "knowledge.json"
_BLUEPRINTS_DIR = _ROOT / "blueprints"
_ONLINE_JSON_URL = "https://raw.githubusercontent.com/siaw-dev/learn-and-build/main/data/knowledge.json"

console = Console()


def _load_vault_entries() -> list[dict]:
    """Load entries from local JSON store, or fallback to GitHub online."""
    if _JSON_PATH.exists():
        try:
            return json.loads(_JSON_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    try:
        with urlopen(_ONLINE_JSON_URL, timeout=5) as res:
            return json.loads(res.read().decode("utf-8"))
    except Exception as e:
        console.print(f"[bold red]❌ Failed to load vault entries:[/bold red] {e}")
        return []


@click.group()
def cli():
    """🏛️ Learn & Build — Engineering Knowledge Vault & Blueprint Assistant"""
    pass


@cli.command("list")
@click.option("--verified-only", is_flag=True, help="Show only verified AI blueprints (exclude baseline stubs)")
@click.option("--json", "as_json", is_flag=True, help="Output in machine-readable JSON format")
def list_entries(verified_only: bool, as_json: bool):
    """List all architectural resources in the vault."""
    entries = _load_vault_entries()
    if verified_only:
        entries = [e for e in entries if e.get("blueprint_status") == "verified"]

    if as_json:
        click.echo(json.dumps(entries, indent=2, ensure_ascii=False))
        return

    table = Table(title=f"🏛️ Knowledge Vault ({len(entries)} items)", border_style="cyan")
    table.add_column("Title", style="bold white", no_wrap=True)
    table.add_column("Category", style="green")
    table.add_column("Source", style="yellow")
    table.add_column("Blueprint Status", style="magenta")
    table.add_column("Blueprint File", style="cyan")

    for e in entries:
        status_style = "[green]✓ Verified[/green]" if e.get("blueprint_status") == "verified" else "[yellow]⚠ Stub[/yellow]"
        table.add_row(
            e.get("title", "Untitled"),
            e.get("category", "General"),
            e.get("source_type", "web"),
            status_style,
            e.get("blueprint_file") or "None",
        )

    console.print(table)


@cli.command("search")
@click.argument("query")
@click.option("--category", "-c", default=None, help="Filter by category")
@click.option("--json", "as_json", is_flag=True, help="Output in machine-readable JSON format")
def search_entries(query: str, category: str | None, as_json: bool):
    """Search blueprints by keyword, hook, tag, or technology."""
    entries = _load_vault_entries()
    q = query.lower()

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
        if q in haystack:
            matches.append(e)

    if as_json:
        click.echo(json.dumps(matches, indent=2, ensure_ascii=False))
        return

    if not matches:
        console.print(f"[yellow]No blueprints found matching '{query}'.[/yellow]")
        return

    table = Table(title=f"Search Results for '{query}' ({len(matches)} matches)", border_style="cyan")
    table.add_column("Title", style="bold white")
    table.add_column("Category", style="green")
    table.add_column("Status", style="magenta")
    table.add_column("Description", style="dim")
    table.add_column("Blueprint", style="cyan")

    for e in matches:
        bp_status = "[green]Verified[/green]" if e.get("blueprint_status") == "verified" else "[yellow]Stub[/yellow]"
        table.add_row(
            e.get("title", ""),
            e.get("category", ""),
            bp_status,
            e.get("description", "")[:80] + "...",
            e.get("blueprint_file") or "None",
        )

    console.print(table)


@cli.command("blueprint")
@click.argument("slug")
@click.option("--json", "as_json", is_flag=True, help="Output in machine-readable JSON format")
def show_blueprint(slug: str, as_json: bool):
    """Display the full architectural blueprint for an entry."""
    # Find matching blueprint file
    slug_clean = slug.removesuffix(".md").replace("blueprints/", "")
    candidate = _BLUEPRINTS_DIR / f"{slug_clean}.md"

    if not candidate.exists():
        # Search among files
        found = list(_BLUEPRINTS_DIR.glob(f"*{slug_clean}*.md"))
        if found:
            candidate = found[0]

    if candidate.exists():
        text = candidate.read_text(encoding="utf-8")
        if as_json:
            click.echo(json.dumps({
                "slug": slug_clean,
                "file": candidate.name,
                "path": str(candidate),
                "content": text,
            }, indent=2, ensure_ascii=False))
            return
        console.print(Panel(Markdown(text), title=f"📐 Technical Blueprint: {candidate.name}", border_style="green"))
    else:
        # Try fetching from GitHub raw
        url = f"https://raw.githubusercontent.com/siaw-dev/learn-and-build/main/blueprints/{slug_clean}.md"
        try:
            with urlopen(url, timeout=5) as res:
                text = res.read().decode("utf-8")
                if as_json:
                    click.echo(json.dumps({
                        "slug": slug_clean,
                        "file": f"{slug_clean}.md",
                        "source": "cloud",
                        "content": text,
                    }, indent=2, ensure_ascii=False))
                    return
                console.print(Panel(Markdown(text), title=f"📐 Technical Blueprint: {slug_clean}.md (Cloud)", border_style="green"))
        except Exception:
            if as_json:
                click.echo(json.dumps({"error": f"Blueprint '{slug}' not found locally or in cloud vault."}, indent=2))
                sys.exit(1)
            console.print(f"[bold red]❌ Blueprint '{slug}' not found locally or in cloud vault.[/bold red]")


@cli.command("note")
@click.argument("slug")
@click.argument("note_text")
@click.option("--tag", "-t", default=None, help="Optional tag, e.g. 'gotcha', 'performance', 'android14'")
@click.option("--author", "-a", default=None, help="Author or agent name")
def add_note(slug: str, note_text: str, tag: str | None, author: str | None):
    """Append a battle-tested field note or production gotcha to a blueprint."""
    from datetime import datetime, timezone
    slug_clean = slug.removesuffix(".md").replace("blueprints/", "")
    candidate = _BLUEPRINTS_DIR / f"{slug_clean}.md"

    if not candidate.exists():
        found = list(_BLUEPRINTS_DIR.glob(f"*{slug_clean}*.md"))
        if found:
            candidate = found[0]

    if not candidate.exists():
        console.print(f"[bold red]❌ Blueprint '{slug}' not found locally in blueprints/.[/bold red]")
        sys.exit(1)

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
    console.print(f"[bold green]✅ Added field note to {candidate.name}:[/bold green]\n  {note_entry}")


@cli.command("fact")
@click.argument("fact_text")
@click.option("--domain", "-d", default="General", help="Architecture domain or category")
@click.option("--tags", "-t", default="", help="Comma-separated tags")
def add_fact(fact_text: str, domain: str, tags: str):
    """Record an unattached architectural invariant or engineering discovery into data/facts.json."""
    from datetime import datetime, timezone
    facts_file = _ROOT / "data" / "facts.json"
    facts = []
    if facts_file.exists():
        try:
            facts = json.loads(facts_file.read_text(encoding="utf-8"))
        except Exception:
            facts = []

    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    fact_entry = {
        "fact": fact_text,
        "domain": domain,
        "tags": tag_list,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    facts.append(fact_entry)
    facts_file.parent.mkdir(parents=True, exist_ok=True)
    facts_file.write_text(json.dumps(facts, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    console.print(f"[bold green]✅ Saved architectural fact to {facts_file.name}![/bold green]")


@cli.command("facts")
@click.option("--domain", "-d", default=None, help="Filter facts by architecture domain")
@click.option("--json", "as_json", is_flag=True, help="Output in machine-readable JSON format")
def list_facts(domain: str | None, as_json: bool):
    """List all architectural invariants and engineering field discoveries."""
    facts_file = _ROOT / "data" / "facts.json"
    facts = []
    if facts_file.exists():
        try:
            facts = json.loads(facts_file.read_text(encoding="utf-8"))
        except Exception:
            facts = []

    if domain:
        facts = [f for f in facts if f.get("domain", "").lower() == domain.lower()]

    if as_json:
        click.echo(json.dumps(facts, indent=2, ensure_ascii=False))
        return

    if not facts:
        console.print("[yellow]No architectural facts recorded yet.[/yellow]")
        return

    table = Table(title=f"🧠 Engineering Facts & Field Discoveries ({len(facts)})", border_style="green")
    table.add_column("Domain", style="cyan", no_wrap=True)
    table.add_column("Fact / Invariant", style="bold white")
    table.add_column("Tags", style="yellow")
    table.add_column("Recorded", style="dim", no_wrap=True)

    for f in facts:
        table.add_row(
            f.get("domain", "General"),
            f.get("fact", ""),
            ", ".join(f.get("tags", [])),
            f.get("recorded_at", "")[:10],
        )

    console.print(table)


@cli.command("scaffold")
@click.argument("slug")
@click.option("--out", "-o", default=None, help="Output directory (defaults to ./<slug>-scaffold)")
@click.option("--json", "as_json", is_flag=True, help="Output in machine-readable JSON format")
def scaffold_entry(slug: str, out: str | None, as_json: bool):
    """Generate compilable starter files from Section 4 of a blueprint."""
    from curator.scaffolder import scaffold_blueprint

    slug_clean = slug.removesuffix(".md").replace("blueprints/", "")
    candidate = _BLUEPRINTS_DIR / f"{slug_clean}.md"

    if not candidate.exists():
        found = list(_BLUEPRINTS_DIR.glob(f"*{slug_clean}*.md"))
        if found:
            candidate = found[0]

    if not candidate.exists():
        if as_json:
            click.echo(json.dumps({"error": f"Blueprint '{slug}' not found locally."}, indent=2))
            sys.exit(1)
        console.print(f"[bold red]❌ Blueprint '{slug}' not found locally in blueprints/.[/bold red]")
        sys.exit(1)

    target_dir = Path(out) if out else Path(f"./{candidate.stem}-scaffold")
    try:
        res = scaffold_blueprint(candidate, target_dir)
        if as_json:
            click.echo(json.dumps({
                "slug": res.slug,
                "target_dir": str(res.target_dir.resolve()),
                "files": [f.filename for f in res.files],
            }, indent=2))
            return

        console.print(Panel(
            f"[bold green]✅ Project Scaffolded Successfully![/bold green]\n\n"
            f"[bold]Target Directory:[/bold] [cyan]{res.target_dir.resolve()}[/cyan]\n"
            f"[bold]Generated Files ({len(res.files)}):[/bold]\n"
            + "\n".join(f"  • [green]{f.filename}[/green] ({f.language})" for f in res.files)
            + f"\n\n[dim]See {res.target_dir}/README.md for build instructions.[/dim]",
            title=f"🚀 Scaffold: {res.slug}",
            border_style="green",
        ))
    except Exception as e:
        if as_json:
            click.echo(json.dumps({"error": str(e)}, indent=2))
            sys.exit(1)
        console.print(f"[bold red]❌ Scaffolding failed:[/bold red] {e}")
        sys.exit(1)


@cli.command("mcp")
def start_mcp():
    """Start the native Model Context Protocol (MCP) server on stdio."""
    from curator.mcp_server import run_stdio_server
    run_stdio_server()


if __name__ == "__main__":
    cli()
