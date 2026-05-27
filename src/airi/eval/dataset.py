from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

DEFAULT_GOLD_PATH = Path("data/sample/eval_gold_items.yml")


def load_gold_items(path: Path = DEFAULT_GOLD_PATH) -> dict[str, Any]:
    if not path.exists():
        return {"relevant_item_ids": [], "notes": "gold file missing"}
    with path.open("r", encoding="utf-8") as file:
        loaded = yaml.safe_load(file) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"Gold file must contain a mapping: {path}")
    relevant = loaded.get("relevant_item_ids", [])
    if not isinstance(relevant, list):
        raise ValueError("relevant_item_ids must be a list")
    return loaded
