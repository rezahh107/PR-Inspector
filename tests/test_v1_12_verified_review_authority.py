from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from pr_inspector import _official_complete, official_review as official_review_module
from pr_inspector._official_bundle import IncompleteReview
from pr_inspector._official_head import VerifiedLivePullRequestHead
from pr_inspector.decision_projection import project_decision
from pr_inspector.official_review import (
    OfficialReviewRuntime,
    _complete_review_with_runtime,
    complete_review,
    is_verified_review_completion,
)
from pr_inspector.verified_review import (
    CanonicalReviewPackage,
    ChangedFile,
    CheckFact,
    EvidenceRecord,
    FIELD_AUTHORITY,
    ProtocolContext,
    ReviewAssemblyError,
    ReviewAssessment,
    ReviewFacts,
    ReviewFinding,
    ReviewRequest,
    assemble_review_package,
    canonical_review_package_bytes,
    parse_review_assessment,
)

REPOSITORY = "example/project"
REPOSITORY_ID = 4242
PR_NUMBER = 42
BASE = "2" * 40
HEAD = "1" * 40
INSPECTOR = "3" * 40


class StaticSource:
    def __init__(self, facts: ReviewFacts, heads: list[VerifiedLivePullRequestHead] | None = None):
        self.facts = facts
        self.heads = list(heads or [_head()])
        self.fetch_count = 0

    def collect(self, request: ReviewRequest) -> ReviewFacts:
        assert request.target_repository == self.facts.repository
        assert request.pr_number == self.facts.pr_number
        return self.facts

    def fetch(self) -> VerifiedLivePullRequestHead:
        index = min(self.fetch_count, len(self.heads) - 1)
        self.fetch_count += 1
        return self.heads[index]


def _head(*, head_sha: str = HEAD, base_sha: str = BASE) -> VerifiedLivePullRequestHead:
    return VerifiedLivePullRequestHead(
        repository=REPOSITORY,
        repository_id=REPOSITORY_ID,
        pr_number=PR_NUMBER,
        state="open",
        base_branch="main",
        base_sha=base_sha,
        head_branch="feature",
        head_sha=head_sha,
        api_url=f"https://api.github.com/repos/{REPOSITORY}/pulls/{PR_NUMBER}",
        html_url=f"https://github.com/{REPOSITORY}/pull/{PR_NUMBER}",
        receipt_sha256="a" * 64,
    )


def _context() -> ProtocolContext:
    return ProtocolContext("v1.12.0", "rezahh107/PR-Inspector", 1288323264, INSPECTOR)


def _facts(*, ci: str = "success", extra_records: tuple[EvidenceRecord, ...] = ()) -> ReviewFacts:
    diff = EvidenceRecord.create(
        kind="DIFF",
        repository=REPOSITORY,
        pr_number=PR_NUMBER,
        head_sha=HEAD,
        source=f"git:{BASE}..{HEAD}",
        payload={"path": "src/a.py", "changed_lines": 4},
    )
    check = EvidenceRecord.create(
        kind="CI",
        repository=REPOSITORY,
        pr_number=PR_NUMBER,
        head_sha=HEAD,
        source="https://github.com/example/project/actions/runs/1",
        payload={"name": "Validate", "status": "completed", "conclusion": ci, "tested_sha": HEAD},
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
        checks=(CheckFact(check.evidence_id, "Validate", True, "completed", ci, HEAD),),
        evidence_catalog=(diff, check, *extra_records),
        review_started="2026-07-23T10:00:00Z",
        review_completed="2026-07-23T10:01:00Z",
        capabilities={},
    )


def _assessment(*, finding: ReviewFinding | None = None) -> ReviewAssessment:
    return ReviewAssessment(
        review_summary="Implement the requested change.",
        findings=(() if finding is None else (finding,)),
        owner_facing_explanation="The official runtime collected the facts and derived the decision.",
        reviewed_files=("src/a.py",),
    )


def _request(**options) -> ReviewRequest:
    return ReviewRequest(REPOSITORY, PR_NUMBER, execution_options=options)


def _package(*, ci: str = "success", finding: ReviewFinding | None = None) -> CanonicalReviewPackage:
    return assemble_review_package(_facts(ci=ci), _assessment(finding=finding), _context())


def test_schema_valid_caller_package_cannot_mint_completion(tmp_path: Path):
    raw = tmp_path / "review-package.json"
    raw.write_text(json.dumps(_package().value()), encoding="utf-8")
    result = complete_review(package_path=raw, output_directory=tmp_path / "out")
    assert isinstance(result, IncompleteReview)
    assert result.diagnostics[0].code == "PRI-PACKAGE-AUTHORITY-001"
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize(
    "field",
    ["base_sha", "head_sha", "changed_files", "ci_status", "tested_sha", "evidence", "technical_status", "risk", "recommendation", "next_action", "reason_codes", "completion_state"],
)
def test_request_execution_options_cannot_inject_authority(field: str):
    with pytest.raises(ReviewAssemblyError, match="authoritative fields"):
        _request(**{field: "forged"})


