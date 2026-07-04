import json
from pathlib import Path

from pr_inspector.validation_v2 import validate_package

ROOT = Path(__file__).resolve().parents[1]


def package(name="golden-green"):
    return json.loads((ROOT / "fixtures" / name / "review-package.json").read_text(encoding="utf-8"))


def codes(value):
    return sorted(item.code for item in validate_package(value))


def test_golden_package_is_valid():
    assert validate_package(package()) == []


def test_intent_fit_valid_satisfied_fixture_is_valid():
    assert validate_package(package("intent-fit-valid-satisfied")) == []


def test_intent_fit_missing_blocks_green_claim():
    diagnostics = codes(package("intent-fit-invalid-missing"))
    assert "PRI-INTENT-001" in diagnostics
    assert "PRI-STATUS-001" in diagnostics


def test_intent_fit_satisfied_requires_supported_evidence():
    assert "PRI-INTENT-002" in codes(package("intent-fit-invalid-hypothesis-only"))


def test_missing_intent_can_be_not_assessable_without_claiming_satisfaction():
    assert validate_package(package("intent-fit-valid-not-assessable")) == []


def test_stale_green_is_rejected():
    value = package()
    value["review_identity"]["review_validity"] = "STALE"
    assert codes(value) == ["PRI-STALE-001", "PRI-STATUS-001"]


def test_current_requires_exact_head_sha():
    value = package()
    value["review_identity"]["reviewed_head_sha"] = "UNKNOWN"
    value["evidence_records"][0]["reviewed_head_sha"] = "UNKNOWN"
    value["evidence_records"][1]["reviewed_head_sha"] = "UNKNOWN"
    assert codes(value) == ["PRI-SHA-001"]
