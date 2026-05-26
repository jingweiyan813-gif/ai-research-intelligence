from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ScoreBreakdown(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimension: str = Field(min_length=1)
    score: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1)
    evidence_item_ids: list[str] = Field(default_factory=list)


class ScoreBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic_relevance: float = Field(ge=0.0, le=1.0)
    quality: float = Field(ge=0.0, le=1.0)
    freshness: float = Field(ge=0.0, le=1.0)
    popularity: float = Field(ge=0.0, le=1.0)
    novelty: float = Field(ge=0.0, le=1.0)
    momentum: float = Field(ge=0.0, le=1.0)
    personal_relevance: float = Field(ge=0.0, le=1.0)
    cross_source_correlation: float = Field(ge=0.0, le=1.0)
    final_score: float = Field(ge=0.0, le=1.0)
    breakdowns: list[ScoreBreakdown] = Field(default_factory=list)
