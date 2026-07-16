import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from pr_inspector.governance import VerifiedGovernanceEvidence
from pr_inspector.governance import _EVIDENCE_CAPABILITIES
from pr_inspector.candidate_v1_11 import (
    GOVERNANCE_REASON_CODES, LOCKED_INSPECTOR_REPOSITORY_ID, OWNER_PROFILE_COMMANDS_ARTIFACT,
    PROFILE_COMMANDS_BYTES, PROTOCOL_VERSION, TECHNICAL_REASON_CODES, bytes_sha256, canonical_sha256,
    classify_governance, collect_candidate_technical_reasons, parse_intake, project_decision,
    reconcile_bot_reviews, render_owner_profile_commands, validate_candidate_package,
    validate_owner_profile_commands, build_candidate_owner_delivery_artifacts, candidate_owner_delivery_stdout, verify_base_review_reference, verify_candidate_inspector_commit_payload,
    verify_governance_payload_bundle, verify_minimal_review_artifact_bytes,
)

ROOT = Path(__file__).resolve().parents[1]
SHA = "a" * 40
OTHER_SHA = "c" * 40
INSPECTOR_SHA = "d" * 40
NOW = datetime(2026, 7, 16, tzinfo=timezone.utc)
HASH = "b" * 64


def full_governance(**overrides):
    value = {"branch_protection_verified": True, "rulesets_verified": True, "required_status_checks_verified": True, "required_check_app_identities_verified": True, "approvals_verified": True, "pr_author_reviewer_independent": True, "bypass_actors_verified": True, "merge_queue_verified": True, "rereview_sequence_verified": True}
    value.update(overrides)
    return value


def inspector_commit(**overrides):
    repo = {"full_name": "rezahh107/PR-Inspector", "id": LOCKED_INSPECTOR_REPOSITORY_ID, "url": "https://api.github.com/repos/rezahh107/PR-Inspector", "html_url": "https://github.com/rezahh107/PR-Inspector"}
    commit = {"sha": INSPECTOR_SHA, "url": f"https://api.github.com/repos/rezahh107/PR-Inspector/commits/{INSPECTOR_SHA}", "html_url": f"https://github.com/rezahh107/PR-Inspector/commit/{INSPECTOR_SHA}"}
    repo.update(overrides.pop("repo", {})); commit.update(overrides.pop("commit", {}))
    return verify_candidate_inspector_commit_payload(repo, commit, INSPECTOR_SHA)


def governance_payload(**overrides):
    payload = {"source": "github_rest_api_https", "target_repository": "o/r", "target_repository_id": 100, "pull_request": 7, "reviewed_head_sha": SHA, "observed_at": NOW.isoformat(), "facts": full_governance(), "required_checks": {"ci": 15368}, "check_runs": [{"name": "ci", "app_id": 15368, "head_sha": SHA, "conclusion": "success"}]}
    payload.update(overrides)
    return payload


def verified_governance(**overrides):
    evidence = object.__new__(VerifiedGovernanceEvidence)
    values = {
        "evidence_id": "ev", "repository": overrides.get("repository", "o/r"), "default_branch": "main",
        "pull_request_number": overrides.get("pull_request", 7), "exact_head_sha": overrides.get("head", SHA),
        "enforcement_status": "verified_enforced", "valid_approval_reviewers": ("reviewer",),
        "required_status_checks": (("ci", 15368),), "exact_head_checks_satisfied": True,
        "approval_complete": True, "specialist_satisfied": True, "specialist_status": "not_required",
        "bypass_actors": (), "merge_readiness_satisfied": True, "merge_authorized": overrides.get("merge_authorized", True),
        "conclusion": "repository-level merge governance is verified and current-head readiness is satisfied",
        "source_response_urls": ("https://api.github.com/repos/o/r",),
    }
    for key, value in values.items():
        object.__setattr__(evidence, key, value)
    _EVIDENCE_CAPABILITIES.add(evidence)
    return evidence


def projection_validator():
    return Draft202012Validator(json.loads((ROOT / "protocols/v1.11.0/schemas/decision-projection.schema.json").read_text()))


