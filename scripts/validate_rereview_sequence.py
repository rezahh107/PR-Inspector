from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from pr_inspector.review_provenance import (
    ProvenanceError,
    trust_policy,
    verify_github_commit_payload,
    verify_review_directory,
)
from pr_inspector.sequence_policy import REREVIEW_COMPLETED, validate_rereview_sequence


def _github_json(url: str, token: str | None, api_version: str) -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": api_version,
        "User-Agent": "PR-Inspector-rereview-verifier",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProvenanceError(f"GitHub evidence request failed: {exc}") from exc
    if not isinstance(payload, dict):
        raise ProvenanceError("GitHub evidence response must be a JSON object")
    return payload


def _parse_review_mapping(values: list[str]) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise argparse.ArgumentTypeError(
                "--review must use EVENT_ID=REVIEW_DIRECTORY"
            )
        event_id, raw_path = value.split("=", 1)
        if not event_id or not raw_path:
            raise argparse.ArgumentTypeError(
                "--review must use EVENT_ID=REVIEW_DIRECTORY"
            )
        if event_id in out:
            raise argparse.ArgumentTypeError(f"duplicate review event id {event_id}")
        out[event_id] = Path(raw_path)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a re-review lifecycle sequence using immutable review artifacts "
            "and live GitHub repository/commit evidence."
        )
    )
    parser.add_argument("sequence", type=Path)
    parser.add_argument(
        "--review",
        action="append",
        default=[],
        metavar="EVENT_ID=REVIEW_DIRECTORY",
        help="Bind one re-review event to its artifact directory.",
    )
    parser.add_argument(
        "--github-token-env",
        default="GITHUB_TOKEN",
        help="Environment variable containing an optional GitHub token.",
    )
    args = parser.parse_args()

    try:
        sequence = json.loads(args.sequence.read_text(encoding="utf-8"))
        review_paths = _parse_review_mapping(args.review)
        policy = trust_policy()
        repository = policy["inspector_repository"]
        api_version = policy["github_api_version"]
        token = os.environ.get(args.github_token_env)

        repo_url = f"https://api.github.com/repos/{repository}"
        repository_payload = _github_json(repo_url, token, api_version)

        verified = {}
        for event in sequence.get("events", []):
            if event.get("event_type") != REREVIEW_COMPLETED:
                continue
            event_id = event["event_id"]
            directory = review_paths.get(event_id)
            if directory is None:
                continue
            commit_sha = event["inspector_commit_sha"]
            commit_url = (
                f"https://api.github.com/repos/{repository}/commits/{commit_sha}"
            )
            commit_payload = _github_json(commit_url, token, api_version)
            inspector_commit = verify_github_commit_payload(
                repository_payload,
                commit_payload,
                expected_commit_sha=commit_sha,
            )
            evidence = verify_review_directory(directory, inspector_commit)
            verified[evidence.evidence_id] = evidence

        diagnostics = validate_rereview_sequence(sequence, verified)
    except (OSError, json.JSONDecodeError, ProvenanceError, argparse.ArgumentTypeError) as exc:
        print(f"PRI-REREVIEW-PROVENANCE-001 /: {exc}")
        return 1

    if diagnostics:
        for item in diagnostics:
            print(item.line())
        return 1

    print("PR Inspector re-review sequence provenance: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
