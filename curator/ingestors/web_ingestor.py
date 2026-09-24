"""
curator/ingestors/web_ingestor.py

General-purpose web page ingestor for articles, docs, and forum threads.
- Fetches page HTML via httpx (follows redirects, handles HTTPS)
- Strips boilerplate (navbars, ads, scripts, styles) via BeautifulSoup
- Detects Open Graph metadata for title/description
- Extracts main article body text
- Returns raw KnowledgeEntry; AI summarization runs in processing/
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from curator.models import KnowledgeEntry, SourceType

_JUNK_TAGS = [
    "script", "style", "nav", "header", "footer", "aside",
    "advertisement", "noscript", "iframe", "form", "button",
    "svg", "figure", "figcaption",
]

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def _get_og_meta(soup: BeautifulSoup, prop: str) -> str:
    """Extract Open Graph or standard meta tag content."""
    tag = soup.find("meta", property=f"og:{prop}") or soup.find("meta", attrs={"name": prop})
    if tag:
        return tag.get("content", "").strip()
    return ""


def _extract_main_text(soup: BeautifulSoup) -> str:
    """
    Strip junk tags and extract the primary readable text.
    Prefers <article>, <main>, or the largest <div> block.
    """
    for tag in soup(_JUNK_TAGS):
        tag.decompose()

    # Try semantic containers first
    for selector in ["article", "main", "[role='main']", ".post-content",
                     ".entry-content", ".article-body", "#content"]:
        container = soup.select_one(selector)
        if container:
            text = container.get_text(separator="\n", strip=True)
            if len(text) > 200:
                return text

    # Fallback: largest text block among divs
    divs = soup.find_all("div")
    if divs:
        largest = max(divs, key=lambda d: len(d.get_text(strip=True)), default=None)
        if largest:
            return largest.get_text(separator="\n", strip=True)

    return soup.get_text(separator="\n", strip=True)


def _detect_author(soup: BeautifulSoup) -> str:
    """Try to detect author from common byline patterns."""
    # Open Graph / meta
    author = _get_og_meta(soup, "author") or _get_og_meta(soup, "article:author")
    if author:
        return author

    # Common byline class names
    for selector in [".author", ".byline", "[rel='author']", "[itemprop='author']"]:
        el = soup.select_one(selector)
        if el:
            text = el.get_text(strip=True)
            if text and len(text) < 80:
                return text

    return ""


def ingest_webpage(url: str) -> KnowledgeEntry:
    """
    Ingest any web page by URL.

    Args:
        url: Full HTTP/HTTPS URL to the page.

    Returns:
        KnowledgeEntry with extracted text in raw_content.
        Category/tags/description will be filled by the AI pipeline.

    Raises:
        RuntimeError: If the page cannot be fetched or parsed.
    """
    try:
        resp = httpx.get(
            url,
            headers=_HEADERS,
            timeout=20,
            follow_redirects=True,
        )
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"HTTP {e.response.status_code} fetching {url}") from e
    except httpx.RequestError as e:
        raise RuntimeError(f"Network error fetching {url}: {e}") from e

    soup = BeautifulSoup(resp.text, "lxml")

    # Title: OG > <title>
    title = _get_og_meta(soup, "title")
    if not title:
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else urlparse(url).hostname or url

    # Description: OG > meta description
    description = _get_og_meta(soup, "description")

    author = _detect_author(soup)
    main_text = _extract_main_text(soup)

    # Truncate to 5000 chars for AI processing
    text_excerpt = main_text[:5000]

    raw_content = "\n\n".join(filter(None, [
        f"Title: {title}",
        f"URL: {url}",
        f"Author: {author}" if author else "",
        f"Meta description: {description}" if description else "",
        f"Page content:\n{text_excerpt}",
    ]))

    return KnowledgeEntry(
        url=url,
        title=title or url,
        description=description or "A web resource.",  # Overwritten by summarizer
        source_type=SourceType.WEB,
        category="Uncategorized",
        author=author or None,
        raw_content=raw_content,
    )
