"""
curator/ingestors/github_ingestor.py

Ingests a GitHub repository via the GitHub REST API.
- Extracts: name, description, stars, license, last commit date, README text
- Falls back gracefully if the API rate-limits (uses unauthenticated calls)
- Returns a raw KnowledgeEntry (unclassified; classifier runs next)
"""

from __future__ import annotations

import re
import base64
from datetime import datetime
from urllib.parse import urlparse

import requests

from curator.models import EntryStatus, KnowledgeEntry, SourceType


_GITHUB_API = "https://api.github.com"
_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "knowledge-curator/1.0",
}


def _parse_owner_repo(url: str) -> tuple[str, str]:
    """Extract owner and repo name from a GitHub URL."""
    path = urlparse(url).path.strip("/")
    parts = path.split("/")
    if len(parts) < 2:
        raise ValueError(f"Cannot parse owner/repo from URL: {url}")
    return parts[0], parts[1].removesuffix(".git")


def _get_readme(owner: str, repo: str, token: str | None = None) -> str:
    """Fetch and decode the default README from GitHub API."""
    headers = dict(_HEADERS)
    if token:
        headers["Authorization"] = f"Bearer {token}"

    resp = requests.get(
        f"{_GITHUB_API}/repos/{owner}/{repo}/readme",
        headers=headers,
        timeout=15,
    )
    if resp.status_code != 200:
        return ""
    data = resp.json()
    content = data.get("content", "")
    encoding = data.get("encoding", "base64")
    if encoding == "base64":
        try:
            return base64.b64decode(content).decode("utf-8", errors="replace")
        except Exception:
            return ""
    return content


def _get_tree_summary(owner: str, repo: str, default_branch: str, token: str | None = None) -> str:
    """Fetch top-level and key source paths from GitHub tree API."""
    headers = dict(_HEADERS)
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        resp = requests.get(
            f"{_GITHUB_API}/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1",
            headers=headers,
            timeout=15,
        )
        if resp.status_code != 200:
            return ""
        tree = resp.json().get("tree", [])
        paths = [
            item["path"] for item in tree
            if not any(item["path"].startswith(p) for p in (".github", "test", "docs", ".git", "gradle", "node_modules"))
            and item.get("type") == "blob"
        ]
        return paths
    except Exception:
        return []


def _fetch_key_source_snippets(owner: str, repo: str, default_branch: str, paths: list[str]) -> str:
    """Fetch raw code snippets from 2-3 most critical source/interface files."""
    if not paths:
        return ""

    # Filter out secondary directories like website, samples, tests
    core_paths = [
        p for p in paths
        if not any(p.lower().startswith(d) for d in ("website/", "site/", "test/", "tests/", "sample/", "samples/"))
    ] or paths

    # Priority ranking for architectural insight
    patterns = [
        # Manifests & specs
        r"(Cargo\.toml|go\.mod|module\.prop|pom\.xml)$",
        # C/C++ headers & kernel hooks
        r"(include/.*\.h|kprobe.*\.c|hook.*\.c|su.*\.c|driver.*\.c)$",
        # Core interfaces / entrypoints
        r"(src/lib\.rs|main\.go|.*Client\.(java|kt|py|go)|.*Service\.(java|kt|py|go)|.*Engine\.(java|kt|py|go)|core\.(py|rs|go))$",
    ]

    selected = []
    for pattern in patterns:
        for path in core_paths:
            if re.search(pattern, path, re.IGNORECASE) and path not in selected:
                selected.append(path)
                if len(selected) >= 3:
                    break
        if len(selected) >= 3:
            break

    # If priority matching found nothing, pick top 2 source code files
    if not selected:
        for path in paths:
            if path.endswith((".rs", ".go", ".c", ".h", ".cpp", ".java", ".kt", ".py")):
                selected.append(path)
                if len(selected) >= 2:
                    break

    snippets = []
    for path in selected[:3]:
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{default_branch}/{path}"
        try:
            r = requests.get(raw_url, timeout=8)
            if r.status_code == 200 and r.text:
                # Truncate to first 2500 chars per file
                code_snippet = r.text[:2500].strip()
                snippets.append(f"--- File: {path} ---\n{code_snippet}")
        except Exception:
            continue

    return "\n\n".join(snippets)


def ingest_github_repo(url: str, token: str | None = None) -> KnowledgeEntry:
    """
    Ingest a GitHub repository by URL.


    Args:
        url:   Full GitHub URL, e.g. https://github.com/topjohnwu/Magisk
        token: Optional GitHub PAT for higher rate limits (5000/hr vs 60/hr)

    Returns:
        KnowledgeEntry with raw_content set but category/tags not yet classified.
    """
    owner, repo = _parse_owner_repo(url)

    headers = dict(_HEADERS)
    if token:
        headers["Authorization"] = f"Bearer {token}"

    resp = requests.get(
        f"{_GITHUB_API}/repos/{owner}/{repo}",
        headers=headers,
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    # Pull README for richer context
    readme = _get_readme(owner, repo, token)
    # Truncate README to first 4000 chars to keep prompts manageable
    readme_excerpt = readme[:4000] if readme else ""

    # Determine status from repo signals
    status = EntryStatus.ACTIVE
    if data.get("archived"):
        status = EntryStatus.ARCHIVED
    elif data.get("disabled"):
        status = EntryStatus.DEPRECATED

    default_branch = data.get("default_branch", "main")
    tree_paths = _get_tree_summary(owner, repo, default_branch, token)
    tree_summary = "\n".join(tree_paths[:60]) if tree_paths else ""
    code_snippets = _fetch_key_source_snippets(owner, repo, default_branch, tree_paths)

    # Build raw content block for classifier and blueprint extractor
    raw_content = "\n\n".join(filter(None, [
        f"Name: {data.get('full_name', '')}",
        f"Description: {data.get('description', '')}",
        f"Topics: {', '.join(data.get('topics', []))}",
        f"Language: {data.get('language', '')}",
        f"Stars: {data.get('stargazers_count', 0)}",
        f"License: {(data.get('license') or {}).get('spdx_id', 'Unknown')}",
        f"Repository File Tree:\n{tree_summary}" if tree_summary else "",
        f"Core Source Code Snippets:\n{code_snippets}" if code_snippets else "",
        f"README excerpt:\n{readme_excerpt}",
    ]))


    return KnowledgeEntry(
        url=url.rstrip("/"),
        title=data.get("full_name", f"{owner}/{repo}"),
        description=data.get("description") or "A GitHub repository.",
        source_type=SourceType.GITHUB,
        # Category & tags will be filled by classifier; use placeholder
        category="Uncategorized",
        tags=data.get("topics", []),
        status=status,
        author=owner,
        stars=data.get("stargazers_count"),
        raw_content=raw_content,
    )
