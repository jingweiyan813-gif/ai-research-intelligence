from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReportSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    evidence_item_ids: list[str] = Field(default_factory=list)


class Report(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    generated_at: datetime
    report_type: str = Field(min_length=1)
    sections: list[ReportSection] = Field(min_length=1)
    top_item_ids: list[str] = Field(default_factory=list)
    trend_claim_ids: list[str] = Field(default_factory=list)
