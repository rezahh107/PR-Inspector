from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping

from .aigov_errors import AIGOVDiagnostic, diagnostic

SEMANTIC_VALIDATOR_VERSION = "1.0"
ACTIVE_PROTOCOL = "v1.11.1"
INSPECTOR_REPOSITORY = "rezahh107/PR-Inspector"
INSPECTOR_REPOSITORY_ID = 1288323264

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_TAGGED_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_TARGET_EXACT_IDENTITY = re.compile(r"^(?P<repository>[^/\s]+/[^#\s]+)#(?P<pr>[1-9][0-9]*)@(?P<head>[0-9a-f]{40})$")
_EXECUTABLE_EXPRESSION = re.compile(r"(?:\$\(|__import__\s*\(|\beval\s*\(|\bexec\s*\(|\bos\.system\s*\(|\bsubprocess\.|/bin/(?:ba)?sh\b|\bpowershell(?:\.exe)?\s+-)", re.IGNORECASE)
_SHA_FIELDS = {"reviewed_head_sha", "head_sha", "base_sha", "commit_sha", "trusted_revision_sha", "exact_head_sha", "head_observed_at_publish", "inspector_commit_sha"}
_POSITIVE_INTEGER_FIELDS = {"repository_id", "target_repository_id", "inspector_repository_id", "pr_number", "transition_pr_number", "attempt_number", "sequence_number", "actor_id", "github_app_id", "installation_id", "run_id", "run_attempt", "job_id", "step_number"}
_ID_KEYS = ("evidence_id", "fact_id", "claim_id", "record_id", "parameter_name", "obligation_id", "attestation_id")
_INSPECTION_RANK = {"minimal": 0, "standard": 1, "strict": 2}
_EVIDENCE_RANK = {"compact": 0, "full": 1, "high_assurance": 2}
_ENFORCEMENT_RANK = {"owner_controlled": 0, "ci_enforced": 1, "repository_enforced": 2}

@dataclass(frozen=True, slots=True)
class AIGOVValidationContext:
    repository_full_name: str | None = None
    repository_id: int | None = None
    pr_number: int | None = None
    reviewed_head_sha: str | None = None
    inspector_repository: str = INSPECTOR_REPOSITORY
    inspector_repository_id: int = INSPECTOR_REPOSITORY_ID
    inspector_commit_sha: str | None = None
    protocol_version: str = ACTIVE_PROTOCOL
    minimum_inspection_profile: str | None = None
    minimum_evidence_profile: str | None = None
    minimum_merge_enforcement_profile: str | None = None
    trusted_workflow_revisions: tuple[str, ...] = ()


def _pointer(parent: str, part: object) -> str:
    text = str(part).replace("~", "~0").replace("/", "~1")
    return f"{parent.rstrip('/')}/{text}" if parent != "/" else f"/{text}"


