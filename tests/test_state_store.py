from __future__ import annotations

from airi.storage import StateStore, StoragePaths


def test_state_store_missing_files_return_empty_structures(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = StateStore(StoragePaths.default(tmp_path))

    assert store.load_seen_items() == {}
    assert store.load_topic_timeseries() == {}
    assert store.load_source_health() == {}
    assert store.load_last_run() == {}
    assert store.load_latest_items() == []


def test_state_store_save_and_load(tmp_path) -> None:  # type: ignore[no-untyped-def]
    paths = StoragePaths.default(tmp_path)
    store = StateStore(paths)

    store.save_seen_items({"item_1": True})
    store.save_topic_timeseries({"ai_agents": [1, 2]})
    store.save_source_health({"github": {"ok": True}})
    store.save_last_run({"status": "ok"})
    store.save_latest_items([{"id": "item_1"}])

    assert paths.state_dir.is_dir()
    assert store.load_seen_items() == {"item_1": True}
    assert store.load_latest_items() == [{"id": "item_1"}]
