import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from pr_inspector._governance_transport import _mint_response
from pr_inspector.governance import VerifiedGovernanceEvidence, _EVIDENCE_CAPABILITIES
from pr_inspector.review_provenance import verify_github_commit_payload
from pr_inspector.candidate_v1_11 import (
    GOVERNANCE_REASON_CODES, GOVERNANCE_STATUS_EFFECT, LOCKED_INSPECTOR_REPOSITORY_ID,
    OWNER_PROFILE_COMMANDS_ARTIFACT, PROFILE_COMMANDS_BYTES, PROTOCOL_VERSION,
    TECHNICAL_REASON_CODES, bind_candidate_governance_evidence,
    build_candidate_owner_delivery_artifacts, build_candidate_review_artifacts,
    bytes_sha256, candidate_owner_delivery_stdout, canonical_sha256,
    classify_governance, parse_intake, project_decision, reconcile_bot_reviews,
    render_owner_profile_commands, validate_candidate_package,
    validate_owner_profile_commands, verify_base_review_reference,
    verify_candidate_inspector_commit_payload, verify_candidate_inspector_commit_responses,
    verify_governance_payload_bundle, verify_minimal_review_artifact_bytes,
    verify_review_surface_inventory_responses, verify_target_identity_response,
)

ROOT = Path(__file__).resolve().parents[1]
SHA = "a" * 40
OTHER_SHA = "c" * 40
INSPECTOR_SHA = "d" * 40
REPO = "o/r"
REPO_ID = 100


def now():
    return datetime.now(timezone.utc)


def response(url, payload, status=200, fetched_at=None):
    return _mint_response(request_url=url, response_url=url, status_code=status, fetched_at=fetched_at or now(), payload=payload)


def target_identity(repo=REPO, repo_id=REPO_ID, fetched_at=None):
    url = f"https://api.github.com/repos/{repo}"
    return verify_target_identity_response(response(url, {"full_name": repo, "id": repo_id, "url": url, "html_url": f"https://github.com/{repo}"}, fetched_at=fetched_at), expected_repository=repo)


def inspector_commit_receipt(repo_id=LOCKED_INSPECTOR_REPOSITORY_ID):
    repo_url = "https://api.github.com/repos/rezahh107/PR-Inspector"
    commit_url = f"{repo_url}/commits/{INSPECTOR_SHA}"
    return verify_candidate_inspector_commit_responses(
        response(repo_url, {"full_name": "rezahh107/PR-Inspector", "id": repo_id, "url": repo_url, "html_url": "https://github.com/rezahh107/PR-Inspector"}),
        response(commit_url, {"sha": INSPECTOR_SHA, "url": commit_url, "html_url": f"https://github.com/rezahh107/PR-Inspector/commit/{INSPECTOR_SHA}"}),
        expected_commit_sha=INSPECTOR_SHA,
    )


def active_mapping_commit():
    repo = {"full_name": "rezahh107/PR-Inspector", "id": LOCKED_INSPECTOR_REPOSITORY_ID, "url": "https://api.github.com/repos/rezahh107/PR-Inspector", "html_url": "https://github.com/rezahh107/PR-Inspector"}
    commit = {"sha": INSPECTOR_SHA, "url": f"https://api.github.com/repos/rezahh107/PR-Inspector/commits/{INSPECTOR_SHA}", "html_url": f"https://github.com/rezahh107/PR-Inspector/commit/{INSPECTOR_SHA}"}
    return verify_github_commit_payload(repo, commit, expected_commit_sha=INSPECTOR_SHA)


