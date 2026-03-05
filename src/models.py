"""Data models for AI Brief Starter."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class NewsItem:
    """Represents a single news item in the pipeline.

    Fields are populated progressively through the pipeline:
    - Fetching: title, link, summary, published, dedupe_link
    - Filtering: (no new fields, items are filtered out)
    - Ranking: score, brief, details, impact
    - Localization: title, brief, details, impact (translated to Chinese)
    - Title completion: title (subject guaranteed)
    - Key points: key_points
    """

    # Core fields (from RSS feed)
    title: str = ""
    link: str = ""
    summary: str = ""
    published: str = ""

    # Deduplication
    dedupe_link: str = ""

    # LLM-generated fields
    score: str = ""
    brief: str = ""
    details: str = ""
    impact: str = ""
    key_points: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for backward compatibility.

        Note: key_points is converted to list in dict (not comma-separated string).
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NewsItem:
        """Create NewsItem from dictionary.

        Handles both old dict format and new format.
        """
        # Handle key_points: could be list or comma-separated string
        key_points = data.get("key_points", [])
        if isinstance(key_points, str):
            # Old format: comma-separated string
            key_points = [kp.strip() for kp in key_points.split(",") if kp.strip()]
        elif not isinstance(key_points, list):
            key_points = []

        return cls(
            title=str(data.get("title", "")),
            link=str(data.get("link", "")),
            summary=str(data.get("summary", "")),
            published=str(data.get("published", "")),
            dedupe_link=str(data.get("dedupe_link", "")),
            score=str(data.get("score", "")),
            brief=str(data.get("brief", "")),
            details=str(data.get("details", "")),
            impact=str(data.get("impact", "")),
            key_points=key_points,
        )

    @classmethod
    def from_dict_list(cls, data_list: list[dict[str, Any]]) -> list[NewsItem]:
        """Convert list of dicts to list of NewsItems."""
        return [cls.from_dict(item) for item in data_list]

    @staticmethod
    def to_dict_list(items: list[NewsItem]) -> list[dict[str, Any]]:
        """Convert list of NewsItems to list of dicts."""
        return [item.to_dict() for item in items]
