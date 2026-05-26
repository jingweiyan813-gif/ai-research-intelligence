from __future__ import annotations

import pytest

from airi.normalize import (
    content_fingerprint,
    short_hash,
    source_payload_hash,
    stable_hash_parts,
)


def test_source_payload_hash_is_stable_regardless_of_key_order() -> None:
    first = source_payload_hash({"b": 2, "a": 1})
    second = source_payload_hash({"a": 1, "b": 2})

    assert first == second
    assert len(first) == 64


def test_content_fingerprint_is_stable_under_whitespace_changes() -> None:
    first = content_fingerprint("An Agent Paper", "Body   text")
    second = content_fingerprint(" An   Agent Paper ", "Body text")

    assert first == second


def test_stable_hash_parts_normalizes_parts() -> None:
    assert stable_hash_parts("Hello, World") == stable_hash_parts(" hello world ")


def test_short_hash_length_validation() -> None:
    assert len(short_hash("hello", length=8)) == 8
    with pytest.raises(ValueError):
        short_hash("hello", length=5)
    with pytest.raises(ValueError):
        short_hash("hello", length=65)