def surface_inventory(repo=REPO, repo_id=REPO_ID, pr=7, head=SHA, bot_sources=None, fetched_at=None, incomplete=False):
    ident = target_identity(repo, repo_id, fetched_at=fetched_at)
    base = f"https://api.github.com/repos/{repo}"
    bot_sources = bot_sources or []
    comments = [{"id": i + 1, "node_id": f"RC{i+1}", "html_url": f"https://github.com/{repo}/pull/{pr}#discussion_r{i+1}", "user": {"login": src, "type": "Bot"}} for i, src in enumerate(bot_sources)]
    payload_comments = {"incomplete_pagination": True} if incomplete else comments
    responses = {
        "review_comments": response(f"{base}/pulls/{pr}/comments?per_page=100", payload_comments, fetched_at=fetched_at),
        "review_threads": response(f"{base}/pulls/{pr}/threads?per_page=100", [], fetched_at=fetched_at),
        "reviews": response(f"{base}/pulls/{pr}/reviews?per_page=100", [], fetched_at=fetched_at),
        "issue_comments": response(f"{base}/issues/{pr}/comments?per_page=100", [], fetched_at=fetched_at),
        "check_runs": response(f"{base}/commits/{head}/check-runs?per_page=100", {"check_runs": []}, fetched_at=fetched_at),
        "check_annotations": response(f"{base}/commits/{head}/check-runs/annotations?per_page=100", [], fetched_at=fetched_at),
        "check_summaries": response(f"{base}/commits/{head}/status", {"statuses": []}, fetched_at=fetched_at),
    }
    return verify_review_surface_inventory_responses(responses, target_repository=repo, target_identity=ident, pull_request=pr, reviewed_head_sha=head)


def governance(authorized=True, repo=REPO, pr=7, head=SHA):
    ev = object.__new__(VerifiedGovernanceEvidence)
    values = {"evidence_id": "ev", "repository": repo, "default_branch": "main", "pull_request_number": pr, "exact_head_sha": head, "enforcement_status": "verified_enforced", "valid_approval_reviewers": ("reviewer",), "required_status_checks": (("ci", 15368),), "exact_head_checks_satisfied": authorized, "approval_complete": authorized, "specialist_satisfied": authorized, "specialist_status": "not_required", "bypass_actors": () if authorized else ("admin",), "merge_readiness_satisfied": authorized, "merge_authorized": authorized, "conclusion": "verified" if authorized else "gap", "source_response_urls": (f"https://api.github.com/repos/{repo}",)}
    for k, v in values.items():
        object.__setattr__(ev, k, v)
    _EVIDENCE_CAPABILITIES.add(ev)
    return ev


def candidate_governance(authorized=True, repo=REPO, repo_id=REPO_ID, pr=7, head=SHA):
    return bind_candidate_governance_evidence(governance(authorized, repo, pr, head), target_identity(repo, repo_id))


def complete_reconciliation(**overrides):
    rec = {"collection_status": "COMPLETE", "open_bot_sources_total": 0, "inspected_total": 0, "counts": {"accepted": 0, "resolved": 0, "stale": 0, "false_positive": 0, "duplicate": 0, "insufficient_evidence": 0, "deferred": 0, "out_of_scope": 0}, "uninspected_source_ids": [], "valid_blocking_finding_ids": [], "suggestion_results": []}
    rec.update(overrides)
    return rec


def package_for_decision(projection=None, reconciliation=None, profile="minimal", legacy_status="GREEN_TECHNICALLY_READY", sources=None, suggestions=None, **overrides):
    rec = reconciliation or complete_reconciliation()
    projection = projection or project_decision(profile, [])
    pkg = json.loads((ROOT / "fixtures/golden-green/review-package.json").read_text())
    pkg["protocol_version"] = PROTOCOL_VERSION
    pkg["review_identity"].update({"target_repository": REPO, "target_repository_id": REPO_ID, "pr_number": 7, "reviewed_head_sha": SHA, "inspector_commit_sha": INSPECTOR_SHA})
    for ev in pkg.get("evidence_records", []):
        ev["reviewed_head_sha"] = SHA
    pkg["external_review_intake"] = {"sources_inspected": sources or [], "suggestions": suggestions or []}
    pkg["decision"]["technical_status"] = legacy_status
    pkg["inspection_profile"] = profile
    pkg["technical_decision"] = projection["technical_decision"]
    pkg["governance_decision"] = projection["governance_decision"]
    pkg["overall_recommendation"] = projection["overall_recommendation"]
    pkg["external_review_reconciliation"] = rec
    pkg.update(overrides)
    return pkg