def package_schema():
    return json.loads((ROOT / "protocols/v1.11.0/schemas/review-package.schema.json").read_text())


def complete_reconciliation(**overrides):
    rec = {"collection_status": "COMPLETE", "open_bot_sources_total": 0, "inspected_total": 0, "counts": {"accepted": 0, "resolved": 0, "stale": 0, "false_positive": 0, "duplicate": 0, "insufficient_evidence": 0, "deferred": 0, "out_of_scope": 0}, "uninspected_source_ids": [], "valid_blocking_finding_ids": [], "suggestion_results": []}
    rec.update(overrides)
    return rec


def package_for_decision(projection=None, reconciliation=None, profile="minimal", legacy_status="GREEN_TECHNICALLY_READY", **overrides):
    reconciliation = reconciliation or complete_reconciliation()
    projection = projection or project_decision(profile, [])
    package = json.loads((ROOT / "fixtures/golden-green/review-package.json").read_text())
    package["protocol_version"] = PROTOCOL_VERSION
    package["review_identity"]["target_repository"] = "o/r"
    package["review_identity"]["pr_number"] = 7
    package["review_identity"]["reviewed_head_sha"] = SHA
    package["review_identity"]["inspector_commit_sha"] = INSPECTOR_SHA
    for ev in package.get("evidence_records", []): ev["reviewed_head_sha"] = SHA
    package["external_review_intake"] = {"sources_inspected": [], "suggestions": []}
    package["decision"]["technical_status"] = legacy_status
    package["inspection_profile"] = profile
    package["technical_decision"] = projection["technical_decision"]
    package["governance_decision"] = projection["governance_decision"]
    package["overall_recommendation"] = projection["overall_recommendation"]
    package["external_review_reconciliation"] = reconciliation
    package.update(overrides)
    return package


def artifact_bytes_for(package=None, projection=None, mutate=None):
    package = package or package_for_decision()
    projection = projection or project_decision("minimal")
    bytes_map = {"review-package.json": json.dumps(package, sort_keys=True).encode()+b"\n", "DECISION_PROJECTION.json": json.dumps(projection, sort_keys=True).encode()+b"\n", "OWNER_DECISION_CARD.fa.md": b"owner\n", "TECHNICAL_HANDOFF.en.md": b"handoff\n", "OWNER_RESULT.fa.txt": "🟢 وضعیت: از نظر فنی آماده\nآمادگی فنی تأیید شده؛ حفاظت ادغام در GitHub جداگانه بررسی شود.\n".encode(), OWNER_PROFILE_COMMANDS_ARTIFACT: PROFILE_COMMANDS_BYTES}
    manifest = {"schema_version": 2, "artifacts": [{"path": name, "sha256": bytes_sha256(raw)} for name, raw in sorted(bytes_map.items())]}
    bytes_map["artifact-manifest.json"] = json.dumps(manifest, sort_keys=True).encode()+b"\n"
    if mutate:
        mutate(bytes_map)
    return bytes_map


def verified_minimal_bundle(**kwargs):
    return verify_minimal_review_artifact_bytes(artifact_bytes_for(**kwargs), inspector_commit())


def test_intake_profiles_and_strict_reuse_requires_verified_bundle():
    assert parse_intake("https://github.com/o/r/pull/7")["inspection_profile"] == "minimal"
    assert parse_intake("حداقلی\nhttps://github.com/o/r/pull/7")["inspection_profile"] == "minimal"
    assert parse_intake("سخت گیرانه\nhttps://github.com/o/r/pull/7")["inspection_profile"] == "strict"
    for marker in [True, {"ok": True}, {"schema_version": 1}]:
        assert parse_intake("سخت گیرانه", {"current_target": {"repository": "o/r", "pull_request": 7}, "live_head_sha": SHA, "verified_minimal_review": marker})["reuse_current_minimal"] is False
    bundle = verified_minimal_bundle()
    assert parse_intake("سخت گیرانه", {"current_target": {"repository": "o/r", "pull_request": 7}, "live_head_sha": SHA, "verified_minimal_review": bundle})["reuse_current_minimal"] is True
    assert parse_intake("سخت گیرانه", {"current_target": {"repository": "o/r", "pull_request": 7}, "live_head_sha": OTHER_SHA, "verified_minimal_review": bundle})["reuse_current_minimal"] is False


