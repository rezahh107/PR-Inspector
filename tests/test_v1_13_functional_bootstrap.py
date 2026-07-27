from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from pr_inspector.functional_runtime import (
    CI_WORKFLOW_PATH,
    CONTRACT_PATH,
    CONTRACT_SCHEMA_PATH,
    ENTRYPOINT,
    PYPROJECT_PATH,
    RUNTIME_BOOTSTRAP_INPUTS,
    FunctionalBootstrapError,
    _derived_integrity_inventory,
    _runtime_digest,
    connector_startup,
    load_json_strict,
    resolve_rules,
    validate_runtime_contract,
)

ROOT = Path(__file__).resolve().parents[1]


def _connector_files() -> dict[str, str]:
    return {
        "CURRENT_VERSION": "v1.13.1\n",
        CONTRACT_PATH: (ROOT / CONTRACT_PATH).read_text(encoding="utf-8"),
        "protocols/v1.13.1/prompts/INTAKE_RESPONSE.fa.md": (
            ROOT / "protocols/v1.13.1/prompts/INTAKE_RESPONSE.fa.md"
        ).read_text(encoding="utf-8"),
    }


def test_connector_only_positive_read_boundary(monkeypatch):
    files = _connector_files()
    reads = []
    forbidden = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("local operation"))
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(Path, "rglob", forbidden)
    result = connector_startup(lambda path: reads.append(path) or files[path])
    assert reads == list(RUNTIME_BOOTSTRAP_INPUTS)
    assert result.reads == RUNTIME_BOOTSTRAP_INPUTS
    assert result.protocol_version == "v1.13.1" and result.intake_response.strip()


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        ("wrong_version", "103"), ("duplicate_key", "101"),
        ("non_object", "101"), ("wrong_repository", "103"),
        ("cross_version_reference", "104"), ("traversal_reference", "104"),
        ("missing_rule", "105"), ("empty_intake", "111"),
    ],
)
def test_connector_startup_invalid_mutation_matrix(mutation, code):
    files = _connector_files()
    if mutation == "wrong_version":
        files["CURRENT_VERSION"] = "v1.13.0\n"
    elif mutation == "duplicate_key":
        files[CONTRACT_PATH] = '{"schema_version":2,"schema_version":2}'
    elif mutation == "non_object":
        files[CONTRACT_PATH] = "[]"
    elif mutation == "empty_intake":
        files["protocols/v1.13.1/prompts/INTAKE_RESPONSE.fa.md"] = " \n"
    else:
        contract = json.loads(files[CONTRACT_PATH])
        if mutation == "wrong_repository": contract["protocol"]["inspector_repository"] = "wrong/repo"
        elif mutation == "cross_version_reference": contract["references"]["pipeline_view"] = "protocols/v1.13.0/pipeline/REVIEW_PIPELINE.md"
        elif mutation == "traversal_reference": contract["references"]["pipeline_view"] = "protocols/v1.13.1/../pipeline.md"
        elif mutation == "missing_rule": contract["functional_rules"].pop()
        files[CONTRACT_PATH] = json.dumps(contract)
    with pytest.raises(FunctionalBootstrapError, match=f"PRI-FUNCTIONAL-BOOTSTRAP-{code}"):
        connector_startup(lambda path: files[path])


def test_schema_rejects_cross_version_reference(tmp_path):
    root = _copy_repo(tmp_path)
    contract_path = root / CONTRACT_PATH
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["references"]["pipeline_view"] = (
        "protocols/v1.13.0/pipeline/REVIEW_PIPELINE.md"
    )
    contract_path.write_text(json.dumps(contract), encoding="utf-8")
    with pytest.raises(FunctionalBootstrapError, match="PRI-FUNCTIONAL-BOOTSTRAP-003"):
        validate_runtime_contract(root, require_git=False)
SCRIPT_SOURCES = tuple(
    sorted(
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "scripts").rglob("*.py")
    )
)
KNOWN_SCRIPT_CARRIERS = {
    "scripts/record_ci_identity.py",
    "scripts/validate_planning_governance.py",
    "scripts/validate_repository.py",
    "scripts/validate_repository_v2.py",
    "scripts/validate_runtime_contract.py",
}


def _copy_repo(tmp_path: Path) -> Path:
    destination = tmp_path / "repo"
    shutil.copytree(
        ROOT,
        destination,
        ignore=shutil.ignore_patterns(
            ".git",
            ".venv",
            ".pytest_cache",
            "__pycache__",
            "*.pyc",
        ),
    )
    return destination


def _manifest(root: Path) -> dict:
    value = yaml.safe_load(
        (root / "protocol-manifest.yaml").read_text(encoding="utf-8")
    )
    assert isinstance(value, dict)
    return value


