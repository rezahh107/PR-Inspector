from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import MappingProxyType

import pytest

from pr_inspector import candidate_v1_11 as candidate
from pr_inspector import candidate_v1_11_base as base

ROOT = Path(__file__).resolve().parents[1]

BASE_SPEC = importlib.util.spec_from_file_location(
    "candidate_v1_11_existing_tests_for_hardening",
    ROOT / "tests/test_candidate_v1_11.py",
)
base_helpers = importlib.util.module_from_spec(BASE_SPEC)
assert BASE_SPEC.loader is not None
BASE_SPEC.loader.exec_module(base_helpers)

REPAIR_SPEC = importlib.util.spec_from_file_location(
    "candidate_v1_11_repair_tests_for_hardening",
    ROOT / "tests/test_candidate_v1_11_repairs.py",
)
repair_helpers = importlib.util.module_from_spec(REPAIR_SPEC)
assert REPAIR_SPEC.loader is not None
REPAIR_SPEC.loader.exec_module(repair_helpers)


def test_non_mapping_context_fails_closed_without_attribute_error():
    result = candidate.parse_intake("سخت گیرانه", ["untrusted-context"])
    assert result["inspection_profile"] == "strict"
    assert result["target"] is None
    assert result["missing"] == ["pull_request_url"]


def test_malformed_review_identity_is_rejected_deterministically():
    bundle = base_helpers.artifact_bundle()
    artifacts = dict(bundle.artifact_bytes)
    package = json.loads(artifacts["review-package.json"])
    package["review_identity"] = []
    artifacts["review-package.json"] = candidate.canonical_json_bytes(package)
    malformed = base.VerifiedCandidateReviewBundle(
        base._REVIEW_TOKEN,
        bundle.reference,
        MappingProxyType(artifacts),
        bundle.package_file_sha256,
        bundle.inspector_commit,
    )
    result = candidate.verify_base_review_reference(
        malformed,
        base_helpers.SHA,
        target_repository=base_helpers.REPO,
        target_repository_id=base_helpers.REPO_ID,
        pull_request=7,
    )
    assert result == {"status": "INVALID", "reason": "review_identity_malformed"}


def test_malformed_pull_request_head_fails_closed_with_value_error():
    url = f"https://api.github.com/repos/{base_helpers.REPO}/pulls/7"
    response = base_helpers.response(url, {"number": 7, "head": "not-an-object"})
    with pytest.raises(ValueError, match="head is missing or invalid"):
        candidate.verify_pull_request_head_response(
            response,
            target_identity=base_helpers.target_identity(),
            pull_request=7,
        )


def test_invalid_annotation_metadata_is_rejected():
    malformed = repair_helpers.annotation(path=["src/a.py"], start_line="3", end_line=2)
    responses = repair_helpers.surface_responses(
        runs=[repair_helpers.check_run(1)],
        annotations={1: [malformed]},
    )
    with pytest.raises(ValueError, match="check-annotation path is invalid"):
        candidate.verify_review_surface_inventory_responses(
            responses,
            target_repository=base_helpers.REPO,
            target_identity=base_helpers.target_identity(),
            pull_request=7,
            reviewed_head_sha=base_helpers.SHA,
        )


def test_nullable_annotation_location_remains_supported():
    nullable = repair_helpers.annotation(path=None, start_line=None, end_line=None)
    inventory = candidate.verify_review_surface_inventory_responses(
        repair_helpers.surface_responses(
            runs=[repair_helpers.check_run(1)],
            annotations={1: [nullable]},
        ),
        target_repository=base_helpers.REPO,
        target_identity=base_helpers.target_identity(),
        pull_request=7,
        reviewed_head_sha=base_helpers.SHA,
    )
    identity = json.loads(inventory.sources[0]["github_object_id"])
    assert identity["annotation_path"] is None
    assert identity["annotation_start_line"] is None
    assert identity["annotation_end_line"] is None