def artifact_bundle(pkg=None, inventory=None):
    inventory = inventory or surface_inventory()
    artifacts = build_candidate_review_artifacts(pkg or package_for_decision(), review_surface_inventory=inventory)
    return verify_minimal_review_artifact_bytes(artifacts, inspector_commit_receipt(), review_surface_inventory=inventory)


def test_prf001_inspector_commit_requires_receipt_derived_candidate_capability():
    repo = {"full_name": "rezahh107/PR-Inspector", "id": LOCKED_INSPECTOR_REPOSITORY_ID, "url": "https://api.github.com/repos/rezahh107/PR-Inspector", "html_url": "https://github.com/rezahh107/PR-Inspector"}
    commit = {"sha": INSPECTOR_SHA, "url": f"https://api.github.com/repos/rezahh107/PR-Inspector/commits/{INSPECTOR_SHA}", "html_url": f"https://github.com/rezahh107/PR-Inspector/commit/{INSPECTOR_SHA}"}
    with pytest.raises(ValueError, match="sealed GitHub API response receipts"):
        verify_candidate_inspector_commit_payload(repo, commit, INSPECTOR_SHA)
    with pytest.raises(ValueError, match="candidate inspector commit receipt"):
        verify_minimal_review_artifact_bytes(build_candidate_review_artifacts(package_for_decision(), review_surface_inventory=surface_inventory()), active_mapping_commit(), review_surface_inventory=surface_inventory())
    lookalike = type("Lookalike", (), {"repository": "rezahh107/PR-Inspector", "repository_id": LOCKED_INSPECTOR_REPOSITORY_ID, "commit_sha": INSPECTOR_SHA})()
    with pytest.raises(ValueError, match="candidate inspector commit receipt"):
        verify_minimal_review_artifact_bytes(build_candidate_review_artifacts(package_for_decision(), review_surface_inventory=surface_inventory()), lookalike, review_surface_inventory=surface_inventory())
    with pytest.raises(ValueError, match="identity mismatch"):
        inspector_commit_receipt(repo_id=999)
    assert artifact_bundle().inspector_commit.commit_sha == INSPECTOR_SHA


def test_prf002_governance_repository_id_is_bound_to_candidate_evidence():
    assert project_decision("strict", [], governance(True), target_repository=REPO, target_repository_id=REPO_ID, pull_request=7, reviewed_head_sha=SHA)["governance_decision"]["status"] == "NOT_VERIFIABLE"
    projection = project_decision("strict", [], candidate_governance(False), target_repository=REPO, target_repository_id=REPO_ID, pull_request=7, reviewed_head_sha=SHA)
    assert projection["governance_decision"] == {"status": "GAP_FOUND", "reason_codes": ["merge_authorization_unverified"]}
    assert GOVERNANCE_STATUS_EFFECT["merge_authorization_unverified"] == "GAP_FOUND"
    assert project_decision("strict", [], candidate_governance(True, repo_id=999), target_repository=REPO, target_repository_id=REPO_ID, pull_request=7, reviewed_head_sha=SHA)["governance_decision"]["status"] == "NOT_VERIFIABLE"


