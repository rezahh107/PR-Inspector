from __future__ import annotations

import copy
import shutil
from contextlib import nullcontext
from pathlib import Path
from typing import Any

import pytest

from pr_inspector.evidence_context import evidence_scope
from tests.governance_test_support import sequence_capability

ROOT = Path(__file__).resolve().parents[1]
_LEGACY_GREEN_MODULES = {
    "test_protocol_v1_4.py",
    "test_sensitive_domains.py",
}
_PLANNING_FIXTURE_MODULES = {
    "test_planning_governance.py",
    "test_planning_governance_authority.py",
}


@pytest.fixture(autouse=True)
def exact_bound_sequence_for_legacy_green_tests(request):
    """Preserve unrelated legacy Green tests under the evidence-bound profile.

    Security-profile tests are intentionally excluded so bare serialized claims
    continue to exercise the fail-closed path.
    """
    path = Path(str(request.fspath))
    scope = (
        evidence_scope(sequence_enforcement=sequence_capability())
        if path.name in _LEGACY_GREEN_MODULES
        else nullcontext()
    )
    with scope:
        yield


def _copy_current_version(destination: Path) -> None:
    target = destination / "CURRENT_VERSION"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "CURRENT_VERSION", target)


def _append_current_exact_head_evidence(module: Any, registry: dict) -> dict:
    candidate = copy.deepcopy(registry)
    package = module.current_package(candidate)
    if any(
        record["work_package_id"] == package["work_package_id"]
        and record["evidence_type"] == "exact_head_ci"
        for record in candidate["evidence_records"]
    ):
        return candidate

    scope = module.load_json_strict(ROOT / package["scope_ref"])
    template = copy.deepcopy(
        next(
            record
            for record in candidate["evidence_records"]
            if record["evidence_type"] == "exact_head_ci"
        )
    )
    template.update(
        evidence_id=(
            f"{package['work_package_id']}-EVIDENCE-EXACT-HEAD-CI-TEST"
        ),
        repository=scope["repository"],
        task_id=package["task_id"],
        work_package_id=package["work_package_id"],
        base_sha=scope["base_sha"],
        head_sha="1" * 40,
        merge_commit_sha=None,
        scope_ref=package["scope_ref"],
        impact_ref=package["impact_refs"][-1],
        producer="github_actions",
        source_ref="github-actions:run:1:job:test",
        verified=True,
    )
    candidate["evidence_records"].append(template)
    return candidate


@pytest.fixture(autouse=True)
def declarative_planning_fixture_compatibility(request, monkeypatch):
    """Make legacy planning fixtures carry declarative authority inputs.

    The production resolver remains fail-closed. This fixture only upgrades the
    isolated test repositories so they contain the same explicit authority
    carriers required by the active v1.13 planning model.
    """
    path = Path(str(request.fspath))
    if path.name not in _PLANNING_FIXTURE_MODULES:
        yield
        return

    module = request.module
    original_copy = module.copy_static_bundle

    def copy_static_bundle(destination: Path) -> Path:
        result = original_copy(destination)
        _copy_current_version(result)
        return result

    monkeypatch.setattr(module, "copy_static_bundle", copy_static_bundle)

    if path.name == "test_planning_governance.py":
        original_read = module.read

        def read(relative: str | Path):
            value = original_read(relative)
            if Path(relative).as_posix() == module.REGISTRY_PATH.as_posix():
                return _append_current_exact_head_evidence(module, value)
            return value

        monkeypatch.setattr(module, "read", read)

        original_init = module.init_git

        def init_git(cwd: Path) -> None:
            original_init(cwd)
            for relative in (Path("CURRENT_VERSION"), module.REGISTRY_PATH):
                target = cwd / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / relative, target)
            module.git(
                "add",
                "CURRENT_VERSION",
                module.REGISTRY_PATH.as_posix(),
                cwd=cwd,
            )
            module.git(
                "commit",
                "-m",
                "planning authority controls",
                cwd=cwd,
            )

        monkeypatch.setattr(module, "init_git", init_git)

    yield