def test_assessment_schema_rejects_decision_authority_fields():
    value = {
        "review_summary": "x",
        "owner_facing_explanation": "x",
        "findings": [],
        "technical_status": "GREEN_TECHNICALLY_READY",
    }
    with pytest.raises(ReviewAssemblyError, match="[Aa]dditional properties"):
        parse_review_assessment(value)


def test_valid_evidence_reference_resolves():
    facts = _facts()
    diff = next(item for item in facts.evidence_catalog if item.kind == "DIFF")
    finding = ReviewFinding(
        "FND-001", "Supported finding", "Observed in the diff.", "LOW", False,
        "The reviewer assessed the collected diff.", (diff.evidence_id,), "CODE_SUPPORTED", ("src/a.py",),
    )
    package = assemble_review_package(facts, _assessment(finding=finding), _context()).value()
    assert package["findings"][0]["evidence_refs"] == [diff.evidence_id]


def test_missing_evidence_reference_fails_exactly():
    finding = ReviewFinding(
        "FND-001", "Missing", "Missing evidence.", "LOW", False,
        "The reference must resolve.", ("EVD-DOES-NOT-EXIST",), "CODE_SUPPORTED",
    )
    with pytest.raises(ReviewAssemblyError, match="unknown evidence"):
        assemble_review_package(_facts(), _assessment(finding=finding), _context())


def test_duplicate_conflicting_evidence_fails():
    facts = _facts()
    original = facts.evidence_catalog[0]
    forged = EvidenceRecord(
        original.evidence_id, original.kind, original.repository, original.pr_number,
        original.head_sha, original.source, {"path": "different.py"},
    )
    with pytest.raises(ReviewAssemblyError, match="duplicate conflicting evidence"):
        replace(facts, evidence_catalog=(*facts.evidence_catalog, forged))


@pytest.mark.parametrize(
    ("attribute", "value"),
    [("repository", "other/repo"), ("pr_number", 99), ("head_sha", "4" * 40)],
)
def test_cross_identity_evidence_fails(attribute: str, value):
    facts = _facts()
    original = facts.evidence_catalog[0]
    forged = replace(original, **{attribute: value})
    with pytest.raises(ReviewAssemblyError, match="another repository, PR, or Head|deterministic"):
        replace(facts, evidence_catalog=(forged, *facts.evidence_catalog[1:]))


def test_failed_required_ci_is_blocked():
    value = _package(ci="failure").value()
    assert value["decision"]["technical_status"] != "GREEN_TECHNICALLY_READY"
    assert "required_technical_check_failed" in value["technical_decision"]["reason_codes"]


def test_blocking_finding_is_not_merge_ready():
    finding = ReviewFinding(
        "FND-001", "Blocking defect", "The change can fail.", "HIGH", True,
        "The reviewer identified a blocking failure mode.", (), "HUMAN_JUDGMENT",
    )
    value = _package(finding=finding).value()
    assert value["decision"]["technical_status"] != "GREEN_TECHNICALLY_READY"
    assert value["overall_recommendation"]["technical_ready"] is False


def test_clean_facts_produce_green_through_single_projection():
    value = _package().value()
    projection = project_decision(value)
    assert value["decision"]["technical_status"] == "GREEN_TECHNICALLY_READY"
    assert projection["technical_status"] == value["decision"]["technical_status"]
    assert value["technical_decision"] == projection["technical_decision"]


def test_every_package_field_has_an_explicit_authority_class():
    assert set(FIELD_AUTHORITY.values()) == {"A", "B", "C", "D"}
    value = _package().value()
    assert value["review_identity"]["reviewed_head_sha"] == HEAD
    assert FIELD_AUTHORITY["/review_identity/reviewed_head_sha"] == "A"
    assert FIELD_AUTHORITY["/findings"] == "B"
    assert FIELD_AUTHORITY["/decision"] == "C"
    assert FIELD_AUTHORITY["/protocol_version"] == "D"


def test_repeated_assembly_is_byte_identical():
    facts = _facts()
    assessment = _assessment()
    first = assemble_review_package(facts, assessment, _context())
    second = assemble_review_package(facts, assessment, _context())
    assert canonical_review_package_bytes(first) == canonical_review_package_bytes(second)
    assert first.canonical_sha256 == second.canonical_sha256
    assert project_decision(first.value()) == project_decision(second.value())


