from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path

import yaml

import pr_inspector

ROOT = Path(__file__).resolve().parents[1]
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
FULL_ACTION_SHA = re.compile(r"^[^@\s]+@[0-9a-f]{40}$")
V1_11_0_LOCK_SHA256 = "9f3b2ec664011c5e54b3af2a34f5db3d11b09ca0be3dad2dfdb82a6d32eefc99"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest() -> dict:
    value = yaml.safe_load((ROOT / "protocol-manifest.yaml").read_text(encoding="utf-8")); assert isinstance(value, dict); return value


def _parse_lock(path: Path) -> dict[str, str]:
    entries = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line or line.startswith("#"): continue
        separator = line.find("  "); assert separator >= 0, f"{path}:{number}: malformed"
        digest, relative = line[:separator], line[separator + 2:]
        assert SHA256_RE.fullmatch(digest); assert relative and relative not in entries
        entries[relative] = digest
    return entries


def test_active_version_metadata_and_load_order_are_aligned():
    current = (ROOT / "CURRENT_VERSION").read_text(encoding="utf-8").strip()
    manifest = _manifest(); pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    version = re.search(r'(?ms)^\[project\].*?^version\s*=\s*"([^"]+)"', pyproject)
    assert current == "v1.13.1"
    assert manifest["active_version"] == current and manifest["status"] == "active"
    assert manifest["canonical_contract"] == "protocols/v1.13.1/functional-runtime-contract.json"
    assert manifest["runtime_bootstrap_inputs"] == [
        "CURRENT_VERSION",
        "protocols/v1.13.1/functional-runtime-contract.json",
        "protocols/v1.13.1/prompts/INTAKE_RESPONSE.fa.md",
    ]
    assert version and version.group(1) == "1.13.1"
    assert pr_inspector.__version__ == "1.13.1"


def test_historical_release_locks_match_exact_bytes():
    historical = ROOT / "release-locks/v1.11.0.sha256"
    assert _sha(historical) == V1_11_0_LOCK_SHA256
    for lock in sorted((ROOT / "release-locks").glob("v*.sha256")):
        for relative, expected in _parse_lock(lock).items():
            assert (ROOT / relative).is_file(); assert _sha(ROOT / relative) == expected


def test_functional_contract_and_owner_authority_are_coherent():
    contract = json.loads((ROOT / "protocols/v1.13.1/functional-runtime-contract.json").read_text(encoding="utf-8"))
    owner = json.loads((ROOT / "protocols/v1.13.1/policies/OWNER_DELIVERY_CONTRACT.json").read_text(encoding="utf-8"))
    registry = yaml.safe_load((ROOT / "protocols/v1.13.1/registries/DECISION_REASON_REGISTRY.yaml").read_text(encoding="utf-8"))
    assert contract["protocol"]["version"] == "v1.13.1"
    assert contract["protocol"]["authority"] == "functional_contract_ssot"
    assert len(contract["functional_rules"]) == 43
    assert owner["protocol_version"] == "v1.13.1"
    assert owner["canonical_owner_accessor"] == "official_owner_delivery"
    assert registry["registry_version"] == "v1.13.1"


def test_candidate_compatibility_exports_no_independent_output_authority():
    import pr_inspector.candidate_v1_11 as candidate
    source = Path(candidate.__file__).read_text(encoding="utf-8")
    forbidden = {"project_decision", "render_candidate_owner_result", "render_candidate_owner_card", "render_candidate_technical_handoff", "render_candidate_next_action_prompt", "build_candidate_review_artifacts"}
    assert forbidden.isdisjoint(candidate.__all__)
    for name in forbidden:
        match = re.search(rf"def {name}\([^\n]*\).*?(?=\n\ndef |\n__all__)", source, flags=re.S)
        assert match and "raise _migration_error" in match.group(0)


def test_v1_13_authority_rules_are_behaviorally_closed():
    matrix = (ROOT / "protocols/v1.13.1/policies/BEHAVIORAL_RULE_COVERAGE.md").read_text(encoding="utf-8")
    mutations = json.loads((ROOT / "fixtures/behavioral-rules/mutation-cases.json").read_text(encoding="utf-8"))
    mutation_rules = {item["rule_id"] for item in mutations["cases"]}
    required = {"PRR-AUTH-PACKAGE-BOUNDARY-001", "PRR-AUTH-EVIDENCE-COMPLETENESS-001", "PRR-AUTH-CLAIM-COMPATIBILITY-001", "PRR-AUTH-DERIVED-FACTS-001", "PRR-AUTH-HUMAN-JUDGMENT-001", "PRR-AUTH-PREVIEW-ISOLATION-001", "PRR-AUTH-REVERIFY-BOUNDARY-001", "PRR-AUTH-EXTERNAL-RECONCILIATION-001"}
    assert required <= mutation_rules
    assert all(rule in matrix for rule in required)


def test_no_temporary_repair_or_generated_residue_is_committed():
    excluded = {".git", ".pytest_cache", "__pycache__", ".venv"}
    forbidden_names = {"generate_post_merge_polish.py", "apply-bounded-governance-repair.yml", "tmp-connector-capability-check.txt"}
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if any(part in excluded for part in relative.parts): continue
        assert ".repair" not in relative.parts
        if path.is_file():
            assert path.name not in forbidden_names
            assert not path.name.endswith((".pyc", ".pyo"))


def test_permanent_workflows_are_read_only_pinned_and_non_self_modifying():
    checkout_count = 0
    forbidden_tokens = ("exec(", "compile(", "base64 -d", "base64 --decode", "marshal.loads", "zlib.decompress")
    for path in sorted((ROOT / ".github/workflows").glob("*.y*ml")):
        raw = path.read_text(encoding="utf-8"); value = yaml.safe_load(raw)
        assert value.get("permissions") == {"contents": "read"}
        assert all(token not in raw for token in forbidden_tokens)
        for job in value["jobs"].values():
            for step in job.get("steps", []):
                action = step.get("uses")
                if not action or action.startswith("./"): continue
                assert FULL_ACTION_SHA.fullmatch(action)
                if action.startswith("actions/checkout@"):
                    checkout_count += 1; assert step.get("with", {}).get("persist-credentials") is False
    assert checkout_count


def test_validation_workflow_runs_runtime_planning_and_full_regression():
    workflow = (ROOT / ".github/workflows/validate-repository.yml").read_text(encoding="utf-8")
    required = ("python scripts/validate_runtime_contract.py", "python scripts/validate_repository_v2.py", "python scripts/validate_planning_governance.py --check-static", "tests/test_v1_13_verified_review_authority.py", "tests/test_repository_closure.py", "python -m pytest")
    assert all(command in workflow for command in required)


def test_operational_github_receipt_factory_is_closure_bound():
    path = ROOT / "pr_inspector/_governance_transport.py"
    source = path.read_text(encoding="utf-8"); tree = ast.parse(source)
    functions = {node.name: node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    assert "_mint_operational_response" not in functions
    assert "_build_operational_response_boundary" in functions and "_mint_response" in functions
    assert "transport_origin" not in {a.arg for a in (*functions["_mint_response"].args.args, *functions["_mint_response"].args.kwonlyargs)}
