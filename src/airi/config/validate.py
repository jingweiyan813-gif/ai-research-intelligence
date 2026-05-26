from __future__ import annotations

from collections.abc import Iterable

from airi.config.schema import EmailExampleConfig, ScoringWeights

_SECRET_PLACEHOLDERS = (
    "",
    "example",
    "placeholder",
    "changeme",
    "change-me",
    "dummy",
    "not-set",
    "your-",
    "replace-me",
    "redacted",
)


def validate_scoring_weights_sum(weights: ScoringWeights) -> None:
    total = sum(weights.model_dump().values())
    if abs(total - 1.0) > 0.000001:
        raise ValueError("scoring weights must sum to 1.0")


def validate_email_example_has_no_real_secrets(config: EmailExampleConfig) -> None:
    candidates = [config.email.password, config.email.api_key]
    unsafe = [secret for secret in candidates if _looks_like_real_secret(secret)]
    if unsafe:
        raise ValueError("email.example.yml must not contain real-looking secrets")


def _looks_like_real_secret(value: str | None) -> bool:
    if value is None:
        return False
    normalized = value.strip().lower()
    if any(marker in normalized for marker in _SECRET_PLACEHOLDERS):
        return False
    return len(normalized) >= 8


def contains_any_secret_text(text: str, secrets: Iterable[str]) -> bool:
    return any(secret in text for secret in secrets)
