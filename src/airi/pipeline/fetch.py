from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from airi.connectors import BaseConnector, ConnectorResult
from airi.models import IntelligenceItem
from airi.storage import StateStore


class FetchPipelineResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[IntelligenceItem]
    connector_results: list[ConnectorResult]
    started_at: datetime
    completed_at: datetime
    total_items: int = Field(ge=0)
    total_errors: int = Field(ge=0)


class FetchPipeline:
    def __init__(
        self,
        connectors: list[BaseConnector],
        state_store: StateStore,
    ) -> None:
        self.connectors = connectors
        self.state_store = state_store

    def run(
        self,
        since: datetime | None = None,
        limit_per_source: int | None = None,
        strict: bool = False,
        save: bool = True,
    ) -> FetchPipelineResult:
        started_at = datetime.now(timezone.utc)
        all_items: list[IntelligenceItem] = []
        connector_results: list[ConnectorResult] = []

        for connector in self.connectors:
            items, result = connector.fetch_and_normalize(
                since=since,
                limit=limit_per_source,
            )
            connector_results.append(result)
            all_items.extend(items)
            if strict and result.errors:
                raise RuntimeError(
                    f"Connector {connector.name} failed: {'; '.join(result.errors)}"
                )

        completed_at = datetime.now(timezone.utc)
        pipeline_result = FetchPipelineResult(
            items=all_items,
            connector_results=connector_results,
            started_at=started_at,
            completed_at=completed_at,
            total_items=len(all_items),
            total_errors=sum(len(result.errors) for result in connector_results),
        )
        if save:
            self._save_result(pipeline_result)
        return pipeline_result

    def _save_result(self, result: FetchPipelineResult) -> None:
        self.state_store.save_latest_items(
            item.model_dump(mode="json") for item in result.items
        )
        self.state_store.save_source_health(
            {
                connector_result.source.value: self._source_health_entry(
                    connector_result
                )
                for connector_result in result.connector_results
            }
        )
        self.state_store.save_last_run(
            {
                "started_at": result.started_at.isoformat(),
                "completed_at": result.completed_at.isoformat(),
                "total_items": result.total_items,
                "total_errors": result.total_errors,
                "source_count": len(result.connector_results),
            }
        )

    @staticmethod
    def _source_health_entry(result: ConnectorResult) -> dict[str, Any]:
        return {
            "source": result.source.value,
            "raw_count": result.raw_count,
            "normalized_count": result.normalized_count,
            "error_count": len(result.errors),
            "errors": result.errors,
            "started_at": result.started_at.isoformat(),
            "completed_at": result.completed_at.isoformat()
            if result.completed_at is not None
            else None,
        }
