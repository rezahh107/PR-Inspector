from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest
import yaml

from pr_inspector.functional_runtime import (
    FunctionalBootstrapError,
    load_json_strict,
    validate_runtime_contract,
)

ROOT = Path(__file__).resolve().parents[1]


def test_runtime_contract_is_valid_without_network(monkeypatch):
    import urllib.request

    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network")),
    )
    value = validate_runtime_contract(ROOT)
    assert value.protocol_version == "v1.13.0"
    assert len(value.functional_runtime_sha256) == 64


def test_manifest_declares_compact_bootstrap_and_full_release_sources():
    manifest = yaml.safe_load(
        (ROOT / "protocol-manifest.yaml").read_text(encoding="utf-8")
    )
    assert manifest["runtime_bootstrap_inputs"] == [
        "CURRENT_VERSION",
        "protocol-manifest.yaml",
        "protocols/v1.13.0/functional-runtime-contract.json",
        "protocols/v1.13.0/schemas/functional-runtime-contract.schema.json",
        "protocols/v1.13.0/prompts/INTAKE_RESPONSE.fa.md",
    ]
    forbidden = (
        "trust/INSPECTOR_TRUST_POLICY.json",
        "release-locks/",
        "protocols/v1.12.0/",
    )
    assert not any(
        token in path
        for path in manifest["runtime_bootstrap_inputs"]
        for token in forbidden
    )
    assert len(manifest["release_validation_sources"]) > len(
        manifest["runtime_bootstrap_inputs"]
    )


def test_contract_rule_registry_is_one_to_one_and_executable():
    contract = load_json_strict(
        ROOT / "protocols/v1.13.0/functional-runtime-contract.json"
    )
    ids = [item["rule_id"] for item in contract["functional_rules"]]
    validators = [item["validator"] for item in contract["functional_rules"]]
    positive = [item["positive_control"] for item in contract["functional_rules"]]
    negative = [item["negative_mutation"] for item in contract["functional_rules"]]
    assert len(ids) == len(set(ids)) == 43
    assert all(validators)
    assert all(positive)
    assert len(negative) == len(set(negative))
    assert all(item["ci_command"] for item in contract["functional_rules"])
    assert all(item["recovery_action"] for item in contract["functional_rules"])


def test_duplicate_keys_fail_closed(tmp_path):
    path = tmp_path / "duplicate.json"
    path.write_text('{"a":1,"a":2}', encoding="utf-8")
    with pytest.raises(
        FunctionalBootstrapError, match="PRI-FUNCTIONAL-BOOTSTRAP-001"
    ):
        load_json_strict(path)


def _copy_runtime_repo(tmp_path: Path) -> Path:
    destination = tmp_path / "repo"
    shutil.copytree(
        ROOT,
        destination,
        ignore=shutil.ignore_patterns(".git", ".venv", ".pytest_cache", "__pycache__"),
    )
    return destination


def _manifest(root: Path) -> dict:
    return yaml.safe_load((root / "protocol-manifest.yaml").read_text(encoding="utf-8"))


def _write_manifest(root: Path, value: dict) -> None:
    (root / "protocol-manifest.yaml").write_text(
        yaml.safe_dump(value, sort_keys=False), encoding="utf-8"
    )


def test_malformed_contract_fails_closed_without_fallback(tmp_path):
    root = _copy_runtime_repo(tmp_path)
    path = root / "protocols/v1.13.0/functional-runtime-contract.json"
    path.write_text('{"schema_version":1,"schema_version":2}', encoding="utf-8")
    with pytest.raises(
        FunctionalBootstrapError, match="PRI-FUNCTIONAL-BOOTSTRAP-001"
    ):
        validate_runtime_contract(root, require_git=False)


def test_version_mismatch_fails_closed_without_fallback(tmp_path):
    root = _copy_runtime_repo(tmp_path)
    (root / "CURRENT_VERSION").write_text("v9.9.9\n", encoding="utf-8")
    with pytest.raises(
        FunctionalBootstrapError, match="PRI-FUNCTIONAL-BOOTSTRAP-002"
    ):
        validate_runtime_contract(root, require_git=False)


def test_missing_reference_fails_closed_without_fallback(tmp_path):
    root = _copy_runtime_repo(tmp_path)
    contract = load_json_strict(
        root / "protocols/v1.13.0/functional-runtime-contract.json"
    )
    missing = root / contract["references"]["reason_registry"]
    missing.unlink()
    with pytest.raises(
        FunctionalBootstrapError, match="PRI-FUNCTIONAL-BOOTSTRAP-004"
    ):
        validate_runtime_contract(root, require_git=False)


def test_contract_digest_drift_fails_closed_without_fallback(tmp_path):
    root = _copy_runtime_repo(tmp_path)
    path = root / "protocols/v1.13.0/functional-runtime-contract.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    value["model_bootstrap"]["instructions"].append("drift")
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(
        FunctionalBootstrapError, match="PRI-FUNCTIONAL-BOOTSTRAP-006"
    ):
        validate_runtime_contract(root, require_git=False)


def test_runtime_digest_drift_fails_closed_without_fallback(tmp_path):
    root = _copy_runtime_repo(tmp_path)
    path = root / "pr_inspector/functional_review.py"
    path.write_text(path.read_text(encoding="utf-8") + "\n# drift\n", encoding="utf-8")
    with pytest.raises(
        FunctionalBootstrapError, match="PRI-FUNCTIONAL-BOOTSTRAP-006"
    ):
        validate_runtime_contract(root, require_git=False)


def test_manifest_contract_digest_is_exact_file_hash():
    manifest = _manifest(ROOT)
    path = ROOT / manifest["functional_runtime_contract"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest[
        "functional_contract_sha256"
    ]
