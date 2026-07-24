from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pr_inspector._official_head import GitHubPullRequestHeadSource, VerifiedLivePullRequestHead
from pr_inspector.official_review import (
    OfficialReviewRuntime,
    _complete_review_with_runtime,
)
from pr_inspector.verified_review import (
    CanonicalReviewPackage,
    ChangedFile,
    CheckFact,
    EvidenceRecord,
    ProtocolContext,
    ReviewAssessment,
    ReviewFacts,
    ReviewFinding,
    ReviewRequest,
    assemble_review_package,
)
from pr_inspector.governance import VerifiedGovernanceEvidence
from pr_inspector.sequence_enforcement import VerifiedSequenceEnforcement


@dataclass
class StaticEvidenceSource:
    facts: ReviewFacts
    live_head: VerifiedLivePullRequestHead
    delegate: GitHubPullRequestHeadSource | None = None

    def collect(self, request: ReviewRequest) -> ReviewFacts:
        return self.facts

    def fetch(self) -> VerifiedLivePullRequestHead:
        if self.delegate is not None:
            return self.delegate.fetch()
        return self.live_head


@dataclass(frozen=True)
class FixtureReviewRuntime:
    request: ReviewRequest
    assessment: ReviewAssessment
    facts: ReviewFacts
    context: ProtocolContext
    source: StaticEvidenceSource
    package: CanonicalReviewPackage


def _result_from_record(record: dict[str, Any]) -> str:
    result = record.get("result")
    return result if result in {"PASS", "FAIL", "UNKNOWN"} else "UNKNOWN"