def test_governance_capability_requires_authoritative_payload_freshness_identity_and_exact_app():
    assert project_decision("strict", [], {"source": "github_rest_api_https", "facts": full_governance()})["governance_decision"]["status"] == "NOT_VERIFIABLE"
    cap = verified_governance()
    assert project_decision("strict", [], cap, target_repository="o/r", target_repository_id=100, pull_request=7, reviewed_head_sha=SHA)["governance_decision"]["status"] == "VERIFIED"
    assert project_decision("strict", [], cap, target_repository="x/y", target_repository_id=100, pull_request=7, reviewed_head_sha=SHA)["governance_decision"]["status"] == "NOT_VERIFIABLE"
    with pytest.raises(ValueError, match="sealed active GitHub governance evidence"):
        verify_governance_payload_bundle(governance_payload(source="fresh_github_api_verifier"), target_repository="o/r", target_repository_id=100, pull_request=7, reviewed_head_sha=SHA, now=NOW)
    with pytest.raises(ValueError, match="sealed active GitHub governance evidence"):
        verify_governance_payload_bundle(governance_payload(observed_at=(NOW - timedelta(hours=1)).isoformat()), target_repository="o/r", target_repository_id=100, pull_request=7, reviewed_head_sha=SHA, now=NOW)
    with pytest.raises(ValueError, match="sealed active GitHub governance evidence"):
        verify_governance_payload_bundle(governance_payload(observed_at=(NOW + timedelta(seconds=1)).isoformat()), target_repository="o/r", target_repository_id=100, pull_request=7, reviewed_head_sha=SHA, now=NOW)
    with pytest.raises(ValueError, match="sealed active GitHub governance evidence"):
        verify_governance_payload_bundle(governance_payload(target_repository="x/y"), target_repository="o/r", target_repository_id=100, pull_request=7, reviewed_head_sha=SHA, now=NOW)
    with pytest.raises(ValueError, match="sealed active GitHub governance evidence"):
        verify_governance_payload_bundle(governance_payload(check_runs=[{"name": "ci", "app_id": 999, "head_sha": SHA, "conclusion": "success"}]), target_repository="o/r", target_repository_id=100, pull_request=7, reviewed_head_sha=SHA, now=NOW)
    mutable = {"facts": full_governance(), "required_checks": {"ci": 15368}, "check_runs": [{"name": "ci", "app_id": 15368, "head_sha": SHA, "conclusion": "success"}]}
    cap = verified_governance(**mutable)
    mutable["facts"]["branch_protection_verified"] = False
    assert classify_governance(cap, target_repository="o/r", target_repository_id=100, pull_request=7, reviewed_head_sha=SHA)["status"] == "VERIFIED"


def test_reason_codes_and_status_effects_are_fail_closed():
    for bad in ["branch_protection_unavailable", "unknown", ""]:
        with pytest.raises(ValueError): project_decision("minimal", [bad])
    with pytest.raises(ValueError): project_decision("minimal", ["required_technical_check_failed", "required_technical_check_failed"])
    assert project_decision("minimal", ["required_technical_check_failed"])["technical_decision"]["status"] == "RED"
    for reason in TECHNICAL_REASON_CODES:
        assert project_decision("minimal", [reason])["technical_decision"]["status"] in {"RED", "YELLOW"}
    for reason in GOVERNANCE_REASON_CODES:
        assert reason in GOVERNANCE_REASON_CODES


