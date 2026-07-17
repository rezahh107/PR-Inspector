from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from pr_inspector.governance import (
    GovernanceEvidenceError,
    SpecialistRequirement,
    fetch_github_api_response,
    github_response_payload,
    verify_github_governance_source,
    verify_governance_record,
)
from pr_inspector.review_provenance import (
    ProvenanceError,
    trust_policy,
    verify_github_commit_payload,
    verify_review_directory,
)
from pr_inspector.sequence_policy import REREVIEW_COMPLETED, validate_rereview_sequence


def _github_json(url: str, token: str | None, api_version: str):
    return fetch_github_api_response(
        url,
        token=token,
        api_version=api_version,
    )


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


def _parse_specialist_mapping(values: list[str]) -> dict[str, SpecialistRequirement]:
    out: dict[str, SpecialistRequirement] = {}
    for value in values:
        if "=" not in value:
            raise argparse.ArgumentTypeError(
                "--specialist-team must use EVENT_ID=ORGANIZATION/TEAM_SLUG"
            )
        event_id, team = value.split("=", 1)
        if not event_id or team.count("/") != 1:
            raise argparse.ArgumentTypeError(
                "--specialist-team must use EVENT_ID=ORGANIZATION/TEAM_SLUG"
            )
        organization, team_slug = team.split("/", 1)
        if event_id in out:
            raise argparse.ArgumentTypeError(
                f"duplicate specialist team event id {event_id}"
            )
        out[event_id] = SpecialistRequirement(organization, team_slug)
    return out


