from __future__ import annotations

from typing import Any, Mapping

from .aigov_errors import AIGOVDiagnostic, diagnostic
from .aigov_paths import normalize_repository_relative_path
from .aigov_validation_support import AIGOVValidationContext


_VERIFIED_CLAIM_STATUSES = {
    "VERIFIED_RESULT_BOUND",
    "VERIFIED_READBACK_BOUND",
}


def _tool_execution_attestation(
    payload: dict[str, Any],
    context: AIGOVValidationContext | None,
) -> list[AIGOVDiagnostic]:
    out: list[AIGOVDiagnostic] = []
    workflow = payload["workflow_identity"]
    if (
        context is not None
        and context.trusted_workflow_revisions
        and workflow["trusted_revision_sha"] not in context.trusted_workflow_revisions
    ):
        out.append(
            diagnostic(
                "AIGOV-SEM-211",
                payload["contract_type"],
                "/workflow_identity/trusted_revision_sha",
                "trusted workflow revision",
                "workflow revision is not in the trusted validation context",
            )
        )
    auth = payload["authentication_provenance"]
    auth_evidence = auth["provenance_evidence_ref"]
    if auth_evidence["evidence_type"] not in {
        "structured_record",
        "workflow_run",
        "workflow_job",
    }:
        out.append(
            diagnostic(
                "AIGOV-SEM-212",
                payload["contract_type"],
                "/authentication_provenance/provenance_evidence_ref/evidence_type",
                "authenticated execution provenance",
                "caller-authored or documentary text is not authentication evidence",
            )
        )

    invocation = payload["invocation_record"]
    result = payload["execution_result"]
    claimed_execution = invocation["claimed_execution"] is True
    execution_succeeded = claimed_execution and invocation["execution_status"] == "success"

    if not claimed_execution:
        unclaimed_requirements = (
            (
                "/invocation_record/invocation_id",
                invocation["invocation_id"] is None,
                "unclaimed execution must not carry an invocation identity",
            ),
            (
                "/invocation_record/executed_at",
                invocation["executed_at"] is None,
                "unclaimed execution must not carry an execution timestamp",
            ),
            (
                "/invocation_record/execution_status",
                invocation["execution_status"] in {"not_attempted", "unverified"},
                "unclaimed execution status must be not_attempted or unverified",
            ),
            (
                "/state_changed",
                payload["state_changed"] is False,
                "unclaimed execution cannot represent a state change",
            ),
            (
                "/readback_status",
                payload["readback_status"] == "NOT_PERFORMED",
                "unclaimed execution must use NOT_PERFORMED readback status",
            ),
            (
                "/readback_ref",
                payload["readback_ref"] is None,
                "unclaimed execution cannot carry readback evidence",
            ),
            (
                "/execution_result/result_identity",
                result["result_identity"] is None,
                "unclaimed execution cannot identify a result",
            ),
            (
                "/execution_result/captured_result_fields",
                result["captured_result_fields"] == [],
                "unclaimed execution cannot capture result fields",
            ),
        )
        for path, satisfied, reason in unclaimed_requirements:
            if not satisfied:
                out.append(
                    diagnostic(
                        "AIGOV-SEM-213",
                        payload["contract_type"],
                        path,
                        "truthful unclaimed execution record",
                        reason,
                    )
                )

    if invocation["execution_status"] == "success":
        if not claimed_execution:
            out.append(
                diagnostic(
                    "AIGOV-SEM-219",
                    payload["contract_type"],
                    "/invocation_record/claimed_execution",
                    "successful execution claim",
                    "success requires claimed_execution to be true",
                )
            )
        if result["result_identity"] is None or not result["captured_result_fields"]:
            out.append(
                diagnostic(
                    "AIGOV-SEM-214",
                    payload["contract_type"],
                    "/execution_result",
                    "successful execution result",
                    "successful execution requires identified captured results",
                )
            )

    captured = set(result["captured_result_fields"])
    for index, claim in enumerate(payload["final_claim_bindings"]):
        status = claim["binding_status"]
        if status not in _VERIFIED_CLAIM_STATUSES:
            continue
        claim_path = f"/final_claim_bindings/{index}"
        if not execution_succeeded:
            out.append(
                diagnostic(
                    "AIGOV-SEM-219",
                    payload["contract_type"],
                    f"{claim_path}/binding_status",
                    "verified final claim execution basis",
                    "verified final claims require truthfully claimed successful execution",
                )
            )
        if result["result_identity"] is None:
            out.append(
                diagnostic(
                    "AIGOV-SEM-214",
                    payload["contract_type"],
                    "/execution_result/result_identity",
                    "verified final claim result identity",
                    "verified final claims require a non-null execution result identity",
                )
            )
        if not set(claim["result_field_refs"]).issubset(captured):
            out.append(
                diagnostic(
                    "AIGOV-SEM-215",
                    payload["contract_type"],
                    f"{claim_path}/result_field_refs",
                    "result-bound final claim",
                    "verified claim references fields not captured from execution result",
                )
            )
        if status == "VERIFIED_READBACK_BOUND":
            readback = payload["readback_ref"]
            exact_readback = (
                payload["readback_status"] == "VERIFIED"
                and isinstance(readback, Mapping)
                and isinstance(readback.get("exact_identity"), str)
                and readback.get("exact_identity") == result["result_identity"]
            )
            if not exact_readback:
                out.append(
                    diagnostic(
                        "AIGOV-SEM-216",
                        payload["contract_type"],
                        f"{claim_path}/binding_status",
                        "read-back-bound final claim",
                        "verified read-back claim requires exact VERIFIED readback evidence for the result",
                    )
                )

    completeness_claimed = any(
        any(
            token in text.lower()
            for token in ("complete", "all_pages", "pagination")
        )
        for claim in payload["final_claim_bindings"]
        for text in (claim["claim_id"], *claim["result_field_refs"])
    )
    if completeness_claimed and payload["pagination_completeness_ref"] is None:
        out.append(
            diagnostic(
                "AIGOV-SEM-217",
                payload["contract_type"],
                "/pagination_completeness_ref",
                "pagination completeness evidence",
                "complete-evidence claim requires pagination completeness proof",
            )
        )
    try:
        normalize_repository_relative_path(workflow["workflow_file"])
    except (TypeError, ValueError) as exc:
        out.append(
            diagnostic(
                "AIGOV-SEM-218",
                payload["contract_type"],
                "/workflow_identity/workflow_file",
                "bounded repository-relative workflow path",
                str(exc),
            )
        )
    return out
