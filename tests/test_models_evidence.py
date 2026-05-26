from __future__ import annotations

import pytest
from pydantic import ValidationError

from airi.models import EvidenceRef, SourceType


def test_evidence_ref_valid() -> None:
    evidence = EvidenceRef(
        item_id="item_abc",
        source=SourceType.GITHUB,
        title="Repo",
        url="https://github.com/example/repo",
        reason="Shows adoption.",
    )

    assert evidence.source == SourceType.GITHUB


def test_evidence_ref_empty_item_id_fails() -> None:
    with pytest.raises(ValidationError):
        EvidenceRef(item_id="", source=SourceType.GITHUB, title="Repo", url="https://x.test")
