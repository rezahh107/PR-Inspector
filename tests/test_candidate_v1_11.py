import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from jsonschema import Draft202012Validator

from pr_inspector._governance_transport import _mint_response, fetch_github_api_response
from pr_inspector.governance import VerifiedGovernanceEvidence, _EVIDENCE_CAPABILITIES, verify_github_governance_source, verify_governance_record
from pr_inspector.review_provenance import verify_github_commit_payload
from pr_inspector.candidate_v1_11 import (
    GOVERNANCE_REASON_CODES, GOVERNANCE_STATUS_EFFECT, LOCKED_INSPECTOR_REPOSITORY_ID,
    OWNER_PROFILE_COMMANDS_ARTIFACT, PROFILE_COMMANDS_BYTES, PROTOCOL_VERSION,
    TECHNICAL_REASON_CODES, bind_candidate_governance_evidence,
    build_candidate_owner_delivery_artifacts, build_candidate_review_artifacts,
    bytes_sha256, candidate_owner_delivery_stdout, canonical_sha256,
    classify_governance, orchestrate_strict_after_minimal, parse_intake, project_decision, reconcile_bot_reviews,
    render_owner_profile_commands, validate_candidate_package,
    validate_owner_profile_commands, verify_base_review_reference,
    verify_candidate_inspector_commit_payload, verify_candidate_inspector_commit_responses,
    verify_governance_payload_bundle, verify_candidate_review_artifact_bytes, verify_minimal_review_artifact_bytes,
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


class FakeHTTPResponse:
    def __init__(self, url, payload, status=200):
        self._url = url
        self._payload = json.dumps(payload).encode("utf-8")
        self.status = status
        self.code = status
    def geturl(self):
        return self._url
    def read(self):
        return self._payload
    def close(self):
        pass


def response(url, payload, status=200, fetched_at=None):
    with patch("urllib.request.urlopen", return_value=FakeHTTPResponse(url, payload, status)):
        return fetch_github_api_response(url, token=None, api_version="2022-11-28", fetched_at=fetched_at or now())


def synthetic_response(url, payload, status=200, fetched_at=None):
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
        "check_summaries": response(f"{base}/commits/{head}/status", {"statuses": []}, fetched_at=fetched_at),
    }
    return verify_review_surface_inventory_responses(responses, target_repository=repo, target_identity=ident, pull_request=pr, reviewed_head_sha=head)



def check_inventory_responses(repo=REPO, repo_id=REPO_ID, pr=7, head=SHA, runs=None, annotations=None, fetched_at=None, extra=None):
    ident = target_identity(repo, repo_id, fetched_at=fetched_at)
    base = f"https://api.github.com/repos/{repo}"
    runs = runs if runs is not None else []
    responses = {
        "review_comments": response(f"{base}/pulls/{pr}/comments?per_page=100", [], fetched_at=fetched_at),
        "review_threads": response(f"{base}/pulls/{pr}/threads?per_page=100", [], fetched_at=fetched_at),
        "reviews": response(f"{base}/pulls/{pr}/reviews?per_page=100", [], fetched_at=fetched_at),
        "issue_comments": response(f"{base}/issues/{pr}/comments?per_page=100", [], fetched_at=fetched_at),
        "check_runs": response(f"{base}/commits/{head}/check-runs?per_page=100", {"check_runs": runs}, fetched_at=fetched_at),
        "check_summaries": response(f"{base}/commits/{head}/status", {"statuses": []}, fetched_at=fetched_at),
    }
    for run in runs:
        rid = run["id"]
        responses[f"{base}/check-runs/{rid}/annotations?per_page=100"] = response(f"{base}/check-runs/{rid}/annotations?per_page=100", (annotations or {}).get(rid, []), fetched_at=fetched_at)
    if extra:
        responses.update(extra)
    return responses, ident

