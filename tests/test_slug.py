from __future__ import annotations

import re

import pytest

from airi.normalize import safe_cache_key, safe_slug


def test_safe_slug_removes_unsafe_path_chars() -> None:
    slug = safe_slug("../Agent / Memory\\ Test: v1!")

    assert "/" not in slug
    assert "\\" not in slug
    assert slug == "agent-memory-test-v1"


def test_safe_slug_empty_returns_item() -> None:
    assert safe_slug("////") == "item"


def test_safe_slug_truncates_to_max_length() -> None:
    assert len(safe_slug("a" * 200, max_length=20)) == 20


def test_safe_cache_key_prevents_path_traversal_and_includes_hash_suffix() -> None:
    key = safe_cache_key("../Agent / Memory\\ Test", max_length=80)

    assert "/" not in key
    assert "\\" not in key
    assert key not in {".", ".."}
    assert re.search(r"-[0-9a-f]{12}$", key) is not None


def test_safe_cache_key_requires_positive_length() -> None:
    with pytest.raises(ValueError):
        safe_cache_key("hello", max_length=0)
