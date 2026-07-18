from __future__ import annotations

from fnmatch import fnmatchcase
from typing import Any, Mapping

from .aigov_errors import AIGOVDiagnostic, diagnostic
from .aigov_validation_support import AIGOVValidationContext, _TAGGED_SHA256, _minimum_profile_diagnostics, canonical_scope_digest

def _repository_review_policy(
    payload: dict[str, Any],
    _context: AIGOVValidationContext | None,
) -> list[AIGOVDiagnostic]:
    out: list[AIGOVDiagnostic] = []
    lifecycle = payload["lifecycle_state"]
    claim = payload["repository_hosted_enforcement_claim"]
    evidence = payload["repository_hosted_enforcement_evidence_ref"]
    if lifecycle in {"candidate", "trial", "inactive", "superseded"} and claim == "verified":
        out.append(
            diagnostic(
                "AIGOV-SEM-101",
                payload["contract_type"],
                "/repository_hosted_enforcement_claim",
                "policy lifecycle enforcement boundary",
                f"{lifecycle} policy cannot claim verified active enforcement",
            )
        )
    if claim == "verified":
        if not isinstance(evidence, Mapping) or evidence.get("evidence_type") not in {
            "repository_api",
            "structured_record",
        }:
            out.append(
                diagnostic(
                    "AIGOV-SEM-102",
                    payload["contract_type"],
                    "/repository_hosted_enforcement_evidence_ref",
                    "structured repository enforcement evidence",
                    "verified enforcement requires repository API or structured-record evidence",
                )
            )
    expected_authority = {
        "owner_controlled": "owner_only",
        "ci_enforced": "owner_with_ci_enforcement",
        "repository_enforced": "owner_with_repository_enforcement",
    }[payload["default_merge_enforcement_profile"]]
    if payload["merge_readiness_authority"] != expected_authority:
        out.append(
            diagnostic(
                "AIGOV-SEM-103",
                payload["contract_type"],
                "/merge_readiness_authority",
                "merge authority/profile consistency",
                "merge-readiness authority contradicts enforcement profile",
            )
        )
    if lifecycle == "active" and payload["transition_record_ref"] is None:
        out.append(
            diagnostic(
                "AIGOV-SEM-104",
                payload["contract_type"],
                "/transition_record_ref",
                "effective policy transition",
                "active policy requires a transition record",
            )
        )
    return out


def _review_policy_resolution(
    payload: dict[str, Any],
    context: AIGOVValidationContext | None,
) -> list[AIGOVDiagnostic]:
    out = _minimum_profile_diagnostics(
        payload["contract_type"], payload, context, prefix="effective_"
    )
    resolution_id = payload["resolution_id"]
    for index, item in enumerate(payload["activated_conditions"]):
        if item["record_id"] == resolution_id:
            out.append(
                diagnostic(
                    "AIGOV-SEM-111",
                    payload["contract_type"],
                    f"/activated_conditions/{index}/record_id",
                    "non-self-referential policy resolution",
                    "policy resolution cannot reference itself",
                )
            )
    if payload["status"] == "RESOLVED" and not payload["evidence_refs"]:
        out.append(
            diagnostic(
                "AIGOV-SEM-112",
                payload["contract_type"],
                "/evidence_refs",
                "authoritative resolution evidence",
                "resolved policy requires evidence",
            )
        )
    return out


def _obligation_authority_binding(
    payload: dict[str, Any],
    _context: AIGOVValidationContext | None,
) -> list[AIGOVDiagnostic]:
    out: list[AIGOVDiagnostic] = []
    stages = (
        "prose_only",
        "schema_backed",
        "validator_backed",
        "fixture_tested",
        "ci_enforced",
        "downstream_contract_enforced",
    )
    rank = stages.index(payload["current_enforcement_status"])
    required = (
        ("schema_carrier_ref", 1),
        ("validator_ref", 2),
        ("fixture_evidence_ref", 3),
        ("ci_evidence_ref", 4),
        ("downstream_consumer_ref", 5),
    )
    for field, minimum in required:
        if rank >= minimum and payload[field] is None:
            out.append(
                diagnostic(
                    "AIGOV-SEM-121",
                    payload["contract_type"],
                    f"/{field}",
                    "monotonic enforcement progression",
                    f"{payload['current_enforcement_status']} requires {field}",
                )
            )
    if rank >= 3 and isinstance(payload["fixture_evidence_ref"], Mapping):
        identity = payload["fixture_evidence_ref"].get("exact_identity", "")
        if identity.endswith("/schema_valid") or identity.endswith("/schema_invalid"):
            out.append(
                diagnostic(
                    "AIGOV-SEM-122",
                    payload["contract_type"],
                    "/fixture_evidence_ref/exact_identity",
                    "valid-and-invalid fixture coverage",
                    "fixture-tested status must identify both valid and invalid fixture coverage",
                )
            )
    if _TAGGED_SHA256.fullmatch(payload["authority_identity"]) is None:
        out.append(
            diagnostic(
                "AIGOV-SEM-123",
                payload["contract_type"],
                "/authority_identity",
                "immutable authority identity",
                "authority identity must be a tagged SHA-256 digest",
            )
        )
    return out


