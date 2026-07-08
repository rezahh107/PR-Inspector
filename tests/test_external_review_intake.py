import json
from pathlib import Path

from pr_inspector.render import render_handoff
from pr_inspector.validation_v2 import validate_package

ROOT = Path(__file__).resolve().parents[1]


def package(name):
    return json.loads((ROOT / "fixtures" / name / "review-package.json").read_text(encoding="utf-8"))


def codes(value):
    return sorted(item.code for item in validate_package(value))


def test_external_review_valid_fixture_is_valid():
    assert validate_package(package("external-review-valid")) == []


def test_accepted_external_suggestion_requires_evidence_record():
    value = package("external-review-invalid-missing-evidence")
    assert "PRI-EXT-001" in codes(value)


def test_accepted_external_suggestion_rejects_unknown_finding_id():
    value = package("external-review-invalid-unknown-finding")
    assert "PRI-EXT-005" in codes(value)


def test_accepted_external_suggestions_render_in_repair_handoff():
    rendered = render_handoff(package("external-review-valid"))
    assert "## 10. External Review Suggestions Considered" in rendered
    assert "| EXT-001 | gemini-code-assist[bot] | accepted | PRF-001 |" in rendered
    assert "## 11. Repair Handoff for Implementer Model" in rendered
    assert "### Accepted External Suggestions" in rendered
    assert "#### EXT-001 → PRF-001" in rendered
    assert "Config access may fail when the optional config key is missing." in rendered
    assert "Handle the missing optional config key with an explicit default or validation error." in rendered


def test_rejected_and_deferred_external_suggestions_do_not_become_repair_instructions():
    rendered = render_handoff(package("external-review-valid"))
    repair_section = rendered.split("## 11. Repair Handoff for Implementer Model", 1)[1]
    assert "EXT-002" not in repair_section
    assert "EXT-003" not in repair_section
    assert "Rename a local variable for readability." not in repair_section
    assert "Consider refactoring the entire config loader." not in repair_section


def test_inaccessible_source_requires_insufficient_evidence_suggestion():
    value = package("external-review-valid")
    value["external_review_intake"]["sources_inspected"][0]["inspected"] = False
    value["external_review_intake"]["suggestions"][0]["triage_decision"] = "deferred"
    value["external_review_intake"]["suggestions"][0]["repair_handoff"] = None
    assert "PRI-EXT-010" in codes(value)


def test_non_accepted_external_suggestion_cannot_carry_repair_handoff():
    value = package("external-review-valid")
    value["external_review_intake"]["suggestions"][0]["triage_decision"] = "rejected"
    assert "PRI-EXT-006" in codes(value)