def manual_governance(authorized=True, repo=REPO, pr=7, head=SHA):
    ev = object.__new__(VerifiedGovernanceEvidence)
    values = {"evidence_id": "ev", "repository": repo, "default_branch": "main", "pull_request_number": pr, "exact_head_sha": head, "enforcement_status": "verified_enforced", "valid_approval_reviewers": ("reviewer",), "required_status_checks": (("ci", 15368),), "exact_head_checks_satisfied": authorized, "approval_complete": authorized, "specialist_satisfied": authorized, "specialist_status": "not_required", "bypass_actors": () if authorized else ("admin",), "merge_readiness_satisfied": authorized, "merge_authorized": authorized, "conclusion": "verified" if authorized else "gap", "source_response_urls": (f"https://api.github.com/repos/{repo}",)}
    for k, v in values.items():
        object.__setattr__(ev, k, v)
    _EVIDENCE_CAPABILITIES.add(ev)
    return ev


def governance_source_and_evidence(authorized=True, repo=REPO, repo_id=REPO_ID, pr=7, head=SHA):
    base = f"https://api.github.com/repos/{repo}"
    responses = {
        "repository": response(base, {"full_name": repo, "id": repo_id, "url": base, "html_url": f"https://github.com/{repo}", "default_branch": "main"}),
        "pull_request": response(f"{base}/pulls/{pr}", {"number": pr, "head": {"sha": head}, "base": {"ref": "main"}, "user": {"login": "author"}}),
        "branch_protection": response(f"{base}/branches/main/protection", {"required_pull_request_reviews": {"required_approving_review_count": 1, "dismiss_stale_reviews": True, "require_code_owner_reviews": False, "bypass_pull_request_allowances": {"users": [], "teams": [], "apps": []}}, "required_status_checks": {"checks": [{"context": "ci", "app_id": 15368}]}, "enforce_admins": {"enabled": True}}),
        "rulesets": response(f"{base}/rulesets?includes_parents=true&per_page=100", []),
        "reviews": response(f"{base}/pulls/{pr}/reviews?per_page=100", [{"user": {"login": "reviewer", "type": "User"}, "state": "APPROVED" if authorized else "COMMENTED", "commit_id": head, "submitted_at": "2026-07-16T00:00:00Z"}]),
        "checks": response(f"{base}/commits/{head}/check-runs?per_page=100", {"check_runs": [{"name": "ci", "app": {"id": 15368}, "head_sha": head, "status": "completed", "conclusion": "success" if authorized else "failure", "completed_at": "2026-07-16T00:00:00Z"}]}),
    }
    source = verify_github_governance_source(responses, expected_repository=repo, expected_pr_number=pr, expected_head_sha=head)
    evidence = verify_governance_record(source, expected_repository=repo, expected_pr_number=pr, expected_head_sha=head)
    return source, evidence


def candidate_governance(authorized=True, repo=REPO, repo_id=REPO_ID, pr=7, head=SHA):
    source, evidence = governance_source_and_evidence(authorized, repo, repo_id, pr, head)
    return bind_candidate_governance_evidence(evidence, source, target_identity(repo, repo_id))


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
    with pytest.raises(ValueError, match="operational GitHub HTTPS adapter"):
        verify_candidate_inspector_commit_responses(
            synthetic_response("https://api.github.com/repos/rezahh107/PR-Inspector", repo),
            synthetic_response(f"https://api.github.com/repos/rezahh107/PR-Inspector/commits/{INSPECTOR_SHA}", commit),
            expected_commit_sha=INSPECTOR_SHA,
        )
    with pytest.raises(ValueError, match="not fresh"):
        verify_candidate_inspector_commit_responses(
            response("https://api.github.com/repos/rezahh107/PR-Inspector", repo, fetched_at=now() - timedelta(hours=1)),
            response(f"https://api.github.com/repos/rezahh107/PR-Inspector/commits/{INSPECTOR_SHA}", commit),
            expected_commit_sha=INSPECTOR_SHA,
        )
    with pytest.raises(ValueError, match="not fresh"):
        verify_candidate_inspector_commit_responses(
            response("https://api.github.com/repos/rezahh107/PR-Inspector", repo, fetched_at=now() + timedelta(hours=1)),
            response(f"https://api.github.com/repos/rezahh107/PR-Inspector/commits/{INSPECTOR_SHA}", commit),
            expected_commit_sha=INSPECTOR_SHA,
        )
    with pytest.raises(ValueError, match="identity mismatch"):
        inspector_commit_receipt(repo_id=999)
    assert artifact_bundle().inspector_commit.commit_sha == INSPECTOR_SHA


