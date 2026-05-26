from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

from airi.models import IntelligenceItem, RawSourceItem, SourceType


class ConnectorResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: SourceType
    raw_count: int = Field(default=0, ge=0)
    normalized_count: int = Field(default=0, ge=0)
    errors: list[str] = Field(default_factory=list)
    started_at: datetime
    completed_at: datetime | None = None


class BaseConnector(ABC):
    name: str
    source: SourceType
    connector_version: str = "v1"

    @abstractmethod
    def fetch_raw(
        self,
        *,
        since: datetime | None = None,
        limit: int | None = None,
    ) -> list[RawSourceItem]:
        raise NotImplementedError

    @abstractmethod
    def normalize(self, raw: RawSourceItem) -> IntelligenceItem:
        raise NotImplementedError

    def fetch_and_normalize(
        self,
        *,
        since: datetime | None = None,
        limit: int | None = None,
    ) -> tuple[list[IntelligenceItem], ConnectorResult]:
        started_at = datetime.now(timezone.utc)
        result = ConnectorResult(source=self.source, started_at=started_at)
        items: list[IntelligenceItem] = []

        try:
            raw_items = self.fetch_raw(since=since, limit=limit)
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"fetch_raw failed: {exc}")
            result.completed_at = datetime.now(timezone.utc)
            return items, result

        result.raw_count = len(raw_items)
        for index, raw_item in enumerate(raw_items):
            try:
                items.append(self.normalize(raw_item))
            except Exception as exc:  # noqa: BLE001
                result.errors.append(f"normalize item {index} failed: {exc}")

        result.normalized_count = len(items)
        result.completed_at = datetime.now(timezone.utc)
        return items, result
