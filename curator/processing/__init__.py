"""curator/processing/__init__.py"""
from .classifier import classify_entry
from .summarizer import summarize_entry
from .deduplicator import is_duplicate

__all__ = ["classify_entry", "summarize_entry", "is_duplicate"]
