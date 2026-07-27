from __future__ import annotations

import inspect
from dataclasses import replace
from pathlib import Path

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
    return replace(legacy._context(), protocol_version="v1.13.0")


def test_v1_13_active_protocol_adapter_installed():
    assert (
        ProtocolContext.from_verified_repository.__func__.__module__
        == "pr_inspector.functional_runtime"
    )


def test_v1_13_context_construction_uses_no_inspector_network_or_full_validator(
    monkeypatch,
):
    import pr_inspector.repository as repository
    import pr_inspector.verified_review as verified_review

    def forbidden(*args, **kwargs):
        raise AssertionError("release-time Inspector verification must not run")

    monkeypatch.setattr(repository, "validate_repository", forbidden)
    monkeypatch.setattr(repository, "validate_active_release_lock", forbidden)
    monkeypatch.setattr(verified_review, "_fetch_github_json", forbidden)
    context = ProtocolContext.from_verified_repository(ROOT)
    assert context.protocol_version == "v1.13.0"
    assert context.inspector_repository == "rezahh107/PR-Inspector"
    assert len(context.inspector_commit_sha) == 40


def test_official_runtime_construction_never_calls_full_repository_validation(
    monkeypatch,
):
    import pr_inspector.repository as repository

    def forbidden(*args, **kwargs):
        raise AssertionError("full repository validation must remain CI-only")

    monkeypatch.setattr(repository, "validate_repository", forbidden)
    monkeypatch.setattr(repository, "validate_active_release_lock", forbidden)
    monkeypatch.setattr(
        official_review_module,
        "github_pull_request_head_source",
        lambda *args, **kwargs: object(),
    )
    request = legacy._request(repository_directory=ROOT)
    runtime = official_review_module._create_official_runtime(request)
    assert runtime.protocol_context.protocol_version == "v1.13.0"


def test_v1_13_package_is_differentially_equal_to_v1_12_except_protocol_identity():
    facts = legacy._facts()
    assessment = legacy._assessment()
    old = assemble_review_package(facts, assessment, legacy._context()).value()
    new = assemble_review_package(facts, assessment, _active_context()).value()
    assert old["protocol_version"] == "v1.12.0"
    assert new["protocol_version"] == "v1.13.0"
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
    candidate["protocol_version"] = "v1.13.0"
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
    assert package["protocol_version"] == "v1.13.0"
    delivery = official_owner_delivery(result)
    assert delivery
    assert source.fetch_count >= 3


def test_projection_identity_remains_bound_to_package_version():
    from pr_inspector.decision_projection import project_decision

    old = assemble_review_package(
        legacy._facts(), legacy._assessment(), legacy._context()
    ).value()
    new = assemble_review_package(
        legacy._facts(), legacy._assessment(), _active_context()
    ).value()
    assert project_decision(old)["protocol_version"] == "v1.12.0"
    assert project_decision(new)["protocol_version"] == "v1.13.0"
