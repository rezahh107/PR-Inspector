from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from pr_inspector import repository as repository_module
from pr_inspector._official_head import VerifiedLivePullRequestHead
from pr_inspector.diagnostics import Diagnostic
from pr_inspector.decision_projection import project_decision
from pr_inspector.verified_review import (
    ChangedFile,
    CheckFact,
    EvidenceRecord,
    ExternalReviewDisposition,
    GitHubReviewEvidenceSource,
    ProtocolContext,
    ReviewAssemblyError,
    ReviewAssessment,
    ReviewFacts,
    ReviewFinding,
    ReviewRequest,
    assemble_review_package,
)
import pr_inspector.verified_review as vr

REPOSITORY = "example/project"
REPOSITORY_ID = 4242
PR_NUMBER = 42
BASE = "2" * 40
HEAD = "1" * 40
INSPECTOR = "3" * 40


class HeadSource:
    def fetch(self) -> VerifiedLivePullRequestHead:
        return _head()


def _head() -> VerifiedLivePullRequestHead:
    return VerifiedLivePullRequestHead(
        repository=REPOSITORY,
        repository_id=REPOSITORY_ID,
        pr_number=PR_NUMBER,
        state="open",
        base_branch="main",
        base_sha=BASE,
        head_branch="feature",
        head_sha=HEAD,
        api_url=f"https://api.github.com/repos/{REPOSITORY}/pulls/{PR_NUMBER}",
        html_url=f"https://github.com/{REPOSITORY}/pull/{PR_NUMBER}",
        receipt_sha256="a" * 64,
    )


def _context(*, required: tuple[str, ...] = ()) -> ProtocolContext:
    return ProtocolContext(
        "v1.12.0",
        "rezahh107/PR-Inspector",
        1288323264,
        INSPECTOR,
        required,
    )


def _base_facts(
    *,
    checks: tuple[CheckFact, ...] = (),
    extra: tuple[EvidenceRecord, ...] = (),
    check_complete: bool = True,
    review_complete: bool = True,
) -> ReviewFacts:
    diff = EvidenceRecord.create(
        kind="DIFF",
        repository=REPOSITORY,
        pr_number=PR_NUMBER,
        head_sha=HEAD,
        source=f"git:{BASE}..{HEAD}",
        payload={"path": "src/a.py", "changed_lines": 4},
    )
    records = [diff, *extra]
    known = {item.evidence_id for item in records}
    for check in checks:
        if check.evidence_id not in known:
            records.append(
                EvidenceRecord.create(
                    kind="CI",
                    repository=REPOSITORY,
                    pr_number=PR_NUMBER,
                    head_sha=HEAD,
                    source=f"fixture:{check.name}",
                    payload={
                        "name": check.name,
                        "status": check.status,
                        "conclusion": check.conclusion,
                        "result": check.result,
                        "tested_sha": HEAD,
                    },
                )
            )
    return ReviewFacts(
        repository=REPOSITORY,
        repository_id=REPOSITORY_ID,
        pr_number=PR_NUMBER,
        pr_state="open",
        base_branch="main",
        base_sha=BASE,
        head_branch="feature",
        head_sha=HEAD,
        merge_base_sha=BASE,
        changed_files=(ChangedFile("src/a.py", 4),),
        checks=checks,
        evidence_catalog=tuple(records),
        review_started="2026-07-23T10:00:00Z",
        review_completed="2026-07-23T10:01:00Z",
        capabilities={},
        check_enumeration_complete=check_complete,
        review_surface_enumeration_complete=review_complete,
    )


def _assessment(
    *,
    findings: tuple[ReviewFinding, ...] = (),
    dispositions: tuple[ExternalReviewDisposition, ...] = (),
) -> ReviewAssessment:
    return ReviewAssessment(
        review_summary="Review the exact change.",
        findings=findings,
        owner_facing_explanation="Facts and assessment were reconciled.",
        reviewed_files=("src/a.py",),
        external_review_dispositions=dispositions,
    )


def _external(kind: str, github_id: int) -> EvidenceRecord:
    source_kind = {
        "COMMENT": "issue_comment",
        "REVIEW": "review_submission",
        "INLINE_COMMENT": "inline_review_comment",
    }[kind]
    return EvidenceRecord.create(
        kind=kind,
        repository=REPOSITORY,
        pr_number=PR_NUMBER,
        head_sha=HEAD,
        source=f"https://github.com/{REPOSITORY}/pull/{PR_NUMBER}#{github_id}",
        payload={
            "github_id": github_id,
            "source_kind": source_kind,
            "state": "COMMENTED",
            "author": "reviewer",
            "body": "Review suggestion",
            "path": "src/a.py" if kind == "INLINE_COMMENT" else None,
            "line": 4 if kind == "INLINE_COMMENT" else None,
            "start_line": None,
            "commit_id": HEAD if kind != "COMMENT" else None,
            "in_reply_to_id": None,
            "html_url": f"https://github.com/{REPOSITORY}/pull/{PR_NUMBER}#{github_id}",
            "enumeration_complete": True,
        },
    )


