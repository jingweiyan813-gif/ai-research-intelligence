from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from airi.models import ExtractionMetadata, ExtractionMethod


def test_extraction_metadata_valid() -> None:
    metadata = ExtractionMetadata(
        method=ExtractionMethod.RULE,
        extractor_name="topic_rules",
        extractor_version="v1",
        extracted_at=datetime.now(timezone.utc),
        confidence=0.8,
    )

    assert metadata.confidence == 0.8


def test_extraction_confidence_range_validation() -> None:
    with pytest.raises(ValidationError):
        ExtractionMetadata(
            method=ExtractionMethod.RULE,
            extractor_name="topic_rules",
            extractor_version="v1",
            extracted_at=datetime.now(timezone.utc),
            confidence=1.5,
        )
