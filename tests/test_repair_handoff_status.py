import json
from pathlib import Path

from pr_inspector.validation_v2 import validate_package

ROOT = Path(__file__).resolve().parents[1]


def package(name="repair-handoff-valid"):
    return json.loads((ROOT / "fixtures" / name / "review-package.json").read_text(encoding="utf-8"))


def codes(value):
    return sorted(item.code for item in validate_package(value))


def test_repair_handoff_blocks_green_even_for_non_blocking_low_finding():
    value = package("repair-handoff-valid")
    value["findings"][0]["severity"] = "LOW"
    value["findings"][0]["blocking"] = False
    value["decision"]["blocking_findings_count"] = 0
    value["decision"]["technical_status"] = "GREEN_TECHNICALLY_READY"
    value["decision"]["next_required_action"] = "Merge after normal owner confirmation."
    assert codes(value) == ["PRI-STATUS-001"]


def test_accepted_external_suggestion_blocks_green_even_when_linked_finding_is_low_non_blocking():
    value = package("external-review-valid")
    value["findings"][0]["severity"] = "LOW"
    value["findings"][0]["blocking"] = False
    value["decision"]["blocking_findings_count"] = 0
    value["decision"]["technical_status"] = "GREEN_TECHNICALLY_READY"
    value["decision"]["next_required_action"] = "Merge after normal owner confirmation."
    assert codes(value) == ["PRI-STATUS-001"]
