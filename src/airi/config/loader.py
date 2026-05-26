from __future__ import annotations

from pathlib import Path
from typing import Any, TypeVar

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ValidationError

from airi.config.schema import (
    AppConfig,
    EmailExampleConfig,
    ScoringConfig,
    SourcesConfig,
    TopicsConfig,
    UserProfileConfig,
    WatchlistsConfig,
)
from airi.config.validate import validate_email_example_has_no_real_secrets

CONFIG_DIR = Path("configs")
LOCAL_OVERRIDE_FILES = {
    "profile": "profile.local.yml",
    "email": "email.local.yml",
    "watchlists": "watchlists.local.yml",
}

ConfigModel = TypeVar("ConfigModel", bound=BaseModel)


class ConfigLoadError(RuntimeError):
    pass


def load_app_config(config_dir: Path | str = CONFIG_DIR) -> AppConfig:
    root = Path(config_dir)
    sources = load_sources_config(root)
    topics = load_topics_config(root)
    scoring = load_scoring_config(root)
    profile = load_profile_config(root)
    email = load_email_config(root)
    watchlists = load_watchlists_config(root)
    local_overrides = local_override_status(root)
    return AppConfig(
        sources=sources,
        topics=topics,
        scoring=scoring,
        profile=profile,
        email=email,
        watchlists=watchlists,
        local_overrides=local_overrides,
    )


def load_sources_config(config_dir: Path | str = CONFIG_DIR) -> SourcesConfig:
    return _load_model(Path(config_dir) / "sources.yml", SourcesConfig)


def load_topics_config(config_dir: Path | str = CONFIG_DIR) -> TopicsConfig:
    return _load_model(Path(config_dir) / "topics.yml", TopicsConfig)


def load_scoring_config(config_dir: Path | str = CONFIG_DIR) -> ScoringConfig:
    return _load_model(Path(config_dir) / "scoring.yml", ScoringConfig)


def load_profile_config(config_dir: Path | str = CONFIG_DIR) -> UserProfileConfig:
    root = Path(config_dir)
    path = _override_or_default(root, "profile")
    return _load_model(path, UserProfileConfig)


def load_email_config(config_dir: Path | str = CONFIG_DIR) -> EmailExampleConfig:
    root = Path(config_dir)
    path = _override_or_default(root, "email")
    config = _load_model(path, EmailExampleConfig)
    if path.name == "email.example.yml":
        validate_email_example_has_no_real_secrets(config)
    return config


def load_watchlists_config(config_dir: Path | str = CONFIG_DIR) -> WatchlistsConfig:
    root = Path(config_dir)
    path = _override_or_default(root, "watchlists")
    return _load_model(path, WatchlistsConfig)


def local_override_status(config_dir: Path | str = CONFIG_DIR) -> dict[str, bool]:
    root = Path(config_dir)
    return {
        name: (root / filename).exists()
        for name, filename in LOCAL_OVERRIDE_FILES.items()
    }


def _override_or_default(config_dir: Path, name: str) -> Path:
    local_path = config_dir / LOCAL_OVERRIDE_FILES[name]
    if local_path.exists():
        return local_path
    return config_dir / f"{name}.example.yml"


def _load_model(path: Path, model_type: type[ConfigModel]) -> ConfigModel:
    try:
        data = _load_yaml(path)
        return model_type.model_validate(data)
    except FileNotFoundError as exc:
        raise ConfigLoadError(f"Config file not found: {path}") from exc
    except ValidationError as exc:
        raise ConfigLoadError(f"Invalid config file: {path}\n{exc}") from exc
    except yaml.YAMLError as exc:
        raise ConfigLoadError(f"Invalid YAML file: {path}\n{exc}") from exc


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        loaded = yaml.safe_load(file)
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ConfigLoadError(f"Config file must contain a YAML mapping: {path}")
    return loaded
