"""Source ingestion adapters: normalize raw items into pipeline-ready inputs.

Two operational source types (news, social) share one interface so new
providers plug in without touching the analysis pipeline.
"""

from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.signal_contract import SourceType


class RawSourceItem(BaseModel):
    """Normalized item as delivered by any adapter."""

    provider: str = Field(min_length=1)
    source_type: SourceType
    external_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    url: str | None = None
    published_at: datetime | None = None

    @field_validator("text")
    @classmethod
    def _strip_text(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("text must not be blank")
        return stripped


class NewsAdapter:
    """News article/headline input. Expect headline or summary in `text`."""

    source_type = SourceType.news

    def normalize(self, raw: dict) -> RawSourceItem:
        return RawSourceItem(
            provider=raw.get("provider", "news-adapter"),
            source_type=self.source_type,
            external_id=str(raw["id"]),
            text=raw["headline"] if "headline" in raw else raw["text"],
            url=raw.get("url"),
            published_at=raw.get("published_at"),
        )


class SocialAdapter:
    """Social post input. Truncates to a retained-text window and records
    missing publication time via null published_at (flagged downstream)."""

    MAX_LEN = 500

    source_type = SourceType.social

    def normalize(self, raw: dict) -> RawSourceItem:
        text = raw["text"]
        return RawSourceItem(
            provider=raw.get("provider", "social-adapter"),
            source_type=self.source_type,
            external_id=str(raw["id"]),
            text=text[: self.MAX_LEN],
            url=raw.get("url"),
            published_at=raw.get("published_at"),
        )


ADAPTERS: dict[SourceType, NewsAdapter | SocialAdapter] = {
    SourceType.news: NewsAdapter(),
    SourceType.social: SocialAdapter(),
}


def normalize_item(source_type: SourceType, raw: dict) -> RawSourceItem:
    return ADAPTERS[source_type].normalize(raw)
