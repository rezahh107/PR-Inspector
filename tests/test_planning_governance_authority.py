from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

from pr_inspector.planning_governance import (
    BASELINE_PATH,
    IMPACT_PATH,
    NEXT_WORK_PATH,
    PLAN_PATH,
    REGISTRY_PATH,
    SCHEMAS,
    SCOPE_PATH,
    load_json_strict,
    validate_planning_repository,
    validate_registry,
)

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str | Path):
    return load_json_strict(ROOT / rel)


def codes(items):
    return {item.code for item in items}


def registry_schema():
    return read(SCHEMAS["registry"])


def copy_static_bundle(destination: Path) -> Path:
    for rel in [
        REGISTRY_PATH,
        SCOPE_PATH,
        IMPACT_PATH,
        NEXT_WORK_PATH,
        PLAN_PATH,
        BASELINE_PATH,
        *SCHEMAS.values(),
    ]:
        target = destination / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, target)
    scope = load_json_strict(destination / SCOPE_PATH)
    for rel in scope["committed_paths"]:
        target = destination / rel
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("\n", encoding="utf-8")
    return destination


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def add_work_package(
    registry: dict,
    *,
    package_id: str = "PINS-PLAN-001-WP02",
    status: str = "planned",
) -> dict:
    package = copy.deepcopy(registry["work_packages"][0])
    package.update(
        work_package_id=package_id,
        title="Second Work Package",
        status=status,
        depends_on=[],
        current=False,
        scope_ref=f"planning/scopes/{package_id}.scope.json",
        impact_refs=[f"planning/progress/impacts/{package_id}.impact.json"],
        evidence_refs=[],
    )
    registry["work_packages"].append(package)
    return package


def evidence_record(
    evidence_id: str,
    evidence_type: str,
    *,
    package: dict,
    head_sha: str = "1" * 40,
    merge_sha: str | None = None,
) -> dict:
    producer = {
        "exact_head_ci": "github_actions",
        "merge": "github_merge_api",
        "post_merge_verification": "post_merge_reconciler",
    }[evidence_type]
    source_ref = (
        "github:pull-request:34:merge"
        if evidence_type == "merge"
        else f"github-actions:run:123:job:{evidence_type}"
    )
    return {
        "evidence_id": evidence_id,
        "evidence_type": evidence_type,
        "repository": "rezahh107/PR-Inspector",
        "task_id": package["task_id"],
        "work_package_id": package["work_package_id"],
        "base_sha": "6be25811d185f001025b61839f94c736c721bbb7",
        "head_sha": head_sha,
        "merge_commit_sha": merge_sha,
        "scope_ref": package["scope_ref"],
        "impact_ref": package["impact_refs"][-1],
        "producer": producer,
        "source_ref": source_ref,
        "verified": True,
    }


def attach_complete_evidence(registry: dict, package: dict) -> None:
    merge_sha = "2" * 40
    records = [
        evidence_record("EVIDENCE-EXACT", "exact_head_ci", package=package),
        evidence_record("EVIDENCE-MERGE", "merge", package=package, merge_sha=merge_sha),
        evidence_record(
            "EVIDENCE-POST",
            "post_merge_verification",
            package=package,
            merge_sha=merge_sha,
        ),
    ]
    registry["evidence_records"].extend(records)
    package["evidence_refs"] = [record["evidence_id"] for record in records]


def test_invalid_utf8_baseline_returns_diagnostic_without_traceback(tmp_path):
    repo = copy_static_bundle(tmp_path / "repo")
    (repo / BASELINE_PATH).write_bytes(b"\xff\xfe\x80")
    diagnostics = validate_planning_repository(repo)
    assert codes(diagnostics) == {"PINS-MARKDOWN-INPUT-INVALID"}
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/validate_planning_governance.py"),
            "--root",
            str(repo),
            "--check-static",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 1
    assert "PINS-MARKDOWN-INPUT-INVALID" in result.stdout
    assert "Traceback" not in result.stdout + result.stderr


def test_task_completion_and_aigov_authorization_bypass_is_rejected(tmp_path):
    repo = copy_static_bundle(tmp_path / "repo")
    registry = load_json_strict(repo / REGISTRY_PATH)
    foundation, future = registry["tasks"]
    foundation.update(
        status="complete",
        completion_claimed=True,
        evidence_refs=["EVIDENCE-1"],
    )
    future.update(status="in_progress", implementation_authorized=True)
    write_json(repo / REGISTRY_PATH, registry)
    found = codes(validate_planning_repository(repo))
    assert {
        "PINS-TASK-COMPLETION-PREDICATE",
        "PINS-EVIDENCE-REFERENCE-INVALID",
        "PINS-UNAUTHORIZED-IMPLEMENTATION",
        "PINS-DEPENDENCY-NOT-COMPLETE",
    } <= found


