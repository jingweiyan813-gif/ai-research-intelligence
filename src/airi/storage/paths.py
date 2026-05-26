from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class StoragePaths(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    project_root: Path
    data_dir: Path
    state_dir: Path
    reports_dir: Path
    sample_dir: Path
    cache_dir: Path
    raw_dir: Path

    @classmethod
    def default(cls, project_root: Path | None = None) -> StoragePaths:
        root = Path.cwd() if project_root is None else project_root
        root = root.resolve()
        data_dir = root / "data"
        return cls(
            project_root=root,
            data_dir=data_dir,
            state_dir=data_dir / "state",
            reports_dir=data_dir / "reports",
            sample_dir=data_dir / "sample",
            cache_dir=data_dir / "cache",
            raw_dir=data_dir / "raw",
        )

    def ensure_public_dirs(self) -> None:
        for directory in (self.state_dir, self.reports_dir, self.sample_dir):
            directory.mkdir(parents=True, exist_ok=True)

    def ensure_private_dirs(self) -> None:
        for directory in (self.cache_dir, self.raw_dir):
            directory.mkdir(parents=True, exist_ok=True)
