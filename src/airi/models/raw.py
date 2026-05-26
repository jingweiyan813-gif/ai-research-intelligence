from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from airi.models.enums import SourceType


class RawSourceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: SourceType
    source_item_id: str | None = None
    raw_url: str = Field(min_length=1)
    raw_title: str = Field(min_length=1)
    raw_text: str | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    fetched_at: datetime
