import json
from pathlib import Path

from pr_inspector.validation_v2 import validate_package

ROOT = Path(__file__).resolve().parents[1]


def test_credential_access_requires_domain_specialist():
    package = json.loads((ROOT / "fixtures/golden-green/review-package.json").read_text(encoding="utf-8"))
    package["decision"]["risk_classification"] = "SENSITIVE"
    package["decision"]["sensitive_domains"] = ["CREDENTIAL_ACCESS"]
    package["decision"]["approval_requirement"] = "HUMAN_TECHNICAL_REVIEW_REQUIRED"
    assert [item.code for item in validate_package(package)] == ["PRI-SENS-002"]
