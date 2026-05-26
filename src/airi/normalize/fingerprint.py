from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from airi.normalize.text import normalize_for_matching


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def content_fingerprint(title: str, body: str | None = None) -> str:
    parts = [title]
    if body is not None:
        parts.append(body)
    return stable_hash_parts(*parts)


def source_payload_hash(payload: Mapping[str, Any]) -> str:
    serialized = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return sha256_hex(serialized)


def stable_hash_parts(*parts: str) -> str:
    normalized_parts = [normalize_for_matching(part) for part in parts]
    return sha256_hex("\n".join(normalized_parts))


def short_hash(text: str, length: int = 12) -> str:
    if length < 6 or length > 64:
        raise ValueError("length must be between 6 and 64")
    return sha256_hex(text)[:length]
