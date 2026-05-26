from __future__ import annotations

import re
from urllib.parse import (
    parse_qsl,
    quote,
    unquote,
    urlencode,
    urlsplit,
    urlunsplit,
)

_TRACKING_PARAM_PREFIXES = ("utm_",)
_TRACKING_PARAM_NAMES = {"ref", "fbclid", "gclid", "mc_cid", "mc_eid"}
_ARXIV_ID_RE = re.compile(r"(?P<id>\d{4}\.\d{4,5}(?:v\d+)?)")


def strip_tracking_params(url: str) -> str:
    parts = urlsplit(url.strip())
    query_params = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        lowered = key.lower()
        is_tracking_param = (
            lowered.startswith(_TRACKING_PARAM_PREFIXES)
            or lowered in _TRACKING_PARAM_NAMES
        )
        if is_tracking_param:
            continue
        query_params.append((key, value))
    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(query_params, doseq=True),
            parts.fragment,
        )
    )


def canonicalize_url(url: str) -> str:
    stripped = strip_tracking_params(url.strip())
    parts = urlsplit(stripped)
    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()
    path = _normalize_path(parts.path)
    if path != "/":
        path = path.rstrip("/")
    return urlunsplit((scheme, netloc, path, parts.query, ""))


def canonicalize_arxiv_url(url: str) -> str:
    parts = urlsplit(url.strip())
    if parts.netloc.lower() not in {"arxiv.org", "www.arxiv.org"}:
        return canonicalize_url(url)
    match = _ARXIV_ID_RE.search(parts.path)
    if match is None:
        return canonicalize_url(url)
    arxiv_id = match.group("id")
    return f"https://arxiv.org/abs/{arxiv_id}"


def canonicalize_github_url(url: str) -> str:
    parts = urlsplit(url.strip())
    if parts.netloc.lower() not in {"github.com", "www.github.com"}:
        return canonicalize_url(url)
    path_parts = [unquote(part) for part in parts.path.split("/") if part]
    if len(path_parts) < 2:
        return canonicalize_url(url)
    owner, repo = path_parts[0], path_parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    return f"https://github.com/{quote(owner, safe='')}/{quote(repo, safe='')}"


def get_registered_domain(url: str) -> str | None:
    parts = urlsplit(url.strip())
    if parts.hostname is None:
        return None
    return parts.hostname.lower()


def _normalize_path(path: str) -> str:
    if not path:
        return ""
    return quote(unquote(path), safe="/:@-._~!$&'()*+,;=")
