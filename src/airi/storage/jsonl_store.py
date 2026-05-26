from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any


class JSONLStore:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir

    def read_jsonl(self, relative_path: str | Path) -> list[dict[str, Any]]:
        return list(self.iter_jsonl(relative_path))

    def write_jsonl(
        self,
        relative_path: str | Path,
        records: Iterable[dict[str, Any]],
    ) -> Path:
        path = self._resolve(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [json.dumps(record, ensure_ascii=False) for record in records]
        text = "\n".join(lines)
        if text:
            text += "\n"
        self._atomic_write_text(path, text)
        return path

    def append_jsonl(
        self,
        relative_path: str | Path,
        records: Iterable[dict[str, Any]],
    ) -> Path:
        path = self._resolve(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as file:
            for record in records:
                file.write(json.dumps(record, ensure_ascii=False) + "\n")
        return path

    def iter_jsonl(self, relative_path: str | Path) -> Iterator[dict[str, Any]]:
        path = self._resolve(relative_path)
        if not path.exists():
            return
        with path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    record = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid JSONL line {line_number} in {path}"
                    ) from exc
                if not isinstance(record, dict):
                    raise ValueError(
                        f"JSONL line {line_number} in {path} is not an object"
                    )
                yield record

    def _resolve(self, relative_path: str | Path) -> Path:
        path = Path(relative_path)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"Unsafe relative path: {relative_path}")
        return self.base_dir / path

    @staticmethod
    def _atomic_write_text(path: Path, text: str) -> None:
        temp_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=path.parent,
                delete=False,
            ) as file:
                temp_path = file.name
                file.write(text)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temp_path, path)
        finally:
            if temp_path is not None:
                temp = Path(temp_path)
                if temp.exists():
                    temp.unlink()
