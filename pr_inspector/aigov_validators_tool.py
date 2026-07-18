from __future__ import annotations

from typing import Any

from .aigov_errors import AIGOVDiagnostic, diagnostic
from .aigov_validation_support import AIGOVValidationContext

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
    if invocation["claimed_execution"] is False:
        if (
            invocation["invocation_id"] is not None
            or invocation["executed_at"] is not None
            or invocation["execution_status"] not in {"not_attempted", "unverified"}
        ):
            out.append(
                diagnostic(
                    "AIGOV-SEM-213",
                    payload["contract_type"],
                    "/invocation_record",
                    "truthful execution claim",
                    "unclaimed execution carries contradictory invocation evidence",
                )
            )
    if invocation["execution_status"] == "success":
        result = payload["execution_result"]
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
    captured = set(payload["execution_result"]["captured_result_fields"])
    for index, claim in enumerate(payload["final_claim_bindings"]):
        if claim["binding_status"] in {
            "VERIFIED_RESULT_BOUND",
            "VERIFIED_READBACK_BOUND",
        } and not set(claim["result_field_refs"]).issubset(captured):
            out.append(
                diagnostic(
                    "AIGOV-SEM-215",
                    payload["contract_type"],
                    f"/final_claim_bindings/{index}/result_field_refs",
                    "result-bound final claim",
                    "verified claim references fields not captured from execution result",
                )
            )
        if (
            claim["binding_status"] == "VERIFIED_READBACK_BOUND"
            and payload["readback_status"] != "VERIFIED"
        ):
            out.append(
                diagnostic(
                    "AIGOV-SEM-216",
                    payload["contract_type"],
                    f"/final_claim_bindings/{index}/binding_status",
                    "read-back-bound final claim",
                    "verified read-back claim requires VERIFIED readback_status",
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
    if ".." in workflow["workflow_file"].split("/"):
        out.append(
            diagnostic(
                "AIGOV-SEM-218",
                payload["contract_type"],
                "/workflow_identity/workflow_file",
                "bounded workflow path",
                "workflow path traversal is forbidden",
            )
        )
    return out
