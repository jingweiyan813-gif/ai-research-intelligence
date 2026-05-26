from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from airi.storage.json_store import JSONStore
from airi.storage.paths import StoragePaths

_SAFE_KEY_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


class CacheStore:
    def __init__(self, paths: StoragePaths) -> None:
        self.paths = paths
        self.json_store = JSONStore(paths.cache_dir)

    def read_cache(self, namespace: str, key: str, default: Any = None) -> Any:
        return self.json_store.read_json(
            self._cache_path(namespace, key),
            default=default,
        )

    def write_cache(self, namespace: str, key: str, data: Any) -> Path:
        self.paths.cache_dir.mkdir(parents=True, exist_ok=True)
        return self.json_store.write_json(self._cache_path(namespace, key), data)

    def clear_namespace(self, namespace: str) -> int:
        namespace_path = self.paths.cache_dir / self._safe_part(namespace)
        if not namespace_path.exists():
            return 0
        count = 0
        for path in namespace_path.glob("*.json"):
            path.unlink()
            count += 1
        return count

    def _cache_path(self, namespace: str, key: str) -> Path:
        return Path(self._safe_part(namespace)) / f"{self._safe_part(key)}.json"

    @staticmethod
    def _safe_part(value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Cache namespace and key must not be empty")
        safe = _SAFE_KEY_PATTERN.sub("_", stripped).strip("._-")
        if not safe:
            raise ValueError("Cache namespace and key must contain safe characters")
        return safe
