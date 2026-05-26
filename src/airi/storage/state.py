from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast

from airi.storage.json_store import JSONStore
from airi.storage.jsonl_store import JSONLStore
from airi.storage.paths import StoragePaths


class StateStore:
    def __init__(self, paths: StoragePaths) -> None:
        self.paths = paths
        self.json_store = JSONStore(paths.state_dir)
        self.jsonl_store = JSONLStore(paths.state_dir)

    def load_seen_items(self) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            self.json_store.read_json("seen_items.json", default={}),
        )

    def save_seen_items(self, data: dict[str, Any]) -> Path:
        self.paths.ensure_public_dirs()
        return self.json_store.write_json("seen_items.json", data)

    def load_topic_timeseries(self) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            self.json_store.read_json("topic_timeseries.json", default={}),
        )

    def save_topic_timeseries(self, data: dict[str, Any]) -> Path:
        self.paths.ensure_public_dirs()
        return self.json_store.write_json("topic_timeseries.json", data)

    def load_source_health(self) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            self.json_store.read_json("source_health.json", default={}),
        )

    def save_source_health(self, data: dict[str, Any]) -> Path:
        self.paths.ensure_public_dirs()
        return self.json_store.write_json("source_health.json", data)

    def load_last_run(self) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            self.json_store.read_json("last_run.json", default={}),
        )

    def save_last_run(self, data: dict[str, Any]) -> Path:
        self.paths.ensure_public_dirs()
        return self.json_store.write_json("last_run.json", data)

    def load_latest_items(self) -> list[dict[str, Any]]:
        return self.jsonl_store.read_jsonl("latest_items.jsonl")

    def save_latest_items(self, items: Iterable[dict[str, Any]]) -> Path:
        self.paths.ensure_public_dirs()
        return self.jsonl_store.write_jsonl("latest_items.jsonl", items)
