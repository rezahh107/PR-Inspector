#!/usr/bin/env python3
"""Publish and verify the PRF-013 head-associated GitHub App check run."""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

CHECK_NAME = "PRF-013 External Coverage Trust"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class PublicationIdentity:
    repository: str
    repository_id: int
    pull_request_number: int
    base_sha: str
    head_sha: str
    issuer_workflow_sha: str
    run_id: str
    run_attempt: int
    attestation_digest: str
    expected_app_id: int


def _validate_identity(identity: PublicationIdentity) -> None:
    if identity.repository != "rezahh107/EV4-Decision-Kernel":
        raise ValueError("unexpected repository")
    if identity.repository_id != 1292378784:
        raise ValueError("unexpected repository id")
    if identity.pull_request_number < 1:
        raise ValueError("pull request number must be positive")
    if not SHA40.fullmatch(identity.base_sha) or not SHA40.fullmatch(identity.head_sha):
        raise ValueError("base/head must be immutable commit SHAs")
    if identity.base_sha == identity.head_sha:
        raise ValueError("head-associated check may not target the base SHA")
    if not SHA40.fullmatch(identity.issuer_workflow_sha):
        raise ValueError("issuer workflow SHA must be immutable")
    if not identity.run_id or identity.run_attempt < 1:
        raise ValueError("run identity is invalid")
    if not SHA256.fullmatch(identity.attestation_digest):
        raise ValueError("attestation digest must be lowercase SHA-256")
    if identity.expected_app_id < 1:
        raise ValueError("expected GitHub App id must be positive")


def build_external_id(identity: PublicationIdentity) -> str:
    _validate_identity(identity)
    return (
        f"ev4-prf013:{identity.repository_id}:{identity.pull_request_number}:"
        f"{identity.head_sha}:{identity.issuer_workflow_sha}:"
        f"{identity.run_id}:{identity.run_attempt}:{identity.attestation_digest}"
    )


def build_check_run_payload(identity: PublicationIdentity) -> dict[str, Any]:
    external_id = build_external_id(identity)
    summary = "\n".join([
        f"repository_id: `{identity.repository_id}`",
        f"pull_request: `{identity.pull_request_number}`",
        f"base_sha: `{identity.base_sha}`",
        f"verified_head_sha: `{identity.head_sha}`",
        f"issuer_workflow_sha: `{identity.issuer_workflow_sha}`",
        f"run: `{identity.run_id}/{identity.run_attempt}`",
        f"attestation_sha256: `{identity.attestation_digest}`",
        "proof_credit_authorized: `false`",
    ])
    return {
        "name": CHECK_NAME,
        "head_sha": identity.head_sha,
        "status": "completed",
        "conclusion": "success",
        "external_id": external_id,
        "output": {
            "title": "Externally verified exact-head Coverage trust",
            "summary": summary,
        },
    }


def validate_check_run_response(
    response: dict[str, Any], identity: PublicationIdentity
) -> None:
    _validate_identity(identity)
    expected_external_id = build_external_id(identity)
    app = response.get("app") or {}
    if response.get("name") != CHECK_NAME:
        raise ValueError("published check name mismatch")
    if response.get("head_sha") != identity.head_sha:
        raise ValueError("published check is not attached to verified PR head")
    if response.get("head_sha") == identity.base_sha:
        raise ValueError("published check is attached to base SHA")
    if response.get("external_id") != expected_external_id:
        raise ValueError("published check external identity mismatch")
    if response.get("status") != "completed" or response.get("conclusion") != "success":
        raise ValueError("published check is not a successful completed result")
    if int(app.get("id") or 0) != identity.expected_app_id:
        raise ValueError("published check source GitHub App mismatch")


def publish_check_run(
    *, api_url: str, token: str, identity: PublicationIdentity
) -> dict[str, Any]:
    if not token:
        raise ValueError("GitHub App installation token is missing")
    payload = build_check_run_payload(identity)
    request = urllib.request.Request(
        f"{api_url.rstrip('/')}/repos/{identity.repository}/check-runs",
        method="POST",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "ev4-prf013-coverage-trust-publisher",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            value = json.load(response)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"check-run publication failed: HTTP {exc.code}: {body}") from exc
    if not isinstance(value, dict):
        raise RuntimeError("check-run API response is not an object")
    validate_check_run_response(value, identity)
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default="https://api.github.com")
    parser.add_argument("--token", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--repository-id", type=int, required=True)
    parser.add_argument("--pull-request-number", type=int, required=True)
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--issuer-workflow-sha", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-attempt", type=int, required=True)
    parser.add_argument("--attestation-digest", required=True)
    parser.add_argument("--expected-app-id", type=int, required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    identity = PublicationIdentity(
        repository=args.repository,
        repository_id=args.repository_id,
        pull_request_number=args.pull_request_number,
        base_sha=args.base_sha,
        head_sha=args.head_sha,
        issuer_workflow_sha=args.issuer_workflow_sha,
        run_id=args.run_id,
        run_attempt=args.run_attempt,
        attestation_digest=args.attestation_digest,
        expected_app_id=args.expected_app_id,
    )
    try:
        response = publish_check_run(
            api_url=args.api_url,
            token=args.token,
            identity=identity,
        )
    except (ValueError, RuntimeError) as exc:
        print(f"COV_EXTERNAL_HEAD_CHECK_PUBLICATION_FAILED: {exc}", file=sys.stderr)
        return 1
    evidence = {
        "schema_version": 1,
        "check_name": response["name"],
        "check_run_id": response.get("id"),
        "head_sha": response["head_sha"],
        "source_app_id": int((response.get("app") or {}).get("id") or 0),
        "external_id": response["external_id"],
        "status": response["status"],
        "conclusion": response["conclusion"],
        "proof_credit_authorized": False,
    }
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(evidence, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps(evidence, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