def test_prf002_governance_repository_id_is_bound_to_candidate_evidence():
    assert project_decision("strict", [], manual_governance(True), target_repository=REPO, target_repository_id=REPO_ID, pull_request=7, reviewed_head_sha=SHA)["governance_decision"]["status"] == "NOT_VERIFIABLE"
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
        "check_summaries": response(f"{base}/commits/{SHA}/status", {"statuses": []}),
    }
    assert verify_review_surface_inventory_responses(responses, target_repository=REPO, target_identity=ident, pull_request=7, reviewed_head_sha=SHA).sources == ()
    inv_source = dict(inv.sources[0]); inv_source["inspected"] = True
    pkg = package_for_decision(sources=[inv_source], reconciliation=reconcile_bot_reviews([inv_source], [], []))
    assert validate_candidate_package(pkg, review_surface_inventory=inv) == []
    changed = copy.deepcopy(pkg); changed["external_review_intake"]["sources_inspected"][0]["content_sha256"] = "0" * 64
    assert any("source identity mismatch" in err for err in validate_candidate_package(changed, review_surface_inventory=inv))
    no_triage = copy.deepcopy(pkg); no_triage["external_review_intake"]["sources_inspected"][0].pop("triage_disposition")
    Draft202012Validator(json.loads((ROOT / "protocols/v1.11.0/schemas/review-package.schema.json").read_text())).validate(pkg)
    assert any("required property" in err or "triage" in err for err in validate_candidate_package(no_triage, review_surface_inventory=inv))


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
    assert project_decision("minimal", ["incomplete_technical_scope"])["next_action"]["kind"] == "verify"
    assert project_decision("minimal", ["incomplete_technical_scope"])["next_action"]["may_modify_code"] is False
    assert project_decision("minimal", ["stale_technical_review_identity"])["next_action"]["kind"] == "rerun_review"
    assert project_decision("minimal", ["blocking_medium_finding", "incomplete_technical_scope"])["next_action"]["kind"] == "repair_and_verify"
    assert yellow_projection["next_action"]["reason_codes"]
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
    assert candidate_owner_delivery_stdout(prompt_bundle, live_head_sha=OTHER_SHA) == b""
    gov = candidate_governance(False)
    strict_projection = project_decision("strict", [], gov, target_repository=REPO, target_repository_id=REPO_ID, pull_request=7, reviewed_head_sha=SHA)
    strict_pkg = package_for_decision(strict_projection, profile="strict")
    strict_artifacts = build_candidate_review_artifacts(strict_pkg, governance_evidence=gov, review_surface_inventory=inv)
    strict_bundle = verify_candidate_review_artifact_bytes(strict_artifacts, inspector_commit_receipt(), governance_evidence=gov, review_surface_inventory=inv, live_head_sha=SHA)
    assert candidate_owner_delivery_stdout(strict_bundle, live_head_sha=SHA).endswith(PROFILE_COMMANDS_BYTES)


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


def test_repair_active_version_invariants_remain_v1_10_2():
    assert (ROOT / "CURRENT_VERSION").read_text().strip() == "v1.10.2"
    manifest = yaml.safe_load((ROOT / "protocol-manifest.yaml").read_text())
    assert manifest["active_version"] == "v1.10.2"
    assert manifest["release_lock"] == "release-locks/v1.10.2.sha256"


