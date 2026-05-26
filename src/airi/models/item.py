from __future__ import annotations

import hashlib
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from airi.models.enums import ItemType, SourceType
from airi.models.extraction import ExtractionMetadata
from airi.models.scores import ScoreBundle
from airi.models.signals import SignalBundle
from airi.models.source import SourceMetadata


def build_item_id(source: SourceType, stable_key: str) -> str:
    digest = hashlib.sha256(f"{source.value}:{stable_key}".encode("utf-8")).hexdigest()
    return f"item_{digest[:12]}"


class IntelligenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    source: SourceType
    item_type: ItemType
    title: str = Field(min_length=1)
    url: str = Field(min_length=1)
    canonical_url: str | None = None
    abstract: str | None = None
    content_snippet: str | None = None
    authors: list[str] = Field(default_factory=list)
    organizations: list[str] = Field(default_factory=list)
    repos: list[str] = Field(default_factory=list)
    papers: list[str] = Field(default_factory=list)
    published_at: datetime | None = None
    fetched_at: datetime
    topics: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    source_metadata: SourceMetadata
    extraction_metadata: list[ExtractionMetadata] = Field(default_factory=list)
    signals: SignalBundle
    scores: ScoreBundle | None = None
    source_payload_hash: str = Field(min_length=1)
    content_fingerprint: str = Field(min_length=1)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("title must not be empty")
        return stripped

    @field_validator("topics", "entities", "keywords")
    @classmethod
    def deduplicate_strings(cls, values: list[str]) -> list[str]:
        seen: set[str] = set()
        deduplicated: list[str] = []
        for value in values:
            if value not in seen:
                seen.add(value)
                deduplicated.append(value)
        return deduplicated

    @model_validator(mode="after")
    def require_matching_source_metadata(self) -> IntelligenceItem:
        if self.source_metadata.source != self.source:
            raise ValueError("source_metadata.source must match source")
        return self
