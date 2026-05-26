from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from airi.models.enums import SourceType


class SourceMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: SourceType
    source_item_id: str | None = None
    source_url: str = Field(min_length=1)
    fetched_at: datetime
    connector_name: str = Field(min_length=1)
    connector_version: str = "v1"
    raw_payload_hash: str = Field(min_length=1)