def test_paginated_list_endpoint_collects_more_than_one_hundred(monkeypatch):
    pages = {
        1: ([{"id": index} for index in range(1, 101)], "https://api.github.test/items?page=2&per_page=100"),
        2: ([{"id": 101}], None),
    }

    def fetch(url, **_):
        page = int(parse_qs(urlparse(url).query).get("page", ["1"])[0])
        return pages[page]

    monkeypatch.setattr(vr, "_fetch_github_page", fetch)
    items = vr._fetch_all_github_pages("https://api.github.test/items", token=None, api_version="v")
    assert len(items) == 101
    assert items[-1]["id"] == 101


def test_paginated_mapping_endpoint_proves_total_count(monkeypatch):
    pages = {
        1: ({"total_count": 101, "check_runs": [{"id": index} for index in range(1, 101)]}, "https://api.github.test/checks?page=2&per_page=100"),
        2: ({"total_count": 101, "check_runs": [{"id": 101}]}, None),
    }

    def fetch(url, **_):
        page = int(parse_qs(urlparse(url).query).get("page", ["1"])[0])
        return pages[page]

    monkeypatch.setattr(vr, "_fetch_github_page", fetch)
    items = vr._fetch_all_github_pages(
        "https://api.github.test/checks", token=None, api_version="v", item_key="check_runs"
    )
    assert len(items) == 101


@pytest.mark.parametrize("mode", ["loop", "malformed", "partial", "network"])
def test_pagination_failures_are_closed(monkeypatch, mode: str):
    first = "https://api.github.test/items?per_page=100"

    def fetch(url, **_):
        if mode == "loop":
            return ([{"id": 1}], first)
        if mode == "malformed":
            return ({"items": []}, None)
        if mode == "partial":
            return ({"total_count": 2, "check_runs": [{"id": 1}]}, None)
        raise ReviewAssemblyError("network failure mid-pagination")

    monkeypatch.setattr(vr, "_fetch_github_page", fetch)
    kwargs = {"item_key": "check_runs"} if mode == "partial" else {}
    with pytest.raises(ReviewAssemblyError):
        vr._fetch_all_github_pages(first, token=None, api_version="v", **kwargs)




def test_pagination_next_link_cannot_change_endpoint(monkeypatch):
    monkeypatch.setattr(
        vr,
        "_fetch_github_page",
        lambda url, **_: ([{"id": 1}], "https://evil.example/items?page=2"),
    )
    with pytest.raises(ReviewAssemblyError, match="changed endpoint"):
        vr._fetch_all_github_pages(
            "https://api.github.test/items", token=None, api_version="v"
        )

def test_missing_required_check_is_explicit_unknown(monkeypatch):
    monkeypatch.setattr(
        vr,
        "_fetch_all_github_pages",
        lambda *args, **kwargs: (
            {
                "id": 1,
                "name": "Observed",
                "status": "completed",
                "conclusion": "success",
                "head_sha": HEAD,
                "details_url": "https://github.com/check/1",
            },
        ),
    )
    source = GitHubReviewEvidenceSource(
        Path("."), HeadSource(), required_check_names=("Observed", "Missing")
    )
    checks, evidence = source._collect_checks(_head())
    missing = next(item for item in checks if item.name == "Missing")
    record = next(item for item in evidence if item.evidence_id == missing.evidence_id)
    assert missing.required is True
    assert missing.status == "missing"
    assert missing.result == "UNKNOWN"
    assert record.payload["missing_required_check"] is True
    assert record.payload["enumeration_complete"] is True

    facts = _base_facts(checks=checks, extra=evidence)
    value = assemble_review_package(facts, _assessment(), _context()).value()
    assert value["decision"]["technical_status"] != "GREEN_TECHNICALLY_READY"


def test_observed_failed_and_pending_checks_remain_distinct(monkeypatch):
    monkeypatch.setattr(
        vr,
        "_fetch_all_github_pages",
        lambda *args, **kwargs: (
            {"id": 1, "name": "Failed", "status": "completed", "conclusion": "failure", "head_sha": HEAD},
            {"id": 2, "name": "Pending", "status": "in_progress", "conclusion": None, "head_sha": HEAD},
        ),
    )
    source = GitHubReviewEvidenceSource(
        Path("."), HeadSource(), required_check_names=("Failed", "Pending")
    )
    checks, _ = source._collect_checks(_head())
    assert {item.name: item.result for item in checks} == {"Failed": "FAIL", "Pending": "UNKNOWN"}


