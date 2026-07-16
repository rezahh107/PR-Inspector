import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from pr_inspector._governance_transport import _mint_response
from pr_inspector.governance import VerifiedGovernanceEvidence, _EVIDENCE_CAPABILITIES
from pr_inspector.review_provenance import VerifiedInspectorCommit, verify_github_commit_payload
from pr_inspector.candidate_v1_11 import (
    GOVERNANCE_REASON_CODES, GOVERNANCE_STATUS_EFFECT, LOCKED_INSPECTOR_REPOSITORY_ID,
    OWNER_PROFILE_COMMANDS_ARTIFACT, PROFILE_COMMANDS_BYTES, PROTOCOL_VERSION,
    TECHNICAL_REASON_CODES, build_candidate_owner_delivery_artifacts,
    build_candidate_review_artifacts, bytes_sha256, candidate_owner_delivery_stdout,
    canonical_sha256, classify_governance, collect_candidate_technical_reasons,
    parse_intake, project_decision, reconcile_bot_reviews, render_owner_profile_commands,
    validate_candidate_package, validate_owner_profile_commands,
    verify_base_review_reference, verify_candidate_inspector_commit_payload,
    verify_governance_payload_bundle, verify_minimal_review_artifact_bytes,
    verify_review_surface_inventory_responses, verify_target_identity_response,
)

ROOT = Path(__file__).resolve().parents[1]
SHA = "a" * 40
OTHER_SHA = "c" * 40
INSPECTOR_SHA = "d" * 40
NOW = datetime(2026, 7, 16, tzinfo=timezone.utc)
REPO = "o/r"
REPO_ID = 100


def response(url, payload, status=200):
    return _mint_response(request_url=url, response_url=url, status_code=status, fetched_at=NOW, payload=payload)


def target_identity(repo=REPO, repo_id=REPO_ID):
    url = f"https://api.github.com/repos/{repo}"
    return verify_target_identity_response(response(url, {"full_name": repo, "id": repo_id, "url": url, "html_url": f"https://github.com/{repo}"}), expected_repository=repo)


def surface_inventory(repo=REPO, repo_id=REPO_ID, pr=7, head=SHA, bot_sources=None):
    ident = target_identity(repo, repo_id)
    base = f"https://api.github.com/repos/{repo}"
    bot_sources = bot_sources or []
    comments = [{"id": i + 1, "user": {"login": src}} for i, src in enumerate(bot_sources)]
    responses = {
        "review_comments": response(f"{base}/pulls/{pr}/comments?per_page=100", comments),
        "reviews": response(f"{base}/pulls/{pr}/reviews?per_page=100", []),
        "issue_comments": response(f"{base}/issues/{pr}/comments?per_page=100", []),
        "check_runs": response(f"{base}/commits/{head}/check-runs?per_page=100", {"check_runs": []}),
    }
    return verify_review_surface_inventory_responses(responses, target_repository=repo, target_identity=ident, pull_request=pr, reviewed_head_sha=head)


def inspector_commit():
    repo = {"full_name": "rezahh107/PR-Inspector", "id": LOCKED_INSPECTOR_REPOSITORY_ID, "url": "https://api.github.com/repos/rezahh107/PR-Inspector", "html_url": "https://github.com/rezahh107/PR-Inspector"}
    commit = {"sha": INSPECTOR_SHA, "url": f"https://api.github.com/repos/rezahh107/PR-Inspector/commits/{INSPECTOR_SHA}", "html_url": f"https://github.com/rezahh107/PR-Inspector/commit/{INSPECTOR_SHA}"}
    return verify_github_commit_payload(repo, commit, expected_commit_sha=INSPECTOR_SHA)


def governance(authorized=True, repo=REPO, repo_id=REPO_ID, pr=7, head=SHA):
    ev = object.__new__(VerifiedGovernanceEvidence)
    values = {"evidence_id": "ev", "repository": repo, "default_branch": "main", "pull_request_number": pr, "exact_head_sha": head, "enforcement_status": "verified_enforced", "valid_approval_reviewers": ("reviewer",), "required_status_checks": (("ci", 15368),), "exact_head_checks_satisfied": authorized, "approval_complete": authorized, "specialist_satisfied": authorized, "specialist_status": "not_required", "bypass_actors": () if authorized else ("admin",), "merge_readiness_satisfied": authorized, "merge_authorized": authorized, "conclusion": "verified" if authorized else "gap", "source_response_urls": (f"https://api.github.com/repos/{repo}",)}
    for k, v in values.items():
        object.__setattr__(ev, k, v)
    _EVIDENCE_CAPABILITIES.add(ev)
    return ev