def _fetch_governance(
    event: dict[str, Any],
    *,
    token: str | None,
    api_version: str,
    specialist_requirement: SpecialistRequirement | None,
):
    repository = event["target_repository"]
    pr_number = event["pr_number"]
    head_sha = event["resulting_head_sha"]
    base_url = f"https://api.github.com/repos/{repository}"

    responses = {
        "repository": fetch_github_api_response(
            base_url, token=token, api_version=api_version
        ),
        "pull_request": fetch_github_api_response(
            f"{base_url}/pulls/{pr_number}",
            token=token,
            api_version=api_version,
        ),
    }
    repository_payload = github_response_payload(responses["repository"])
    if not isinstance(repository_payload, dict):
        raise GovernanceEvidenceError(
            "insufficient_evidence: repository endpoint is not an object"
        )
    default_branch = repository_payload.get("default_branch")
    if not isinstance(default_branch, str) or not default_branch:
        raise GovernanceEvidenceError(
            "insufficient_evidence: repository default branch is missing"
        )

    protection_url = (
        f"{base_url}/branches/{urllib.parse.quote(default_branch, safe='')}/protection"
    )
    rulesets_url = f"{base_url}/rulesets?includes_parents=true&per_page=100"
    reviews_url = f"{base_url}/pulls/{pr_number}/reviews?per_page=100"
    checks_url = f"{base_url}/commits/{head_sha}/check-runs?per_page=100"
    responses.update(
        {
            "branch_protection": fetch_github_api_response(
                protection_url, token=token, api_version=api_version
            ),
            "rulesets": fetch_github_api_response(
                rulesets_url, token=token, api_version=api_version
            ),
            "reviews": fetch_github_api_response(
                reviews_url, token=token, api_version=api_version
            ),
            "checks": fetch_github_api_response(
                checks_url, token=token, api_version=api_version
            ),
        }
    )

    rulesets_payload = github_response_payload(responses["rulesets"])
    if responses["rulesets"].status_code == 200 and isinstance(rulesets_payload, list):
        for summary in rulesets_payload:
            if (
                isinstance(summary, dict)
                and summary.get("enforcement") == "active"
                and isinstance(summary.get("id"), int)
            ):
                ruleset_id = summary["id"]
                responses[f"ruleset:{ruleset_id}"] = fetch_github_api_response(
                    f"{base_url}/rulesets/{ruleset_id}",
                    token=token,
                    api_version=api_version,
                )

    if specialist_requirement is not None:
        reviews_payload = github_response_payload(responses["reviews"])
        if responses["reviews"].status_code == 200 and isinstance(reviews_payload, list):
            reviewers = {
                item["user"]["login"]
                for item in reviews_payload
                if isinstance(item, dict)
                and item.get("state") == "APPROVED"
                and item.get("commit_id") == head_sha
                and isinstance(item.get("user"), dict)
                and isinstance(item["user"].get("login"), str)
            }
            for reviewer in sorted(reviewers):
                url = (
                    "https://api.github.com/orgs/"
                    f"{urllib.parse.quote(specialist_requirement.organization, safe='')}"
                    "/teams/"
                    f"{urllib.parse.quote(specialist_requirement.team_slug, safe='')}"
                    "/memberships/"
                    f"{urllib.parse.quote(reviewer, safe='')}"
                )
                responses[f"specialist:{reviewer}"] = fetch_github_api_response(
                    url, token=token, api_version=api_version
                )

    source = verify_github_governance_source(
        responses,
        expected_repository=repository,
        expected_pr_number=pr_number,
        expected_head_sha=head_sha,
        specialist_requirement=specialist_requirement,
    )
    return verify_governance_record(
        source,
        expected_repository=repository,
        expected_pr_number=pr_number,
        expected_head_sha=head_sha,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a re-review lifecycle sequence using immutable review artifacts, "
            "live GitHub repository/commit evidence, and payload-derived governance evidence."
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
        "--specialist-team",
        action="append",
        default=[],
        metavar="EVENT_ID=ORGANIZATION/TEAM_SLUG",
        help=(
            "Require authoritative active GitHub team membership for a specialist "
            "reviewer on one merge_authorized event."
        ),
    )
    parser.add_argument(
        "--github-token-env",
        default="GITHUB_TOKEN",
        help="Environment variable containing an optional GitHub token.",
    )
    args = parser.parse_args()

    try:
        sequence = json.loads(args.sequence.read_text(encoding="utf-8"))
        sequence_for_validation = copy.deepcopy(sequence)
        review_paths = _parse_review_mapping(args.review)
        specialist_by_event = _parse_specialist_mapping(args.specialist_team)
        policy = trust_policy()
        inspector_repository = policy["inspector_repository"]
        api_version = policy["github_api_version"]
        token = os.environ.get(args.github_token_env)

        repo_url = f"https://api.github.com/repos/{inspector_repository}"
        repository_payload = _github_json(repo_url, token, api_version)

        verified_reviews = {}
        for event in sequence_for_validation.get("events", []):
            if event.get("event_type") != REREVIEW_COMPLETED:
                continue
            event_id = event["event_id"]
            directory = review_paths.get(event_id)
            if directory is None:
                continue
            commit_sha = event["inspector_commit_sha"]
            commit_url = (
                f"https://api.github.com/repos/{inspector_repository}/commits/{commit_sha}"
            )
            commit_payload = _github_json(commit_url, token, api_version)
            inspector_commit = verify_github_commit_payload(
                repository_payload,
                commit_payload,
                expected_commit_sha=commit_sha,
            )
            evidence = verify_review_directory(directory, inspector_commit)
            verified_reviews[evidence.evidence_id] = evidence

        verified_governance = {}
        for event in sequence_for_validation.get("events", []):
            if event.get("event_type") != "merge_authorized":
                continue
            event_id = event["event_id"]
            evidence = _fetch_governance(
                event,
                token=token,
                api_version=api_version,
                specialist_requirement=specialist_by_event.get(event_id),
            )
            declared_id = event.get("governance_evidence_id")
            if declared_id is not None and declared_id != evidence.evidence_id:
                raise GovernanceEvidenceError(
                    "insufficient_evidence: declared governance_evidence_id does not "
                    "match freshly fetched payload-derived evidence"
                )
            event["governance_evidence_id"] = evidence.evidence_id
            verified_governance[evidence.evidence_id] = evidence

        diagnostics = validate_rereview_sequence(
            sequence_for_validation,
            verified_reviews,
            verified_governance,
        )
    except GovernanceEvidenceError as exc:
        print(f"PRI-GOV-CLI-001 /: {exc}")
        return 1
    except (OSError, json.JSONDecodeError, ProvenanceError, argparse.ArgumentTypeError) as exc:
        print(f"PRI-REREVIEW-PROVENANCE-001 /: {exc}")
        return 1

    if diagnostics:
        for item in diagnostics:
            print(item.line())
        return 1
    print("PR Inspector re-review sequence provenance and governance: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
