from __future__ import annotations

import copy
import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from pr_inspector.ci_identity import build_ci_identity
from pr_inspector.derived_outputs import write_review_artifacts
from pr_inspector.review_provenance import (
    event_evidence_fields,
    verify_github_commit_payload,
    verify_review_directory,
)
from pr_inspector.security_profile import (
    verify_profile_predicates,
    verify_sequence_enforcement,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session", autouse=True)
def verified_personal_profile_evidence():
    """Install verifier-created exact-target capabilities for the canonical Green fixture."""

    package = json.loads(
        (ROOT / "fixtures/golden-green/review-package.json").read_text(
            encoding="utf-8"
        )
    )
    package = copy.deepcopy(package)
    now = datetime.now(timezone.utc)
    package["review_identity"]["review_started"] = (
        now - timedelta(minutes=10)
    ).isoformat().replace("+00:00", "Z")
    package["review_identity"]["review_completed"] = (
        now - timedelta(minutes=5)
    ).isoformat().replace("+00:00", "Z")

    # The prior review is deliberately rendered before the sequence capability exists.
    # It therefore routes to verify and can be provenance-verified without circularly
    # assuming the capability that this fixture is about to mint.
    with tempfile.TemporaryDirectory(prefix="pr-inspector-profile-evidence-") as temp:
        directory = Path(temp)
        package_bytes = (
            json.dumps(
                package,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
        (directory / "review-package.json").write_bytes(package_bytes)
        write_review_artifacts(
            package,
            directory,
            review_package_bytes=package_bytes,
        )

        inspector_repository = package["review_identity"]["inspector_repository"]
        inspector_sha = package["review_identity"]["inspector_commit_sha"]
        repository_id = 1288323264
        repository_api = f"https://api.github.com/repos/{inspector_repository}"
        repository_html = f"https://github.com/{inspector_repository}"
        commit = verify_github_commit_payload(
            {
                "full_name": inspector_repository,
                "id": repository_id,
                "url": repository_api,
                "html_url": repository_html,
            },
            {
                "sha": inspector_sha,
                "url": f"{repository_api}/commits/{inspector_sha}",
                "html_url": f"{repository_html}/commit/{inspector_sha}",
            },
            expected_commit_sha=inspector_sha,
        )
        review_evidence = verify_review_directory(directory, commit)

    sequence = {
        "schema_version": 3,
        "events": [
            {
                "event_id": "fixture-implemented",
                "event_type": "implemented_pending_rereview",
                "target_repository": review_evidence.target_repository,
                "pr_number": review_evidence.pr_number,
                "resulting_head_sha": review_evidence.reviewed_head_sha,
            },
            {
                "event_id": "fixture-rereview",
                "event_type": "pr_inspector_rereview_completed",
                "target_repository": review_evidence.target_repository,
                "pr_number": review_evidence.pr_number,
                "resulting_head_sha": review_evidence.reviewed_head_sha,
                "reviewed_head_sha": review_evidence.reviewed_head_sha,
                "review_validity": "CURRENT",
                **event_evidence_fields(review_evidence),
            },
        ],
    }
    ci_identity = build_ci_identity(
        tested_ref_type="pull_request_head",
        tested_sha=review_evidence.reviewed_head_sha,
        tested_tree_sha="a" * 40,
        reviewed_head_sha=review_evidence.reviewed_head_sha,
        synthetic_merge=False,
        claim_exact_head=True,
        workflow_run_id=1,
        job_ids=["validate-3.10"],
    )
    carrier = package["security_profile"]
    predicates = verify_profile_predicates(
        reference=carrier["predicate_evidence_reference"],
        expected_repository=review_evidence.target_repository,
        expected_pr_number=review_evidence.pr_number,
        expected_head_sha=review_evidence.reviewed_head_sha,
        expected_protocol_version=review_evidence.protocol_version,
        selected_profile=carrier["selected_profile"],
        trusted_repository_policy="personal_minimum_security",
        authoritative_requirement_states={
            "external_requirement": "verified_absent",
            "legal_requirement": "verified_absent",
            "contractual_requirement": "verified_absent",
            "organizational_requirement": "verified_absent",
            "production_requirement": "verified_absent",
        },
        verified_at=now,
    )
    sequence_capability = verify_sequence_enforcement(
        reference=carrier["sequence_enforcement_reference"],
        sequence=sequence,
        verified_review_evidence={review_evidence.evidence_id: review_evidence},
        ci_identity=ci_identity,
        expected_repository=review_evidence.target_repository,
        expected_pr_number=review_evidence.pr_number,
        expected_head_sha=review_evidence.reviewed_head_sha,
        expected_protocol_version=review_evidence.protocol_version,
        expected_workflow_run_id=1,
        verified_at=now,
    )

    # Strong references keep the weakly registered capabilities alive for the session.
    yield predicates, sequence_capability, review_evidence