def complete_reconciliation(**overrides):
    rec = {"collection_status": "COMPLETE", "open_bot_sources_total": 0, "inspected_total": 0, "counts": {"accepted": 0, "resolved": 0, "stale": 0, "false_positive": 0, "duplicate": 0, "insufficient_evidence": 0, "deferred": 0, "out_of_scope": 0}, "uninspected_source_ids": [], "valid_blocking_finding_ids": [], "suggestion_results": []}
    rec.update(overrides)
    return rec


def package_for_decision(projection=None, reconciliation=None, profile="minimal", legacy_status="GREEN_TECHNICALLY_READY", **overrides):
    rec = reconciliation or complete_reconciliation()
    projection = projection or project_decision(profile, [])
    pkg = json.loads((ROOT / "fixtures/golden-green/review-package.json").read_text())
    pkg["protocol_version"] = PROTOCOL_VERSION
    pkg["review_identity"].update({"target_repository": REPO, "target_repository_id": REPO_ID, "pr_number": 7, "reviewed_head_sha": SHA, "inspector_commit_sha": INSPECTOR_SHA})
    for ev in pkg.get("evidence_records", []):
        ev["reviewed_head_sha"] = SHA
    pkg["external_review_intake"] = {"sources_inspected": [], "suggestions": []}
    pkg["decision"]["technical_status"] = legacy_status
    pkg["inspection_profile"] = profile
    pkg["technical_decision"] = projection["technical_decision"]
    pkg["governance_decision"] = projection["governance_decision"]
    pkg["overall_recommendation"] = projection["overall_recommendation"]
    pkg["external_review_reconciliation"] = rec
    pkg.update(overrides)
    return pkg


def valid_artifacts(pkg=None, inventory=None):
    pkg = pkg or package_for_decision()
    inventory = inventory if inventory is not None else surface_inventory()
    return build_candidate_review_artifacts(pkg, review_surface_inventory=inventory)


def test_prf001_inspector_commit_requires_active_verified_capability():
    repo = {"full_name": "rezahh107/PR-Inspector", "id": LOCKED_INSPECTOR_REPOSITORY_ID, "url": "https://api.github.com/repos/rezahh107/PR-Inspector", "html_url": "https://github.com/rezahh107/PR-Inspector"}
    commit = {"sha": INSPECTOR_SHA, "url": f"https://api.github.com/repos/rezahh107/PR-Inspector/commits/{INSPECTOR_SHA}", "html_url": f"https://github.com/rezahh107/PR-Inspector/commit/{INSPECTOR_SHA}"}
    with pytest.raises(ValueError, match="active VerifiedInspectorCommit"):
        verify_candidate_inspector_commit_payload(repo, commit, INSPECTOR_SHA)
    with pytest.raises(TypeError):
        VerifiedInspectorCommit()
    lookalike = type("Lookalike", (), {"repository": "rezahh107/PR-Inspector", "repository_id": LOCKED_INSPECTOR_REPOSITORY_ID, "commit_sha": INSPECTOR_SHA})()
    with pytest.raises(ValueError, match="active verified inspector commit"):
        verify_minimal_review_artifact_bytes(valid_artifacts(), lookalike, review_surface_inventory=surface_inventory())
    assert verify_minimal_review_artifact_bytes(valid_artifacts(), inspector_commit(), review_surface_inventory=surface_inventory()).inspector_commit.commit_sha == INSPECTOR_SHA


def test_prf002_governance_negative_evidence_has_registered_gap_status():
    projection = project_decision("strict", [], governance(False), target_repository=REPO, target_repository_id=REPO_ID, pull_request=7, reviewed_head_sha=SHA)
    assert projection["governance_decision"] == {"status": "GAP_FOUND", "reason_codes": ["merge_authorization_unverified"]}
    assert projection["overall_recommendation"]["merge_governance_verified"] is False
    assert GOVERNANCE_STATUS_EFFECT["merge_authorization_unverified"] == "GAP_FOUND"
    for reason in GOVERNANCE_REASON_CODES:
        status = project_decision("strict", [], None)["governance_decision"]["status"] if reason == "repository_settings_not_verified" else GOVERNANCE_STATUS_EFFECT[reason]
        assert status in {"NOT_VERIFIABLE", "GAP_FOUND"}


