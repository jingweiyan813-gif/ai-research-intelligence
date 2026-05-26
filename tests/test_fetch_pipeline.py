from __future__ import annotations

import pytest

from airi.connectors import FakeConnector
from airi.pipeline import FetchPipeline
from airi.storage import StateStore, StoragePaths


def pipeline_for(tmp_path, connectors):  # type: ignore[no-untyped-def]
    return FetchPipeline(
        connectors=connectors,
        state_store=StateStore(StoragePaths.default(tmp_path)),
    )


def test_pipeline_continues_in_non_strict_mode(tmp_path) -> None:  # type: ignore[no-untyped-def]
    pipeline = pipeline_for(
        tmp_path,
        [FakeConnector(item_count=2, fail_fetch=True), FakeConnector(item_count=2)],
    )

    result = pipeline.run(save=False)

    assert result.total_items == 2
    assert result.total_errors == 1
    assert len(result.connector_results) == 2


def test_pipeline_raises_in_strict_mode_if_connector_has_errors(tmp_path) -> None:  # type: ignore[no-untyped-def]
    pipeline = pipeline_for(tmp_path, [FakeConnector(fail_fetch=True)])

    with pytest.raises(RuntimeError, match="Connector fake failed"):
        pipeline.run(strict=True, save=False)


def test_pipeline_save_true_writes_state_files(tmp_path) -> None:  # type: ignore[no-untyped-def]
    paths = StoragePaths.default(tmp_path)
    state_store = StateStore(paths)
    pipeline = FetchPipeline([FakeConnector(item_count=2)], state_store)

    result = pipeline.run(save=True)

    assert result.total_items == 2
    assert (paths.state_dir / "latest_items.jsonl").exists()
    assert (paths.state_dir / "source_health.json").exists()
    assert (paths.state_dir / "last_run.json").exists()
    assert len(state_store.load_latest_items()) == 2
    assert state_store.load_last_run()["total_items"] == 2
    assert state_store.load_source_health()["unknown"]["normalized_count"] == 2


def test_pipeline_save_false_does_not_write_state(tmp_path) -> None:  # type: ignore[no-untyped-def]
    paths = StoragePaths.default(tmp_path)
    pipeline = FetchPipeline([FakeConnector(item_count=2)], StateStore(paths))

    result = pipeline.run(save=False)

    assert result.total_items == 2
    assert not paths.state_dir.exists()
