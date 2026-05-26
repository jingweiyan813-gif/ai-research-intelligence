from __future__ import annotations

import pytest

from airi.normalize import (
    compact_text,
    normalize_for_matching,
    normalize_text,
    normalize_whitespace,
)


def test_normalize_whitespace_collapses_spaces_and_newlines() -> None:
    text = "  hello\t\tworld\r\nnext   line  "

    assert normalize_whitespace(text) == "hello world\nnext line"


def test_normalize_text_strips_lines_and_removes_empty_lines() -> None:
    text = "  first line  \n\n   second line\t\t  \n  "

    assert normalize_text(text) == "first line\nsecond line"


def test_normalize_for_matching_lowercases_and_removes_noisy_punctuation() -> None:
    text = "Hello, C++ / C# agents_v2.0 - test!"

    assert normalize_for_matching(text) == "hello c++ c# agents_v2.0 - test"


def test_compact_text_truncates_with_ellipsis() -> None:
    assert compact_text("hello world", 8) == "hello..."


def test_compact_text_requires_positive_max_chars() -> None:
    with pytest.raises(ValueError):
        compact_text("hello", 0)