def canonical_scope_digest(payload: Mapping[str, object]) -> str:
    fields = (
        "repository_identity",
        "target_identity",
        "base_sha",
        "head_sha",
        "included_paths",
        "excluded_paths",
        "deferred_items",
        "dependencies",
        "scope_authority_binding_refs",
        "governing_revision",
        "unresolved_scope",
        "scope_status",
    )
    canonical = {field: payload[field] for field in fields}
    raw = json.dumps(
        canonical,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _walk(value: object, path: str = "/"):
    yield path, value
    if isinstance(value, Mapping):
        for key, item in value.items():
            yield from _walk(item, _pointer(path, key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk(item, _pointer(path, index))


def _walk_keyed(value: object, path: str = "/"):
    if isinstance(value, Mapping):
        for key, item in value.items():
            child = _pointer(path, key)
            yield key, child, item
            yield from _walk_keyed(item, child)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk_keyed(item, _pointer(path, index))


def _target(payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
    value = payload.get("target_identity")
    if isinstance(value, Mapping) and "repository_full_name" in value:
        return value
    value = payload.get("pre_merge_target_identity")
    if isinstance(value, Mapping):
        return value
    direct = {
        "repository_full_name": payload.get("repository_full_name"),
        "repository_id": payload.get("repository_id"),
        "pr_number": payload.get("pr_number"),
        "reviewed_head_sha": payload.get("reviewed_head_sha"),
    }
    if all(item is not None for item in direct.values()):
        return direct
    return None


def _global_diagnostics(
    contract_type: str,
    payload: dict[str, Any],
    context: AIGOVValidationContext | None,
) -> list[AIGOVDiagnostic]:
    out: list[AIGOVDiagnostic] = []
    if payload.get("activation_state") != "inactive":
        out.append(
            diagnostic(
                "AIGOV-SEM-001",
                contract_type,
                "/activation_state",
                "inactive boundary",
                "all S-003 models must remain inactive",
            )
        )

    for key, path, value in _walk_keyed(payload):
        if key in _SHA_FIELDS and isinstance(value, str) and _SHA40.fullmatch(value) is None:
            out.append(
                diagnostic(
                    "AIGOV-SEM-002",
                    contract_type,
                    path,
                    "full Git commit identity",
                    "commit SHA must be 40 lowercase hexadecimal characters",
                )
            )
        if (
            isinstance(value, str)
            and (
                (
                    key.endswith("_digest")
                    and key != "supplied_value_or_canonical_digest"
                )
                or key in {"policy_identity", "source_digest", "record_digest"}
            )
            and _TAGGED_SHA256.fullmatch(value) is None
        ):
            out.append(
                diagnostic(
                    "AIGOV-SEM-003",
                    contract_type,
                    path,
                    "tagged SHA-256 identity",
                    "digest must use sha256: followed by 64 lowercase hexadecimal characters",
                )
            )
        if key.endswith("_sha256") and isinstance(value, str):
            if _SHA256.fullmatch(value) is None:
                out.append(
                    diagnostic(
                        "AIGOV-SEM-004",
                        contract_type,
                        path,
                        "raw SHA-256 identity",
                        "SHA-256 must contain 64 lowercase hexadecimal characters",
                    )
                )
        if key in _POSITIVE_INTEGER_FIELDS and value is not None:
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                out.append(
                    diagnostic(
                        "AIGOV-SEM-005",
                        contract_type,
                        path,
                        "positive numeric identity",
                        "identity must be a positive integer and not a boolean",
                    )
                )
        if isinstance(value, str) and _EXECUTABLE_EXPRESSION.search(value):
            out.append(
                diagnostic(
                    "AIGOV-SEM-006",
                    contract_type,
                    path,
                    "non-executable authority data",
                    "embedded executable expression or command marker is forbidden",
                )
            )

    for path, value in _walk(payload):
        if not isinstance(value, list):
            continue
        for identity_key in _ID_KEYS:
            seen: dict[str, int] = {}
            for index, item in enumerate(value):
                if not isinstance(item, Mapping):
                    continue
                identity = item.get(identity_key)
                if not isinstance(identity, str):
                    continue
                if identity in seen:
                    out.append(
                        diagnostic(
                            "AIGOV-SEM-007",
                            contract_type,
                            _pointer(path, index),
                            "unique identifier",
                            f"duplicate {identity_key}: {identity}",
                            evidence_path=_pointer(path, seen[identity]),
                        )
                    )
                else:
                    seen[identity] = index

    target = _target(payload)
    if target is not None:
        out.extend(_target_context_diagnostics(contract_type, target, context))
        out.extend(_evidence_target_diagnostics(contract_type, payload, target))

    if context is not None:
        inspector = payload.get("inspector_identity")
        if isinstance(inspector, Mapping):
            if inspector.get("repository") != context.inspector_repository:
                out.append(
                    diagnostic(
                        "AIGOV-SEM-008",
                        contract_type,
                        "/inspector_identity/repository",
                        "Inspector repository identity",
                        "Inspector repository does not match validation context",
                    )
                )
            if inspector.get("repository_id") != context.inspector_repository_id:
                out.append(
                    diagnostic(
                        "AIGOV-SEM-009",
                        contract_type,
                        "/inspector_identity/repository_id",
                        "Inspector numeric identity",
                        "Inspector repository ID does not match validation context",
                    )
                )
            if (
                context.inspector_commit_sha is not None
                and inspector.get("commit_sha") != context.inspector_commit_sha
            ):
                out.append(
                    diagnostic(
                        "AIGOV-SEM-010",
                        contract_type,
                        "/inspector_identity/commit_sha",
                        "Inspector commit identity",
                        "Inspector commit does not match validation context",
                    )
                )
    return out


def _target_context_diagnostics(
    contract_type: str,
    target: Mapping[str, Any],
    context: AIGOVValidationContext | None,
) -> list[AIGOVDiagnostic]:
    if context is None:
        return []
    checks = (
        (
            "repository_full_name",
            context.repository_full_name,
            "AIGOV-SEM-011",
            "Repository full-name identity",
        ),
        (
            "repository_id",
            context.repository_id,
            "AIGOV-SEM-012",
            "Repository numeric identity",
        ),
        ("pr_number", context.pr_number, "AIGOV-SEM-013", "pull-request identity"),
        (
            "reviewed_head_sha",
            context.reviewed_head_sha,
            "AIGOV-SEM-014",
            "reviewed Head identity",
        ),
    )
    out: list[AIGOVDiagnostic] = []
    for key, expected, code, invariant in checks:
        if expected is not None and target.get(key) != expected:
            out.append(
                diagnostic(
                    code,
                    contract_type,
                    f"/target_identity/{key}",
                    invariant,
                    "value does not match validation context",
                )
            )
    return out


def _evidence_target_diagnostics(
    contract_type: str,
    payload: Mapping[str, Any],
    target: Mapping[str, Any],
) -> list[AIGOVDiagnostic]:
    out: list[AIGOVDiagnostic] = []
    expected = (
        target.get("repository_full_name"),
        target.get("pr_number"),
        target.get("reviewed_head_sha"),
    )
    if any(item is None for item in expected):
        return out
    for path, value in _walk(payload):
        if not isinstance(value, Mapping):
            continue
        if not {
            "evidence_id",
            "evidence_type",
            "exact_identity",
            "source_digest",
            "retrieval_method",
        }.issubset(value):
            continue
        exact = value.get("exact_identity")
        if not isinstance(exact, str):
            continue
        match = _TARGET_EXACT_IDENTITY.fullmatch(exact)
        if match is None:
            continue
        actual = (
            match.group("repository"),
            int(match.group("pr")),
            match.group("head"),
        )
        if actual != expected:
            out.append(
                diagnostic(
                    "AIGOV-SEM-015",
                    contract_type,
                    f"{path.rstrip('/')}/exact_identity",
                    "evidence target identity",
                    "evidence targets a different repository, PR, or Head",
                )
            )
    return out


def _minimum_profile_diagnostics(
    contract_type: str,
    payload: Mapping[str, Any],
    context: AIGOVValidationContext | None,
    *,
    prefix: str,
) -> list[AIGOVDiagnostic]:
    if context is None:
        return []
    out: list[AIGOVDiagnostic] = []
    specs = (
        (
            f"{prefix}inspection_profile",
            context.minimum_inspection_profile,
            _INSPECTION_RANK,
            "AIGOV-SEM-016",
        ),
        (
            f"{prefix}evidence_profile",
            context.minimum_evidence_profile,
            _EVIDENCE_RANK,
            "AIGOV-SEM-017",
        ),
        (
            f"{prefix}merge_enforcement_profile",
            context.minimum_merge_enforcement_profile,
            _ENFORCEMENT_RANK,
            "AIGOV-SEM-018",
        ),
    )
    for field, minimum, ranking, code in specs:
        if minimum is None or field not in payload:
            continue
        actual = payload.get(field)
        if actual not in ranking or minimum not in ranking or ranking[actual] < ranking[minimum]:
            out.append(
                diagnostic(
                    code,
                    contract_type,
                    f"/{field}",
                    "activated minimum profile",
                    f"{actual!r} is below required minimum {minimum!r}",
                )
            )
    return out
