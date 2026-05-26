from __future__ import annotations

from airi.normalize import (
    canonicalize_arxiv_url,
    canonicalize_github_url,
    canonicalize_url,
    get_registered_domain,
    strip_tracking_params,
)


def test_strip_tracking_params_preserves_useful_query_params() -> None:
    url = "https://example.com/a?utm_source=x&id=1&ref=hn&gclid=abc&keep=yes"

    assert strip_tracking_params(url) == "https://example.com/a?id=1&keep=yes"


def test_canonicalize_url_lowercases_host_removes_fragment_and_trailing_slash() -> None:
    url = " HTTPS://Example.COM/Path/?utm_source=x&id=1#section "

    assert canonicalize_url(url) == "https://example.com/Path?id=1"


def test_canonicalize_arxiv_abs_and_pdf_urls() -> None:
    assert canonicalize_arxiv_url("https://arxiv.org/pdf/2401.12345.pdf") == (
        "https://arxiv.org/abs/2401.12345"
    )
    assert canonicalize_arxiv_url("https://arxiv.org/abs/2401.12345") == (
        "https://arxiv.org/abs/2401.12345"
    )


def test_canonicalize_arxiv_version_suffix_support() -> None:
    assert canonicalize_arxiv_url("https://arxiv.org/pdf/2401.12345v2") == (
        "https://arxiv.org/abs/2401.12345v2"
    )


def test_canonicalize_arxiv_non_arxiv_fallback() -> None:
    assert canonicalize_arxiv_url("https://Example.com/a/?utm_campaign=x") == (
        "https://example.com/a"
    )


def test_canonicalize_github_repo_from_issue_blob_tree_urls() -> None:
    assert canonicalize_github_url("https://github.com/OpenAI/Codex/issues/1") == (
        "https://github.com/OpenAI/Codex"
    )
    blob_url = "https://github.com/OpenAI/Codex/blob/main/README.md"
    assert canonicalize_github_url(blob_url) == (
        "https://github.com/OpenAI/Codex"
    )
    assert canonicalize_github_url("https://github.com/OpenAI/Codex/tree/main") == (
        "https://github.com/OpenAI/Codex"
    )


def test_canonicalize_github_non_github_fallback() -> None:
    assert canonicalize_github_url("https://Example.com/repo/#readme") == (
        "https://example.com/repo"
    )


def test_get_registered_domain_returns_host() -> None:
    assert get_registered_domain("https://Sub.Example.com/path") == "sub.example.com"
    assert get_registered_domain("not-a-url") is None