def test_reconciliation_uppercase_severities_duplicates_and_immutability():
    sources = [{"source_id": "bot-review-1", "inspected": True}]
    for finding, expected in [({"finding_id": "F1", "severity": "CRITICAL", "blocking": True}, ["F1"]), ({"finding_id": "F1", "severity": "HIGH", "blocking": False}, ["F1"]), ({"finding_id": "F1", "severity": "MEDIUM", "blocking": True}, ["F1"]), ({"finding_id": "F1", "severity": "LOW", "blocking": False}, [])]:
        rec = reconcile_bot_reviews(sources, [{"suggestion_id": "S1", "source_id": "bot-review-1", "triage_decision": "accepted", "linked_finding_ids": ["F1"]}], [finding])
        assert rec["valid_blocking_finding_ids"] == expected
    with pytest.raises(ValueError, match="duplicate id bot-review-1"):
        reconcile_bot_reviews([sources[0], sources[0]], [], [])
    with pytest.raises(ValueError, match="duplicate id F1"):
        reconcile_bot_reviews(sources, [], [{"finding_id": "F1"}, {"finding_id": "F1"}])
    with pytest.raises(ValueError, match="duplicate id S1"):
        reconcile_bot_reviews(sources, [{"suggestion_id": "S1", "source_id": "bot-review-1", "triage_decision": "stale"}, {"suggestion_id": "S1", "source_id": "bot-review-1", "triage_decision": "resolved"}], [])
    item = {"source_id": "bot-review-1", "triage_decision": "accepted", "linked_finding_ids": []}
    original = copy.deepcopy(item); rec = reconcile_bot_reviews(sources, [item], [])
    assert item == original and rec["suggestion_results"][0]["repair_authorized"] is False


def test_candidate_package_semantics_collect_structured_technical_evidence_and_recompute_reconciliation():
    assert validate_candidate_package(package_for_decision()) == []
    for mutation in [
        lambda p: p["checks"].append({"check_id": "C", "name": "ci", "required": True, "result": "FAIL"}),
        lambda p: p["findings"].append({"finding_id": "F", "severity": "CRITICAL", "evidence_label": "CODE_SUPPORTED", "blocking": True}),
        lambda p: p["findings"].append({"finding_id": "F", "severity": "HIGH", "evidence_label": "REPRODUCED", "blocking": True}),
        lambda p: p["findings"].append({"finding_id": "F", "severity": "MEDIUM", "evidence_label": "CODE_SUPPORTED", "blocking": True}),
        lambda p: p["review_identity"].update({"review_validity": "STALE"}),
        lambda p: p["review_identity"].update({"review_mode": "PARTIAL"}),
        lambda p: p["scope"].update({"coverage_complete": False}),
        lambda p: p.update({"intent_fit": {"intent_fit_result": "unsatisfied", "unsupported_claims": ["claim"]}}),
        lambda p: p["required_actions"].append("do thing"),
    ]:
        pkg = package_for_decision(); mutation(pkg)
        assert validate_candidate_package(pkg), mutation
    pkg = package_for_decision()
    pkg["external_review_intake"] = {"sources_inspected": [{"source_id": "bot", "inspected": False}], "suggestions": [{"suggestion_id": "S", "source_id": "bot", "triage_decision": "accepted", "linked_finding_ids": ["F"]}]}
    pkg["findings"] = [{"finding_id": "F", "severity": "HIGH", "evidence_label": "REPRODUCED", "blocking": True}]
    pkg["external_review_reconciliation"] = complete_reconciliation()
    assert validate_candidate_package(pkg)


