from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from airi.models.enums import SourceType


class EvidenceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(min_length=1)
    source: SourceType
    title: str = Field(min_length=1)
    url: str = Field(min_length=1)
    reason: str | None = None
