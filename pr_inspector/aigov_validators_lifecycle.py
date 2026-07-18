from __future__ import annotations

from typing import Any, Mapping

from .aigov_errors import AIGOVDiagnostic, diagnostic
from .aigov_validation_support import AIGOVValidationContext

def _policy_transition_record(
    payload: dict[str, Any],
    _context: AIGOVValidationContext | None,
) -> list[AIGOVDiagnostic]:
    out: list[AIGOVDiagnostic] = []
    if payload["current_policy_identity"] == payload["target_policy_identity"]:
        out.append(
            diagnostic(
                "AIGOV-SEM-181",
                payload["contract_type"],
                "/target_policy_identity",
                "distinct policy transition identities",
                "current and target policy identities must differ",
            )
        )
    if payload["evaluation_policy_identity"] != payload["current_policy_identity"]:
        out.append(
            diagnostic(
                "AIGOV-SEM-182",
                payload["contract_type"],
                "/evaluation_policy_identity",
                "current-policy evaluation authority",
                "transition must be evaluated exclusively under current policy",
            )
        )
    progressed = payload["post_merge_closure_status"] != "not_started"
    if progressed:
        required = (
            "owner_merge_evidence_ref",
            "merge_result_proof_ref",
        )
        for field in required:
            if payload[field] is None:
                out.append(
                    diagnostic(
                        "AIGOV-SEM-183",
                        payload["contract_type"],
                        f"/{field}",
                        "post-Merge transition evidence",
                        f"transition progression requires {field}",
                    )
                )
        if payload["current_main_validation"] != "PASS":
            out.append(
                diagnostic(
                    "AIGOV-SEM-184",
                    payload["contract_type"],
                    "/current_main_validation",
                    "exact-main transition verification",
                    "progressed transition requires current-main PASS",
                )
            )
    if payload["owner_authority_verified"] and payload["owner_merge_evidence_ref"] is None:
        out.append(
            diagnostic(
                "AIGOV-SEM-185",
                payload["contract_type"],
                "/owner_merge_evidence_ref",
                "owner Merge authority evidence",
                "verified owner authority requires owner Merge evidence",
            )
        )
    if (
        isinstance(payload["transition_receipt_ref"], Mapping)
        and payload["transition_receipt_ref"]["record_id"] == payload["transition_id"]
    ):
        out.append(
            diagnostic(
                "AIGOV-SEM-186",
                payload["contract_type"],
                "/transition_receipt_ref/record_id",
                "non-self-referential transition Receipt",
                "transition Receipt cannot reference transition record itself",
            )
        )
    return out


def _merge_readiness_record(
    payload: dict[str, Any],
    _context: AIGOVValidationContext | None,
) -> list[AIGOVDiagnostic]:
    out: list[AIGOVDiagnostic] = []
    if payload["technical_status_ref"]["record_type"] != "decision_projection":
        out.append(
            diagnostic(
                "AIGOV-SEM-191",
                payload["contract_type"],
                "/technical_status_ref/record_type",
                "technical status reference separation",
                "technical status must be referenced through a decision_projection record",
            )
        )
    if payload["policy_resolution_ref"]["record_type"] != "review_policy_resolution":
        out.append(
            diagnostic(
                "AIGOV-SEM-192",
                payload["contract_type"],
                "/policy_resolution_ref/record_type",
                "policy result separation",
                "Merge readiness must reference review_policy_resolution",
            )
        )
    if payload["merge_readiness_result"] == "READY_FOR_USER_MERGE":
        if payload["merge_governance_status"] not in {
            "enforcement_verified",
            "enforcement_not_required",
        }:
            out.append(
                diagnostic(
                    "AIGOV-SEM-193",
                    payload["contract_type"],
                    "/merge_governance_status",
                    "Merge authorization prerequisite",
                    "ready result requires verified or explicitly unnecessary enforcement",
                )
            )
    else:
        if not payload["blocking_reasons"] and not payload["unresolved_evidence_refs"]:
            out.append(
                diagnostic(
                    "AIGOV-SEM-194",
                    payload["contract_type"],
                    "/blocking_reasons",
                    "non-ready explanation",
                    "non-ready result requires blocking reason or unresolved evidence",
                )
            )
    return out


