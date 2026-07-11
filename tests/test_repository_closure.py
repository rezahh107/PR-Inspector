import hashlib
import re
from pathlib import Path

import pytest
import yaml

import pr_inspector

ROOT = Path(__file__).resolve().parents[1]
V18_LOCK_SHA256 = "d4f684a361dff638d823b7e1eb2edf73a3068cc3c1f52eb4ab1fca10fb8a7abd"
FULL_ACTION_SHA = re.compile(r"^[^@\s]+@[0-9a-f]{40}$")
SHA256_DIGEST = re.compile(r"^[0-9a-f]{64}$")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _lock_failure(path: Path, line_number: int, reason: str) -> None:
    raise AssertionError(f"{path}:{line_number}: {reason}")


def _parse_lock(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not line or line.startswith("#"):
            continue

        separator_index = line.find("  ")
        if separator_index < 0:
            _lock_failure(
                path,
                line_number,
                "missing exact double-space separator",
            )

        digest = line[:separator_index]
        relative_path = line[separator_index + 2 :]
        if SHA256_DIGEST.fullmatch(digest) is None:
            _lock_failure(
                path,
                line_number,
                "SHA-256 digest must be exactly 64 lowercase hexadecimal characters",
            )
        if not relative_path:
            _lock_failure(path, line_number, "relative path must not be empty")
        if relative_path != relative_path.strip():
            _lock_failure(
                path,
                line_number,
                "relative path must not contain surrounding whitespace",
            )
        if relative_path in entries:
            _lock_failure(
                path,
                line_number,
                f"duplicate relative path: {relative_path}",
            )
        entries[relative_path] = digest
    return entries


def _load_workflow(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    try:
        workflow = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        problem = getattr(exc, "problem", None) or exc.__class__.__name__
        raise AssertionError(f"{path}: invalid workflow YAML: {problem}") from exc

    assert isinstance(workflow, dict), (
        f"{path}: top-level YAML value must be a mapping, "
        f"got {type(workflow).__name__}"
    )
    assert workflow.get("permissions") == {"contents": "read"}, (
        f"{path}: permissions must be exactly {{'contents': 'read'}}"
    )

    jobs = workflow.get("jobs")
    assert isinstance(jobs, dict), (
        f"{path}: jobs must be a mapping, got {type(jobs).__name__}"
    )
    for job_name, job in jobs.items():
        assert isinstance(job, dict), (
            f"{path}: job {job_name!r} must be a mapping, "
            f"got {type(job).__name__}"
        )
        if "steps" not in job:
            continue
        steps = job["steps"]
        assert isinstance(steps, list), (
            f"{path}: job {job_name!r} steps must be a list, "
            f"got {type(steps).__name__}"
        )
        for step_index, step in enumerate(steps):
            assert isinstance(step, dict), (
                f"{path}: job {job_name!r} step {step_index} must be a mapping, "
                f"got {type(step).__name__}"
            )
    return workflow


def _manifest() -> dict:
    return yaml.safe_load((ROOT / "protocol-manifest.yaml").read_text(encoding="utf-8"))


def test_parse_lock_accepts_valid_entries(tmp_path):
    lock = tmp_path / "valid.sha256"
    lock.write_text(
        "# test lock\n"
        f"{'a' * 64}  protocols/v1.9.0/example.md\n",
        encoding="utf-8",
    )

    assert _parse_lock(lock) == {
        "protocols/v1.9.0/example.md": "a" * 64,
    }


def _assert_lock_failure(lock: Path, expected_line: int, expected_reason: str) -> None:
    with pytest.raises(AssertionError) as captured:
        _parse_lock(lock)
    message = str(captured.value)
    assert str(lock) in message
    assert f":{expected_line}:" in message
    assert expected_reason in message


def test_parse_lock_rejects_missing_separator(tmp_path):
    lock = tmp_path / "missing-separator.sha256"
    lock.write_text(f"{'a' * 64} protocols/v1.9.0/example.md\n", encoding="utf-8")

    _assert_lock_failure(lock, 1, "missing exact double-space separator")


@pytest.mark.parametrize("digest", ["a" * 63, "A" * 64, "g" * 64])
def test_parse_lock_rejects_invalid_digest(tmp_path, digest):
    lock = tmp_path / "invalid-digest.sha256"
    lock.write_text(f"{digest}  protocols/v1.9.0/example.md\n", encoding="utf-8")

    _assert_lock_failure(
        lock,
        1,
        "SHA-256 digest must be exactly 64 lowercase hexadecimal characters",
    )


def test_parse_lock_rejects_empty_relative_path(tmp_path):
    lock = tmp_path / "empty-path.sha256"
    lock.write_text(f"{'a' * 64}  \n", encoding="utf-8")

    _assert_lock_failure(lock, 1, "relative path must not be empty")


def test_parse_lock_rejects_duplicate_relative_path(tmp_path):
    lock = tmp_path / "duplicate-path.sha256"
    lock.write_text(
        f"{'a' * 64}  protocols/v1.9.0/example.md\n"
        f"{'b' * 64}  protocols/v1.9.0/example.md\n",
        encoding="utf-8",
    )

    _assert_lock_failure(
        lock,
        2,
        "duplicate relative path: protocols/v1.9.0/example.md",
    )


def test_load_workflow_accepts_valid_structure(tmp_path):
    workflow = tmp_path / "valid.yml"
    workflow.write_text(
        "permissions:\n"
        "  contents: read\n"
        "jobs:\n"
        "  validate:\n"
        "    steps:\n"
        "      - name: Test\n"
        "        run: python -m pytest\n",
        encoding="utf-8",
    )

    assert _load_workflow(workflow)["jobs"]["validate"]["steps"][0]["name"] == "Test"


@pytest.mark.parametrize("raw", ["", "# comment only\n"])
def test_load_workflow_rejects_empty_or_comment_only_yaml(tmp_path, raw):
    workflow = tmp_path / "empty.yml"
    workflow.write_text(raw, encoding="utf-8")

    with pytest.raises(AssertionError, match="top-level YAML value must be a mapping"):
        _load_workflow(workflow)


@pytest.mark.parametrize("raw", ["- item\n", "scalar\n"])
def test_load_workflow_rejects_top_level_list_or_scalar(tmp_path, raw):
    workflow = tmp_path / "top-level.yml"
    workflow.write_text(raw, encoding="utf-8")

    with pytest.raises(AssertionError, match="top-level YAML value must be a mapping"):
        _load_workflow(workflow)


def test_load_workflow_rejects_non_mapping_jobs(tmp_path):
    workflow = tmp_path / "jobs.yml"
    workflow.write_text(
        "permissions:\n"
        "  contents: read\n"
        "jobs: []\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="jobs must be a mapping"):
        _load_workflow(workflow)


def test_load_workflow_rejects_non_mapping_job(tmp_path):
    workflow = tmp_path / "job.yml"
    workflow.write_text(
        "permissions:\n"
        "  contents: read\n"
        "jobs:\n"
        "  validate: invalid\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="job 'validate' must be a mapping"):
        _load_workflow(workflow)


def test_load_workflow_rejects_non_list_steps(tmp_path):
    workflow = tmp_path / "steps.yml"
    workflow.write_text(
        "permissions:\n"
        "  contents: read\n"
        "jobs:\n"
        "  validate:\n"
        "    steps: {}\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="job 'validate' steps must be a list"):
        _load_workflow(workflow)


def test_load_workflow_rejects_non_mapping_step(tmp_path):
    workflow = tmp_path / "step.yml"
    workflow.write_text(
        "permissions:\n"
        "  contents: read\n"
        "jobs:\n"
        "  validate:\n"
        "    steps:\n"
        "      - invalid\n",
        encoding="utf-8",
    )

    with pytest.raises(AssertionError, match="step 0 must be a mapping"):
        _load_workflow(workflow)


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
        "confirmed_merged_implementation_findings_at_audit_start: none",
        "closure_pr_review_state: pending_independent_review",
        "live_review_thread_state: not_asserted_by_static_document",
        "bot_commented_feedback: not_approval",
        "closure_status: implementation_complete_closure_polish_pending_independent_review",
    )
    for statement in required:
        assert statement in status

    assert "repository settings remain a separate administrative evidence boundary" in status
    assert "independently reviewed, approved, merge-authorized, or merged" in status
    assert "No additional runtime implementation defect was confirmed" in status


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
        workflow = _load_workflow(path)

        for token in forbidden_executable_payload_tokens:
            assert token not in raw, f"{path.name}: {token}"

        for job in workflow["jobs"].values():
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
