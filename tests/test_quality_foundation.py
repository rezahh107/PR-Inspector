from pathlib import Path

from pr_inspector.repository import validate_quality_foundation

ROOT = Path(__file__).resolve().parents[1]
QUALITY_DOC = ROOT / "docs/QUALITY_ATTRIBUTE_MODEL.md"
SEED_RULES = [
    "COR-INTENT-001",
    "COR-REG-001",
    "COR-STATE-001",
    "COR-TEST-001",
    "COR-RESEARCH-001",
]


def test_quality_foundation_is_guarded_non_canonical_reference():
    text = QUALITY_DOC.read_text(encoding="utf-8")
    assert "non-canonical planning reference" in text
    assert "If this document conflicts with the active protocol, the active protocol wins." in text
    assert "No active protocol behavior is changed" in text
    for rule_id in SEED_RULES:
        assert rule_id in text


def test_quality_foundation_validator_accepts_current_document():
    assert validate_quality_foundation(ROOT, []) == []


def test_quality_foundation_validator_rejects_manifest_promotion_without_protocol_versioning():
    diagnostics = validate_quality_foundation(ROOT, ["docs/QUALITY_ATTRIBUTE_MODEL.md"])
    assert [item.code for item in diagnostics] == ["PRI-QUAL-002"]
