from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .decision_projection_core import ProjectionError
from .governance import (
    VerifiedGovernanceEvidence,
    is_verified_governance_evidence,
)
from .sequence_enforcement import (
    VerifiedSequenceEnforcement,
    sequence_enforcement_matches_package,
)

PERSONAL_MINIMUM_SECURITY_PROFILE = "personal_ai_operated_strong_governance_minimum_security"
OPTIONAL_HARDENING_CONTROLS = (
    "dedicated_github_app",
    "github_app_private_key",
    "exact_app_id_check_runs",
    "branch_protection",
    "repository_rulesets",
    "merge_queue",
    "codeowners_approval",
    "repository_hosted_exact_source_enforcement",
)
RSN_MERGE_ENFORCEMENT_MINIMUM_MISSING = "RSN-MERGE-ENFORCEMENT-MINIMUM-MISSING"
RSN_REPOSITORY_HOSTED_REQUIRED = "RSN-REPOSITORY-HOSTED-ENFORCEMENT-REQUIRED"
RSN_REPOSITORY_SETTINGS_CLAIM_UNVERIFIED = "RSN-REPOSITORY-SETTINGS-CLAIM-UNVERIFIED"
RSN_MERGE_AUTHORIZATION_CLAIM_UNVERIFIED = "RSN-MERGE-AUTHORIZATION-CLAIM-UNVERIFIED"


@dataclass(frozen=True)
class SecurityProfileAssessment:
    profile_name: str
    security_level: str
    sequence_ci_enforced: bool
    repository_hosted_requirement: str
    repository_hosted_enforcement: str
    github_app_exact_source_enforcement: str
    repository_settings_enforced: str
    merge_authorized: str
    governance_evidence_status: str
    governance_evidence_id: str | None
    blocks_green_merge_recommendation: bool
    reason_codes: tuple[str, ...]
    controls: tuple[tuple[str, str], ...]

    def projection(self) -> dict[str, Any]:
        return {
            "name": self.profile_name,
            "security_level": self.security_level,
            "sequence_ci_enforced": self.sequence_ci_enforced,
            "repository_hosted_requirement": self.repository_hosted_requirement,
            "repository_hosted_enforcement": self.repository_hosted_enforcement,
            "github_app_exact_source_enforcement": self.github_app_exact_source_enforcement,
            "repository_settings_enforced": self.repository_settings_enforced,
            "merge_authorized": self.merge_authorized,
            "governance_evidence_status": self.governance_evidence_status,
            "governance_evidence_id": self.governance_evidence_id,
            "blocks_green_merge_recommendation": self.blocks_green_merge_recommendation,
            "reason_codes": list(self.reason_codes),
            "controls": [
                {"control": control, "classification": classification}
                for control, classification in self.controls
            ],
        }


def _matching_verified_evidence(
    pkg: dict[str, Any],
    carrier: dict[str, Any],
    evidence: VerifiedGovernanceEvidence | None,
) -> bool:
    identity = pkg.get("review_identity")
    if not isinstance(identity, dict):
        return False
    return (
        is_verified_governance_evidence(evidence)
        and evidence.repository == identity.get("target_repository")
        and evidence.pull_request_number == identity.get("pr_number")
        and evidence.exact_head_sha == identity.get("reviewed_head_sha")
        and carrier.get("governance_evidence_id") == evidence.evidence_id
    )


def assess_security_profile(
    pkg: dict[str, Any],
    governance_evidence: VerifiedGovernanceEvidence | None = None,
    sequence_enforcement: VerifiedSequenceEnforcement | None = None,
) -> SecurityProfileAssessment:
    carrier = pkg.get("security_profile")
    if not isinstance(carrier, dict):
        raise ProjectionError("security_profile must be present as an object")
    if not isinstance(pkg.get("review_identity"), dict):
        raise ProjectionError("review_identity must be present as an object")

    evidence_matches = _matching_verified_evidence(pkg, carrier, governance_evidence)
    sequence_verified = bool(
        carrier.get("sequence_ci_enforced", False)
        and sequence_enforcement_matches_package(pkg, sequence_enforcement)
    )
    repository_hosted_verified = bool(
        evidence_matches
        and governance_evidence is not None
        and governance_evidence.enforcement_status == "verified_enforced"
    )
    repository_settings_verified = bool(
        carrier.get("claim_repository_settings_enforced", False)
        and repository_hosted_verified
    )
    merge_authorized_verified = bool(
        carrier.get("claim_merge_authorized", False)
        and evidence_matches
        and governance_evidence is not None
        and governance_evidence.merge_authorized
    )

    repository_hosted_required = any(
        (
            carrier.get("explicit_repository_requirement", False),
            carrier.get("security_activation_trigger", False),
            carrier.get("external_requirement", False),
            carrier.get("claim_repository_settings_enforced", False),
            carrier.get("claim_merge_authorized", False),
            carrier.get("governance_evidence_id") is not None,
        )
    )
    reasons: list[str] = []
    if not sequence_verified and not repository_hosted_verified:
        reasons.append(RSN_MERGE_ENFORCEMENT_MINIMUM_MISSING)
    if repository_hosted_required and not repository_hosted_verified:
        reasons.append(RSN_REPOSITORY_HOSTED_REQUIRED)
    if carrier.get("claim_repository_settings_enforced", False) and not repository_settings_verified:
        reasons.append(RSN_REPOSITORY_SETTINGS_CLAIM_UNVERIFIED)
    if carrier.get("claim_merge_authorized", False) and not merge_authorized_verified:
        reasons.append(RSN_MERGE_AUTHORIZATION_CLAIM_UNVERIFIED)

    requirement = "required" if repository_hosted_required else "optional_hardening"
    return SecurityProfileAssessment(
        profile_name=carrier.get("profile_name", PERSONAL_MINIMUM_SECURITY_PROFILE),
        security_level="minimum_security",
        sequence_ci_enforced=sequence_verified,
        repository_hosted_requirement=requirement,
        repository_hosted_enforcement=("verified" if repository_hosted_verified else "not_verified"),
        github_app_exact_source_enforcement=requirement,
        repository_settings_enforced=(
            "verified" if repository_settings_verified else
            "rejected" if carrier.get("claim_repository_settings_enforced", False) else
            "not_claimed"
        ),
        merge_authorized=(
            "verified" if merge_authorized_verified else
            "rejected" if carrier.get("claim_merge_authorized", False) else
            "not_claimed"
        ),
        governance_evidence_status=(
            "verified" if evidence_matches else
            "rejected" if carrier.get("governance_evidence_id") is not None else
            "not_provided"
        ),
        governance_evidence_id=carrier.get("governance_evidence_id"),
        blocks_green_merge_recommendation=bool(reasons),
        reason_codes=tuple(dict.fromkeys(reasons)),
        controls=tuple((control, requirement) for control in OPTIONAL_HARDENING_CONTROLS),
    )


__all__ = [
    "OPTIONAL_HARDENING_CONTROLS",
    "PERSONAL_MINIMUM_SECURITY_PROFILE",
    "RSN_MERGE_AUTHORIZATION_CLAIM_UNVERIFIED",
    "RSN_MERGE_ENFORCEMENT_MINIMUM_MISSING",
    "RSN_REPOSITORY_HOSTED_REQUIRED",
    "RSN_REPOSITORY_SETTINGS_CLAIM_UNVERIFIED",
    "SecurityProfileAssessment",
    "assess_security_profile",
]
