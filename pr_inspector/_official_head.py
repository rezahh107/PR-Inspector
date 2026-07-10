from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Mapping

_SOURCE_MARKER = object()
_HEAD_MARKER = object()
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class CompletionError(ValueError):
    pass


@dataclass(frozen=True)
class GitHubPullRequestHeadSource:
    repository: str
    pr_number: int
    api_version: str
    token: str | None = field(default=None, repr=False, compare=False)
    _marker: object = field(default=None, repr=False, compare=False)

    def fetch(self) -> "VerifiedLivePullRequestHead":
        if self._marker is not _SOURCE_MARKER:
            raise CompletionError("live PR-head source is not verifier-created")
        return _fetch_verified_pull_request_head(self)


@dataclass(frozen=True)
class VerifiedLivePullRequestHead:
    repository: str
    repository_id: int
    pr_number: int
    head_sha: str
    api_url: str
    html_url: str
    receipt_sha256: str
    _marker: object = field(repr=False, compare=False)


def github_pull_request_head_source(
    repository: str,
    pr_number: int,
    *,
    token: str | None,
    api_version: str,
) -> GitHubPullRequestHeadSource:
    if repository.count("/") != 1 or any(not part for part in repository.split("/")):
        raise CompletionError("target repository must use OWNER/REPOSITORY")
    if not isinstance(pr_number, int) or isinstance(pr_number, bool) or pr_number < 1:
        raise CompletionError("pull request number must be a positive integer")
    if not api_version:
        raise CompletionError("GitHub API version is required")
    return GitHubPullRequestHeadSource(
        repository, pr_number, api_version, token, _SOURCE_MARKER
    )


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _github_json(url: str, *, token: str | None, api_version: str) -> Mapping[str, Any]:
    headers = {
        "Accept": "application/vnd.github+json",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "X-GitHub-Api-Version": api_version,
        "User-Agent": "PR-Inspector-official-output-verifier",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=20) as response:
            if getattr(response, "status", 200) != 200:
                raise CompletionError(f"GitHub PR endpoint returned HTTP {response.status}")
            payload = json.loads(response.read().decode("utf-8"))
    except CompletionError:
        raise
    except (
        urllib.error.HTTPError,
        urllib.error.URLError,
        TimeoutError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise CompletionError(f"live GitHub PR-head request failed: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise CompletionError("live GitHub PR endpoint must return a JSON object")
    return payload


def _fetch_verified_pull_request_head(
    source: GitHubPullRequestHeadSource,
) -> VerifiedLivePullRequestHead:
    api_url = f"https://api.github.com/repos/{source.repository}/pulls/{source.pr_number}"
    html_url = f"https://github.com/{source.repository}/pull/{source.pr_number}"
    payload = _github_json(api_url, token=source.token, api_version=source.api_version)
    base = payload.get("base")
    repo = base.get("repo") if isinstance(base, Mapping) else None
    head = payload.get("head")
    repo_id = repo.get("id") if isinstance(repo, Mapping) else None
    head_sha = head.get("sha") if isinstance(head, Mapping) else None
    valid = (
        payload.get("number") == source.pr_number,
        payload.get("url") == api_url,
        payload.get("html_url") == html_url,
        isinstance(repo, Mapping) and repo.get("full_name") == source.repository,
        isinstance(repo_id, int) and not isinstance(repo_id, bool) and repo_id > 0,
        isinstance(head_sha, str) and _SHA_RE.fullmatch(head_sha) is not None,
    )
    if not all(valid):
        raise CompletionError(
            "insufficient_evidence: GitHub PR payload is partial or does not match canonical identity"
        )
    return VerifiedLivePullRequestHead(
        source.repository,
        repo_id,
        source.pr_number,
        head_sha,
        api_url,
        html_url,
        _sha256(_canonical_json(payload)),
        _HEAD_MARKER,
    )


def require_head(
    receipt: VerifiedLivePullRequestHead,
    repository: str,
    pr_number: int,
    head_sha: str,
) -> None:
    if receipt._marker is not _HEAD_MARKER:
        raise CompletionError("live PR-head receipt is not verifier-created")
    if (receipt.repository, receipt.pr_number, receipt.head_sha) != (
        repository,
        pr_number,
        head_sha,
    ):
        raise CompletionError("live GitHub PR head does not match expected review identity")
