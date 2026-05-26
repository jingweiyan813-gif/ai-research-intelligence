from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


class JSONStore:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir

    def read_json(self, relative_path: str | Path, default: Any = None) -> Any:
        path = self._resolve(relative_path)
        if not path.exists():
            return default
        try:
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON file: {path}") from exc

    def write_json(self, relative_path: str | Path, data: Any) -> Path:
        path = self._resolve(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._atomic_write_text(
            path,
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        )
        return path

    def exists(self, relative_path: str | Path) -> bool:
        return self._resolve(relative_path).exists()

    def delete(self, relative_path: str | Path) -> bool:
        path = self._resolve(relative_path)
        if not path.exists():
            return False
        path.unlink()
        return True

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