def test_prf003_numeric_repository_id_is_schema_and_reuse_required():
    Draft202012Validator(json.loads((ROOT / "protocols/v1.11.0/schemas/review-package.schema.json").read_text())).validate(package_for_decision())
    for bad_id in [None, 0, -1, "100"]:
        pkg = package_for_decision()
        if bad_id is None:
            del pkg["review_identity"]["target_repository_id"]
        else:
            pkg["review_identity"]["target_repository_id"] = bad_id
        assert validate_candidate_package(pkg, review_surface_inventory=surface_inventory())
    bundle = verify_minimal_review_artifact_bytes(valid_artifacts(), inspector_commit(), review_surface_inventory=surface_inventory())
    assert verify_base_review_reference(bundle, SHA, target_repository=REPO, target_repository_id=REPO_ID, pull_request=7)["status"] == "VERIFIED"
    assert verify_base_review_reference(bundle, SHA, target_repository=REPO, target_repository_id=999, pull_request=7)["status"] == "INVALID"
    assert project_decision("strict", [], governance(True, repo="x/y"), target_repository=REPO, target_repository_id=REPO_ID, pull_request=7, reviewed_head_sha=SHA)["governance_decision"]["status"] == "NOT_VERIFIABLE"


def test_prf004_required_checks_and_finding_evidence_are_semantically_bound():
    base = package_for_decision()
    mutations = []
    mutations.append(lambda p: p["checks"][0].update({"state": "MENTIONED_UNVERIFIED", "result": "PASS"}))
    mutations.append(lambda p: p["checks"][0].update({"state": "UNAVAILABLE", "result": "PASS"}))
    mutations.append(lambda p: p["evidence_records"][0].update({"result": "FAIL"}))
    mutations.append(lambda p: p["evidence_records"][0].update({"result": "UNKNOWN"}))
    mutations.append(lambda p: p["evidence_records"][0].update({"reviewed_head_sha": OTHER_SHA}))
    mutations.append(lambda p: p["checks"][0].update({"evidence_id": "EVD-999"}))
    mutations.append(lambda p: p["evidence_records"].append(copy.deepcopy(p["evidence_records"][0])))
    mutations.append(lambda p: (p["evidence_records"][0].update({"evidence_type": "DOCUMENTATION", "result": "PASS"}), p["findings"].append({"finding_id": "F1", "severity": "HIGH", "evidence_label": "REPRODUCED", "blocking": True, "file_location": None, "symbol": None, "relevant_code": None, "issue": "i", "failure_scenario": "s", "recommended_fix": "f", "recommended_test": "t", "evidence_refs": ["EVD-001"], "rule_ids": []})))
    mutations.append(lambda p: p["findings"].append({"finding_id": "F2", "severity": "HIGH", "evidence_label": "CODE_SUPPORTED", "blocking": True, "file_location": None, "symbol": None, "relevant_code": None, "issue": "i", "failure_scenario": "s", "recommended_fix": "f", "recommended_test": "t", "evidence_refs": [], "rule_ids": []}))
    for mutate in mutations:
        pkg = copy.deepcopy(base)
        mutate(pkg)
        assert validate_candidate_package(pkg, review_surface_inventory=surface_inventory()), mutate


def test_prf005_reconciliation_requires_sealed_review_surface_inventory():
    forged_empty = package_for_decision()
    assert validate_candidate_package(forged_empty) == []  # schema-only local package has no external inventory claim
    inv = surface_inventory(bot_sources=["reviewdog[bot]"])
    assert validate_candidate_package(forged_empty, review_surface_inventory=inv)
    pkg = package_for_decision()
    pkg["external_review_intake"] = {"sources_inspected": [{"source_id": "EXTSRC-001", "source_type": "github_pr_review_comment", "author": "reviewdog[bot]", "is_bot": True, "url": None, "inspected": True}], "suggestions": []}
    pkg["external_review_reconciliation"] = {**complete_reconciliation(), "open_bot_sources_total": 1, "inspected_total": 1}
    assert validate_candidate_package(pkg, review_surface_inventory=inv) == []
    assert validate_candidate_package(pkg, review_surface_inventory=surface_inventory(head=OTHER_SHA))
    with pytest.raises(ValueError, match="inaccessible"):
        base = f"https://api.github.com/repos/{REPO}"
        ident = target_identity()
        verify_review_surface_inventory_responses({"review_comments": response(f"{base}/pulls/7/comments?per_page=100", [], 500), "reviews": response(f"{base}/pulls/7/reviews?per_page=100", []), "issue_comments": response(f"{base}/issues/7/comments?per_page=100", []), "check_runs": response(f"{base}/commits/{SHA}/check-runs?per_page=100", {"check_runs": []})}, target_repository=REPO, target_identity=ident, pull_request=7, reviewed_head_sha=SHA)


