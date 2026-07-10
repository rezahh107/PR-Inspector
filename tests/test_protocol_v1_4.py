import copy
import json
from pathlib import Path

from pr_inspector.derived_outputs import build_review_artifacts, write_review_artifacts
from pr_inspector.render import render_owner, render_handoff
from pr_inspector.validation_v2 import validate_directory, validate_package

ROOT = Path(__file__).resolve().parents[1]


def package(name="golden-green"):
    return json.loads((ROOT / "fixtures" / name / "review-package.json").read_text(encoding="utf-8"))


def codes(value):
    return sorted(item.code for item in validate_package(value))


def test_golden_package_is_valid():
    assert validate_package(package()) == []


def test_intent_fit_valid_satisfied_fixture_is_valid():
    assert validate_package(package("intent-fit-valid-satisfied")) == []


def test_repair_handoff_valid_fixture_is_valid_and_rendered():
    value = package("repair-handoff-valid")
    assert validate_package(value) == []
    rendered = render_handoff(value)
    assert "## 11. Repair Handoff for Implementer Model" in rendered
    assert "Intended recipient: implementer_model" in rendered
    assert "### PRF-001" in rendered
    assert "- PRR-EVID-001" in rendered
    assert "## 12. Files Reviewed Outside the Diff" in rendered


def test_repair_handoff_rejects_unknown_finding_reference():
    value = package("repair-handoff-valid")
    value["repair_handoff"]["affected_findings"][0]["finding_id"] = "PRF-999"
    assert "PRI-HANDOFF-001" in codes(value)


def test_repair_handoff_rejects_rule_not_attached_to_referenced_finding():
    value = package("repair-handoff-valid")
    value["repair_handoff"]["affected_findings"][0]["affected_rule_ids"] = ["PRR-SCOPE-001"]
    assert "PRI-HANDOFF-002" in codes(value)


def test_intent_fit_missing_blocks_green_claim():
    diagnostics = codes(package("intent-fit-invalid-missing"))
    assert "PRI-INTENT-001" in diagnostics
    assert "PRI-STATUS-001" in diagnostics


def test_intent_fit_satisfied_requires_supported_evidence():
    assert "PRI-INTENT-002" in codes(package("intent-fit-invalid-hypothesis-only"))


def test_missing_intent_can_be_not_assessable_without_claiming_satisfaction():
    assert validate_package(package("intent-fit-valid-not-assessable")) == []


def test_non_green_without_intent_fit_is_valid_when_no_satisfaction_claim_is_made():
    value = package()
    value.pop("intent_fit")
    value["decision"]["technical_status"] = "YELLOW_CHANGES_OR_VERIFICATION_REQUIRED"
    value["decision"]["next_required_action"] = "Clarify intended behavior before merge."
    assert validate_package(value) == []


def test_stale_green_is_rejected():
    value = package()
    value["review_identity"]["review_validity"] = "STALE"
    assert codes(value) == ["PRI-STALE-001", "PRI-STATUS-001"]


def test_sensitive_review_requires_specialist():
    value = package()
    value["decision"]["risk_classification"] = "SENSITIVE"
    value["decision"]["sensitive_domains"] = ["AUTHENTICATION"]
    value["decision"]["approval_requirement"] = "PROJECT_OWNER_CONFIRMATION"
    assert codes(value) == ["PRI-SENS-001", "PRI-SENS-002"]


def test_blocking_count_is_derived_from_findings():
    value = package()
    value["decision"]["blocking_findings_count"] = 1
    assert codes(value) == ["PRI-COUNT-001"]


def test_reproduced_requires_failing_runtime_evidence():
    value = package()
    value["findings"] = [{
        "finding_id": "PRF-001",
        "severity": "HIGH",
        "evidence_label": "REPRODUCED",
        "blocking": True,
        "file_location": "src/a.py:10",
        "symbol": "parse",
        "relevant_code": "return parse(value)",
        "issue": "A failure was claimed without failing execution evidence.",
        "failure_scenario": "The claimed failure cannot be independently reproduced.",
        "recommended_fix": "Attach exact failing execution evidence.",
        "recommended_test": "Run the failing case against the reviewed head SHA.",
        "evidence_refs": ["EVD-002"],
        "rule_ids": ["PRR-EXEC-001"]
    }]
    value["decision"]["blocking_findings_count"] = 1
    value["decision"]["technical_status"] = "RED_DO_NOT_MERGE"
    assert codes(value) == ["PRI-EXEC-001"]


def test_green_with_missing_required_check_is_rejected():
    value = package()
    value["checks"][0].update({"state": "UNAVAILABLE", "result": "UNKNOWN", "evidence_id": None})
    assert codes(value) == ["PRI-STATUS-001"]


def test_current_requires_exact_head_sha():
    value = package()
    value["review_identity"]["reviewed_head_sha"] = "UNKNOWN"
    value["evidence_records"][0]["reviewed_head_sha"] = "UNKNOWN"
    value["evidence_records"][1]["reviewed_head_sha"] = "UNKNOWN"
    assert codes(value) == ["PRI-SHA-001"]


def test_ordinary_review_rejects_production_capability():
    value = package()
    value["capabilities"]["production"] = "AVAILABLE"
    assert codes(value) == ["PRI-SECRET-001"]


def test_rendering_and_artifact_consistency(tmp_path):
    value = package()
    package_path = tmp_path / "review-package.json"
    package_path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    owner = render_owner(value)
    handoff = render_handoff(value)
    assert owner == render_owner(copy.deepcopy(value))
    assert handoff == render_handoff(copy.deepcopy(value))
    write_review_artifacts(value, tmp_path, review_package_bytes=package_path.read_bytes())
    assert validate_directory(tmp_path) == []
    (tmp_path / "OWNER_DECISION_CARD.fa.md").write_text(owner + "changed", encoding="utf-8")
    assert [item.code for item in validate_directory(tmp_path)] == ["PRI-CONSIST-001", "PRI-MANIFEST-003"]


def test_malformed_nested_data_is_schema_rejected_without_semantic_crash():
    value = package()
    value["checks"][0]["required"] = "yes"
    value["capabilities"].pop("network")
    diagnostics = validate_package(value)
    assert len(diagnostics) >= 2
    assert {item.code for item in diagnostics} == {"PRI-SCHEMA-001"}