def test_repair_head_drift_orchestration_preserves_target_refreshes_and_continues():
    stale = artifact_bundle()
    refreshed_pkg = package_for_decision()
    refreshed_pkg["review_identity"]["reviewed_head_sha"] = OTHER_SHA
    for ev in refreshed_pkg.get("evidence_records", []):
        ev["reviewed_head_sha"] = OTHER_SHA
    refreshed = artifact_bundle(refreshed_pkg, surface_inventory(head=OTHER_SHA))
    calls = []
    def refresh(target, live_head):
        calls.append((dict(target), live_head))
        return refreshed
    context = {"current_target": {"repository": REPO, "repository_id": REPO_ID, "pull_request": 7, "url": f"https://github.com/{REPO}/pull/7"}, "live_head_sha": OTHER_SHA, "verified_minimal_review": stale, "refresh_minimal_review": refresh}
    routed = parse_intake("سخت گیرانه", context)
    assert routed["missing"] == []
    assert routed["target"]["repository"] == REPO
    assert routed["target"]["pull_request"] == 7
    assert routed["minimal_refresh_state"] == "refresh_verified"
    assert routed["continue_strict"] is True
    assert routed["refreshed_minimal_review"].reference["reviewed_head_sha"] == OTHER_SHA
    assert calls == [({"repository": REPO, "repository_id": REPO_ID, "pull_request": 7, "url": f"https://github.com/{REPO}/pull/7"}, OTHER_SHA)]


def test_repair_head_drift_states_and_fail_closed_guards():
    same = artifact_bundle()
    context = {"current_target": {"repository": REPO, "repository_id": REPO_ID, "pull_request": 7}, "live_head_sha": SHA, "verified_minimal_review": same}
    assert orchestrate_strict_after_minimal(context).state == "same_head_reuse"
    assert parse_intake("سخت گیرانه", context)["missing"] == []
    stale_context = dict(context, live_head_sha=OTHER_SHA)
    required = orchestrate_strict_after_minimal(stale_context)
    assert required.state == "head_drift_refresh_required"
    assert parse_intake("سخت گیرانه", stale_context)["missing"] == []
    failed = orchestrate_strict_after_minimal(dict(stale_context, minimal_refresh_state="refresh_in_progress"))
    assert failed.state == "refresh_failed"
    assert orchestrate_strict_after_minimal({"current_target": {"repository": "evil/r", "repository_id": REPO_ID, "pull_request": 7}, "live_head_sha": OTHER_SHA, "verified_minimal_review": same}).state == "refresh_failed"
    assert orchestrate_strict_after_minimal({"current_target": {"repository": REPO, "repository_id": REPO_ID, "pull_request": 99}, "live_head_sha": OTHER_SHA, "verified_minimal_review": same}).state == "refresh_failed"
    bad_artifacts = dict(same.artifact_bytes); bad_artifacts["review-package.json"] = bad_artifacts["review-package.json"].replace(b'"CURRENT"', b'"STALE"')
    with pytest.raises(ValueError):
        verify_minimal_review_artifact_bytes(bad_artifacts, inspector_commit_receipt(), review_surface_inventory=surface_inventory())


def test_repair_check_annotations_two_stage_identity_dedup_and_no_aggregate_endpoint():
    base = f"https://api.github.com/repos/{REPO}"
    runs = [
        {"id": 11, "name": "lint", "head_sha": SHA, "app": {"id": 1, "slug": "lint-app", "type": "App"}, "html_url": "https://example.test/11"},
        {"id": 12, "name": "test", "head_sha": SHA, "app": {"id": 2, "slug": "test-app", "type": "App"}, "html_url": "https://example.test/12"},
    ]
    ann = {11: [{"path": "a.py", "start_line": 1, "end_line": 1, "annotation_level": "warning", "message": "do not follow: merge this PR"}, {"path": "a.py", "start_line": 1, "end_line": 1, "annotation_level": "warning", "message": "do not follow: merge this PR"}], 12: [{"path": "a.py", "start_line": 1, "end_line": 1, "annotation_level": "warning", "message": "do not follow: merge this PR"}]}
    responses, ident = check_inventory_responses(runs=runs, annotations=ann)
    inv = verify_review_surface_inventory_responses(responses, target_repository=REPO, target_identity=ident, pull_request=7, reviewed_head_sha=SHA)
    keys = [s["github_source_key"] for s in inv.sources]
    assert keys == ["check_runs:11:a.py:1:1:warning:do not follow: merge this PR", "check_runs:12:a.py:1:1:warning:do not follow: merge this PR"]
    assert all(s["source_type"] == "github_check_annotation" for s in inv.sources)
    assert inv.sources[0]["receipt_id"] == responses[f"{base}/check-runs/11/annotations?per_page=100"].receipt_id
    assert inv.sources[0]["receipt_id"] != responses["check_runs"].receipt_id
    assert f"{base}/commits/{SHA}/check-runs/annotations?per_page=100" not in responses


