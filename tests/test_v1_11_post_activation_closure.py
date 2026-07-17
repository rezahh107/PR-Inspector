from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from pr_inspector._governance_transport import (
    GovernanceEvidenceError,
    _mint_response,
    github_response_payload,
)
from pr_inspector._official_bundle import artifact_hashes
from pr_inspector._official_head import CompletionError
from pr_inspector.decision_projection import (
    ProjectionError,
    project_decision,
    validate_projection_invariants,
)
from pr_inspector.derived_outputs import (
    PROFILE_COMMANDS_NAME,
    PROFILE_COMMANDS_TEXT,
    PROJECTION_NAME,
    build_review_artifacts,
)
from pr_inspector.render import canonical_json_bytes

ROOT = Path(__file__).resolve().parents[1]


def _package() -> dict:
    return json.loads(
        (ROOT / "fixtures/golden-green/review-package.json").read_text(
            encoding="utf-8"
        )
    )


def _candidate_status(technical_status: str) -> str:
    return {
        "GREEN_TECHNICALLY_READY": "GREEN",
        "YELLOW_CHANGES_OR_VERIFICATION_REQUIRED": "YELLOW",
        "RED_DO_NOT_MERGE": "RED",
    }[technical_status]


def test_active_projection_derives_v1_11_decisions_from_canonical_evidence() -> None:
    package = _package()
    package["technical_decision"] = {"status": "GREEN", "reason_codes": []}
    package["governance_decision"] = {"status": "VERIFIED", "reason_codes": []}
    package["overall_recommendation"] = {
        "technical_ready": True,
        "merge_governance_verified": True,
    }

    projection = project_decision(package)

    assert projection["technical_decision"]["status"] == _candidate_status(
        projection["technical_status"]
    )
    assert projection["governance_decision"] == {
        "status": "NOT_REQUESTED",
        "reason_codes": [],
    }
    assert projection["overall_recommendation"] == {
        "technical_ready": projection["technical_status"]
        == "GREEN_TECHNICALLY_READY",
        "merge_governance_verified": False,
    }


def test_projection_invariants_reject_contradictory_technical_decision() -> None:
    projection = project_decision(_package())
    projection["technical_decision"]["status"] = (
        "GREEN"
        if projection["technical_decision"]["status"] != "GREEN"
        else "YELLOW"
    )

    with pytest.raises(
        ProjectionError,
        match="technical_decision contradicts canonical technical status",
    ):
        validate_projection_invariants(projection)


def test_projection_invariants_reject_unknown_governance_status() -> None:
    projection = project_decision(_package())
    projection["governance_decision"]["status"] = "UNKNOWN"

    with pytest.raises(
        ProjectionError,
        match="canonical governance status is invalid",
    ):
        validate_projection_invariants(projection)


def test_official_artifacts_always_include_hashed_profile_commands() -> None:
    package = _package()
    artifacts = build_review_artifacts(package)
    profile_bytes = artifacts[PROFILE_COMMANDS_NAME].encode("utf-8")
    manifest = json.loads(artifacts["artifact-manifest.json"])
    projection = json.loads(artifacts[PROJECTION_NAME])
    artifact_bytes = {
        name: text.encode("utf-8") for name, text in artifacts.items()
    }
    artifact_bytes["review-package.json"] = canonical_json_bytes(package)

    assert artifacts[PROFILE_COMMANDS_NAME] == PROFILE_COMMANDS_TEXT
    assert manifest["owner_profile_commands"] == {
        "path": PROFILE_COMMANDS_NAME,
        "sha256": hashlib.sha256(profile_bytes).hexdigest(),
        "hash_scope": "final_file_bytes",
    }
    assert PROFILE_COMMANDS_NAME in artifact_hashes(artifact_bytes, projection)

    without_profile = dict(artifact_bytes)
    without_profile.pop(PROFILE_COMMANDS_NAME)
    with pytest.raises(CompletionError, match="missing expected artifact"):
        artifact_hashes(without_profile, projection)


def _annotation_response(payload: object):
    url = "https://api.github.com/repos/o/r/check-runs/7/annotations?per_page=100"
    return _mint_response(
        request_url=url,
        response_url=url,
        status_code=200,
        fetched_at=datetime.now(timezone.utc),
        payload=payload,
        transport_origin="github_https",
    )


@pytest.mark.parametrize(
    "annotation",
    [
        {"id": True, "start_line": 1, "end_line": 1},
        {"id": 0, "start_line": 1, "end_line": 1},
        {"id": -1, "start_line": 1, "end_line": 1},
        {"start_line": True, "end_line": 1},
        {"start_line": 0, "end_line": 1},
        {"start_line": 1, "end_line": 0},
        {"start_line": 2, "end_line": 1},
    ],
)
def test_annotation_transport_rejects_invalid_identity_and_lines(
    annotation: dict,
) -> None:
    with pytest.raises(GovernanceEvidenceError, match="check annotation"):
        github_response_payload(_annotation_response([annotation]))


def test_annotation_transport_accepts_optional_id_and_positive_lines() -> None:
    annotation = {
        "path": "src/a.py",
        "start_line": 1,
        "end_line": 2,
        "annotation_level": "warning",
        "message": "untrusted content",
    }
    assert github_response_payload(_annotation_response([annotation])) == [annotation]