def _post_merge_closure(
    payload: dict[str, Any],
    _context: AIGOVValidationContext | None,
) -> list[AIGOVDiagnostic]:
    out: list[AIGOVDiagnostic] = []
    pre = payload["pre_merge_target_identity"]
    resulting = payload["resulting_default_branch_identity"]
    repository = resulting["repository_identity"]
    if (
        pre["repository_full_name"],
        pre["repository_id"],
    ) != (
        repository["repository_full_name"],
        repository["repository_id"],
    ):
        out.append(
            diagnostic(
                "AIGOV-SEM-201",
                payload["contract_type"],
                "/resulting_default_branch_identity/repository_identity",
                "post-Merge repository identity",
                "resulting main belongs to a different repository",
            )
        )
    if pre["reviewed_head_sha"] == resulting["commit_sha"]:
        out.append(
            diagnostic(
                "AIGOV-SEM-202",
                payload["contract_type"],
                "/resulting_default_branch_identity/commit_sha",
                "pre/post Merge identity distinction",
                "resulting main identity must be distinct from reviewed Head",
            )
        )
    outcomes = set(payload["closure_outcomes"])
    if "content_loss_detected" in outcomes and payload["post_merge_closure_status"] == "closure_recorded":
        out.append(
            diagnostic(
                "AIGOV-SEM-203",
                payload["contract_type"],
                "/closure_outcomes",
                "content-loss closure block",
                "content loss cannot coexist with successful closure",
            )
        )
    if "insufficient_evidence" in outcomes and payload["post_merge_closure_status"] == "closure_recorded":
        out.append(
            diagnostic(
                "AIGOV-SEM-204",
                payload["contract_type"],
                "/closure_outcomes",
                "evidence-complete closure",
                "insufficient evidence cannot be recorded as verified closure",
            )
        )
    if payload["post_merge_closure_status"] == "closure_recorded":
        if payload["content_equivalence_result"] != "content_equivalence_verified":
            out.append(
                diagnostic(
                    "AIGOV-SEM-205",
                    payload["contract_type"],
                    "/content_equivalence_result",
                    "method-aware content equivalence",
                    "recorded closure requires verified content equivalence",
                )
            )
        if payload["current_main_validation"] != "PASS":
            out.append(
                diagnostic(
                    "AIGOV-SEM-206",
                    payload["contract_type"],
                    "/current_main_validation",
                    "exact-main closure verification",
                    "recorded closure requires current-main PASS",
                )
            )
        if payload["closure_receipt_ref"] is None:
            out.append(
                diagnostic(
                    "AIGOV-SEM-207",
                    payload["contract_type"],
                    "/closure_receipt_ref",
                    "closure evidence",
                    "recorded closure requires a closure Receipt reference",
                )
            )
    method = payload["detected_merge_method"]
    topology = payload["history_topology_result"]
    if method == "merge_commit" and payload["post_merge_closure_status"] == "closure_recorded":
        if topology != "history_topology_verified":
            out.append(
                diagnostic(
                    "AIGOV-SEM-208",
                    payload["contract_type"],
                    "/history_topology_result",
                    "Merge-commit topology verification",
                    "merge_commit closure requires verified history topology",
                )
            )
    if method in {"squash_merge", "rebase_merge"} and topology not in {
        "history_topology_verified",
        "history_topology_not_preserved_by_merge_method",
    }:
        out.append(
            diagnostic(
                "AIGOV-SEM-209",
                payload["contract_type"],
                "/history_topology_result",
                "method-aware non-ancestry handling",
                "Squash/Rebase topology must be verified or explicitly not preserved",
            )
        )
    return out