@pytest.mark.parametrize("field", ["check_enumeration_complete", "review_surface_enumeration_complete"])
def test_incomplete_enumeration_cannot_assemble(field: str):
    facts = replace(_base_facts(), **{field: False})
    with pytest.raises(ReviewAssemblyError, match="enumeration is incomplete"):
        assemble_review_package(facts, _assessment(), _context())


def test_all_three_review_surfaces_are_collected(monkeypatch):
    def pages(url, **_):
        if "/issues/" in url:
            return ({"id": 11, "user": {"login": "issue-user"}, "body": "issue", "html_url": "https://x/11"},)
        if url.endswith("/reviews") or "/reviews?" in url:
            return ({"id": 12, "user": {"login": "review-user"}, "body": "review", "state": "COMMENTED", "html_url": "https://x/12", "commit_id": HEAD},)
        return ({"id": 13, "user": {"login": "inline-user"}, "body": "inline", "path": "src/a.py", "line": 5, "html_url": "https://x/13", "commit_id": HEAD},)

    monkeypatch.setattr(vr, "_fetch_all_github_pages", pages)
    source = GitHubReviewEvidenceSource(Path("."), HeadSource())
    records = source._collect_review_surfaces(_head())
    assert {item.kind for item in records} == {"COMMENT", "REVIEW", "INLINE_COMMENT"}
    inline = next(item for item in records if item.kind == "INLINE_COMMENT")
    assert inline.payload["path"] == "src/a.py"
    assert inline.payload["line"] == 5


def test_all_external_sources_must_be_reconciled_for_complete():
    records = (_external("COMMENT", 1), _external("REVIEW", 2), _external("INLINE_COMMENT", 3))
    facts = _base_facts(extra=records)
    dispositions = tuple(
        ExternalReviewDisposition(item.evidence_id, "resolved", "Already addressed.")
        for item in records
    )
    value = assemble_review_package(
        facts, _assessment(dispositions=dispositions), _context()
    ).value()
    reconciliation = value["external_review_reconciliation"]
    assert reconciliation["collection_status"] == "COMPLETE"
    assert reconciliation["uninspected_source_ids"] == []
    assert reconciliation["counts"]["resolved"] == 3


def test_unclassified_external_source_is_explicit_and_blocks_green():
    record = _external("INLINE_COMMENT", 3)
    value = assemble_review_package(
        _base_facts(extra=(record,)), _assessment(), _context()
    ).value()
    reconciliation = value["external_review_reconciliation"]
    assert reconciliation["collection_status"] == "INCOMPLETE"
    assert reconciliation["uninspected_source_ids"] == [record.evidence_id]
    assert value["decision"]["technical_status"] != "GREEN_TECHNICALLY_READY"
    assert "RSN-EXTERNAL-REVIEW-INCOMPLETE" in {
        item["reason_code"] for item in project_decision(value)["reason_details"]
    }


def test_new_external_source_added_before_completion_is_uninspected():
    first = _external("COMMENT", 1)
    second = _external("INLINE_COMMENT", 2)
    assessment = _assessment(
        dispositions=(ExternalReviewDisposition(first.evidence_id, "resolved", "Reviewed."),)
    )
    value = assemble_review_package(
        _base_facts(extra=(first, second)), assessment, _context()
    ).value()
    assert value["external_review_reconciliation"]["uninspected_source_ids"] == [second.evidence_id]


def test_accepted_source_must_link_to_real_finding_and_counts_are_derived():
    source = _external("COMMENT", 1)
    finding = ReviewFinding(
        "FND-001",
        "Accepted defect",
        "The reviewer confirmed the defect.",
        "HIGH",
        True,
        "The external suggestion was verified against the collected facts.",
        (source.evidence_id,),
        "HUMAN_JUDGMENT",
        ("src/a.py",),
    )
    disposition = ExternalReviewDisposition(
        source.evidence_id, "accepted", "Verified and accepted.", (finding.finding_id,)
    )
    value = assemble_review_package(
        _base_facts(extra=(source,)),
        _assessment(findings=(finding,), dispositions=(disposition,)),
        _context(),
    ).value()
    reconciliation = value["external_review_reconciliation"]
    assert reconciliation["counts"]["accepted"] == 1
    assert reconciliation["valid_blocking_finding_ids"] == [finding.finding_id]


