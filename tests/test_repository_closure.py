import hashlib
import re
from pathlib import Path

import yaml

import pr_inspector

ROOT = Path(__file__).resolve().parents[1]
V18_LOCK_SHA256 = "d4f684a361dff638d823b7e1eb2edf73a3068cc3c1f52eb4ab1fca10fb8a7abd"
FULL_ACTION_SHA = re.compile(r"^[^@\s]+@[0-9a-f]{40}$")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _parse_lock(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        digest, relative_path = line.split("  ", 1)
        entries[relative_path] = digest
    return entries


def _manifest() -> dict:
    return yaml.safe_load((ROOT / "protocol-manifest.yaml").read_text(encoding="utf-8"))


def test_active_version_declarations_and_paths_are_aligned():
    current = (ROOT / "CURRENT_VERSION").read_text(encoding="utf-8").strip()
    manifest = _manifest()
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    project_version_match = re.search(
        r'(?ms)^\[project\].*?^version\s*=\s*"([^"]+)"', pyproject
    )
    assert project_version_match is not None
    project_version = project_version_match.group(1)

    assert current == "v1.9.0"
    assert manifest["active_version"] == current
    assert manifest["status"] == "active"
    assert manifest["release_lock"] == f"release-locks/{current}.sha256"
    assert project_version == current.removeprefix("v")
    assert pr_inspector.__version__ == project_version

    active_section = readme.split("## Active protocol", 1)[1]
    assert f"`{current}`" in active_section
    for relative_path in manifest["load_order"]:
        assert (ROOT / relative_path).is_file(), relative_path


def test_current_status_statement_is_explicit_and_truthful():
    status = (ROOT / "docs/CANONICAL_OUTPUT_ENFORCEMENT.md").read_text(
        encoding="utf-8"
    )
    required = (
        "active_protocol: v1.9.0",
        "implementation_state: merged_on_main",
        "canonical_output_boundary: implemented",
        "publication_commit_point: implemented",
        "verified_byte_snapshot_accessors: implemented",
        "governance_code_boundary: implemented",
        "repository_settings_enforcement: insufficient_evidence",
        "open_implementation_findings: none_confirmed",
        "open_code_findings: []",
        "closure_status: implementation_complete_closure_polish_pending_independent_review",
    )
    for statement in required:
        assert statement in status

    assert "repository settings remain a separate administrative evidence boundary" in status
    assert "independently reviewed, approved, merge-authorized, or merged" in status


def test_active_lifecycle_documents_have_no_branch_era_status_claims():
    current = (ROOT / "CURRENT_VERSION").read_text(encoding="utf-8").strip()
    paths = (
        ROOT / "README.md",
        ROOT / "docs/CANONICAL_OUTPUT_ENFORCEMENT.md",
        ROOT / f"protocols/{current}/PR_REVIEW_CONTRACT.md",
        ROOT / f"protocols/{current}/policies/DECISION_GATES.md",
        ROOT
        / f"protocols/{current}/policies/CANONICAL_OUTPUT_BEHAVIORAL_RULE_COVERAGE.md",
    )
    forbidden = (
        "status: candidate implementation boundary",
        "status: implemented on the stacked repair branch",
        "exact candidate head",
        "candidate pipeline",
        "active v1.8 implementation",
        "pr #13 and this stacked pr remain open and unmerged",
        "active protocol is pending activation",
        "v1.9.0 exists only on a feature branch",
        "default branch is not yet authoritative",
        "implementation_state: implementation_pending",
    )
    for path in paths:
        text = path.read_text(encoding="utf-8").lower()
        for phrase in forbidden:
            assert phrase not in text, f"{path.relative_to(ROOT)}: {phrase}"


def test_active_and_historical_release_locks_match_exact_bytes():
    manifest = _manifest()
    current_lock = ROOT / manifest["release_lock"]
    current_entries = _parse_lock(current_lock)
    assert set(current_entries) == set(manifest["load_order"])

    for relative_path, expected in current_entries.items():
        path = ROOT / relative_path
        assert path.is_file(), relative_path
        assert _sha256(path) == expected, relative_path

    historical_lock = ROOT / "release-locks/v1.8.0.sha256"
    assert _sha256(historical_lock) == V18_LOCK_SHA256
    historical_entries = _parse_lock(historical_lock)
    assert historical_entries
    assert all(path.startswith("protocols/v1.8.0/") for path in historical_entries)
    for relative_path, expected in historical_entries.items():
        path = ROOT / relative_path
        assert path.is_file(), relative_path
        assert _sha256(path) == expected, relative_path


def test_no_temporary_repair_or_encoded_payload_residue_is_committed():
    excluded_parts = {".git", ".pytest_cache", "__pycache__", ".venv"}
    forbidden_names = {
        "generate_post_merge_polish.py",
        "apply-bounded-governance-repair.yml",
        "apply-pr14-final.yml",
        "export-current-snapshot.yml",
    }

    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if any(part in excluded_parts for part in relative.parts):
            continue
        assert ".repair" not in relative.parts, relative
        if path.is_file():
            assert path.name not in forbidden_names, relative
            assert not path.match("payload-*.b64"), relative
            assert not path.match("chunk-*.b64"), relative


def test_permanent_workflows_are_read_only_pinned_and_non_self_modifying():
    workflow_paths = sorted((ROOT / ".github/workflows").glob("*.y*ml"))
    assert workflow_paths
    checkout_steps = []
    forbidden_executable_payload_tokens = (
        "exec(",
        "compile(",
        "base64 -d",
        "base64 --decode",
        "marshal.loads",
        "zlib.decompress",
    )

    for path in workflow_paths:
        raw = path.read_text(encoding="utf-8")
        workflow = yaml.safe_load(raw)
        assert workflow.get("permissions") == {"contents": "read"}, path.name

        for token in forbidden_executable_payload_tokens:
            assert token not in raw, f"{path.name}: {token}"

        for job in workflow.get("jobs", {}).values():
            for step in job.get("steps", []):
                action = step.get("uses")
                if not action:
                    continue
                if action.startswith("./"):
                    continue
                assert FULL_ACTION_SHA.fullmatch(action), f"{path.name}: {action}"
                if action.startswith("actions/checkout@"):
                    checkout_steps.append(step)
                    assert step.get("with", {}).get("persist-credentials") is False

    assert checkout_steps
