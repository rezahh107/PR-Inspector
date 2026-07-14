from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from weakref import WeakSet

from .governance import (
    VerifiedGovernanceEvidence,
    is_verified_governance_evidence,
)

SEQUENCE_ENFORCEMENT_CHECK_CONTEXT = "Validate rereview sequence enforcement"
_SEQUENCE_MARKER = object()
_SEQUENCE_CAPABILITIES: WeakSet[VerifiedSequenceEnforcement] = WeakSet()
_PRODUCER_MARKER = object()
_PRODUCER_CAPABILITIES: WeakSet[VerifiedSequenceProducerEvidence] = WeakSet()
_SHA40 = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True, eq=False)
class VerifiedSequenceProducerEvidence:
    evidence_id: str
    repository: str
    pull_request_number: int
    exact_head_sha: str
    check_context: str
    app_id: int
    workflow_path: str
    workflow_sha: str
    validator_command: str
    source_governance_evidence_id: str
    _marker: object = field(repr=False, compare=False)


@dataclass(frozen=True, eq=False)
class VerifiedSequenceEnforcement:
    evidence_id: str
    repository: str
    pull_request_number: int
    exact_head_sha: str
    check_context: str
    app_id: int
    source_governance_evidence_id: str
    source_producer_evidence_id: str
    _marker: object = field(repr=False, compare=False)


def is_verified_sequence_producer_evidence(value: object) -> bool:
    return (
        isinstance(value, VerifiedSequenceProducerEvidence)
        and value._marker is _PRODUCER_MARKER
        and value in _PRODUCER_CAPABILITIES
    )


def is_verified_sequence_enforcement(value: object) -> bool:
    return (
        isinstance(value, VerifiedSequenceEnforcement)
        and value._marker is _SEQUENCE_MARKER
        and value in _SEQUENCE_CAPABILITIES
    )


def verify_sequence_producer_evidence(
    governance_evidence: VerifiedGovernanceEvidence,
    *,
    check_context: str,
    app_id: int,
    workflow_path: str,
    workflow_sha: str,
    validator_command: str,
) -> VerifiedSequenceProducerEvidence:
    """Mint evidence that the designated sequence check came from trusted execution.

    This proof is intentionally separate from GitHub required-check presence: a
    same-name/same-App check is insufficient unless this verifier also binds an
    immutable workflow identity and the sequence-validator command to the exact
    repository, PR, and head.
    """

    if not is_verified_governance_evidence(governance_evidence):
        raise ValueError("sequence producer evidence requires verified governance evidence")
    if check_context != SEQUENCE_ENFORCEMENT_CHECK_CONTEXT:
        raise ValueError("sequence producer evidence requires the designated check context")
    if (check_context, app_id) not in governance_evidence.required_status_checks:
        raise ValueError("sequence producer evidence requires an exact-App required check")
    if not governance_evidence.exact_head_checks_satisfied:
        raise ValueError("sequence producer evidence requires successful exact-head checks")
    if not workflow_path.startswith(".github/workflows/") or not workflow_path.endswith((".yml", ".yaml")):
        raise ValueError("sequence producer workflow path is not trusted")
    if not _SHA40.fullmatch(workflow_sha):
        raise ValueError("sequence producer workflow SHA must be immutable")
    if "validate_rereview_sequence.py" not in validator_command:
        raise ValueError("sequence producer did not execute the sequence validator")

    payload = {
        "repository": governance_evidence.repository,
        "pull_request_number": governance_evidence.pull_request_number,
        "exact_head_sha": governance_evidence.exact_head_sha,
        "check_context": check_context,
        "app_id": app_id,
        "workflow_path": workflow_path,
        "workflow_sha": workflow_sha,
        "validator_command": validator_command,
        "source_governance_evidence_id": governance_evidence.evidence_id,
    }
    evidence_id = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()
    proof = VerifiedSequenceProducerEvidence(evidence_id=evidence_id, _marker=_PRODUCER_MARKER, **payload)
    _PRODUCER_CAPABILITIES.add(proof)
    return proof


def verify_sequence_ci_enforcement(
    governance_evidence: VerifiedGovernanceEvidence,
    *,
    check_context: str,
    app_id: int,
    producer_evidence: VerifiedSequenceProducerEvidence | None = None,
) -> VerifiedSequenceEnforcement:
    """Mint an opaque capability from the designated exact-head sequence check.

    The capability is available only when the designated check is an exact-App
    required status check and every required check succeeded on the reviewed head.
    A different required check, a serialized lookalike, or a bare boolean cannot
    satisfy this boundary. Capability registration is identity-based so separately
    verified equal evidence instances cannot invalidate one another.
    """

    if not is_verified_governance_evidence(governance_evidence):
        raise ValueError("sequence enforcement requires verified governance evidence")
    if check_context != SEQUENCE_ENFORCEMENT_CHECK_CONTEXT:
        raise ValueError(
            "sequence enforcement requires the designated sequence check context"
        )
    if not isinstance(app_id, int) or app_id <= 0:
        raise ValueError("sequence check app_id must be a positive integer")
    if not is_verified_sequence_producer_evidence(producer_evidence):
        raise ValueError("sequence enforcement requires verified producer execution evidence")
    assert isinstance(producer_evidence, VerifiedSequenceProducerEvidence)
    if (
        producer_evidence.repository != governance_evidence.repository
        or producer_evidence.pull_request_number != governance_evidence.pull_request_number
        or producer_evidence.exact_head_sha != governance_evidence.exact_head_sha
        or producer_evidence.check_context != check_context
        or producer_evidence.app_id != app_id
        or producer_evidence.source_governance_evidence_id != governance_evidence.evidence_id
    ):
        raise ValueError("sequence producer evidence does not match governance evidence")

    required_check = (check_context, app_id)
    if required_check not in governance_evidence.required_status_checks:
        raise ValueError(
            "sequence enforcement check is not an exact-App required status check"
        )
    if not governance_evidence.exact_head_checks_satisfied:
        raise ValueError(
            "sequence enforcement requires successful required checks on the exact head"
        )

    payload = {
        "repository": governance_evidence.repository,
        "pull_request_number": governance_evidence.pull_request_number,
        "exact_head_sha": governance_evidence.exact_head_sha,
        "check_context": check_context,
        "app_id": app_id,
        "source_governance_evidence_id": governance_evidence.evidence_id,
        "source_producer_evidence_id": producer_evidence.evidence_id,
    }
    evidence_id = hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    capability = VerifiedSequenceEnforcement(
        evidence_id=evidence_id,
        _marker=_SEQUENCE_MARKER,
        **payload,
    )
    _SEQUENCE_CAPABILITIES.add(capability)
    return capability


def sequence_enforcement_matches_package(
    package: dict[str, object],
    capability: VerifiedSequenceEnforcement | None,
) -> bool:
    if not is_verified_sequence_enforcement(capability):
        return False
    assert isinstance(capability, VerifiedSequenceEnforcement)
    identity = package.get("review_identity")
    if not isinstance(identity, dict):
        return False
    return (
        capability.repository == identity.get("target_repository")
        and capability.pull_request_number == identity.get("pr_number")
        and capability.exact_head_sha == identity.get("reviewed_head_sha")
    )


__all__ = [
    "SEQUENCE_ENFORCEMENT_CHECK_CONTEXT",
    "VerifiedSequenceEnforcement",
    "VerifiedSequenceProducerEvidence",
    "is_verified_sequence_enforcement",
    "is_verified_sequence_producer_evidence",
    "sequence_enforcement_matches_package",
    "verify_sequence_ci_enforcement",
    "verify_sequence_producer_evidence",
]