@pytest.mark.parametrize("case", ["unknown_source", "unknown_finding", "unknown_classification", "duplicate"])
def test_invalid_external_dispositions_fail_closed(case: str):
    source = _external("COMMENT", 1)
    finding = ReviewFinding(
        "FND-001", "Finding", "Description", "LOW", False, "Rationale"
    )
    if case == "unknown_source":
        assessment = _assessment(
            dispositions=(ExternalReviewDisposition("EVD-NOT-THERE", "resolved", "Reviewed."),)
        )
    elif case == "unknown_finding":
        assessment = _assessment(
            dispositions=(ExternalReviewDisposition(source.evidence_id, "accepted", "Accepted.", ("FND-999",)),)
        )
    elif case == "unknown_classification":
        with pytest.raises(ReviewAssemblyError, match="unknown external review classification"):
            ExternalReviewDisposition(source.evidence_id, "trusted", "No.")
        return
    else:
        item = ExternalReviewDisposition(source.evidence_id, "resolved", "Reviewed.")
        with pytest.raises(ReviewAssemblyError, match="duplicate external review disposition"):
            _assessment(dispositions=(item, item))
        return
    with pytest.raises(ReviewAssemblyError):
        assemble_review_package(
            _base_facts(extra=(source,)),
            replace(assessment, findings=(finding,)),
            _context(),
        )


def _write_protocol_root(root: Path, *, current: str = "v1.12.0", active: str = "v1.12.0") -> None:
    (root / "CURRENT_VERSION").write_text(current + "\n", encoding="utf-8")
    (root / "BOOTSTRAP.md").write_text("# Bootstrap\n", encoding="utf-8")
    (root / "protocol-manifest.yaml").write_text(
        "schema_version: 1\n"
        f"active_version: {active}\n"
        "status: active\n"
        "entrypoint: BOOTSTRAP.md\n"
        "required_check_names: [Validate]\n",
        encoding="utf-8",
    )
    trust = root / f"protocols/{current}/trust"
    trust.mkdir(parents=True)
    (trust / "INSPECTOR_TRUST_POLICY.json").write_text(
        json.dumps(
            {
                "protocol_version": current,
                "inspector_repository": "rezahh107/PR-Inspector",
                "inspector_repository_id": 1288323264,
            }
        ),
        encoding="utf-8",
    )


def _install_protocol_verifiers(monkeypatch, *, repo_name="rezahh107/PR-Inspector", repo_id=1288323264, commit_sha=INSPECTOR):
    monkeypatch.setattr(repository_module, "validate_repository", lambda root: [])

    def git(root, *args):
        if args == ("rev-parse", "HEAD"):
            return INSPECTOR
        if args == ("remote", "get-url", "origin"):
            return "https://github.com/rezahh107/PR-Inspector.git"
        raise AssertionError(args)

    def github(url, **_):
        if "/commits/" in url:
            return {"sha": commit_sha}
        return {"full_name": repo_name, "id": repo_id}

    monkeypatch.setattr(vr, "_run_git", git)
    monkeypatch.setattr(vr, "_fetch_github_json", github)


def test_valid_protocol_context_is_verified(tmp_path: Path, monkeypatch):
    _write_protocol_root(tmp_path)
    _install_protocol_verifiers(monkeypatch)
    context = ProtocolContext.from_verified_repository(tmp_path)
    assert context.protocol_version == "v1.12.0"
    assert context.required_check_names == ("Validate",)


@pytest.mark.parametrize("case", ["version", "repo", "repo_id", "commit", "missing_commit", "release_lock", "canonical_hash"])
def test_protocol_context_verification_failures_are_closed(tmp_path: Path, monkeypatch, case: str):
    _write_protocol_root(tmp_path, active="v1.11.1" if case == "version" else "v1.12.0")
    _install_protocol_verifiers(
        monkeypatch,
        repo_name="other/repo" if case == "repo" else "rezahh107/PR-Inspector",
        repo_id=999 if case == "repo_id" else 1288323264,
        commit_sha=("4" * 40) if case == "commit" else INSPECTOR,
    )
    if case == "missing_commit":
        monkeypatch.setattr(vr, "_fetch_github_json", lambda url, **_: {} if "/commits/" in url else {"full_name": "rezahh107/PR-Inspector", "id": 1288323264})
    if case in {"release_lock", "canonical_hash"}:
        monkeypatch.setattr(
            repository_module,
            "validate_repository",
            lambda root: [Diagnostic("PRI-LOCK-001" if case == "release_lock" else "PRI-HASH-001", "/", "invalid")],
        )
    with pytest.raises(ReviewAssemblyError):
        ProtocolContext.from_verified_repository(tmp_path)