def _write_manifest(root: Path, value: dict) -> None:
    (root / "protocol-manifest.yaml").write_text(
        yaml.safe_dump(value, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _reconcile_runtime(root: Path) -> tuple[str, ...]:
    raw = load_json_strict(root / CONTRACT_PATH)
    rules = resolve_rules(raw)
    inventory = _derived_integrity_inventory(root, raw, rules)
    manifest = _manifest(root)
    manifest["functional_digest_paths"] = list(inventory)
    manifest["functional_runtime_sha256"] = _runtime_digest(root, inventory)
    _write_manifest(root, manifest)
    return inventory


def _init_git(root: Path) -> str:
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "runtime@example.invalid"],
        cwd=root,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Runtime Test"],
        cwd=root,
        check=True,
    )
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-m", "baseline"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


def _commit(root: Path, relative: str, message: str) -> None:
    subprocess.run(["git", "add", relative], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=root,
        check=True,
        capture_output=True,
    )


def test_clean_runtime_contract_is_valid_and_offline(monkeypatch):
    import urllib.request

    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("network access is forbidden")
        ),
    )
    value = validate_runtime_contract(ROOT)
    assert value.protocol_version == "v1.13.1"
    assert len(value.functional_runtime_sha256) == 64


def test_manifest_uses_canonical_bootstrap_identity():
    manifest = _manifest(ROOT)
    assert manifest["entrypoint"] == ENTRYPOINT
    assert manifest["active_version"] == "v1.13.1"
    assert manifest["functional_runtime_contract"] == CONTRACT_PATH
    assert manifest["functional_runtime_schema"] == CONTRACT_SCHEMA_PATH
    assert manifest["runtime_bootstrap_inputs"] == list(
        RUNTIME_BOOTSTRAP_INPUTS
    )


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("entrypoint", "README.md"),
        ("active_version", "v1.12.0"),
        ("functional_runtime_contract", "alternate.json"),
        ("functional_runtime_schema", "alternate.schema.json"),
    ],
)
def test_manifest_canonical_repointing_fails_closed(
    tmp_path: Path,
    field: str,
    replacement: str,
):
    root = _copy_repo(tmp_path)
    manifest = _manifest(root)
    manifest[field] = replacement
    _write_manifest(root, manifest)
    with pytest.raises(
        FunctionalBootstrapError,
        match="PRI-FUNCTIONAL-BOOTSTRAP-002",
    ):
        validate_runtime_contract(root, require_git=False)


@pytest.mark.parametrize(
    "mutation",
    ["missing", "extra", "duplicate", "reordered", "alias", "nonexistent"],
)
def test_manifest_cannot_distort_derived_inventory(
    tmp_path: Path,
    mutation: str,
):
    root = _copy_repo(tmp_path)
    inventory = list(_reconcile_runtime(root))
    if mutation == "missing":
        inventory.pop()
    elif mutation == "extra":
        inventory.append("README.md")
    elif mutation == "duplicate":
        inventory.append(inventory[-1])
    elif mutation == "reordered":
        inventory[0], inventory[1] = inventory[1], inventory[0]
    elif mutation == "alias":
        inventory[0] = "./" + inventory[0]
    else:
        inventory.append("pr_inspector/does_not_exist.py")
    manifest = _manifest(root)
    manifest["functional_digest_paths"] = inventory
    _write_manifest(root, manifest)
    with pytest.raises(
        FunctionalBootstrapError,
        match="PRI-FUNCTIONAL-BOOTSTRAP-006",
    ):
        validate_runtime_contract(root, require_git=False)


@pytest.mark.parametrize(
    "relative",
    ["pr_inspector/official_review.py", "scripts/validate_repository.py"],
)
def test_symlinked_authority_carrier_fails_closed(
    tmp_path: Path,
    relative: str,
):
    root = _copy_repo(tmp_path)
    target = root / relative
    backup = root / (relative.replace("/", "_") + ".real.py")
    target.replace(backup)
    try:
        target.symlink_to(backup)
    except OSError as exc:
        pytest.skip(f"symlink unavailable: {exc}")
    with pytest.raises(
        FunctionalBootstrapError,
        match="PRI-FUNCTIONAL-BOOTSTRAP-004",
    ):
        validate_runtime_contract(root, require_git=False)


@pytest.mark.parametrize(
    "relative",
    [
        "pr_inspector/official_review.py",
        "pr_inspector/verified_review.py",
        "pr_inspector/validation_v2.py",
        "pr_inspector/decision_projection.py",
        "pr_inspector/owner_delivery.py",
    ],
)
def test_runtime_module_mutation_breaks_runtime_digest(
    tmp_path: Path,
    relative: str,
):
    root = _copy_repo(tmp_path)
    _reconcile_runtime(root)
    path = root / relative
    path.write_text(
        path.read_text(encoding="utf-8") + "\n# unreconciled drift\n",
        encoding="utf-8",
    )
    with pytest.raises(
        FunctionalBootstrapError,
        match="PRI-FUNCTIONAL-BOOTSTRAP-006",
    ):
        validate_runtime_contract(root, require_git=False)


