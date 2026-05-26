from __future__ import annotations

import re

from airi.normalize.fingerprint import short_hash
from airi.normalize.text import normalize_for_matching

_UNSAFE_SLUG_CHARS_RE = re.compile(r"[^A-Za-z0-9_.\-\s]+")
_WHITESPACE_RE = re.compile(r"\s+")
_DASH_RE = re.compile(r"-+")


def safe_slug(text: str, max_length: int = 80) -> str:
    if max_length <= 0:
        raise ValueError("max_length must be positive")
    normalized = normalize_for_matching(text)
    normalized = normalized.replace("/", " ").replace("\\", " ")
    slug = _UNSAFE_SLUG_CHARS_RE.sub("", normalized)
    slug = _WHITESPACE_RE.sub("-", slug)
    slug = _DASH_RE.sub("-", slug).strip("-._")
    if not slug:
        slug = "item"
    return slug[:max_length].strip("-._") or "item"


def safe_cache_key(text: str, max_length: int = 120) -> str:
    if max_length <= 0:
        raise ValueError("max_length must be positive")
    suffix = short_hash(text, length=12)
    suffix_with_sep = f"-{suffix}"
    slug_max_length = max(1, max_length - len(suffix_with_sep))
    slug = safe_slug(text, max_length=slug_max_length)
    key = f"{slug}{suffix_with_sep}"[:max_length].strip("-._")
    if key in {"", ".", ".."}:
        return f"item-{suffix}"
    return key.replace("/", "-").replace("\\", "-")
