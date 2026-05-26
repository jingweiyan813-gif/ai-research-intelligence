from __future__ import annotations

from airi.storage import StoragePaths


def test_public_dirs_creation(tmp_path) -> None:  # type: ignore[no-untyped-def]
    paths = StoragePaths.default(tmp_path)

    paths.ensure_public_dirs()

    assert paths.state_dir.is_dir()
    assert paths.reports_dir.is_dir()
    assert paths.sample_dir.is_dir()
    assert not paths.cache_dir.exists()
    assert not paths.raw_dir.exists()


def test_private_dirs_creation_only_when_requested(tmp_path) -> None:  # type: ignore[no-untyped-def]
    paths = StoragePaths.default(tmp_path)

    paths.ensure_private_dirs()

    assert paths.cache_dir.is_dir()
    assert paths.raw_dir.is_dir()
    assert not paths.state_dir.exists()
