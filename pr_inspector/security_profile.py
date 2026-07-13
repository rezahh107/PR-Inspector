from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .governance import (
    VerifiedGovernanceEvidence,
    is_verified_governance_evidence,
)

PERSONAL_MINIMUM_SECURITY_PROFILE = (
    "personal_ai_operated_strong_governance_minimum_security"
)

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

RSN_MERGE_ENFORCEMENT_MINIMUM_MISSING = (
    "RSN-MERGE-ENFORCEMENT-MINIMUM-MISSING"
)
RSN_REPOSITORY_HOSTED_REQUIRED = (
    "RSN-REPOSITORY-HOSTED-ENFORCEMENT-REQUIRED"
)
RSN_REPOSITORY_SETTINGS_CLAIM_UNVERIFIED = (
    "RSN-REPOSITORY-SETTINGS-CLAIM-UNVERIFIED"
)
RSN_MERGE_AUTHORIZATION_CLAIM_UNVERIFIED = (
    "RSN-MERGE-AUTHORIZATION-CLAIM-UNVERIFIED"
)


@dataclass(frozen=True)
class SecurityProfileAssessment:
    profile_name: str
    security_level: str
    sequence_ci_enforced: bool
    repository_hosted_enforcement: str
    github_app_exact_source_enforcement: str
    repository_settings_enforced: str
    merge_authorized: str
    blocks_green_merge_recommendation: bool
    reason_codes: tuple[str, ...]
    controls: tuple[tuple[str, str], ...]

    def projection(self) -> dict[str, Any]:
        return {
            "name": self.profile_name,
            "security_level": self.security_level,
            "sequence_ci_enforced": self.sequence_ci_enforced,
            "repository_hosted_enforcement": self.repository_hosted_enforcement,
            "github_app_exact_source_enforcement": (
                self.github_app_exact_source_enforcement
            ),
            "repository_settings_enforced": self.repository_settings_enforced,
            "merge_authorized": self.merge_authorized,
            "blocks_green_merge_recommendation": (
                self.blocks_green_merge_recommendation
            ),
            "reason_codes": list(self.reason_codes),
            "controls": [
                {"control": control, "classification": classification}
                for control, classification in self.controls
            ],
        }


def classify_governance_claim(
    claim_name: str,
    *,
    claimed: bool,
    governance_evidence: VerifiedGovernanceEvidence | None = None,
) -> str:
    """Classify stronger GitHub-governance claims without trusting caller data."""

    if claim_name not in {
        "repository_settings_enforced",
        "merge_authorized",
    }:
        raise ValueError(f"unsupported governance claim: {claim_name}")
    if not claimed:
        return "not_claimed"
    if not is_verified_governance_evidence(governance_evidence):
        return "rejected"

    assert isinstance(governance_evidence, VerifiedGovernanceEvidence)
    if claim_name == "repository_settings_enforced":
        return (
            "verified"
            if governance_evidence.enforcement_status == "verified_enforced"
            else "rejected"
        )
    return "verified" if governance_evidence.merge_authorized else "rejected"


def assess_security_profile(
    *,
    sequence_ci_enforced: bool = True,
    explicit_repository_requirement: bool = False,
    security_activation_trigger: bool = False,
    external_requirement: bool = False,
    claim_repository_settings_enforced: bool = False,
    claim_merge_authorized: bool = False,
    governance_evidence: VerifiedGovernanceEvidence | None = None,
) -> SecurityProfileAssessment:
    """Evaluate the default personal profile and any bounded activation trigger."""

    repository_settings_status = classify_governance_claim(
        "repository_settings_enforced",
        claimed=claim_repository_settings_enforced,
        governance_evidence=governance_evidence,
    )
    merge_authorized_status = classify_governance_claim(
        "merge_authorized",
        claimed=claim_merge_authorized,
        governance_evidence=governance_evidence,
    )
    repository_hosted_verified = (
        repository_settings_status == "verified"
        or merge_authorized_status == "verified"
    )
    repository_hosted_required = any(
        (
            explicit_repository_requirement,
            security_activation_trigger,
            external_requirement,
            claim_repository_settings_enforced,
            claim_merge_authorized,
        )
    )

    reasons: list[str] = []
    minimum_satisfied = sequence_ci_enforced or repository_hosted_verified
    if not minimum_satisfied:
        reasons.append(RSN_MERGE_ENFORCEMENT_MINIMUM_MISSING)
    if repository_hosted_required and not repository_hosted_verified:
        reasons.append(RSN_REPOSITORY_HOSTED_REQUIRED)
    if (
        claim_repository_settings_enforced
        and repository_settings_status != "verified"
    ):
        reasons.append(RSN_REPOSITORY_SETTINGS_CLAIM_UNVERIFIED)
    if claim_merge_authorized and merge_authorized_status != "verified":
        reasons.append(RSN_MERGE_AUTHORIZATION_CLAIM_UNVERIFIED)

    classification = (
        "required" if repository_hosted_required else "optional_hardening"
    )
    controls = tuple(
        (control, classification)
        for control in OPTIONAL_HARDENING_CONTROLS
    )
    return SecurityProfileAssessment(
        profile_name=PERSONAL_MINIMUM_SECURITY_PROFILE,
        security_level="minimum_security",
        sequence_ci_enforced=sequence_ci_enforced,
        repository_hosted_enforcement=classification,
        github_app_exact_source_enforcement=classification,
        repository_settings_enforced=repository_settings_status,
        merge_authorized=merge_authorized_status,
        blocks_green_merge_recommendation=bool(reasons),
        reason_codes=tuple(dict.fromkeys(reasons)),
        controls=controls,
    )


def green_merge_recommended(
    projection: dict[str, Any],
    assessment: SecurityProfileAssessment,
) -> bool:
    """Return the bounded recommendation without upgrading stronger claims."""

    return (
        projection.get("technical_status") == "GREEN_TECHNICALLY_READY"
        and projection.get("review_identity", {}).get("validity") == "CURRENT"
        and projection.get("next_action", {}).get("kind") == "merge_now"
        and not assessment.blocks_green_merge_recommendation
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
    "classify_governance_claim",
    "green_merge_recommended",
]
