from __future__ import annotations

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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest() -> dict:
    return yaml.safe_load((ROOT / "protocol-manifest.yaml").read_text(encoding="utf-8"))


def _parse_lock(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line or line.startswith("#"):
            continue
        separator = line.find("  ")
        assert separator >= 0, f"{path}:{number}: missing exact double-space separator"
        digest = line[:separator]
        relative = line[separator + 2 :]
        assert SHA256_RE.fullmatch(digest), f"{path}:{number}: invalid digest"
        assert relative and relative == relative.strip(), f"{path}:{number}: invalid path"
        assert relative not in entries, f"{path}:{number}: duplicate path"
        entries[relative] = digest
    return entries


def _workflow(path: Path) -> dict:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    assert value.get("permissions") == {"contents": "read"}
    assert isinstance(value.get("jobs"), dict)
    return value


def test_active_version_metadata_and_load_order_are_aligned():
    current = (ROOT / "CURRENT_VERSION").read_text(encoding="utf-8").strip()
    manifest = _manifest()
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    version_match = re.search(r'(?ms)^\[project\].*?^version\s*=\s*"([^"]+)"', pyproject)

    assert current == "v1.11.1"
    assert manifest["active_version"] == current
    assert manifest["status"] == "active"
    assert manifest["release_lock"] == "release-locks/v1.11.1.sha256"
    assert manifest["canonical_contract"].startswith("protocols/v1.11.1/")
    assert manifest["canonical_schema"].startswith("protocols/v1.11.1/")
    assert len(manifest["load_order"]) == 24
    assert len(manifest["load_order"]) == len(set(manifest["load_order"]))
    assert all(path.startswith("protocols/v1.11.1/") for path in manifest["load_order"])
    assert all((ROOT / path).is_file() for path in manifest["load_order"])
    assert version_match and version_match.group(1) == "1.11.1"
    assert pr_inspector.__version__ == "1.11.1"
    assert "## Active protocol" in readme and "`v1.11.1`" in readme


def test_v1_11_1_status_document_is_explicit_and_truthful():
    status = (ROOT / "docs/CANONICAL_OUTPUT_ENFORCEMENT.md").read_text(encoding="utf-8")
    required = (
        "active_protocol: v1.11.1",
        "implementation_state: v1.11.1_output_authority_consolidation_pending_independent_review",
        "canonical_output_boundary: implemented",
        "verified_byte_snapshot_accessors: implemented",
        "candidate_pre_package_compatibility: implemented",
        "candidate_independent_output_authority: removed",
        "prompt_semantic_completeness: implemented",
        "repository_settings_enforcement: insufficient_evidence",
        "closure_pr_review_state: pending_independent_review",
        "live_review_thread_state: not_asserted_by_static_document",
        "bot_commented_feedback: not_approval",
    )
    for statement in required:
        assert statement in status
    assert "does not claim it is independently reviewed, approved, merge-authorized, or merged" in status
    assert "actual external orchestration execution remains separately verifiable evidence" in status


def test_active_and_historical_release_locks_match_exact_bytes():
    manifest = _manifest()
    active_lock = ROOT / manifest["release_lock"]
    active = _parse_lock(active_lock)
    assert set(active) == set(manifest["load_order"])
    for relative, expected in active.items():
        path = ROOT / relative
        assert path.is_file(), relative
        assert _sha256(path) == expected, relative

    historical_v110 = ROOT / "release-locks/v1.11.0.sha256"
    assert _sha256(historical_v110) == V1_11_0_LOCK_SHA256
    for lock in sorted((ROOT / "release-locks").glob("v*.sha256")):
        entries = _parse_lock(lock)
        assert entries, lock
        for relative, expected in entries.items():
            path = ROOT / relative
            assert path.is_file(), f"{lock.name}: {relative}"
            assert _sha256(path) == expected, f"{lock.name}: {relative}"


def test_active_protocol_versions_and_authority_contract_are_coherent():
    current = "v1.11.1"
    owner_contract = json.loads(
        (ROOT / f"protocols/{current}/policies/OWNER_DELIVERY_CONTRACT.json").read_text(encoding="utf-8")
    )
    trust = json.loads(
        (ROOT / f"protocols/{current}/trust/INSPECTOR_TRUST_POLICY.json").read_text(encoding="utf-8")
    )
    registry = yaml.safe_load(
        (ROOT / f"protocols/{current}/registries/DECISION_REASON_REGISTRY.yaml").read_text(encoding="utf-8")
    )
    contract = (ROOT / f"protocols/{current}/PR_REVIEW_CONTRACT.md").read_text(encoding="utf-8")

    assert owner_contract["protocol_version"] == current
    assert owner_contract["canonical_owner_accessor"] == "official_owner_delivery"
    assert owner_contract["profile_commands_behavior"] == "always_generated_separate_verified_artifact"
    assert trust["protocol_version"] == current
    assert trust["inspector_repository"] == "rezahh107/PR-Inspector"
    assert trust["inspector_repository_id"] == 1288323264
    assert registry["registry_version"] == current
    assert "candidate_reason_domains" not in registry
    assert "one canonical projection authority" in contract.lower()
    assert "official_owner_delivery" in contract
    assert "pre-package compatibility" in contract.lower()


def test_candidate_compatibility_exports_no_independent_output_authority():
    import pr_inspector.candidate_v1_11 as candidate

    source = Path(candidate.__file__).read_text(encoding="utf-8")
    forbidden_exports = {
        "project_decision",
        "render_candidate_owner_result",
        "render_candidate_owner_card",
        "render_candidate_technical_handoff",
        "render_candidate_next_action_prompt",
        "build_candidate_review_artifacts",
        "verify_candidate_review_artifact_bytes",
        "verify_minimal_review_artifact_bytes",
        "build_candidate_owner_delivery_artifacts",
    }
    assert forbidden_exports.isdisjoint(candidate.__all__)
    assert "Repair independently validated technical findings before rereview." not in source
    assert "return raw_owner +" not in source
    for name in forbidden_exports:
        function_source = re.search(
            rf"def {name}\([^\n]*\).*?(?=\n\ndef |\n__all__)",
            source,
            flags=re.S,
        )
        assert function_source, name
        assert "raise _migration_error" in function_source.group(0), name
    assert "return official_owner_delivery(completion).encode" in source


def test_repository_closure_requires_new_output_rules():
    matrix = (
        ROOT / "protocols/v1.11.1/policies/BEHAVIORAL_RULE_COVERAGE.md"
    ).read_text(encoding="utf-8")
    mutations = json.loads(
        (ROOT / "fixtures/behavioral-rules/mutation-cases.json").read_text(encoding="utf-8")
    )
    cases = {item["case_id"]: item for item in mutations["cases"]}
    assert "PRR-PROMPT-SEMANTIC-001" in matrix
    assert "PRR-OUTPUT-AUTHORITY-001" in matrix
    assert cases["generic_prompt_semantically_incomplete"]["rule_id"] == "PRR-PROMPT-SEMANTIC-001"
    assert cases["candidate_output_authority_exposed"]["rule_id"] == "PRR-OUTPUT-AUTHORITY-001"


def test_integration_docs_require_verified_completion_and_official_delivery():
    paths = (
        ROOT / "README.md",
        ROOT / "docs/CANONICAL_OUTPUT_ENFORCEMENT.md",
        ROOT / "protocols/v1.11.1/PR_REVIEW_CONTRACT.md",
        ROOT / "protocols/v1.11.1/policies/OWNER_OUTPUT_UX.md",
        ROOT / "protocols/v1.11.1/pipeline/REVIEW_PIPELINE.md",
    )
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "VerifiedReviewCompletion" in text, path
        assert "official_owner_delivery" in text, path
    combined = "\n".join(path.read_text(encoding="utf-8").lower() for path in paths)
    assert "manual concatenation" in combined
    assert "profile commands" in combined


def test_no_stale_active_candidate_or_branch_era_claims():
    paths = (
        ROOT / "README.md",
        ROOT / "docs/CANONICAL_OUTPUT_ENFORCEMENT.md",
        ROOT / "protocols/v1.11.1/PR_REVIEW_CONTRACT.md",
        ROOT / "protocols/v1.11.1/policies/DECISION_GATES.md",
        ROOT / "protocols/v1.11.1/policies/CANONICAL_OUTPUT_BEHAVIORAL_RULE_COVERAGE.md",
    )
    forbidden = (
        "candidate v1.11.0 dual inspection profiles (not active)",
        "active protocol is pending activation",
        "default branch is not yet authoritative",
        "implementation_state: implementation_pending",
        "status: candidate implementation boundary",
        "status: implemented on the stacked repair branch",
    )
    for path in paths:
        text = path.read_text(encoding="utf-8").lower()
        for phrase in forbidden:
            assert phrase not in text, f"{path.relative_to(ROOT)}: {phrase}"


def test_no_temporary_repair_or_generated_residue_is_committed():
    excluded = {".git", ".pytest_cache", "__pycache__", ".venv"}
    forbidden_names = {
        "generate_post_merge_polish.py",
        "apply-bounded-governance-repair.yml",
        "apply-pr14-final.yml",
        "export-current-snapshot.yml",
        "pr18-readonly-export.yml",
        "tmp-connector-capability-check.txt",
    }
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if any(part in excluded for part in relative.parts):
            continue
        assert ".repair" not in relative.parts
        if path.is_file():
            assert path.name not in forbidden_names, relative
            assert not path.name.endswith((".pyc", ".pyo")), relative
            assert not path.match("payload-*.b64"), relative
            assert not path.match("chunk-*.b64"), relative


def test_permanent_workflows_are_read_only_pinned_and_non_self_modifying():
    workflows = sorted((ROOT / ".github/workflows").glob("*.y*ml"))
    assert workflows
    checkout_count = 0
    forbidden_tokens = ("exec(", "compile(", "base64 -d", "base64 --decode", "marshal.loads", "zlib.decompress")
    for path in workflows:
        raw = path.read_text(encoding="utf-8")
        value = _workflow(path)
        for token in forbidden_tokens:
            assert token not in raw, f"{path.name}: {token}"
        for job in value["jobs"].values():
            assert isinstance(job, dict)
            for step in job.get("steps", []):
                assert isinstance(step, dict)
                action = step.get("uses")
                if not action or action.startswith("./"):
                    continue
                assert FULL_ACTION_SHA.fullmatch(action), f"{path.name}: {action}"
                if action.startswith("actions/checkout@"):
                    checkout_count += 1
                    assert step.get("with", {}).get("persist-credentials") is False
    assert checkout_count


def test_validation_workflow_runs_repository_closure_semantics_and_full_suite():
    workflow = (ROOT / ".github/workflows/validate-repository.yml").read_text(encoding="utf-8")
    required = (
        "python scripts/validate_repository_v2.py",
        "python -m pytest -q tests/test_behavioral_rule_coverage.py",
        "python -m pytest -q tests/test_repository_closure.py",
        "python -m pytest -q tests/test_canonical_output_enforcement.py",
        "python -m pytest -q tests/test_canonical_output_atomicity.py",
        "python -m pytest",
    )
    for command in required:
        assert command in workflow
