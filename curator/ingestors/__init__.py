"""curator/ingestors/__init__.py"""
from .github_ingestor import ingest_github_repo
from .youtube_ingestor import ingest_youtube_video
from .web_ingestor import ingest_webpage

__all__ = ["ingest_github_repo", "ingest_youtube_video", "ingest_webpage"]
