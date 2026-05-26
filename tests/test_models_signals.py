from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from airi.models import CommonSignals, GitHubSignals, SignalBundle


def test_signal_bundle_valid() -> None:
    signals = SignalBundle(
        common=CommonSignals(freshness_days=1.5, source_importance=0.8),
        github=GitHubSignals(
            stars=100,
            forks=12,
            last_pushed_at=datetime.now(timezone.utc),
        ),
    )

    assert signals.github is not None
    assert signals.github.stars == 100


def test_negative_signal_counts_fail() -> None:
    with pytest.raises(ValidationError):
        GitHubSignals(stars=-1)


def test_source_importance_range_validation() -> None:
    with pytest.raises(ValidationError):
        CommonSignals(source_importance=1.1)