def test_prf003_inventory_is_mandatory_for_green_and_reuse_context_requires_id():
    pkg = package_for_decision()
    assert validate_candidate_package(pkg)
    with pytest.raises(ValueError, match="sealed review surface inventory"):
        build_candidate_review_artifacts(pkg)
    with pytest.raises(ValueError, match="sealed review surface inventory"):
        verify_minimal_review_artifact_bytes(build_candidate_review_artifacts(pkg, review_surface_inventory=surface_inventory()), inspector_commit_receipt())
    bundle = artifact_bundle()
    assert parse_intake("سخت گیرانه", {"current_target": {"repository": REPO, "pull_request": 7}, "live_head_sha": SHA, "verified_minimal_review": bundle})["reuse_current_minimal"] is False
    assert parse_intake("سخت گیرانه", {"current_target": {"repository": REPO, "repository_id": REPO_ID, "pull_request": 7}, "live_head_sha": SHA, "verified_minimal_review": bundle})["reuse_current_minimal"] is True
    assert verify_base_review_reference(bundle, SHA, target_repository=REPO, target_repository_id=999, pull_request=7)["status"] == "INVALID"


def test_prf004_review_surface_inventory_surfaces_freshness_pagination_and_bot_identity():
    inv = surface_inventory(bot_sources=["automation-user"])
    assert inv.sources[0]["author"] == "automation-user"
    assert inv.sources[0]["source_type"] == "github_pr_review_comment"
    assert inv.sources[0]["inspected"] is False
    assert inv.sources[0]["github_source_key"] == "review_comments:RC1"
    with pytest.raises(ValueError, match="pagination"):
        surface_inventory(bot_sources=["bot-user"], incomplete=True)
    with pytest.raises(ValueError, match="not fresh"):
        surface_inventory(fetched_at=now() - timedelta(hours=1))
    with pytest.raises(ValueError, match="not fresh"):
        surface_inventory(fetched_at=now() + timedelta(hours=1))
    # human login containing bot is not classified unless actor type is Bot/App
    base = f"https://api.github.com/repos/{REPO}"
    ident = target_identity()
    responses = {
        "review_comments": response(f"{base}/pulls/7/comments?per_page=100", [{"id": 1, "node_id": "x", "user": {"login": "robotics-human", "type": "User"}}]),
        "review_threads": response(f"{base}/pulls/7/threads?per_page=100", []),
        "reviews": response(f"{base}/pulls/7/reviews?per_page=100", []),
        "issue_comments": response(f"{base}/issues/7/comments?per_page=100", []),
        "check_runs": response(f"{base}/commits/{SHA}/check-runs?per_page=100", {"check_runs": []}),
        "check_annotations": response(f"{base}/commits/{SHA}/check-runs/annotations?per_page=100", []),
        "check_summaries": response(f"{base}/commits/{SHA}/status", {"statuses": []}),
    }
    assert verify_review_surface_inventory_responses(responses, target_repository=REPO, target_identity=ident, pull_request=7, reviewed_head_sha=SHA).sources == ()


def test_prf005_projection_controls_prompt_routing_and_owner_bytes():
    inv = surface_inventory()
    green_projection = project_decision("minimal", [])
    assert green_projection["owner_readiness"]["message_key"] == "technical_green"
    assert green_projection["next_action"]["prompt_required"] is False
    green = build_candidate_review_artifacts(package_for_decision(green_projection), review_surface_inventory=inv)
    assert "NEXT_ACTION_PROMPT.en.md" not in green
    assert green["OWNER_RESULT.fa.txt"] == "🟢 وضعیت: از نظر فنی آماده\nآمادگی فنی تأیید شده؛ حفاظت ادغام در GitHub جداگانه بررسی شود.\n".encode()
    yellow_projection = project_decision("minimal", ["blocking_medium_finding"])
    assert yellow_projection["next_action"]["prompt_required"] is True
    assert yellow_projection["owner_readiness"]["message_key"] == "technical_yellow_repair"
    yellow_pkg = package_for_decision(yellow_projection, legacy_status="YELLOW_CHANGES_OR_VERIFICATION_REQUIRED")
    yellow_pkg["findings"].append({"finding_id": "PRF-003", "severity": "MEDIUM", "evidence_label": "CODE_SUPPORTED", "blocking": True, "file_location": "src/a.py:1", "symbol": None, "relevant_code": "code", "issue": "i", "failure_scenario": "s", "recommended_fix": "f", "recommended_test": "t", "evidence_refs": ["EVD-002"], "rule_ids": ["PRR-TEST-001"]})
    yellow_pkg["decision"]["blocking_findings_count"] = 1
    yellow = build_candidate_review_artifacts(yellow_pkg, review_surface_inventory=inv)
    assert "NEXT_ACTION_PROMPT.en.md" in yellow
    tampered = dict(yellow); tampered.pop("NEXT_ACTION_PROMPT.en.md")
    with pytest.raises(ValueError, match="artifact set"):
        verify_minimal_review_artifact_bytes(tampered, inspector_commit_receipt(), review_surface_inventory=inv)


