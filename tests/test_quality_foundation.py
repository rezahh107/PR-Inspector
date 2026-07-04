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
BOUNDARY_PHRASES = [
    "Status: repository-required planning infrastructure.",
    "It is not part of the active protocol `load_order`.",
    "It defines no active review rule.",
    "Its seed rules are planning-only until promoted through a new protocol snapshot, schema/validator/fixture, and release lock.",
    "Repository validation protects this document from deletion/drift and prevents accidental promotion into the active protocol `load_order`.",
    "Validation does not make this document part of the active protocol and does not make the seed rules active review rules.",
    "No active protocol behavior is changed",
]


def test_quality_foundation_has_explicit_repository_planning_boundary():
    text = QUALITY_DOC.read_text(encoding="utf-8")
    for phrase in BOUNDARY_PHRASES:
        assert phrase in text
    for rule_id in SEED_RULES:
        assert rule_id in text


def test_quality_foundation_validator_accepts_current_document():
    assert validate_quality_foundation(ROOT, []) == []


def test_quality_foundation_validator_rejects_manifest_promotion_without_protocol_versioning():
    diagnostics = validate_quality_foundation(ROOT, ["docs/QUALITY_ATTRIBUTE_MODEL.md"])
    assert [item.code for item in diagnostics] == ["PRI-QUAL-002"]