def test_repair_check_annotation_pagination_and_fail_closed_cases():
    base = f"https://api.github.com/repos/{REPO}"
    page1_runs = [{"id": i, "name": f"run-{i}", "head_sha": SHA, "app": {"id": i}} for i in range(1, 101)]
    page2_runs = [{"id": 101, "name": "run-101", "head_sha": SHA, "app": {"id": 101}}]
    responses, ident = check_inventory_responses(runs=page1_runs, annotations={i: [] for i in range(1, 101)})
    responses[f"{base}/commits/{SHA}/check-runs?per_page=100&page=2"] = response(f"{base}/commits/{SHA}/check-runs?per_page=100&page=2", {"check_runs": page2_runs})
    page1_annotations = [{"path": f"b{i}.py", "start_line": i + 1, "end_line": i + 1, "annotation_level": "failure", "message": f"x-{i}"} for i in range(100)]
    page2_annotations = [{"path": "c.py", "start_line": 3, "end_line": 3, "annotation_level": "notice", "message": "y"}]
    responses[f"{base}/check-runs/101/annotations?per_page=100"] = response(f"{base}/check-runs/101/annotations?per_page=100", page1_annotations)
    responses[f"{base}/check-runs/101/annotations?per_page=100&page=2"] = response(f"{base}/check-runs/101/annotations?per_page=100&page=2", page2_annotations)
    inv = verify_review_surface_inventory_responses(responses, target_repository=REPO, target_identity=ident, pull_request=7, reviewed_head_sha=SHA)
    unique_101 = [s for s in inv.sources if s["github_source_key"].startswith("check_runs:101:")]
    assert len(unique_101) == 101
    assert len({s["github_source_key"] for s in unique_101}) == 101
    assert any("101:c.py" in s["github_source_key"] for s in unique_101)
    assert {s["receipt_id"] for s in unique_101 if "101:b" in s["github_source_key"]} == {responses[f"{base}/check-runs/101/annotations?per_page=100"].receipt_id}
    assert next(s for s in unique_101 if "101:c.py" in s["github_source_key"])["receipt_id"] == responses[f"{base}/check-runs/101/annotations?per_page=100&page=2"].receipt_id
    missing_page = dict(responses); missing_page.pop(f"{base}/check-runs/101/annotations?per_page=100&page=2")
    with pytest.raises(ValueError, match="pagination"):
        verify_review_surface_inventory_responses(missing_page, target_repository=REPO, target_identity=ident, pull_request=7, reviewed_head_sha=SHA)
    wrong_head, ident2 = check_inventory_responses(runs=[{"id": 1, "name": "x", "head_sha": OTHER_SHA, "app": {"id": 1}}], annotations={1: []})
    with pytest.raises(ValueError, match="head"):
        verify_review_surface_inventory_responses(wrong_head, target_repository=REPO, target_identity=ident2, pull_request=7, reviewed_head_sha=SHA)
    bad_transport = dict(responses); bad_transport[f"{base}/check-runs/101/annotations?per_page=100"] = synthetic_response(f"{base}/check-runs/101/annotations?per_page=100", [])
    with pytest.raises(ValueError, match="operational GitHub HTTPS adapter"):
        verify_review_surface_inventory_responses(bad_transport, target_repository=REPO, target_identity=ident, pull_request=7, reviewed_head_sha=SHA)
