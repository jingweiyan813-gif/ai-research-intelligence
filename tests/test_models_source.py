from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from airi.models import SourceMetadata, SourceType


def test_source_metadata_valid() -> None:
    metadata = SourceMetadata(
        source=SourceType.ARXIV,
        source_url="https://arxiv.org/abs/1234",
        fetched_at=datetime.now(timezone.utc),
        connector_name="arxiv",
        raw_payload_hash="abc123",
    )

    assert metadata.connector_version == "v1"


def test_source_metadata_empty_required_field_fails() -> None:
    with pytest.raises(ValidationError):
        SourceMetadata(
            source=SourceType.ARXIV,
            source_url="",
            fetched_at=datetime.now(timezone.utc),
            connector_name="arxiv",
            raw_payload_hash="abc123",
        )