def test_private_runtime_seam_collects_and_publishes_once(tmp_path: Path):
    facts = _facts()
    source = StaticSource(facts)
    result = _complete_review_with_runtime(
        _request(), _assessment(), tmp_path / "out",
        runtime=OfficialReviewRuntime(source, _context()),
    )
    assert is_verified_review_completion(result)
    assert (tmp_path / "out" / "review-package.json").is_file()
    assert source.fetch_count >= 3




@pytest.mark.parametrize(
    ("keyword", "value"),
    [
        ("evidence_source", object()),
        ("_protocol_context", _context()),
        ("review_facts", _facts()),
        ("verified_head", _head()),
    ],
)
def test_public_completion_rejects_authority_injection_keywords(
    tmp_path: Path, keyword: str, value: object
):
    with pytest.raises(TypeError, match="unexpected keyword argument"):
        complete_review(
            _request(),
            _assessment(),
            tmp_path / "out",
            **{keyword: value},
        )


def test_public_completion_constructs_internal_runtime(tmp_path: Path, monkeypatch):
    source = StaticSource(_facts())
    runtime = OfficialReviewRuntime(source, _context())
    calls = []

    def factory(request):
        calls.append(request)
        return runtime

    monkeypatch.setattr(official_review_module, "_create_official_runtime", factory)
    result = complete_review(_request(), _assessment(), tmp_path / "out")
    assert is_verified_review_completion(result)
    assert calls == [_request()]


def test_public_module_does_not_export_authority_bearing_runtime_types():
    forbidden = {
        "OfficialReviewRuntime",
        "ReviewEvidenceSource",
        "ReviewFacts",
        "ProtocolContext",
        "GitHubReviewEvidenceSource",
        "CanonicalReviewPackage",
        "VerifiedLivePullRequestHead",
        "assemble_review_package",
    }
    assert forbidden.isdisjoint(set(official_review_module.__all__))

def test_head_drift_before_publication_publishes_nothing(tmp_path: Path):
    facts = _facts()
    source = StaticSource(facts, [_head(), _head(head_sha="4" * 40)])
    result = _complete_review_with_runtime(
        _request(), _assessment(), tmp_path / "out",
        runtime=OfficialReviewRuntime(source, _context()),
    )
    assert isinstance(result, IncompleteReview)
    assert any(item.code == "PRI-COMPLETE-008" for item in result.diagnostics)
    assert not (tmp_path / "out").exists()


def test_head_drift_preserves_existing_valid_bundle(tmp_path: Path):
    output = tmp_path / "out"
    first = _complete_review_with_runtime(
        _request(), _assessment(), output,
        runtime=OfficialReviewRuntime(StaticSource(_facts()), _context()),
    )
    assert is_verified_review_completion(first)
    before = {path.name: path.read_bytes() for path in output.iterdir() if path.is_file()}
    result = _complete_review_with_runtime(
        _request(), _assessment(), output,
        runtime=OfficialReviewRuntime(
            StaticSource(_facts(), [_head(), _head(head_sha="4" * 40)]),
            _context(),
        ),
    )
    assert isinstance(result, IncompleteReview)
    after = {path.name: path.read_bytes() for path in output.iterdir() if path.is_file()}
    assert after == before


def test_render_failure_leaves_no_partial_result(tmp_path: Path, monkeypatch):
    def fail(*args, **kwargs):
        raise ValueError("render failed")
    monkeypatch.setattr(_official_complete, "write_review_artifacts", fail)
    output = tmp_path / "out"
    result = _complete_review_with_runtime(
        _request(), _assessment(), output,
        runtime=OfficialReviewRuntime(StaticSource(_facts()), _context()),
    )
    assert isinstance(result, IncompleteReview)
    assert not output.exists()


def test_legacy_positional_path_returns_stable_migration_diagnostic(tmp_path: Path):
    result = complete_review(tmp_path / "legacy.json", None, tmp_path / "out")
    assert isinstance(result, IncompleteReview)
    assert [item.code for item in result.diagnostics] == ["PRI-PACKAGE-AUTHORITY-001"]


def test_raw_canonical_package_object_is_not_public_completion_input(tmp_path: Path):
    result = complete_review(_package(), None, tmp_path / "out")
    assert isinstance(result, IncompleteReview)
    assert result.diagnostics[0].code == "PRI-PACKAGE-AUTHORITY-001"


def test_repository_closure_has_one_assembler_and_no_temporary_export_workflow():
    root = Path(__file__).resolve().parents[1]
    source = (root / "pr_inspector/verified_review.py").read_text(encoding="utf-8")
    assert source.count("def assemble_review_package(") == 1
    assert not (root / ".github/workflows/export-pr21-rerepair.yml").exists()
    assert not (root / "sitecustomize.py").exists()
    assert not (root / "usercustomize.py").exists()
