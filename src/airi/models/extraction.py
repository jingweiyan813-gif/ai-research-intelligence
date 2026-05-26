from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from airi.models.enums import ExtractionMethod


class ExtractionMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: ExtractionMethod
    extractor_name: str = Field(min_length=1)
    extractor_version: str = Field(min_length=1)
    extracted_at: datetime
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