def test_prf006_owner_delivery_requires_verified_bundle_and_atomic_prompt():
    inv = surface_inventory()
    bundle = artifact_bundle(inventory=inv)
    assert build_candidate_owner_delivery_artifacts(bundle)[OWNER_PROFILE_COMMANDS_ARTIFACT] == PROFILE_COMMANDS_BYTES
    assert candidate_owner_delivery_stdout(bundle).endswith(PROFILE_COMMANDS_BYTES)
    assert candidate_owner_delivery_stdout({"OWNER_RESULT.fa.txt": b"x\ny\n", OWNER_PROFILE_COMMANDS_ARTIFACT: PROFILE_COMMANDS_BYTES}) == b""
    yellow_projection = project_decision("minimal", ["required_technical_check_failed"])
    yellow_pkg = package_for_decision(yellow_projection, legacy_status="RED_DO_NOT_MERGE")
    yellow_pkg["checks"][0]["result"] = "FAIL"
    prompt_bundle = artifact_bundle(yellow_pkg, inv)
    stdout = candidate_owner_delivery_stdout(prompt_bundle)
    assert b"Repair independently" in stdout and "## پرامپت اقدام".encode() in stdout
    tampered = dict(prompt_bundle.artifact_bytes); tampered[OWNER_PROFILE_COMMANDS_ARTIFACT] += b"x"
    fake = type("FakeBundle", (), {"artifact_bytes": tampered})()
    assert candidate_owner_delivery_stdout(fake) == b""


def test_existing_intake_reconciliation_reason_schema_and_registry_paths():
    assert parse_intake("https://github.com/o/r/pull/7")["inspection_profile"] == "minimal"
    assert parse_intake("حداقلی\nhttps://github.com/o/r/pull/7")["inspection_profile"] == "minimal"
    assert parse_intake("سخت گیرانه\nhttps://github.com/o/r/pull/7")["inspection_profile"] == "strict"
    with pytest.raises(ValueError): project_decision("minimal", ["unknown"])
    assert project_decision("minimal", ["required_technical_check_failed"])["technical_decision"]["status"] == "RED"
    rec = reconcile_bot_reviews([{"source_id": "EXTSRC-001", "source_type": "github_pr_review_comment", "author": "bot", "is_bot": True, "url": None, "inspected": True}], [{"suggestion_id": "S", "source_id": "EXTSRC-001", "triage_decision": "accepted", "linked_finding_ids": ["PRF-001"]}], [{"finding_id": "PRF-001", "severity": "HIGH", "blocking": True}])
    assert rec["valid_blocking_finding_ids"] == ["PRF-001"]
    assert render_owner_profile_commands("minimal") == PROFILE_COMMANDS_BYTES
    assert validate_owner_profile_commands(PROFILE_COMMANDS_BYTES) == []
    Draft202012Validator(json.loads((ROOT / "protocols/v1.11.0/schemas/decision-projection.schema.json").read_text())).validate(project_decision("minimal"))
    registry = yaml.safe_load((ROOT / "protocols/v1.11.0/registries/DECISION_REASON_REGISTRY.yaml").read_text())
    entries = {entry["reason_code"]: entry for entry in registry["candidate_reason_domains"]}
    assert set(entries) == TECHNICAL_REASON_CODES | GOVERNANCE_REASON_CODES
