from __future__ import annotations

import subprocess
import sys

from airi.storage import StateStore, StoragePaths
from tests.factories import make_item


def test_run_weekly_dry_run_supports_no_email() -> None:
    with _isolated_state():
        result = subprocess.run(
            [sys.executable, "scripts/run_weekly.py", "--dry-run", "--no-email"],
            check=False,
            capture_output=True,
            text=True,
        )

    assert result.returncode == 0
    assert "Weekly report:" in result.stdout
    assert "super-secret" not in result.stdout


def test_run_eval_script() -> None:
    with _isolated_state():
        result = subprocess.run(
            [sys.executable, "scripts/run_eval.py"],
            check=False,
            capture_output=True,
            text=True,
        )

    assert result.returncode == 0
    assert "Eval report:" in result.stdout


class _isolated_state:
    def __enter__(self):  # type: ignore[no-untyped-def]
        self._cwd = __import__("os").getcwd()
        self._tmp = __import__("tempfile").TemporaryDirectory()
        __import__("shutil").copytree(
            self._cwd,
            self._tmp.name,
            dirs_exist_ok=True,
            ignore=__import__("shutil").ignore_patterns(
                ".git",
                ".venv",
                "__pycache__",
                "*.pyc",
            ),
        )
        __import__("os").chdir(self._tmp.name)
        state = StateStore(StoragePaths.default())
        state.save_latest_items([make_item(item_id="a").model_dump(mode="json")])
        return self

    def __exit__(self, *args):  # type: ignore[no-untyped-def]
        __import__("os").chdir(self._cwd)
        self._tmp.cleanup()