def test_minimal_review_reuse_verifies_bytes_not_caller_mappings_and_rejects_mutations():
    bundle = verified_minimal_bundle()
    assert verify_base_review_reference(bundle, SHA)["status"] == "VERIFIED"
    assert verify_base_review_reference({"manual": True}, SHA)["reason"] == "verified_minimal_review_required"
    with pytest.raises(ValueError, match="inspector"):
        verify_minimal_review_artifact_bytes(artifact_bytes_for(), object())
    strict_projection = project_decision("strict", [], verified_governance(), target_repository="o/r", target_repository_id=100, pull_request=7, reviewed_head_sha=SHA)
    strict_pkg = package_for_decision(strict_projection, profile="strict")
    with pytest.raises(ValueError, match="minimal"):
        verify_minimal_review_artifact_bytes(artifact_bytes_for(strict_pkg, strict_projection), inspector_commit())
    for mut, err in [
        (lambda b: b.update({"review-package.json": b"{}\n"}), "minimal|semantically invalid|protocol"),
        (lambda b: b.update({"DECISION_PROJECTION.json": b"{}\n"}), "minimal|schema|required"),
        (lambda b: b.update({"artifact-manifest.json": json.dumps({"artifacts": []}).encode()+b"\n"}), "manifest mismatch|incomplete|schema_version"),
        (lambda b: b.update({"OWNER_PROFILE_COMMANDS.fa.txt": PROFILE_COMMANDS_BYTES.replace(b"\n", b"\r\n")}), "profile commands|BOM|CRLF"),
        (lambda b: b.pop("TECHNICAL_HANDOFF.en.md"), "incomplete|unexpected"),
    ]:
        with pytest.raises(ValueError, match=err):
            verify_minimal_review_artifact_bytes(artifact_bytes_for(mutate=mut), inspector_commit())
    assert verify_base_review_reference(bundle, OTHER_SHA)["status"] == "STALE"


def test_profile_commands_artifact_exact_bytes_and_validation():
    assert render_owner_profile_commands("minimal") == PROFILE_COMMANDS_BYTES
    assert render_owner_profile_commands("strict") == PROFILE_COMMANDS_BYTES
    assert validate_owner_profile_commands(PROFILE_COMMANDS_BYTES) == []
    for raw in [PROFILE_COMMANDS_BYTES.replace(b"\n", b"\r\n"), b"\xef\xbb\xbf" + PROFILE_COMMANDS_BYTES, PROFILE_COMMANDS_BYTES.rstrip(b"\n"), PROFILE_COMMANDS_BYTES + b"extra\n"]:
        assert validate_owner_profile_commands(raw)
    contract = json.loads((ROOT / "protocols/v1.11.0/policies/OWNER_DELIVERY_CONTRACT.json").read_text())
    assert contract["profile_commands_name"] == OWNER_PROFILE_COMMANDS_ARTIFACT
    Draft202012Validator(json.loads((ROOT / "protocols/v1.11.0/schemas/owner-delivery-contract.schema.json").read_text())).validate(contract)
    artifacts = build_candidate_owner_delivery_artifacts("🟢 وضعیت: از نظر فنی آماده\nآمادگی فنی تأیید شده؛ حفاظت ادغام در GitHub جداگانه بررسی شود.\n".encode())
    assert candidate_owner_delivery_stdout(artifacts).endswith(PROFILE_COMMANDS_BYTES)
    tampered = dict(artifacts); tampered[OWNER_PROFILE_COMMANDS_ARTIFACT] = PROFILE_COMMANDS_BYTES + b"x"
    assert candidate_owner_delivery_stdout(tampered) == b""


def test_projection_schema_registry_and_determinism():
    validator = projection_validator()
    for projection in [project_decision("minimal"), project_decision("strict", [], verified_governance(), target_repository="o/r", target_repository_id=100, pull_request=7, reviewed_head_sha=SHA), project_decision("strict", [], None)]:
        validator.validate(projection)
    invalid = project_decision("minimal"); invalid["technical_decision"]["reason_codes"] = ["unknown"]
    assert list(validator.iter_errors(invalid))
    assert canonical_sha256(project_decision("strict", [], verified_governance(), target_repository="o/r", target_repository_id=100, pull_request=7, reviewed_head_sha=SHA)) == canonical_sha256(project_decision("strict", [], verified_governance(), target_repository="o/r", target_repository_id=100, pull_request=7, reviewed_head_sha=SHA))
    registry = yaml.safe_load((ROOT / "protocols/v1.11.0/registries/DECISION_REASON_REGISTRY.yaml").read_text())
    entries = {entry["reason_code"]: entry for entry in registry["candidate_reason_domains"]}
    assert set(entries) == TECHNICAL_REASON_CODES | GOVERNANCE_REASON_CODES
