from __future__ import annotations

import re
import string

_WHITESPACE_RE = re.compile(r"[ \t\f\v]+")
_BLANK_LINE_RE = re.compile(r"\n+")
_ALLOWED_MATCHING_PUNCTUATION = "+#.-_"
_REMOVE_FOR_MATCHING = "".join(
    char
    for char in string.punctuation
    if char not in _ALLOWED_MATCHING_PUNCTUATION
)
_MATCHING_TRANSLATION = str.maketrans("", "", _REMOVE_FOR_MATCHING)


def normalize_whitespace(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = _WHITESPACE_RE.sub(" ", normalized)
    return normalized.strip()


def normalize_text(text: str) -> str:
    normalized = normalize_whitespace(text)
    lines = [line.strip() for line in normalized.split("\n")]
    non_empty_lines = [line for line in lines if line]
    return "\n".join(non_empty_lines)


def normalize_for_matching(text: str) -> str:
    normalized = normalize_text(text).lower()
    normalized = normalized.translate(_MATCHING_TRANSLATION)
    normalized = _BLANK_LINE_RE.sub(" ", normalized)
    return normalize_whitespace(normalized)


def compact_text(text: str, max_chars: int) -> str:
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    normalized = normalize_text(text)
    if len(normalized) <= max_chars:
        return normalized
    if max_chars <= 3:
        return "." * max_chars
    return normalized[: max_chars - 3].rstrip() + "..."
