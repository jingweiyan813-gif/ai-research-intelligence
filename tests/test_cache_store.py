from __future__ import annotations

import pytest

from airi.storage import CacheStore, StoragePaths


def test_cache_store_read_write_and_clear(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = CacheStore(StoragePaths.default(tmp_path))

    path = store.write_cache("github", "repo/example", {"stars": 10})

    assert path.name == "repo_example.json"
    assert store.read_cache("github", "repo/example") == {"stars": 10}
    assert store.clear_namespace("github") == 1
    assert store.read_cache("github", "repo/example", default=None) is None


def test_cache_safe_key_prevents_path_traversal(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = CacheStore(StoragePaths.default(tmp_path))

    path = store.write_cache("../secrets", "../../token", {"safe": True})

    assert tmp_path in path.parents
    assert ".." not in path.parts
    assert path.name == "token.json"


def test_cache_empty_key_fails(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = CacheStore(StoragePaths.default(tmp_path))

    with pytest.raises(ValueError):
        store.write_cache("github", "../", {"safe": True})