def test_prf006_artifacts_are_projection_rendered_for_green_yellow_red_and_prompt_routes():
    inv = surface_inventory()
    green_pkg = package_for_decision()
    green = build_candidate_review_artifacts(green_pkg, review_surface_inventory=inv)
    assert "NEXT_ACTION_PROMPT.en.md" not in green
    yellow_projection = project_decision("minimal", ["blocking_medium_finding"])
    yellow_pkg = package_for_decision(yellow_projection, legacy_status="YELLOW_CHANGES_OR_VERIFICATION_REQUIRED")
    yellow_pkg["findings"].append({"finding_id": "PRF-003", "severity": "MEDIUM", "evidence_label": "CODE_SUPPORTED", "blocking": True, "file_location": "src/a.py:1", "symbol": None, "relevant_code": "code", "issue": "i", "failure_scenario": "s", "recommended_fix": "f", "recommended_test": "t", "evidence_refs": ["EVD-002"], "rule_ids": ["PRR-TEST-001"]})
    yellow_pkg["decision"]["blocking_findings_count"] = 1
    yellow = build_candidate_review_artifacts(yellow_pkg, review_surface_inventory=inv)
    assert "NEXT_ACTION_PROMPT.en.md" in yellow and b"YELLOW" in yellow["OWNER_RESULT.fa.txt"]
    red_projection = project_decision("minimal", ["required_technical_check_failed"])
    red_pkg = package_for_decision(red_projection, legacy_status="RED_DO_NOT_MERGE")
    red_pkg["checks"][0]["result"] = "FAIL"
    red = build_candidate_review_artifacts(red_pkg, review_surface_inventory=inv)
    assert "NEXT_ACTION_PROMPT.en.md" in red and b"RED" in red["OWNER_RESULT.fa.txt"]
    tampered = dict(green); tampered["OWNER_DECISION_CARD.fa.md"] = b"owner\n"
    with pytest.raises(ValueError, match="OWNER_DECISION_CARD"):
        verify_minimal_review_artifact_bytes(tampered, inspector_commit(), review_surface_inventory=inv)
    tampered = dict(yellow); tampered.pop("NEXT_ACTION_PROMPT.en.md")
    with pytest.raises(ValueError, match="artifact set"):
        verify_minimal_review_artifact_bytes(tampered, inspector_commit(), review_surface_inventory=inv)
    assert candidate_owner_delivery_stdout(build_candidate_owner_delivery_artifacts(green["OWNER_RESULT.fa.txt"])).endswith(PROFILE_COMMANDS_BYTES)
    bad = build_candidate_owner_delivery_artifacts(green["OWNER_RESULT.fa.txt"]); bad = dict(bad); bad[OWNER_PROFILE_COMMANDS_ARTIFACT] += b"x"
    assert candidate_owner_delivery_stdout(bad) == b""


def test_existing_intake_reason_reconciliation_and_schema_determinism():
    assert parse_intake("https://github.com/o/r/pull/7")["inspection_profile"] == "minimal"
    assert parse_intake("حداقلی\nhttps://github.com/o/r/pull/7")["inspection_profile"] == "minimal"
    assert parse_intake("سخت گیرانه\nhttps://github.com/o/r/pull/7")["inspection_profile"] == "strict"
    bundle = verify_minimal_review_artifact_bytes(valid_artifacts(), inspector_commit(), review_surface_inventory=surface_inventory())
    assert parse_intake("سخت گیرانه", {"current_target": {"repository": REPO, "repository_id": REPO_ID, "pull_request": 7}, "live_head_sha": SHA, "verified_minimal_review": bundle})["reuse_current_minimal"] is True
    assert parse_intake("سخت گیرانه", {"current_target": {"repository": REPO, "repository_id": REPO_ID, "pull_request": 7}, "live_head_sha": OTHER_SHA, "verified_minimal_review": bundle})["reuse_current_minimal"] is False
    with pytest.raises(ValueError): project_decision("minimal", ["unknown"])
    assert project_decision("minimal", ["required_technical_check_failed"])["technical_decision"]["status"] == "RED"
    rec = reconcile_bot_reviews([{"source_id": "bot", "inspected": True}], [{"suggestion_id": "S", "source_id": "bot", "triage_decision": "accepted", "linked_finding_ids": ["F"]}], [{"finding_id": "F", "severity": "HIGH", "blocking": True}])
    assert rec["valid_blocking_finding_ids"] == ["F"]
    assert render_owner_profile_commands("minimal") == PROFILE_COMMANDS_BYTES
    assert validate_owner_profile_commands(PROFILE_COMMANDS_BYTES) == []
    Draft202012Validator(json.loads((ROOT / "protocols/v1.11.0/schemas/decision-projection.schema.json").read_text())).validate(project_decision("minimal"))
    registry = yaml.safe_load((ROOT / "protocols/v1.11.0/registries/DECISION_REASON_REGISTRY.yaml").read_text())
    entries = {entry["reason_code"]: entry for entry in registry["candidate_reason_domains"]}
    assert set(entries) == TECHNICAL_REASON_CODES | GOVERNANCE_REASON_CODES
