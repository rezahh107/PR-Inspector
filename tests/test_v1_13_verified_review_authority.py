from __future__ import annotations

import inspect
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from pr_inspector import official_review as official_review_module
from pr_inspector.official_review import (
    OfficialReviewRuntime,
    _complete_review_with_runtime,
    complete_review,
    is_verified_review_completion,
    official_owner_delivery,
)
from pr_inspector.verified_review import ProtocolContext, assemble_review_package
from tests import test_v1_12_verified_review_authority as legacy

ROOT = Path(__file__).resolve().parents[1]


def _active_context() -> ProtocolContext:
    return replace(legacy._context(), protocol_version="v1.13.1")


def test_v1_13_active_protocol_adapter_installed():
    assert (
        ProtocolContext.from_verified_repository.__func__.__module__
        == "pr_inspector.verified_review"
    )


def test_v1_13_official_context_uses_exact_real_commit(
    monkeypatch,
):
    import pr_inspector.repository as repository
    import pr_inspector.verified_review as verified_review

    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()
    monkeypatch.setattr(repository, "validate_repository", lambda root: [])
    original_git = verified_review._run_git
    monkeypatch.setattr(
        verified_review, "_run_git",
        lambda root, *args: "https://github.com/rezahh107/PR-Inspector.git"
        if args == ("remote", "get-url", "origin") else original_git(root, *args),
    )
    monkeypatch.setattr(
        verified_review, "_fetch_github_json",
        lambda url, **kwargs: {"full_name": "rezahh107/PR-Inspector", "id": 1288323264}
        if url.endswith("PR-Inspector") else {"sha": commit},
    )
    context = ProtocolContext.from_verified_repository(ROOT)
    assert context.protocol_version == "v1.13.1"
    assert context.inspector_repository == "rezahh107/PR-Inspector"
    assert context.inspector_commit_sha == commit


def test_v1_13_zero_commit_is_rejected(monkeypatch):
    import pr_inspector.repository as repository
    import pr_inspector.verified_review as verified_review
    monkeypatch.setattr(repository, "validate_repository", lambda root: [])
    monkeypatch.setattr(verified_review, "_run_git", lambda root, *args: "0" * 40)
    with pytest.raises(verified_review.ReviewAssemblyError, match="commit SHA is invalid"):
        ProtocolContext.from_verified_repository(ROOT)


def test_official_runtime_construction_uses_verified_context(
    monkeypatch,
):
    import pr_inspector.repository as repository

    context = _active_context()
    monkeypatch.setattr(ProtocolContext, "from_verified_repository", classmethod(lambda cls, *args, **kwargs: context))
    monkeypatch.setattr(
        official_review_module,
        "github_pull_request_head_source",
        lambda *args, **kwargs: object(),
    )
    request = legacy._request(repository_directory=ROOT)
    runtime = official_review_module._create_official_runtime(request)
    assert runtime.protocol_context.protocol_version == "v1.13.1"


def test_v1_13_package_is_differentially_equal_to_v1_12_except_protocol_identity():
    facts = legacy._facts()
    assessment = legacy._assessment()
    old = assemble_review_package(facts, assessment, legacy._context()).value()
    new = assemble_review_package(facts, assessment, _active_context()).value()
    assert old["protocol_version"] == "v1.12.0"
    assert new["protocol_version"] == "v1.13.1"
    old = dict(old)
    new = dict(new)
    old.pop("protocol_version")
    new.pop("protocol_version")
    assert new == old


def test_v1_13_preserves_canonical_bytes_and_public_caller_shape():
    facts = legacy._facts()
    assessment = legacy._assessment()
    first = assemble_review_package(facts, assessment, _active_context())
    second = assemble_review_package(facts, assessment, _active_context())
    assert first.canonical_bytes == second.canonical_bytes
    assert first.canonical_sha256 == second.canonical_sha256
    assert list(inspect.signature(complete_review).parameters) == [
        "request",
        "assessment",
        "output_directory",
        "package_path",
    ]


def test_v1_13_fixture_validation_matches_v1_12_diagnostics():
    from pr_inspector.validation_v2 import validate_package

    base = assemble_review_package(
        legacy._facts(),
        legacy._assessment(),
        legacy._context(),
    ).value()
    candidate = dict(base)
    candidate["protocol_version"] = "v1.13.1"
    old = [
        (item.code, item.path, item.message)
        for item in validate_package(base)
    ]
    new = [
        (item.code, item.path, item.message)
        for item in validate_package(candidate)
    ]
    assert new == old


def test_v1_13_reaches_official_completion_and_owner_delivery(tmp_path):
    source = legacy.StaticSource(legacy._facts())
    result = _complete_review_with_runtime(
        legacy._request(),
        legacy._assessment(),
        tmp_path / "out",
        runtime=OfficialReviewRuntime(source, _active_context()),
    )
    assert is_verified_review_completion(result)
    package = __import__("json").loads(
        (tmp_path / "out" / "review-package.json").read_text(encoding="utf-8")
    )
    assert package["protocol_version"] == "v1.13.1"
    delivery = official_owner_delivery(result)
    assert delivery
    assert source.fetch_count >= 3


def test_v1_13_provenance_review_directory_roundtrip(tmp_path):
    from pr_inspector.review_provenance import (
        verify_github_commit_payload,
        verify_review_directory,
    )
    from tests.test_behavioral_rule_coverage import _github_responses

    source = legacy.StaticSource(legacy._facts())
    output = tmp_path / "out"
    result = _complete_review_with_runtime(
        legacy._request(), legacy._assessment(), output,
        runtime=OfficialReviewRuntime(source, _active_context()),
    )
    assert is_verified_review_completion(result)
    commit = _active_context().inspector_commit_sha
    repository_response, commit_response = _github_responses(commit)
    verified_commit = verify_github_commit_payload(
        repository_response, commit_response, expected_commit_sha=commit
    )
    evidence = verify_review_directory(output, verified_commit)
    assert evidence.inspector_commit_sha == commit

    other = "4" * 40
    repository_response, commit_response = _github_responses(other)
    mismatched = verify_github_commit_payload(
        repository_response, commit_response, expected_commit_sha=other
    )
    with pytest.raises(Exception, match="commit is not verified"):
        verify_review_directory(output, mismatched)


def test_projection_identity_remains_bound_to_package_version():
    from pr_inspector.decision_projection import project_decision

    old = assemble_review_package(
        legacy._facts(), legacy._assessment(), legacy._context()
    ).value()
    new = assemble_review_package(
        legacy._facts(), legacy._assessment(), _active_context()
    ).value()
    assert project_decision(old)["protocol_version"] == "v1.12.0"
    assert project_decision(new)["protocol_version"] == "v1.13.1"