def test_complete_task_requires_all_owned_work_packages_post_merge_verified():
    registry = read(REGISTRY_PATH)
    task = registry["tasks"][0]
    package = registry["work_packages"][0]
    task.update(status="complete", completion_claimed=True)
    attach_complete_evidence(registry, package)
    task["evidence_refs"] = ["EVIDENCE-POST"]
    assert "PINS-TASK-COMPLETION-PREDICATE" in codes(
        validate_registry(registry, registry_schema())
    )


def test_dependent_authorization_requires_authoritative_completion_predicate():
    registry = read(REGISTRY_PATH)
    foundation, future = registry["tasks"]
    foundation.update(status="complete", completion_claimed=True, evidence_refs=["FAKE"])
    future.update(status="authorized", implementation_authorized=True)
    found = codes(validate_registry(registry, registry_schema()))
    assert "PINS-DEPENDENCY-NOT-COMPLETE" in found
    assert "PINS-UNAUTHORIZED-IMPLEMENTATION" in found


def test_non_current_missing_scope_and_impact_refs_are_traversed(tmp_path):
    repo = copy_static_bundle(tmp_path / "repo")
    registry = load_json_strict(repo / REGISTRY_PATH)
    package = add_work_package(registry, status="post_merge_verified")
    attach_complete_evidence(registry, package)
    write_json(repo / REGISTRY_PATH, registry)
    diagnostics = validate_planning_repository(repo)
    assert "PINS-CROSS-FILE-BINDING-MISMATCH" in codes(diagnostics)
    assert any(item.path == f"/{package['scope_ref']}" for item in diagnostics)


def test_non_current_existing_scope_with_stale_identity_is_rejected(tmp_path):
    repo = copy_static_bundle(tmp_path / "repo")
    registry = load_json_strict(repo / REGISTRY_PATH)
    package = add_work_package(registry)
    write_json(repo / REGISTRY_PATH, registry)
    stale_scope = load_json_strict(repo / SCOPE_PATH)
    write_json(repo / package["scope_ref"], stale_scope)
    assert "PINS-CROSS-FILE-BINDING-MISMATCH" in codes(
        validate_planning_repository(repo)
    )


def test_fabricated_prefix_shaped_evidence_does_not_resolve():
    registry = read(REGISTRY_PATH)
    package = registry["work_packages"][0]
    package["evidence_refs"] = ["exact_head:run-1"]
    found = codes(validate_registry(registry, registry_schema()))
    assert "PINS-EVIDENCE-REFERENCE-INVALID" in found
    assert "PINS-WP-LIFECYCLE-INVALID" in found


def test_evidence_provenance_must_bind_registered_artifacts():
    registry = read(REGISTRY_PATH)
    package = registry["work_packages"][0]
    record = evidence_record("EVIDENCE-EXACT", "exact_head_ci", package=package)
    record["impact_ref"] = "planning/progress/impacts/STALE.json"
    registry["evidence_records"].append(record)
    package["evidence_refs"] = [record["evidence_id"]]
    assert "PINS-EVIDENCE-PROVENANCE-MISMATCH" in codes(
        validate_registry(registry, registry_schema())
    )


def test_evidence_schema_rejects_fabricated_producer_shape():
    registry = read(REGISTRY_PATH)
    package = registry["work_packages"][0]
    record = evidence_record("EVIDENCE-EXACT", "exact_head_ci", package=package)
    record["producer"] = "github_merge_api"
    record["source_ref"] = "arbitrary"
    registry["evidence_records"].append(record)
    assert codes(validate_registry(registry, registry_schema())) == {
        "PINS-REGISTRY-SCHEMA-INVALID"
    }


def test_post_merge_evidence_must_share_head_merge_and_latest_impact(tmp_path):
    repo = copy_static_bundle(tmp_path / "repo")
    registry = load_json_strict(repo / REGISTRY_PATH)
    package = registry["work_packages"][0]
    package["status"] = "post_merge_verified"
    attach_complete_evidence(registry, package)
    registry["evidence_records"][1]["head_sha"] = "3" * 40
    registry["evidence_records"][2]["merge_commit_sha"] = "4" * 40
    write_json(repo / REGISTRY_PATH, registry)
    impact = load_json_strict(repo / IMPACT_PATH)
    impact.update(
        state_after="post_merge_verified",
        completion_claimed=True,
        next_lifecycle_action="none",
        remaining_obligations=[],
    )
    write_json(repo / IMPACT_PATH, impact)
    assert "PINS-EVIDENCE-PROVENANCE-MISMATCH" in codes(
        validate_planning_repository(repo)
    )
