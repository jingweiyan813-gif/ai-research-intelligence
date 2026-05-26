from __future__ import annotations

import math
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from airi.models.enums import TrendType
from airi.models.evidence import EvidenceRef


class TopicTrend(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str = Field(min_length=1)
    window_start: datetime
    window_end: datetime
    item_count: int = Field(ge=0)
    source_count: int = Field(ge=0)
    paper_count: int = Field(ge=0)
    repo_count: int = Field(ge=0)
    hn_count: int = Field(ge=0)
    company_count: int = Field(ge=0)
    previous_window_count: int = Field(ge=0)
    growth_rate: float
    momentum_score: float = Field(ge=0.0, le=1.0)
    novelty_score: float = Field(ge=0.0, le=1.0)
    trend_type: TrendType
    representative_item_ids: list[str]
    interpretation: str | None = None

    @model_validator(mode="after")
    def require_valid_window(self) -> TopicTrend:
        if self.window_end <= self.window_start:
            raise ValueError("window_end must be after window_start")
        return self


class TrendClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    trend_type: TrendType
    claim: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_refs: list[EvidenceRef] = Field(min_length=1)
    window_start: datetime
    window_end: datetime
    metrics: dict[str, float] = Field(default_factory=dict)

    @field_validator("metrics")
    @classmethod
    def require_finite_metric_values(
        cls,
        metrics: dict[str, float],
    ) -> dict[str, float]:
        for value in metrics.values():
            if not math.isfinite(value):
                raise ValueError("metric values must be finite numbers")
        return metrics

    @model_validator(mode="after")
    def require_valid_window(self) -> TrendClaim:
        if self.window_end <= self.window_start:
            raise ValueError("window_end must be after window_start")
        return self
