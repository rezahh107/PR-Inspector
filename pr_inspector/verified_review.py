"""Deterministic in-process review-package assembly for protocol v1.12.0.

The public runtime accepts only caller intent (`ReviewRequest`) and bounded reviewer
analysis (`ReviewAssessment`).  Repository identity, Base/Head, changed files, CI,
evidence, and Inspector metadata are collected by the configured evidence source.
The canonical package is assembled in memory and is never accepted from a caller file.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping, Protocol, Sequence, runtime_checkable

from jsonschema import Draft202012Validator

from ._official_head import GitHubPullRequestHeadSource, VerifiedLivePullRequestHead
from .decision_projection import project_decision
from .evidence_context import evidence_scope
from .governance import VerifiedGovernanceEvidence
from .render import package_sha256
from .sequence_enforcement import VerifiedSequenceEnforcement
from .validation_v2 import validate_package

ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT_SCHEMA = ROOT / "protocols/v1.12.0/schemas/review-assessment.schema.json"
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
_ALLOWED_EVIDENCE_CLASSES = {
    "HUMAN_JUDGMENT",
    "HYPOTHESIS",
    "CODE_SUPPORTED",
    "REPRODUCED",
    "NOT_ASSESSABLE",
}

# Every canonical package surface resolves to one and only one authority class.
# More-specific paths override broader prefixes.
FIELD_AUTHORITY: Mapping[str, str] = {
    "/schema_version": "D",
    "/protocol_version": "D",
    "/inspection_profile": "D",
    "/review_identity/target_repository": "A",
    "/review_identity/target_repository_id": "A",
    "/review_identity/pr_number": "A",
    "/review_identity/base_branch": "A",
    "/review_identity/base_sha": "A",
    "/review_identity/head_branch": "A",
    "/review_identity/reviewed_head_sha": "A",
    "/review_identity/merge_base_sha": "A",
    "/review_identity/inspector_repository": "D",
    "/review_identity/inspector_commit_sha": "D",
    "/review_identity/review_started": "A",
    "/review_identity/review_completed": "A",
    "/review_identity": "C",
    "/capabilities": "A",
    "/scope": "C",
    "/change_summary": "B",
    "/evidence_records": "A",
    "/checks": "C",
    "/findings": "B",
    "/unverified_areas": "B",
    "/required_actions": "B",
    "/out_of_scope_observations": "B",
    "/owner_card": "B",
    "/red_gate_flags": "C",
    "/security_profile": "D",
    "/intent_fit": "C",
    "/external_review_intake": "A",
    "/external_review_reconciliation": "C",
    "/decision": "C",
    "/technical_decision": "C",
    "/governance_decision": "C",
    "/overall_recommendation": "C",
}


class ReviewAssemblyError(ValueError):
    """Raised when facts, assessment, evidence references, or assembly are invalid."""


@dataclass(frozen=True)
class ReviewRequest:
    """Caller-selectable intent only; no factual or decision authority."""

    target_repository: str
    pr_number: int
    inspection_profile: str = "minimal"
    governance_profile: str | None = None
    execution_options: Mapping[str, Any] = field(default_factory=dict, compare=False)

    def __post_init__(self) -> None:
        if self.target_repository.count("/") != 1 or any(
            not part for part in self.target_repository.split("/")
        ):
            raise ReviewAssemblyError("target_repository must use OWNER/REPOSITORY")
        if not isinstance(self.pr_number, int) or isinstance(self.pr_number, bool) or self.pr_number < 1:
            raise ReviewAssemblyError("pr_number must be a positive integer")
        if self.inspection_profile not in {"minimal", "strict"}:
            raise ReviewAssemblyError("inspection_profile must be minimal or strict")
        forbidden = {
            "repository_id", "base_sha", "head_sha", "merge_base_sha", "changed_files",
            "ci_status", "tested_sha", "evidence", "technical_status", "risk",
            "recommendation", "next_action", "reason_codes", "completion_state",
        }
        overlap = forbidden.intersection(self.execution_options)
        if overlap:
            raise ReviewAssemblyError(
                "execution_options contains authoritative fields: " + ", ".join(sorted(overlap))
            )


@dataclass(frozen=True)
class ChangedFile:
    path: str
    changed_lines: int

    def __post_init__(self) -> None:
        pure = PurePosixPath(self.path)
        if pure.is_absolute() or ".." in pure.parts or not pure.parts:
            raise ReviewAssemblyError(f"invalid changed-file path: {self.path}")
        if self.changed_lines < 0:
            raise ReviewAssemblyError("changed_lines cannot be negative")


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    kind: str
    repository: str
    pr_number: int
    head_sha: str
    source: str
    payload: Mapping[str, Any]

    @classmethod
    def create(
        cls,
        *,
        kind: str,
        repository: str,
        pr_number: int,
        head_sha: str,
        source: str,
        payload: Mapping[str, Any],
    ) -> "EvidenceRecord":
        normalized = json.loads(_canonical_json_bytes(dict(payload)).decode("utf-8"))
        identity = {
            "kind": kind,
            "repository": repository,
            "pr_number": pr_number,
            "head_sha": head_sha,
            "source": source,
            "payload": normalized,
        }
        evidence_id = "EVD-" + _sha256(_canonical_json_bytes(identity))[:16].upper()
        return cls(evidence_id, kind, repository, pr_number, head_sha, source, normalized)

    def expected_id(self) -> str:
        return EvidenceRecord.create(
            kind=self.kind,
            repository=self.repository,
            pr_number=self.pr_number,
            head_sha=self.head_sha,
            source=self.source,
            payload=self.payload,
        ).evidence_id


@dataclass(frozen=True)
class CheckFact:
    evidence_id: str
    name: str
    required: bool
    status: str
    conclusion: str | None
    tested_sha: str

    @property
    def result(self) -> str:
        if self.conclusion == "success":
            return "PASS"
        if self.conclusion in {"failure", "timed_out", "action_required", "cancelled"}:
            return "FAIL"
        return "UNKNOWN"


@dataclass(frozen=True)
class ReviewFacts:
    repository: str
    repository_id: int
    pr_number: int
    pr_state: str
    base_branch: str
    base_sha: str
    head_branch: str
    head_sha: str
    merge_base_sha: str
    changed_files: tuple[ChangedFile, ...]
    checks: tuple[CheckFact, ...]
    evidence_catalog: tuple[EvidenceRecord, ...]
    review_started: str
    review_completed: str
    capabilities: Mapping[str, str]

    def __post_init__(self) -> None:
        for name, sha in (
            ("base_sha", self.base_sha),
            ("head_sha", self.head_sha),
            ("merge_base_sha", self.merge_base_sha),
        ):
            if SHA40_RE.fullmatch(sha) is None:
                raise ReviewAssemblyError(f"{name} must be a 40-character lowercase SHA")
        if self.repository_id < 1 or self.pr_number < 1:
            raise ReviewAssemblyError("repository_id and pr_number must be positive")
        if self.pr_state not in {"open", "closed"}:
            raise ReviewAssemblyError("pr_state must be open or closed")
        paths = [item.path for item in self.changed_files]
        if len(paths) != len(set(paths)):
            raise ReviewAssemblyError("changed_files contains duplicate paths")
        _validate_evidence_catalog(self)
        check_ids = {item.evidence_id for item in self.checks}
        catalog_ids = {item.evidence_id for item in self.evidence_catalog}
        missing = check_ids - catalog_ids
        if missing:
            raise ReviewAssemblyError(
                "checks reference missing evidence: " + ", ".join(sorted(missing))
            )
        for check in self.checks:
            if check.tested_sha != self.head_sha:
                raise ReviewAssemblyError(
                    f"check {check.name} is bound to another Head: {check.tested_sha}"
                )


@dataclass(frozen=True)
class ReviewFinding:
    finding_id: str
    title: str
    description: str
    severity: str
    blocking: bool
    reviewer_rationale: str
    evidence_refs: tuple[str, ...] = ()
    evidence_class: str = "HUMAN_JUDGMENT"
    affected_surfaces: tuple[str, ...] = ()
    suggested_action: str = "Review and address the finding."
    recommended_test: str = "Run the narrowest relevant validation."
    relevant_code: str = "not_captured"
    rule_ids: tuple[str, ...] = ()
    symbol: str = "not_applicable"

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Z][A-Z0-9_-]{2,63}", self.finding_id):
            raise ReviewAssemblyError(f"invalid finding_id: {self.finding_id}")
        if self.severity not in {"CRITICAL", "HIGH", "MEDIUM", "LOW"}:
            raise ReviewAssemblyError(f"invalid severity for {self.finding_id}")
        if self.evidence_class not in _ALLOWED_EVIDENCE_CLASSES:
            raise ReviewAssemblyError(f"invalid evidence_class for {self.finding_id}")
        if len(self.evidence_refs) != len(set(self.evidence_refs)):
            raise ReviewAssemblyError(f"duplicate evidence reference in {self.finding_id}")


@dataclass(frozen=True)
class ReviewAssessment:
    review_summary: str
    findings: tuple[ReviewFinding, ...]
    owner_facing_explanation: str
    reviewed_files: tuple[str, ...] = ()
    unverified_areas: tuple[str, ...] = ()
    out_of_scope_observations: tuple[str, ...] = ()
    suggested_actions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.review_summary or not self.owner_facing_explanation:
            raise ReviewAssemblyError("review_summary and owner_facing_explanation are required")
        ids = [item.finding_id for item in self.findings]
        if len(ids) != len(set(ids)):
            raise ReviewAssemblyError("finding_id values must be unique")
        reviewed = [PurePosixPath(path).as_posix() for path in self.reviewed_files]
        if len(reviewed) != len(set(reviewed)):
            raise ReviewAssemblyError("reviewed_files contains duplicates")


@dataclass(frozen=True)
class ProtocolContext:
    protocol_version: str
    inspector_repository: str
    inspector_repository_id: int
    inspector_commit_sha: str

    @classmethod
    def from_repository(cls, repository_directory: Path = ROOT) -> "ProtocolContext":
        root = Path(repository_directory).resolve()
        version = (root / "CURRENT_VERSION").read_text(encoding="utf-8").strip()
        manifest = _load_json_or_yaml(root / "protocol-manifest.yaml")
        if manifest.get("active_version") != version:
            raise ReviewAssemblyError("CURRENT_VERSION and protocol-manifest active_version differ")
        trust = json.loads(
            (root / f"protocols/{version}/trust/INSPECTOR_TRUST_POLICY.json").read_text(
                encoding="utf-8"
            )
        )
        commit_sha = _run_git(root, "rev-parse", "HEAD")
        if SHA40_RE.fullmatch(commit_sha) is None:
            raise ReviewAssemblyError("Inspector runtime commit SHA is invalid")
        return cls(
            protocol_version=version,
            inspector_repository=trust["inspector_repository"],
            inspector_repository_id=trust["inspector_repository_id"],
            inspector_commit_sha=commit_sha,
        )


@dataclass(frozen=True)
class CanonicalReviewPackage:
    protocol_version: str
    repository: str
    repository_id: int
    pr_number: int
    base_sha: str
    head_sha: str
    canonical_sha256: str
    file_sha256: str
    canonical_bytes: bytes = field(repr=False)

    def value(self) -> dict[str, Any]:
        value = json.loads(self.canonical_bytes.decode("utf-8"))
        if package_sha256(value) != self.canonical_sha256:
            raise ReviewAssemblyError("canonical package value changed")
        if _sha256(self.canonical_bytes) != self.file_sha256:
            raise ReviewAssemblyError("canonical package bytes changed")
        return value


@runtime_checkable
class ReviewEvidenceSource(Protocol):
    def collect(self, request: ReviewRequest) -> ReviewFacts:
        ...

    def fetch(self) -> VerifiedLivePullRequestHead:
        """Fetch the current live PR identity for publication rechecks."""
        ...


@dataclass(frozen=True)
class GitHubReviewEvidenceSource:
    """Default production collector using the existing live Head source and local git."""

    repository_directory: Path
    head_source: GitHubPullRequestHeadSource
    token: str | None = field(default=None, repr=False, compare=False)
    api_version: str = "2022-11-28"
    required_check_names: tuple[str, ...] = ()
    clock: Callable[[], datetime] = field(
        default=lambda: datetime.now(timezone.utc), repr=False, compare=False
    )

    def fetch(self) -> VerifiedLivePullRequestHead:
        return self.head_source.fetch()

    def collect(self, request: ReviewRequest) -> ReviewFacts:
        started = _iso(self.clock())
        head = self.fetch()
        if (request.target_repository, request.pr_number) != (head.repository, head.pr_number):
            raise ReviewAssemblyError("ReviewRequest does not match the collected live PR")
        directory = Path(self.repository_directory).resolve()
        if _run_git(directory, "rev-parse", "HEAD") != head.head_sha:
            raise ReviewAssemblyError("collector checkout HEAD does not match the live PR Head")
        merge_base = _run_git(directory, "merge-base", head.base_sha, head.head_sha)
        changed_files = _collect_changed_files(directory, merge_base, head.head_sha)
        evidence: list[EvidenceRecord] = []
        for item in changed_files:
            evidence.append(
                EvidenceRecord.create(
                    kind="DIFF",
                    repository=head.repository,
                    pr_number=head.pr_number,
                    head_sha=head.head_sha,
                    source=f"git:{merge_base}..{head.head_sha}",
                    payload={"path": item.path, "changed_lines": item.changed_lines},
                )
            )
        checks, check_evidence = self._collect_checks(head)
        evidence.extend(check_evidence)
        evidence.extend(self._collect_review_surfaces(head))
        completed = _iso(self.clock())
        return ReviewFacts(
            repository=head.repository,
            repository_id=head.repository_id,
            pr_number=head.pr_number,
            pr_state=head.state,
            base_branch=head.base_branch,
            base_sha=head.base_sha,
            head_branch=head.head_branch,
            head_sha=head.head_sha,
            merge_base_sha=merge_base,
            changed_files=changed_files,
            checks=checks,
            evidence_catalog=tuple(evidence),
            review_started=started,
            review_completed=completed,
            capabilities={
                "repository_read": "AVAILABLE",
                "pr_metadata_diff": "AVAILABLE",
                "git_github": "AVAILABLE",
                "network": "AVAILABLE",
                "shell_sandbox": "AVAILABLE",
                "test_execution": "AVAILABLE_BUT_NOT_USED",
                "ci_status_logs": "AVAILABLE" if checks else "UNAVAILABLE",
                "dependency_security_metadata": "UNAVAILABLE",
                "credential_access": "UNAVAILABLE",
                "production": "UNAVAILABLE",
            },
        )

    def _collect_checks(
        self, head: VerifiedLivePullRequestHead
    ) -> tuple[tuple[CheckFact, ...], tuple[EvidenceRecord, ...]]:
        url = f"https://api.github.com/repos/{head.repository}/commits/{head.head_sha}/check-runs"
        payload = _fetch_github_json(url, token=self.token, api_version=self.api_version)
        raw_runs = payload.get("check_runs", []) if isinstance(payload, Mapping) else []
        checks: list[CheckFact] = []
        evidence: list[EvidenceRecord] = []
        for raw in raw_runs:
            if not isinstance(raw, Mapping):
                continue
            tested_sha = raw.get("head_sha")
            if tested_sha != head.head_sha:
                raise ReviewAssemblyError("collected check is bound to another Head")
            name = raw.get("name")
            status = raw.get("status")
            conclusion = raw.get("conclusion")
            if not isinstance(name, str) or not name or not isinstance(status, str):
                raise ReviewAssemblyError("collected check is missing required identity")
            record = EvidenceRecord.create(
                kind="CI",
                repository=head.repository,
                pr_number=head.pr_number,
                head_sha=head.head_sha,
                source=str(raw.get("details_url") or url),
                payload={
                    "name": name,
                    "status": status,
                    "conclusion": conclusion,
                    "tested_sha": tested_sha,
                    "check_run_id": raw.get("id"),
                },
            )
            required = not self.required_check_names or name in self.required_check_names
            checks.append(CheckFact(record.evidence_id, name, required, status, conclusion, tested_sha))
            evidence.append(record)
        return tuple(checks), tuple(evidence)

    def _collect_review_surfaces(
        self, head: VerifiedLivePullRequestHead
    ) -> tuple[EvidenceRecord, ...]:
        records: list[EvidenceRecord] = []
        endpoints = (
            ("COMMENT", f"https://api.github.com/repos/{head.repository}/issues/{head.pr_number}/comments"),
            ("REVIEW", f"https://api.github.com/repos/{head.repository}/pulls/{head.pr_number}/reviews"),
        )
        for kind, url in endpoints:
            payload = _fetch_github_json(url, token=self.token, api_version=self.api_version)
            if not isinstance(payload, list):
                raise ReviewAssemblyError(f"{kind.lower()} endpoint did not return a list")
            for raw in payload:
                if not isinstance(raw, Mapping):
                    continue
                records.append(
                    EvidenceRecord.create(
                        kind=kind,
                        repository=head.repository,
                        pr_number=head.pr_number,
                        head_sha=head.head_sha,
                        source=str(raw.get("html_url") or raw.get("url") or url),
                        payload={
                            "id": raw.get("id"),
                            "state": raw.get("state"),
                            "user": (raw.get("user") or {}).get("login")
                            if isinstance(raw.get("user"), Mapping)
                            else None,
                            "body": raw.get("body", ""),
                        },
                    )
                )
        return tuple(records)


def parse_review_assessment(value: Mapping[str, Any]) -> ReviewAssessment:
    if not isinstance(value, Mapping):
        raise ReviewAssemblyError("ReviewAssessment must be a mapping")
    schema = json.loads(ASSESSMENT_SCHEMA.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(dict(value)),
        key=lambda item: list(item.absolute_path),
    )
    if errors:
        rendered = "; ".join(
            f"/{'/'.join(map(str, error.absolute_path))}: {error.message}" for error in errors
        )
        raise ReviewAssemblyError(f"ReviewAssessment validation failed: {rendered}")
    findings = tuple(
        ReviewFinding(
            finding_id=item["finding_id"],
            title=item["title"],
            description=item["description"],
            severity=item["severity"],
            blocking=item["blocking"],
            reviewer_rationale=item["reviewer_rationale"],
            evidence_refs=tuple(item.get("evidence_refs", [])),
            evidence_class=item.get("evidence_class", "HUMAN_JUDGMENT"),
            affected_surfaces=tuple(item.get("affected_surfaces", [])),
            suggested_action=item.get("suggested_action", "Review and address the finding."),
            recommended_test=item.get("recommended_test", "Run the narrowest relevant validation."),
            relevant_code=item.get("relevant_code", "not_captured"),
            rule_ids=tuple(item.get("rule_ids", [])),
            symbol=item.get("symbol", "not_applicable"),
        )
        for item in value["findings"]
    )
    return ReviewAssessment(
        review_summary=value["review_summary"],
        findings=findings,
        owner_facing_explanation=value["owner_facing_explanation"],
        reviewed_files=tuple(value.get("reviewed_files", [])),
        unverified_areas=tuple(value.get("unverified_areas", [])),
        out_of_scope_observations=tuple(value.get("out_of_scope_observations", [])),
        suggested_actions=tuple(value.get("suggested_actions", [])),
    )


# Narrow source-compatibility alias for callers that used the unreleased v1.12 draft name.
parse_review_draft = parse_review_assessment
ReviewDraft = ReviewAssessment


def collect_review_facts(
    request: ReviewRequest, evidence_source: ReviewEvidenceSource
) -> ReviewFacts:
    if not isinstance(request, ReviewRequest):
        raise ReviewAssemblyError("request must be ReviewRequest")
    if not isinstance(evidence_source, ReviewEvidenceSource):
        raise ReviewAssemblyError("evidence_source must implement collect() and fetch()")
    facts = evidence_source.collect(request)
    if not isinstance(facts, ReviewFacts):
        raise ReviewAssemblyError("evidence_source.collect() must return ReviewFacts")
    if (facts.repository, facts.pr_number) != (request.target_repository, request.pr_number):
        raise ReviewAssemblyError("collected facts do not match ReviewRequest")
    return facts


def assemble_review_package(
    facts: ReviewFacts,
    assessment: ReviewAssessment,
    protocol_context: ProtocolContext,
    *,
    inspection_profile: str = "minimal",
    governance_evidence: VerifiedGovernanceEvidence | None = None,
    sequence_enforcement: VerifiedSequenceEnforcement | None = None,
) -> CanonicalReviewPackage:
    """Pure deterministic package assembly from collected facts and bounded analysis."""

    if not isinstance(facts, ReviewFacts):
        raise ReviewAssemblyError("facts must be ReviewFacts")
    if not isinstance(assessment, ReviewAssessment):
        raise ReviewAssemblyError("assessment must be ReviewAssessment")
    if not isinstance(protocol_context, ProtocolContext):
        raise ReviewAssemblyError("protocol_context must be ProtocolContext")
    if protocol_context.protocol_version != "v1.12.0":
        raise ReviewAssemblyError("official assembler requires active protocol v1.12.0")
    if inspection_profile not in {"minimal", "strict"}:
        raise ReviewAssemblyError("inspection_profile must be minimal or strict")
    if inspection_profile == "strict" and governance_evidence is None:
        raise ReviewAssemblyError("strict profile requires governance evidence")

    evidence_by_id = _validate_evidence_catalog(facts)
    findings = [_finding_record(item, evidence_by_id, facts) for item in assessment.findings]
    changed_paths = {item.path for item in facts.changed_files}
    reviewed_paths = set(assessment.reviewed_files)
    unknown_reviewed = reviewed_paths - changed_paths
    if unknown_reviewed:
        raise ReviewAssemblyError(
            "assessment reviewed_files are outside the collected diff: "
            + ", ".join(sorted(unknown_reviewed))
        )
    files_fully_reviewed = sorted(reviewed_paths)
    files_not_reviewed = sorted(changed_paths - reviewed_paths)
    coverage_complete = not files_not_reviewed

    evidence_records = [_package_evidence_record(item) for item in facts.evidence_catalog]
    checks = [
        {
            "check_id": f"CHK-{index:03d}",
            "evidence_id": item.evidence_id,
            "name": item.name,
            "required": item.required,
            "result": item.result,
            "state": "CI_INSPECTED",
        }
        for index, item in enumerate(facts.checks, 1)
    ]
    external_sources = [
        {
            "source_id": item.evidence_id,
            "source_type": item.kind,
            "source_name": item.source,
            "source_status": "INSPECTED",
        }
        for item in facts.evidence_catalog
        if item.kind in {"COMMENT", "REVIEW"}
    ]
    capabilities = {
        "repository_read": "UNAVAILABLE",
        "pr_metadata_diff": "UNAVAILABLE",
        "git_github": "UNAVAILABLE",
        "network": "UNAVAILABLE",
        "shell_sandbox": "UNAVAILABLE",
        "test_execution": "UNAVAILABLE",
        "ci_status_logs": "UNAVAILABLE",
        "dependency_security_metadata": "UNAVAILABLE",
        "credential_access": "UNAVAILABLE",
        "production": "UNAVAILABLE",
    }
    capabilities.update(dict(facts.capabilities))

    package: dict[str, Any] = {
        "schema_version": 1,
        "protocol_version": protocol_context.protocol_version,
        "inspection_profile": inspection_profile,
        "review_identity": {
            "target_repository": facts.repository,
            "target_repository_id": facts.repository_id,
            "pr_number": facts.pr_number,
            "base_branch": facts.base_branch,
            "base_sha": facts.base_sha,
            "head_branch": facts.head_branch,
            "reviewed_head_sha": facts.head_sha,
            "merge_base_sha": facts.merge_base_sha,
            "inspector_repository": protocol_context.inspector_repository,
            "inspector_commit_sha": protocol_context.inspector_commit_sha,
            "review_started": facts.review_started,
            "review_completed": facts.review_completed,
            "review_mode": "FULL" if coverage_complete else "PARTIAL",
            "execution_mode": "CI_EVIDENCE_ONLY" if facts.checks else "NONE",
            "review_validity": "CURRENT",
        },
        "capabilities": capabilities,
        "scope": {
            "coverage_complete": coverage_complete,
            "excluded_generated_or_vendor_files": [],
            "files_fully_reviewed": files_fully_reviewed,
            "files_not_reviewed": files_not_reviewed,
            "files_partially_reviewed": [],
            "files_reviewed_outside_diff": [],
            "high_risk_areas_not_reviewed": [],
            "high_risk_areas_reviewed": [],
            "scope_limit_reason": None if coverage_complete else "reviewer assessment did not cover every collected changed file",
            "total_changed_files": len(facts.changed_files),
            "total_changed_lines": sum(item.changed_lines for item in facts.changed_files),
        },
        "change_summary": {
            "intended_behavior": assessment.review_summary,
            "previous_behavior": "not asserted by the bounded assessment",
            "actual_implementation": "machine-collected facts plus bounded reviewer assessment",
            "mismatch": "",
        },
        "evidence_records": evidence_records,
        "checks": checks,
        "findings": findings,
        "unverified_areas": list(assessment.unverified_areas),
        "required_actions": list(assessment.suggested_actions),
        "out_of_scope_observations": list(assessment.out_of_scope_observations),
        "owner_card": {
            "summary": assessment.owner_facing_explanation,
            "checked": "Repository identity, exact Base/Head, changed files, evidence references, and available CI were collected by the official runtime.",
            "risk": "Technical status is derived only by the canonical decision projection.",
            "unknown": "; ".join(assessment.unverified_areas) if assessment.unverified_areas else "No reviewer-declared unknowns.",
            "specialist_reason": "Strict profile requires governance evidence." if inspection_profile == "strict" else "Minimal profile uses the deterministic in-process assembler.",
            "mental_model": None,
        },
        "red_gate_flags": [],
        "security_profile": {
            "profile_name": "personal_single_operator_correctness",
            "security_activation_trigger": False,
            "explicit_repository_requirement": False,
            "external_requirement": False,
            "claim_merge_authorized": False,
            "claim_repository_settings_enforced": governance_evidence is not None,
            "governance_evidence_id": getattr(governance_evidence, "evidence_id", None),
            "sequence_ci_enforced": bool(sequence_enforcement) or (
                bool(facts.checks)
                and all((not check.required) or check.result == "PASS" for check in facts.checks)
            ),
        },
        "intent_fit": {
            "intent_source": "review_request",
            "stated_intent": assessment.review_summary,
            "intent_fit_result": (
                "satisfied"
                if coverage_complete
                and all((not check.required) or check.result == "PASS" for check in facts.checks)
                and not any(item["blocking"] for item in findings)
                else "not_assessable"
            ),
            "implementation_evidence": [
                {
                    "evidence_label": "CODE_SUPPORTED",
                    "evidence_refs": [record.evidence_id for record in facts.evidence_catalog if record.kind in {"DIFF", "CI"}],
                    "evidence_summary": "Exact diff identity and available exact-Head CI were collected by the official runtime.",
                    "file": "multiple" if len(facts.changed_files) != 1 else facts.changed_files[0].path,
                    "lines_or_symbol": "collected_diff",
                }
            ] if coverage_complete and facts.evidence_catalog else [],
            "unsupported_claims": [],
        },
        "external_review_intake": {"sources_inspected": external_sources, "suggestions": []},
        "external_review_reconciliation": {
            "collection_status": "COMPLETE",
            "counts": {
                "accepted": 0,
                "deferred": 0,
                "duplicate": 0,
                "false_positive": 0,
                "insufficient_evidence": 0,
                "out_of_scope": 0,
                "resolved": 0,
                "stale": 0,
            },
            "inspected_total": len(external_sources),
            "open_bot_sources_total": 0,
            "suggestion_results": [],
            "uninspected_source_ids": [],
            "valid_blocking_finding_ids": [item["finding_id"] for item in findings if item["blocking"]],
        },
        # Seed values are overwritten below by the sole decision authority.
        "decision": {
            "technical_status": "YELLOW_CHANGES_OR_VERIFICATION_REQUIRED",
            "risk_classification": "LOW",
            "approval_requirement": "NO_ADDITIONAL_TECHNICAL_APPROVAL",
            "sensitive_domains": [],
            "blocking_findings_count": sum(1 for item in findings if item["blocking"]),
            "next_required_action": assessment.suggested_actions[0] if assessment.suggested_actions else "Review the canonical decision projection.",
        },
        "technical_decision": {"status": "YELLOW", "reason_codes": []},
        "governance_decision": {"status": "NOT_REQUESTED", "reason_codes": []},
        "overall_recommendation": {"technical_ready": False, "merge_governance_verified": False},
    }
    with evidence_scope(governance_evidence, sequence_enforcement):
        projection = project_decision(package, governance_evidence, sequence_enforcement)
        package["decision"]["technical_status"] = projection["technical_status"]
        package["technical_decision"] = dict(projection["technical_decision"])
        package["governance_decision"] = dict(projection["governance_decision"])
        package["overall_recommendation"] = dict(projection["overall_recommendation"])
        diagnostics = validate_package(package, governance_evidence, sequence_enforcement)
    if diagnostics:
        raise ReviewAssemblyError(
            "assembled package failed canonical validation: "
            + "; ".join(item.line() for item in diagnostics)
        )
    _assert_field_authority_complete(package)
    canonical = _canonical_json_bytes(package)
    return CanonicalReviewPackage(
        protocol_version=protocol_context.protocol_version,
        repository=facts.repository,
        repository_id=facts.repository_id,
        pr_number=facts.pr_number,
        base_sha=facts.base_sha,
        head_sha=facts.head_sha,
        canonical_sha256=package_sha256(package),
        file_sha256=_sha256(canonical),
        canonical_bytes=canonical,
    )


# Compatibility alias for the unreleased branch implementation; both names resolve to
# the same sole official assembler.
assemble_verified_review_package = assemble_review_package
VerifiedReviewPackage = CanonicalReviewPackage


def canonical_review_package_bytes(package: CanonicalReviewPackage) -> bytes:
    if type(package) is not CanonicalReviewPackage:
        raise ReviewAssemblyError("package must be CanonicalReviewPackage")
    package.value()
    return bytes(package.canonical_bytes)


def canonical_review_package_value(package: CanonicalReviewPackage) -> dict[str, Any]:
    if type(package) is not CanonicalReviewPackage:
        raise ReviewAssemblyError("package must be CanonicalReviewPackage")
    return package.value()


verified_review_package_bytes = canonical_review_package_bytes
verified_review_package_value = canonical_review_package_value


def render_unverified_preview(assessment: ReviewAssessment) -> dict[str, Any]:
    if not isinstance(assessment, ReviewAssessment):
        raise ReviewAssemblyError("preview requires ReviewAssessment")
    return {
        "artifact_assurance": "DECLARATION",
        "verification_status": "MANUAL_UNVERIFIED",
        "official_completion": False,
        "review_summary": assessment.review_summary,
        "findings": [
            {
                "finding_id": item.finding_id,
                "title": item.title,
                "description": item.description,
                "severity": item.severity,
                "blocking": item.blocking,
                "evidence_refs": list(item.evidence_refs),
            }
            for item in assessment.findings
        ],
    }


def _validate_evidence_catalog(facts: ReviewFacts) -> dict[str, EvidenceRecord]:
    by_id: dict[str, EvidenceRecord] = {}
    for record in facts.evidence_catalog:
        if not isinstance(record, EvidenceRecord):
            raise ReviewAssemblyError("evidence_catalog contains a non-EvidenceRecord value")
        previous = by_id.get(record.evidence_id)
        if previous is not None and previous != record:
            raise ReviewAssemblyError(f"duplicate conflicting evidence: {record.evidence_id}")
        if record.evidence_id != record.expected_id():
            raise ReviewAssemblyError(f"evidence id is not deterministic: {record.evidence_id}")
        if (record.repository, record.pr_number, record.head_sha) != (
            facts.repository,
            facts.pr_number,
            facts.head_sha,
        ):
            raise ReviewAssemblyError(
                f"evidence {record.evidence_id} is bound to another repository, PR, or Head"
            )
        by_id[record.evidence_id] = record
    return by_id


def _finding_record(
    finding: ReviewFinding,
    evidence_by_id: Mapping[str, EvidenceRecord],
    facts: ReviewFacts,
) -> dict[str, Any]:
    missing = [ref for ref in finding.evidence_refs if ref not in evidence_by_id]
    if missing:
        raise ReviewAssemblyError(
            f"finding {finding.finding_id} references unknown evidence: {', '.join(missing)}"
        )
    if finding.evidence_class == "CODE_SUPPORTED":
        if not finding.evidence_refs or not all(
            evidence_by_id[ref].kind in {"CODE", "DIFF"} for ref in finding.evidence_refs
        ):
            raise ReviewAssemblyError(
                f"finding {finding.finding_id}: CODE_SUPPORTED requires CODE or DIFF evidence"
            )
        evidence_label = "CODE_SUPPORTED"
    elif finding.evidence_class == "REPRODUCED":
        failing = [
            evidence_by_id[ref]
            for ref in finding.evidence_refs
            if evidence_by_id[ref].kind in {"CI", "EXECUTION"}
            and evidence_by_id[ref].payload.get("result", _result_from_conclusion(evidence_by_id[ref].payload.get("conclusion"))) == "FAIL"
        ]
        if not failing:
            raise ReviewAssemblyError(
                f"finding {finding.finding_id}: REPRODUCED requires failing CI or EXECUTION evidence"
            )
        evidence_label = "REPRODUCED"
    elif finding.evidence_class in {"HUMAN_JUDGMENT", "HYPOTHESIS"}:
        evidence_label = "HYPOTHESIS"
    else:
        evidence_label = "NOT_ASSESSABLE"
    file_location = ", ".join(finding.affected_surfaces) or "not_applicable"
    return {
        "finding_id": finding.finding_id,
        "issue": finding.title,
        "severity": finding.severity,
        "blocking": finding.blocking,
        "evidence_label": evidence_label,
        "evidence_refs": list(finding.evidence_refs),
        "failure_scenario": finding.description,
        "file_location": file_location,
        "recommended_fix": finding.suggested_action,
        "recommended_test": finding.recommended_test,
        "relevant_code": finding.relevant_code,
        "rule_ids": list(finding.rule_ids),
        "symbol": finding.symbol,
    }


def _package_evidence_record(record: EvidenceRecord) -> dict[str, Any]:
    result = record.payload.get("result")
    if record.kind in {"DIFF", "CODE"}:
        result = "PASS"
    elif result not in {"PASS", "FAIL", "UNKNOWN"}:
        result = _result_from_conclusion(record.payload.get("conclusion"))
    excerpt = record.payload.get("excerpt")
    if not isinstance(excerpt, str):
        excerpt = json.dumps(record.payload, ensure_ascii=False, sort_keys=True)[:2000]
    return {
        "evidence_id": record.evidence_id,
        "evidence_type": record.kind if record.kind in {"CI", "CODE", "EXECUTION"} else "CODE",
        "excerpt": excerpt,
        "limitations": [],
        "redactions": [],
        "reference": record.source,
        "result": result,
        "reviewed_head_sha": record.head_sha,
        "sha256": _sha256(_canonical_json_bytes(record.payload)),
        "source": record.source,
    }


def _result_from_conclusion(conclusion: object) -> str:
    if conclusion == "success":
        return "PASS"
    if conclusion in {"failure", "timed_out", "action_required", "cancelled"}:
        return "FAIL"
    return "UNKNOWN"


def _assert_field_authority_complete(package: Mapping[str, Any]) -> None:
    unresolved: list[str] = []

    def walk(value: Any, path: str) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                walk(child, f"{path}/{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}/{index}")
        else:
            if not _authority_for_path(path):
                unresolved.append(path)

    walk(package, "")
    if unresolved:
        raise ReviewAssemblyError(
            "canonical fields have no authority classification: " + ", ".join(unresolved[:20])
        )


def _authority_for_path(path: str) -> str | None:
    candidates = [prefix for prefix in FIELD_AUTHORITY if path == prefix or path.startswith(prefix + "/")]
    if not candidates:
        return None
    return FIELD_AUTHORITY[max(candidates, key=len)]


def _collect_changed_files(directory: Path, merge_base: str, head_sha: str) -> tuple[ChangedFile, ...]:
    raw = _run_git(directory, "diff", "--numstat", "--find-renames", merge_base, head_sha)
    result: list[ChangedFile] = []
    for line in raw.splitlines():
        if not line:
            continue
        additions, deletions, path = line.split("\t", 2)
        changed_lines = 0 if "-" in {additions, deletions} else int(additions) + int(deletions)
        result.append(ChangedFile(path, changed_lines))
    return tuple(sorted(result, key=lambda item: item.path))


def _run_git(directory: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(directory), *args],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        stderr = getattr(exc, "stderr", "")
        raise ReviewAssemblyError(f"git collection failed: {stderr or exc}") from exc
    return result.stdout.strip()


def _fetch_github_json(url: str, *, token: str | None, api_version: str) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": api_version,
        "User-Agent": "PR-Inspector-review-facts-collector",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=20) as response:
            if getattr(response, "status", 200) != 200:
                raise ReviewAssemblyError(f"GitHub endpoint returned HTTP {response.status}")
            return json.loads(response.read().decode("utf-8"))
    except ReviewAssemblyError:
        raise
    except (
        urllib.error.HTTPError,
        urllib.error.URLError,
        TimeoutError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise ReviewAssemblyError(f"GitHub evidence collection failed: {exc}") from exc


def _canonical_json_bytes(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ReviewAssemblyError(f"value is not canonical JSON: {exc}") from exc


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_json_or_yaml(path: Path) -> Mapping[str, Any]:
    if path.suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    import yaml

    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ReviewAssemblyError(f"{path.name} must contain an object")
    return value


def is_verified_review_package(value: object) -> bool:
    """Compatibility predicate: v1.12 packages are ordinary exact-type immutable values."""

    return type(value) is CanonicalReviewPackage