def _classification_record(
    payload: dict[str, Any],
    _context: AIGOVValidationContext | None,
) -> list[AIGOVDiagnostic]:
    out: list[AIGOVDiagnostic] = []
    evidence_ids = {item["evidence_id"] for item in payload["evidence_refs"]}
    for index, fact in enumerate(payload["observed_facts"]):
        evidence_id = fact["evidence_ref"]["evidence_id"]
        if evidence_id not in evidence_ids:
            out.append(
                diagnostic(
                    "AIGOV-SEM-131",
                    payload["contract_type"],
                    f"/observed_facts/{index}/evidence_ref/evidence_id",
                    "fact-to-evidence binding",
                    "observed fact evidence is absent from the record evidence set",
                )
            )
    if _TAGGED_SHA256.fullmatch(
        payload["classification_authority_ref"]["authority_identity"]
    ) is None:
        out.append(
            diagnostic(
                "AIGOV-SEM-132",
                payload["contract_type"],
                "/classification_authority_ref/authority_identity",
                "classification authority identity",
                "classification authority must be digest-bound",
            )
        )
    return out


def _normalized_path(value: str) -> str:
    while value.startswith("./"):
        value = value[2:]
    return value.replace("\\", "/")


def _path_overlap(left: str, right: str) -> bool:
    left = _normalized_path(left)
    right = _normalized_path(right)
    if left == right:
        return True
    if left.endswith("/**") and right.startswith(left[:-3]):
        return True
    if right.endswith("/**") and left.startswith(right[:-3]):
        return True
    return fnmatchcase(left, right) or fnmatchcase(right, left)


def _scope_record(
    payload: dict[str, Any],
    _context: AIGOVValidationContext | None,
) -> list[AIGOVDiagnostic]:
    out: list[AIGOVDiagnostic] = []
    repository = payload["repository_identity"]
    target = payload["target_identity"]
    if (
        repository["repository_full_name"],
        repository["repository_id"],
    ) != (
        target["repository_full_name"],
        target["repository_id"],
    ):
        out.append(
            diagnostic(
                "AIGOV-SEM-141",
                payload["contract_type"],
                "/repository_identity",
                "scope repository identity",
                "repository identity differs from target identity",
            )
        )
    if payload["head_sha"] != target["reviewed_head_sha"]:
        out.append(
            diagnostic(
                "AIGOV-SEM-142",
                payload["contract_type"],
                "/head_sha",
                "scope Head identity",
                "scope head_sha differs from target reviewed Head",
            )
        )
    for left_index, left in enumerate(payload["included_paths"]):
        if ".." in _normalized_path(left).split("/") or left.startswith("/"):
            out.append(
                diagnostic(
                    "AIGOV-SEM-143",
                    payload["contract_type"],
                    f"/included_paths/{left_index}",
                    "bounded repository path",
                    "scope path traversal or absolute path is forbidden",
                )
            )
        for right_index, right in enumerate(payload["excluded_paths"]):
            if _path_overlap(left, right):
                out.append(
                    diagnostic(
                        "AIGOV-SEM-144",
                        payload["contract_type"],
                        f"/included_paths/{left_index}",
                        "non-contradictory scope",
                        f"included path overlaps excluded path at index {right_index}",
                        evidence_path=f"/excluded_paths/{right_index}",
                    )
                )
    expected = canonical_scope_digest(payload)
    if payload["scope_digest"] != expected:
        out.append(
            diagnostic(
                "AIGOV-SEM-145",
                payload["contract_type"],
                "/scope_digest",
                "deterministic canonical scope digest",
                f"scope digest does not match canonical scope data; expected {expected}",
            )
        )
    return out
