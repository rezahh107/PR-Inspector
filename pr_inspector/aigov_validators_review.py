from __future__ import annotations

from typing import Any, Mapping

from .aigov_errors import AIGOVDiagnostic, diagnostic
from .aigov_validation_support import ACTIVE_PROTOCOL, INSPECTOR_REPOSITORY, INSPECTOR_REPOSITORY_ID, AIGOVValidationContext, _minimum_profile_diagnostics

_RECEIPT_PUBLICATION_FIELDS = {"publication_attempt_id", "published_at", "publisher_identity", "comment_id", "comment_url", "retry_count", "publication_status", "readback_status"}

def _review_execution(
    payload: dict[str, Any],
    context: AIGOVValidationContext | None,
) -> list[AIGOVDiagnostic]:
    out = _minimum_profile_diagnostics(
        payload["contract_type"], payload, context, prefix=""
    )
    inspector = payload["inspector_identity"]
    if (
        inspector["repository"] != INSPECTOR_REPOSITORY
        or inspector["repository_id"] != INSPECTOR_REPOSITORY_ID
    ):
        out.append(
            diagnostic(
                "AIGOV-SEM-151",
                payload["contract_type"],
                "/inspector_identity",
                "exact Inspector identity",
                "Inspector repository identity is not canonical",
            )
        )
    if payload["policy_resolution_ref"]["record_type"] != "review_policy_resolution":
        out.append(
            diagnostic(
                "AIGOV-SEM-152",
                payload["contract_type"],
                "/policy_resolution_ref/record_type",
                "policy resolution reference type",
                "review execution must reference review_policy_resolution",
            )
        )
    if payload["execution_status"] == "performed" and not payload[
        "tool_execution_attestation_refs"
    ]:
        out.append(
            diagnostic(
                "AIGOV-SEM-153",
                payload["contract_type"],
                "/tool_execution_attestation_refs",
                "successful execution evidence",
                "performed review execution requires tool attestation evidence",
            )
        )
    for index, item in enumerate(payload["tool_execution_attestation_refs"]):
        if item["record_type"] != "tool_execution_attestation":
            out.append(
                diagnostic(
                    "AIGOV-SEM-154",
                    payload["contract_type"],
                    f"/tool_execution_attestation_refs/{index}/record_type",
                    "tool attestation reference type",
                    "unexpected tool execution reference type",
                )
            )
    if payload["protocol_version"] != (context.protocol_version if context else ACTIVE_PROTOCOL):
        out.append(
            diagnostic(
                "AIGOV-SEM-155",
                payload["contract_type"],
                "/protocol_version",
                "exact protocol identity",
                "review execution protocol does not match validated protocol",
            )
        )
    return out


def _review_receipt_core(
    payload: dict[str, Any],
    context: AIGOVValidationContext | None,
) -> list[AIGOVDiagnostic]:
    out: list[AIGOVDiagnostic] = []
    if payload["sequence_number"] == 1 and (
        payload["supersedes_review_id"] is not None
        or payload["supersession_reason"] is not None
    ):
        out.append(
            diagnostic(
                "AIGOV-SEM-161",
                payload["contract_type"],
                "/sequence_number",
                "Receipt sequence origin",
                "sequence 1 cannot supersede an earlier review",
            )
        )
    if payload["sequence_number"] > 1 and payload["supersedes_review_id"] is None:
        out.append(
            diagnostic(
                "AIGOV-SEM-162",
                payload["contract_type"],
                "/supersedes_review_id",
                "Receipt supersession chain",
                "sequence greater than 1 requires supersedes_review_id",
            )
        )
    if payload["protocol_version"] != (context.protocol_version if context else ACTIVE_PROTOCOL):
        out.append(
            diagnostic(
                "AIGOV-SEM-163",
                payload["contract_type"],
                "/protocol_version",
                "exact protocol identity",
                "Receipt Core protocol does not match validated protocol",
            )
        )
    if (
        payload["inspector_repository"] != INSPECTOR_REPOSITORY
        or payload["inspector_repository_id"] != INSPECTOR_REPOSITORY_ID
    ):
        out.append(
            diagnostic(
                "AIGOV-SEM-164",
                payload["contract_type"],
                "/inspector_repository",
                "exact Inspector identity",
                "Receipt Core Inspector identity is not canonical",
            )
        )
    if payload["canonical_package_digest"] == payload["decision_projection_digest"]:
        out.append(
            diagnostic(
                "AIGOV-SEM-165",
                payload["contract_type"],
                "/decision_projection_digest",
                "non-contradictory artifact identity",
                "package and decision-projection digests must identify distinct artifacts",
            )
        )
    forbidden = sorted(_RECEIPT_PUBLICATION_FIELDS.intersection(payload))
    if forbidden:
        out.append(
            diagnostic(
                "AIGOV-SEM-166",
                payload["contract_type"],
                "/",
                "Receipt Core/publication separation",
                "publication metadata is forbidden in Receipt Core: "
                + ", ".join(forbidden),
            )
        )
    return out


def _publication_attempt(
    payload: dict[str, Any],
    _context: AIGOVValidationContext | None,
) -> list[AIGOVDiagnostic]:
    out: list[AIGOVDiagnostic] = []
    key = payload["idempotency_key"]
    comparisons = (
        ("review_id", payload["review_id"]),
        ("repository_id", payload["target_repository_id"]),
        ("pr_number", payload["pr_number"]),
        ("reviewed_head_sha", payload["head_observed_at_publish"]),
        ("receipt_core_digest", payload["receipt_core_digest"]),
    )
    for field, expected in comparisons:
        if key[field] != expected:
            out.append(
                diagnostic(
                    "AIGOV-SEM-171",
                    payload["contract_type"],
                    f"/idempotency_key/{field}",
                    "publication idempotency identity",
                    f"idempotency {field} differs from publication attempt identity",
                )
            )
    if payload["attempt_number"] == 1 and payload["prior_attempt_ref"] is not None:
        out.append(
            diagnostic(
                "AIGOV-SEM-172",
                payload["contract_type"],
                "/prior_attempt_ref",
                "publication attempt sequence",
                "first publication attempt cannot reference a prior attempt",
            )
        )
    if payload["attempt_number"] > 1 and payload["prior_attempt_ref"] is None:
        out.append(
            diagnostic(
                "AIGOV-SEM-173",
                payload["contract_type"],
                "/prior_attempt_ref",
                "publication attempt sequence",
                "subsequent publication attempt requires prior_attempt_ref",
            )
        )
    if (
        isinstance(payload["prior_attempt_ref"], Mapping)
        and payload["prior_attempt_ref"]["record_id"] == payload["publication_attempt_id"]
    ):
        out.append(
            diagnostic(
                "AIGOV-SEM-174",
                payload["contract_type"],
                "/prior_attempt_ref/record_id",
                "non-self-referential publication attempt",
                "publication attempt cannot reference itself",
            )
        )
    if payload["readback_status"] == "VERIFIED" and payload["readback_evidence_ref"] is None:
        out.append(
            diagnostic(
                "AIGOV-SEM-175",
                payload["contract_type"],
                "/readback_evidence_ref",
                "verified publication read-back",
                "verified read-back requires structured evidence",
            )
        )
    return out
