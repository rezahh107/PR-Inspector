import hashlib
import re
from pathlib import Path

import pytest
import yaml

import pr_inspector
from pr_inspector import candidate_v1_11

ROOT = Path(__file__).resolve().parents[1]
V18_LOCK_SHA256 = "d4f684a361dff638d823b7e1eb2edf73a3068cc3c1f52eb4ab1fca10fb8a7abd"
SHA256_DIGEST = re.compile(r"^[0-9a-f]{64}$")
FULL_ACTION_SHA = re.compile(r"^[^@\s]+@[0-9a-f]{40}$")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_lock(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line or line.startswith("#"):
            continue
        separator = line.find("  ")
        if separator < 0:
            raise AssertionError(f"{path}:{line_number}: missing exact double-space separator")
        digest = line[:separator]
        relative = line[separator + 2 :]
        if SHA256_DIGEST.fullmatch(digest) is None:
            raise AssertionError(f"{path}:{line_number}: invalid SHA-256 digest")
        if not relative or relative != relative.strip():
            raise AssertionError(f"{path}:{line_number}: invalid relative path")
        if relative in entries:
            raise AssertionError(f"{path}:{line_number}: duplicate relative path: {relative}")
        entries[relative] = digest
    return entries


def manifest() -> dict:
    return yaml.safe_load((ROOT / "protocol-manifest.yaml").read_text(encoding="utf-8"))


def load_workflow(path: Path) -> dict:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    assert value.get("permissions") == {"contents": "read"}
    assert isinstance(value.get("jobs"), dict)
    return value


def test_active_version_declarations_and_paths_are_aligned():
    current = (ROOT / "CURRENT_VERSION").read_text(encoding="utf-8").strip()
    data = manifest()
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    project_version = re.search(
        r'(?ms)^\[project\].*?^version\s*=\s*"([^"]+)"', pyproject
    )
    assert current == "v1.11.1"
    assert data["active_version"] == current
    assert data["status"] == "active"
    assert data["release_lock"] == "release-locks/v1.11.1.sha256"
    assert data["canonical_contract"].startswith("protocols/v1.11.1/")
    assert data["canonical_schema"].startswith("protocols/v1.11.1/")
    assert project_version is not None
    assert project_version.group(1) == "1.11.1"
    assert pr_inspector.__version__ == "1.11.1"
    assert "`v1.11.1`" in (ROOT / "README.md").read_text(encoding="utf-8")
    assert len(data["load_order"]) == 24
    assert len(data["load_order"]) == len(set(data["load_order"]))
    assert all(path.startswith("protocols/v1.11.1/") for path in data["load_order"])
    assert all((ROOT / path).is_file() for path in data["load_order"])


def test_corrected_activation_status_is_explicit_and_truthful():
    status = (ROOT / "docs/CANONICAL_OUTPUT_ENFORCEMENT.md").read_text(encoding="utf-8")
    required = (
        "active_protocol: v1.11.1",
        "implementation_state: v1.11.1_corrected_activation_pending_independent_review",
        "single_projection_authority: implemented",
        "single_prompt_authority: implemented",
        "single_verification_authority: implemented",
        "single_owner_delivery_authority: implemented",
        "semantic_prompt_completeness: implemented",
        "candidate_output_authority: eliminated_fail_closed",
        "external_chat_connector_acceptance: not_run",
        "repository_settings_enforcement: insufficient_evidence",
    )
    for statement in required:
        assert statement in status
    assert "independently reviewed, approved, merge-authorized, or merged" in status


def test_active_and_historical_release_locks_match_exact_bytes():
    data = manifest()
    active = parse_lock(ROOT / data["release_lock"])
    assert set(active) == set(data["load_order"])
    for relative, digest in active.items():
        path = ROOT / relative
        assert path.is_file(), relative
        assert sha256(path) == digest, relative

    v110 = parse_lock(ROOT / "release-locks/v1.11.0.sha256")
    assert v110
    assert all(path.startswith("protocols/v1.11.0/") for path in v110)
    for relative, digest in v110.items():
        assert sha256(ROOT / relative) == digest, relative

    v18_lock = ROOT / "release-locks/v1.8.0.sha256"
    assert sha256(v18_lock) == V18_LOCK_SHA256
    for relative, digest in parse_lock(v18_lock).items():
        assert sha256(ROOT / relative) == digest, relative


def test_candidate_compatibility_exports_no_output_authority():
    forbidden = {
        "project_decision",
        "render_candidate_next_action_prompt",
        "render_candidate_owner_result",
        "render_candidate_owner_card",
        "render_candidate_technical_handoff",
        "build_candidate_review_artifacts",
        "verify_candidate_review_artifact_bytes",
        "verify_minimal_review_artifact_bytes",
        "build_candidate_owner_delivery_artifacts",
        "candidate_owner_delivery_stdout",
    }
    assert forbidden.isdisjoint(candidate_v1_11.__all__)
    source = Path(candidate_v1_11.__file__).read_text(encoding="utf-8")
    assert "Repair independently validated technical findings before rereview" not in source
    assert "for _name in dir(" not in source
    assert "for name in tuple(dir(" not in source
    assert "CandidateOutputMigrationError" in source


def test_one_active_output_authority_is_documented_and_installed():
    contract = (ROOT / "protocols/v1.11.1/PR_REVIEW_CONTRACT.md").read_text(encoding="utf-8")
    status = (ROOT / "docs/CANONICAL_OUTPUT_ENFORCEMENT.md").read_text(encoding="utf-8")
    assert "decision_projection.project_decision" in contract
    assert "VerifiedReviewCompletion" in contract
    assert "official_owner_delivery" in contract
    assert "Candidate output symbols are unsupported" in contract
    assert "Candidate legacy output symbols" in status

    from pr_inspector import official_review

    assert callable(official_review.official_owner_delivery)
    assert callable(official_review.official_owner_profile_commands)


def test_prompt_semantic_validator_is_wired_into_official_directory_validation():
    validation = (ROOT / "pr_inspector/validation_v2.py").read_text(encoding="utf-8")
    derived = (ROOT / "pr_inspector/derived_outputs.py").read_text(encoding="utf-8")
    assert "validate_prompt_directory" in validation
    assert "require_prompt_semantics" in derived
    assert "[CANONICAL ACTION CONTRACT]" in (
        ROOT / "pr_inspector/prompt_semantics.py"
    ).read_text(encoding="utf-8")


def test_required_repository_files_and_no_temporary_residue():
    for relative in (
        "README.md",
        "BOOTSTRAP.md",
        "AGENTS.md",
        "CURRENT_VERSION",
        "protocol-manifest.yaml",
        "CHANGELOG.md",
        "LICENSE",
        "requirements.txt",
        "requirements-dev.txt",
        "pyproject.toml",
        "docs/QUALITY_ATTRIBUTE_MODEL.md",
    ):
        assert (ROOT / relative).is_file(), relative

    excluded = {".git", ".pytest_cache", "__pycache__", ".venv"}
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if any(part in excluded for part in relative.parts):
            continue
        assert ".repair" not in relative.parts
        assert not path.name.startswith("payload-")
        assert not path.name.startswith("chunk-")


def test_permanent_workflows_remain_read_only_pinned_and_non_self_modifying():
    workflows = sorted((ROOT / ".github/workflows").glob("*.y*ml"))
    assert workflows
    checkout_count = 0
    forbidden = ("exec(", "compile(", "base64 -d", "base64 --decode", "marshal.loads", "zlib.decompress")
    for path in workflows:
        raw = path.read_text(encoding="utf-8")
        workflow = load_workflow(path)
        for token in forbidden:
            assert token not in raw, f"{path.name}: {token}"
        for job in workflow["jobs"].values():
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


def test_release_does_not_modify_or_relabel_v1_11_0():
    old_contract = ROOT / "protocols/v1.11.0/PR_REVIEW_CONTRACT.md"
    old_lock = ROOT / "release-locks/v1.11.0.sha256"
    assert old_contract.is_file()
    assert old_lock.is_file()
    assert "Version:** 1.11.0" in old_contract.read_text(encoding="utf-8")
    assert "protocols/v1.11.0/" in old_lock.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "bad",
    [
        f"{'a' * 63}  protocols/v1.11.1/a.md\n",
        f"{'A' * 64}  protocols/v1.11.1/a.md\n",
        f"{'a' * 64} protocols/v1.11.1/a.md\n",
        f"{'a' * 64}  \n",
    ],
)
def test_release_lock_parser_fails_closed(tmp_path, bad):
    path = tmp_path / "bad.sha256"
    path.write_text(bad, encoding="utf-8")
    with pytest.raises(AssertionError):
        parse_lock(path)
