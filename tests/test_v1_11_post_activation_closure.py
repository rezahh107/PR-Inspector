import hashlib
import json
from pathlib import Path

import pytest

from pr_inspector import candidate_v1_11, runtime_v1_11
from pr_inspector._official_bundle import _OFFICIAL, capture_artifact_bytes
from pr_inspector.decision_projection import project_decision
from pr_inspector.derived_outputs import (
    MANIFEST_NAME,
    PROFILE_COMMANDS_NAME,
    PROFILE_COMMANDS_TEXT,
    build_review_artifacts,
    write_review_artifacts,
)
from tests.governance_test_support import sequence_capability

ROOT = Path(__file__).resolve().parents[1]


def package(name: str = "golden-green") -> dict:
    return json.loads(
        (ROOT / "fixtures" / name / "review-package.json").read_text(
            encoding="utf-8"
        )
    )


def active_projection(value: dict) -> dict:
    return project_decision(value, sequence_enforcement=sequence_capability())


def test_candidate_import_path_is_only_a_runtime_compatibility_surface():
    assert candidate_v1_11.parse_intake is runtime_v1_11.parse_intake
    assert (
        candidate_v1_11._validate_annotation_metadata
        is runtime_v1_11._validate_annotation_metadata
    )


@pytest.mark.parametrize(
    "annotation",
    [
        {"id": True, "annotation_level": "warning"},
        {"id": 0, "annotation_level": "warning"},
        {"id": -1, "annotation_level": "warning"},
        {"id": "1", "annotation_level": "warning"},
        {"start_line": True, "annotation_level": "warning"},
        {"start_line": 0, "annotation_level": "warning"},
        {"start_line": -1, "annotation_level": "warning"},
        {"end_line": 0, "annotation_level": "warning"},
        {"end_line": -1, "annotation_level": "warning"},
    ],
)
def test_annotation_identity_and_lines_fail_closed(annotation):
    with pytest.raises(ValueError, match="check annotation"):
        runtime_v1_11._validate_annotation_metadata(annotation)


def test_valid_annotation_metadata_remains_accepted():
    runtime_v1_11._validate_annotation_metadata(
        {
            "id": 7,
            "path": "src/app.py",
            "start_line": 3,
            "end_line": 5,
            "annotation_level": "warning",
        }
    )


def test_caller_authored_false_red_cannot_override_canonical_green():
    value = package()
    value["technical_decision"] = {
        "status": "RED",
        "reason_codes": ["critical_supported_finding"],
    }
    value["governance_decision"] = {
        "status": "GAP_FOUND",
        "reason_codes": ["merge_authorization_unverified"],
    }
    value["overall_recommendation"] = {
        "technical_ready": False,
        "merge_governance_verified": True,
    }

    projection = active_projection(value)

    assert projection["technical_decision"] == {
        "status": "GREEN",
        "reason_codes": [],
    }
    assert projection["governance_decision"] == {
        "status": "NOT_REQUESTED",
        "reason_codes": [],
    }
    assert projection["overall_recommendation"] == {
        "technical_ready": True,
        "merge_governance_verified": False,
    }


def test_caller_authored_false_green_cannot_override_canonical_yellow():
    value = package("repair-handoff-valid")
    value["technical_decision"] = {"status": "GREEN", "reason_codes": []}
    value["overall_recommendation"] = {
        "technical_ready": True,
        "merge_governance_verified": True,
    }

    projection = active_projection(value)

    assert projection["technical_decision"]["status"] == "YELLOW"
    assert projection["overall_recommendation"]["technical_ready"] is False
    assert projection["overall_recommendation"]["merge_governance_verified"] is False


def test_strict_without_sealed_governance_does_not_rewrite_technical_status():
    value = package()
    value["inspection_profile"] = "strict"
    projection = active_projection(value)

    assert projection["technical_decision"]["status"] == "GREEN"
    assert projection["governance_decision"] == {
        "status": "NOT_VERIFIABLE",
        "reason_codes": ["repository_settings_not_verified"],
    }
    assert projection["overall_recommendation"] == {
        "technical_ready": True,
        "merge_governance_verified": False,
    }
    assert projection["governance_follow_up"]["may_modify_code"] is False
    assert projection["governance_follow_up"]["prompt_required"] is False


def test_profile_commands_are_generated_hashed_and_official():
    value = package()
    artifacts = build_review_artifacts(
        value,
        sequence_enforcement=sequence_capability(),
    )
    manifest = json.loads(artifacts[MANIFEST_NAME])

    assert artifacts[PROFILE_COMMANDS_NAME] == PROFILE_COMMANDS_TEXT
    assert manifest["owner_profile_commands"] == {
        "path": PROFILE_COMMANDS_NAME,
        "sha256": hashlib.sha256(PROFILE_COMMANDS_TEXT.encode("utf-8")).hexdigest(),
        "hash_scope": "final_file_bytes",
    }
    assert PROFILE_COMMANDS_NAME in _OFFICIAL


def test_profile_commands_survive_official_capture(tmp_path):
    value = package()
    package_bytes = (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    (tmp_path / "review-package.json").write_bytes(package_bytes)
    write_review_artifacts(
        value,
        tmp_path,
        review_package_bytes=package_bytes,
        sequence_enforcement=sequence_capability(),
    )

    files, directories = capture_artifact_bytes(tmp_path)

    assert not directories
    assert files[PROFILE_COMMANDS_NAME] == PROFILE_COMMANDS_TEXT.encode("utf-8")