@pytest.mark.parametrize("relative", SCRIPT_SOURCES)
def test_every_script_mutation_breaks_runtime_digest(
    tmp_path: Path,
    relative: str,
):
    root = _copy_repo(tmp_path)
    _reconcile_runtime(root)
    _init_git(root)
    path = root / relative
    path.write_text(
        path.read_text(encoding="utf-8") + "\n# unreconciled script drift\n",
        encoding="utf-8",
    )
    _commit(root, relative, "mutate script authority")
    with pytest.raises(
        FunctionalBootstrapError,
        match="PRI-FUNCTIONAL-BOOTSTRAP-006",
    ):
        validate_runtime_contract(root)


def test_required_script_carriers_are_present():
    assert KNOWN_SCRIPT_CARRIERS <= set(SCRIPT_SOURCES)
    assert len(SCRIPT_SOURCES) > len(KNOWN_SCRIPT_CARRIERS)


@pytest.mark.parametrize(
    "relative",
    ["pr_inspector/new_runtime.py", "scripts/new_validator.py"],
)
def test_untracked_new_authority_carrier_cannot_escape_inventory(
    tmp_path: Path,
    relative: str,
):
    root = _copy_repo(tmp_path)
    _reconcile_runtime(root)
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("AUTHORITY = True\n", encoding="utf-8")
    with pytest.raises(
        FunctionalBootstrapError,
        match="PRI-FUNCTIONAL-BOOTSTRAP-006",
    ):
        validate_runtime_contract(root, require_git=False)


def test_pyproject_mutation_breaks_runtime_digest(tmp_path: Path):
    root = _copy_repo(tmp_path)
    _reconcile_runtime(root)
    _init_git(root)
    path = root / PYPROJECT_PATH
    path.write_text(
        path.read_text(encoding="utf-8") + "\n# unreconciled environment drift\n",
        encoding="utf-8",
    )
    _commit(root, PYPROJECT_PATH, "mutate execution environment")
    with pytest.raises(
        FunctionalBootstrapError,
        match="PRI-FUNCTIONAL-BOOTSTRAP-006",
    ):
        validate_runtime_contract(root)


def test_untracked_alternate_contract_repoint_is_rejected(tmp_path: Path):
    root = _copy_repo(tmp_path)
    (root / "alternate.json").write_text("{}\n", encoding="utf-8")
    manifest = _manifest(root)
    manifest["functional_runtime_contract"] = "alternate.json"
    _write_manifest(root, manifest)
    with pytest.raises(
        FunctionalBootstrapError,
        match="PRI-FUNCTIONAL-BOOTSTRAP-002",
    ):
        validate_runtime_contract(root, require_git=False)


def test_contract_hash_is_exact_file_hash():
    manifest = _manifest(ROOT)
    observed = hashlib.sha256((ROOT / CONTRACT_PATH).read_bytes()).hexdigest()
    assert observed == manifest["functional_contract_sha256"]


def test_derived_inventory_covers_complete_execution_authority():
    raw = load_json_strict(ROOT / CONTRACT_PATH)
    inventory = set(
        _derived_integrity_inventory(ROOT, raw, resolve_rules(raw))
    )
    package_sources = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "pr_inspector").rglob("*.py")
    }
    script_sources = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "scripts").rglob("*.py")
    }
    assert package_sources <= inventory
    assert script_sources <= inventory
    assert set(raw["references"].values()) <= inventory
    assert PYPROJECT_PATH in inventory
    assert ENTRYPOINT in inventory
    assert "CURRENT_VERSION" in inventory
    assert CI_WORKFLOW_PATH in inventory
    assert "protocol-manifest.yaml" not in inventory


def test_checkout_identity_and_runtime_acceptance_are_not_conflated(
    tmp_path: Path,
):
    root = _copy_repo(tmp_path)
    _reconcile_runtime(root)
    reference = _init_git(root)
    baseline = validate_runtime_contract(root)
    assert baseline.inspector_commit_sha == reference

    outside = root / "docs/non_runtime_control.txt"
    outside.parent.mkdir(exist_ok=True)
    outside.write_text("outside runtime authority\n", encoding="utf-8")
    _commit(root, outside.relative_to(root).as_posix(), "outside runtime")
    later = validate_runtime_contract(root)
    assert later.inspector_commit_sha != reference
    assert later.functional_runtime_sha256 == baseline.functional_runtime_sha256

    carrier_relative = "scripts/validate_repository.py"
    carrier = root / carrier_relative
    carrier.write_text(
        carrier.read_text(encoding="utf-8") + "\n# changed authority\n",
        encoding="utf-8",
    )
    _commit(root, carrier_relative, "unreconciled authority")
    with pytest.raises(
        FunctionalBootstrapError,
        match="PRI-FUNCTIONAL-BOOTSTRAP-006",
    ):
        validate_runtime_contract(root)


def test_dirty_manifest_control_fails_production_identity(tmp_path: Path):
    root = _copy_repo(tmp_path)
    _reconcile_runtime(root)
    _init_git(root)
    manifest = root / "protocol-manifest.yaml"
    manifest.write_text(
        manifest.read_text(encoding="utf-8") + "\n# dirty\n",
        encoding="utf-8",
    )
    with pytest.raises(
        FunctionalBootstrapError,
        match="PRI-FUNCTIONAL-BOOTSTRAP-009",
    ):
        validate_runtime_contract(root)