def fixture_review_runtime(
    value: dict[str, Any],
    *,
    head_source: GitHubPullRequestHeadSource | None = None,
    governance_evidence: VerifiedGovernanceEvidence | None = None,
    sequence_enforcement: VerifiedSequenceEnforcement | None = None,
) -> FixtureReviewRuntime:
    identity = value["review_identity"]
    request = ReviewRequest(
        target_repository=identity["target_repository"],
        pr_number=identity["pr_number"],
        inspection_profile=value.get("inspection_profile", "minimal"),
    )
    head = VerifiedLivePullRequestHead(
        repository=identity["target_repository"],
        repository_id=identity.get("target_repository_id", 4242),
        pr_number=identity["pr_number"],
        state="open",
        base_branch=identity["base_branch"],
        base_sha=identity["base_sha"],
        head_branch=identity["head_branch"],
        head_sha=identity["reviewed_head_sha"],
        api_url=f"https://api.github.com/repos/{identity['target_repository']}/pulls/{identity['pr_number']}",
        html_url=f"https://github.com/{identity['target_repository']}/pull/{identity['pr_number']}",
        receipt_sha256="a" * 64,
    )

    scope = value["scope"]
    paths = sorted(
        set(scope.get("files_fully_reviewed", []))
        | set(scope.get("files_partially_reviewed", []))
        | set(scope.get("files_not_reviewed", []))
    )
    while len(paths) < scope.get("total_changed_files", len(paths)):
        paths.append(f"__fixture__/file-{len(paths) + 1}.txt")
    total_lines = scope.get("total_changed_lines", 0)
    changed_files = tuple(
        ChangedFile(path, total_lines if index == 0 else 0)
        for index, path in enumerate(paths)
    )

    old_to_new: dict[str, str] = {}
    records: list[EvidenceRecord] = []
    for raw in value.get("evidence_records", []):
        kind = raw.get("evidence_type", "CODE")
        record = EvidenceRecord.create(
            kind=kind,
            repository=head.repository,
            pr_number=head.pr_number,
            head_sha=head.head_sha,
            source=raw.get("source") or raw.get("reference") or "fixture",
            payload={
                "excerpt": raw.get("excerpt", "fixture evidence"),
                "reference": raw.get("reference"),
                "result": _result_from_record(raw),
                "conclusion": "success" if _result_from_record(raw) == "PASS" else "failure" if _result_from_record(raw) == "FAIL" else None,
            },
        )
        old_to_new[raw["evidence_id"]] = record.evidence_id
        records.append(record)

    known_diff_paths = {
        record.payload.get("path")
        for record in records
        if record.kind in {"DIFF", "CODE"}
    }
    for changed in changed_files:
        if changed.path in known_diff_paths:
            continue
        records.append(
            EvidenceRecord.create(
                kind="DIFF",
                repository=head.repository,
                pr_number=head.pr_number,
                head_sha=head.head_sha,
                source=f"fixture-diff:{changed.path}",
                payload={"path": changed.path, "changed_lines": changed.changed_lines},
            )
        )

    checks: list[CheckFact] = []
    record_by_old = {item["evidence_id"]: item for item in value.get("evidence_records", [])}
    for raw in value.get("checks", []):
        old_id = raw.get("evidence_id")
        if old_id not in old_to_new:
            source_raw = record_by_old.get(old_id, {})
            record = EvidenceRecord.create(
                kind="CI",
                repository=head.repository,
                pr_number=head.pr_number,
                head_sha=head.head_sha,
                source=source_raw.get("source", "fixture-ci"),
                payload={
                    "name": raw.get("name", "fixture check"),
                    "result": raw.get("result", "UNKNOWN"),
                    "conclusion": "success" if raw.get("result") == "PASS" else "failure" if raw.get("result") == "FAIL" else None,
                },
            )
            old_to_new[old_id] = record.evidence_id
            records.append(record)
        result = raw.get("result", "UNKNOWN")
        checks.append(
            CheckFact(
                evidence_id=old_to_new[old_id],
                name=raw.get("name", "fixture check"),
                required=raw.get("required", True),
                status="completed",
                conclusion="success" if result == "PASS" else "failure" if result == "FAIL" else None,
                tested_sha=head.head_sha,
            )
        )

    findings = tuple(
        ReviewFinding(
            finding_id=item["finding_id"],
            title=item["issue"],
            description=item["failure_scenario"],
            severity=item["severity"],
            blocking=item["blocking"],
            reviewer_rationale=item.get("reviewer_rationale", item["issue"]),
            evidence_class=(
                item.get("evidence_label")
                if item.get("evidence_label") in {"CODE_SUPPORTED", "REPRODUCED", "NOT_ASSESSABLE"}
                else "HUMAN_JUDGMENT"
            ),
            evidence_refs=tuple(old_to_new[ref] for ref in item.get("evidence_refs", []) if ref in old_to_new),
            affected_surfaces=tuple(
                [item["file_location"]]
                if item.get("file_location") not in {None, "", "not_applicable"}
                else []
            ),
            suggested_action=item.get("recommended_fix", "Review the finding."),
            recommended_test=item.get("recommended_test", "Run relevant validation."),
            relevant_code=item.get("relevant_code", "not_captured"),
            rule_ids=tuple(item.get("rule_ids", [])),
            symbol=item.get("symbol", "not_applicable"),
        )
        for item in value.get("findings", [])
    )
    assessment = ReviewAssessment(
        review_summary=value.get("change_summary", {}).get("intended_behavior", "Fixture review"),
        findings=findings,
        owner_facing_explanation=value.get("owner_card", {}).get("summary", "Fixture review result."),
        reviewed_files=tuple(scope.get("files_fully_reviewed", [])),
        unverified_areas=tuple(value.get("unverified_areas", [])),
        out_of_scope_observations=tuple(value.get("out_of_scope_observations", [])),
        suggested_actions=tuple(value.get("required_actions", [])),
    )
    facts = ReviewFacts(
        repository=head.repository,
        repository_id=head.repository_id,
        pr_number=head.pr_number,
        pr_state=head.state,
        base_branch=head.base_branch,
        base_sha=head.base_sha,
        head_branch=head.head_branch,
        head_sha=head.head_sha,
        merge_base_sha=identity["merge_base_sha"],
        changed_files=changed_files,
        checks=tuple(checks),
        evidence_catalog=tuple(records),
        review_started=identity.get("review_started", "2026-07-03T10:00:00Z"),
        review_completed=identity.get("review_completed", "2026-07-03T10:10:00Z"),
        capabilities=value.get("capabilities", {}),
    )
    context = ProtocolContext(
        protocol_version="v1.12.0",
        inspector_repository=identity["inspector_repository"],
        inspector_repository_id=1288323264,
        inspector_commit_sha=identity["inspector_commit_sha"],
    )
    source = StaticEvidenceSource(facts, head, delegate=head_source)
    package = assemble_review_package(
        facts,
        assessment,
        context,
        inspection_profile=request.inspection_profile,
        governance_evidence=governance_evidence,
        sequence_enforcement=sequence_enforcement,
    )
    return FixtureReviewRuntime(request, assessment, facts, context, source, package)


def verified_package_from_fixture(
    value: dict[str, Any],
    *,
    governance_evidence: VerifiedGovernanceEvidence | None = None,
    sequence_enforcement: VerifiedSequenceEnforcement | None = None,
) -> CanonicalReviewPackage:
    return fixture_review_runtime(
        value,
        governance_evidence=governance_evidence,
        sequence_enforcement=sequence_enforcement,
    ).package


def complete_fixture_review(
    value: dict[str, Any],
    output,
    *,
    head_source: GitHubPullRequestHeadSource | None = None,
    governance_evidence: VerifiedGovernanceEvidence | None = None,
    sequence_enforcement: VerifiedSequenceEnforcement | None = None,
):
    runtime = fixture_review_runtime(
        value,
        head_source=head_source,
        governance_evidence=governance_evidence,
        sequence_enforcement=sequence_enforcement,
    )
    result = _complete_review_with_runtime(
        runtime.request,
        runtime.assessment,
        output,
        runtime=OfficialReviewRuntime(
            runtime.source,
            runtime.context,
            governance_evidence,
            sequence_enforcement,
        ),
    )
    return result, runtime.package
