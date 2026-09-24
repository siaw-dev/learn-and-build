"""
curator/ingestors/youtube_ingestor.py

Ingests a YouTube video using youtube-transcript-api.
- Extracts video ID from any youtube.com or youtu.be URL
- Fetches full transcript text (auto-generated or manual captions)
- Falls back gracefully if captions are unavailable
- Returns raw KnowledgeEntry; AI summarization runs in processing/
"""

from __future__ import annotations

import re
from urllib.parse import urlparse, parse_qs

import httpx
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

from curator.models import KnowledgeEntry, SourceType


_YT_API_BASE = "https://www.youtube.com/oembed"


def _extract_video_id(url: str) -> str:
    """Extract YouTube video ID from various URL formats."""
    parsed = urlparse(url)

    # youtu.be/<id>
    if parsed.netloc in ("youtu.be",):
        return parsed.path.lstrip("/").split("?")[0]

    # youtube.com/watch?v=<id>
    qs = parse_qs(parsed.query)
    if "v" in qs:
        return qs["v"][0]

    # youtube.com/shorts/<id> or /embed/<id>
    m = re.search(r"/(shorts|embed|v)/([a-zA-Z0-9_-]{11})", parsed.path)
    if m:
        return m.group(2)

    raise ValueError(f"Cannot extract YouTube video ID from URL: {url}")


def _fetch_video_metadata(video_id: str) -> dict:
    """Fetch video title and author via oEmbed (no API key needed)."""
    try:
        resp = httpx.get(
            _YT_API_BASE,
            params={"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"},
            timeout=10,
            follow_redirects=True,
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                "title": data.get("title", f"YouTube Video {video_id}"),
                "author": data.get("author_name", ""),
            }
    except Exception:
        pass
    return {"title": f"YouTube Video {video_id}", "author": ""}


def _fetch_transcript(video_id: str) -> str:
    """
    Attempt to fetch transcript in English first, then any available language.
    Returns empty string if transcripts are unavailable.
    """
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        # Try English manual first, then auto-generated
        try:
            t = transcript_list.find_manually_created_transcript(["en", "en-US", "en-GB"])
        except Exception:
            try:
                t = transcript_list.find_generated_transcript(["en", "en-US", "en-GB"])
            except Exception:
                # Grab first available and translate
                t = next(iter(transcript_list))

        entries = t.fetch()
        # Concatenate all text snippets into a single string
        full_text = " ".join(item.text for item in entries)
        return full_text

    except (NoTranscriptFound, TranscriptsDisabled, VideoUnavailable) as e:
        raise RuntimeError(f"Transcript unavailable: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Transcript fetch error: {e}") from e


def ingest_youtube_video(url: str) -> KnowledgeEntry:
    """
    Ingest a YouTube video by URL.

    Args:
        url: Any valid youtube.com or youtu.be URL.

    Returns:
        KnowledgeEntry with full transcript in raw_content.
        Category/tags/description will be filled by the AI classifier+summarizer.

    Raises:
        RuntimeError: If transcript is unavailable or video cannot be accessed.
        ValueError:   If the URL is not a recognizable YouTube format.
    """
    video_id = _extract_video_id(url)
    meta = _fetch_video_metadata(video_id)
    transcript = _fetch_transcript(video_id)

    canonical_url = f"https://www.youtube.com/watch?v={video_id}"

    # Truncate transcript to 6000 chars for AI processing
    transcript_excerpt = transcript[:6000]

    raw_content = "\n\n".join([
        f"Title: {meta['title']}",
        f"Author/Channel: {meta['author']}",
        f"Video URL: {canonical_url}",
        f"Transcript excerpt:\n{transcript_excerpt}",
    ])

    return KnowledgeEntry(
        url=canonical_url,
        title=meta["title"],
        description=f"YouTube video by {meta['author']}.",  # Overwritten by summarizer
        source_type=SourceType.YOUTUBE,
        category="Uncategorized",
        author=meta["author"],
        raw_content=raw_content,
    )
