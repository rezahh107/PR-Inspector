from __future__ import annotations

import json
import weakref
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, TypeAlias, Union


class _StringEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class ActivationState(_StringEnum):
    INACTIVE = "inactive"


class InspectionProfile(_StringEnum):
    MINIMAL = "minimal"
    STANDARD = "standard"
    STRICT = "strict"


class EvidenceProfile(_StringEnum):
    """Schema-backed AIGOV v2.5.0 evidence profile."""

    COMPACT = "compact"
    FULL = "full"
    HIGH_ASSURANCE = "high_assurance"


class ExecutionUrgency(_StringEnum):
    """Schema-backed AIGOV v2.5.0 execution urgency."""

    NORMAL = "normal"
    EXPEDITED = "expedited"


class FutureEvidenceProfile(_StringEnum):
    """Future inactive vocabulary requested by S-003; not schema-activated."""

    MINIMAL = "minimal"
    STANDARD = "standard"
    STRICT = "strict"


class FutureExecutionUrgency(_StringEnum):
    """Future inactive vocabulary requested by S-003; not schema-activated."""

    ROUTINE = "routine"
    ELEVATED = "elevated"
    URGENT = "urgent"


class ActivationResult(_StringEnum):
    """Future inactive activation result; not used by active PR-Inspector."""

    NOT_ATTEMPTED = "not_attempted"
    BLOCKED = "blocked"
    ACTIVATED = "activated"
    FAILED = "failed"


class PolicyLifecycle(_StringEnum):
    CANDIDATE = "candidate"
    TRIAL = "trial"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    INACTIVE = "inactive"


class BehavioralEnforcementStatus(_StringEnum):
    PROSE_ONLY = "prose_only"
    SCHEMA_BACKED = "schema_backed"
    VALIDATOR_BACKED = "validator_backed"
    FIXTURE_TESTED = "fixture_tested"
    CI_ENFORCED = "ci_enforced"
    DOWNSTREAM_CONTRACT_ENFORCED = "downstream_contract_enforced"


class EvidenceSufficiency(_StringEnum):
    SUFFICIENT = "sufficient"
    INSUFFICIENT = "insufficient"


class ReceiptPublicationStatus(_StringEnum):
    NOT_REQUIRED = "not_required"
    NOT_ATTEMPTED = "not_attempted"
    PUBLISHING = "publishing"
    PUBLISHED_VERIFIED = "published_verified"
    PUBLICATION_FAILED = "publication_failed"


class PublicationAttemptStatus(_StringEnum):
    NOT_ATTEMPTED = "not_attempted"
    PUBLISHING = "publishing"
    PUBLISHED_VERIFIED = "published_verified"
    PUBLICATION_FAILED = "publication_failed"


class MergeEnforcementProfile(_StringEnum):
    OWNER_CONTROLLED = "owner_controlled"
    CI_ENFORCED = "ci_enforced"
    REPOSITORY_ENFORCED = "repository_enforced"


class MergeGovernanceStatus(_StringEnum):
    ENFORCEMENT_VERIFIED = "enforcement_verified"
    ENFORCEMENT_UNVERIFIED = "enforcement_unverified"
    ENFORCEMENT_NOT_REQUIRED = "enforcement_not_required"
    ENFORCEMENT_CONFLICTING = "enforcement_conflicting"


class MergeMethod(_StringEnum):
    MERGE_COMMIT = "merge_commit"
    SQUASH_MERGE = "squash_merge"
    REBASE_MERGE = "rebase_merge"


class MergeReadinessResult(_StringEnum):
    READY_FOR_USER_MERGE = "READY_FOR_USER_MERGE"
    NOT_READY = "NOT_READY"
    BLOCKED_POLICY_UNRESOLVED = "BLOCKED_POLICY_UNRESOLVED"
    BLOCKED_REQUIRED_REVIEW = "BLOCKED_REQUIRED_REVIEW"
    BLOCKED_REQUIRED_PUBLICATION = "BLOCKED_REQUIRED_PUBLICATION"


class PostMergeClosureStatus(_StringEnum):
    NOT_STARTED = "not_started"
    MERGE_RESULT_VERIFIED = "merge_result_verified"
    CURRENT_MAIN_VALIDATED = "current_main_validated"
    BLOCKED_STATUS_DRIFT = "blocked_status_drift"
    STATUS_RECONCILED = "status_reconciled"
    CLOSURE_RECORDED = "closure_recorded"


class DependentWorkAuthorization(_StringEnum):
    ALLOWED = "allowed"
    BLOCKED_POST_MERGE_CLOSURE = "blocked_post_merge_closure"
    BLOCKED_STATUS_DRIFT = "blocked_status_drift"


class MethodAwareOutcome(_StringEnum):
    CONTENT_EQUIVALENCE_VERIFIED = "content_equivalence_verified"
    HISTORY_TOPOLOGY_VERIFIED = "history_topology_verified"
    HISTORY_TOPOLOGY_NOT_PRESERVED = "history_topology_not_preserved_by_merge_method"
    CONTENT_LOSS_DETECTED = "content_loss_detected"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ToolExecutionStatus(_StringEnum):
    NOT_ATTEMPTED = "not_attempted"
    INVOKED = "invoked"
    SUCCESS = "success"
    FAILED = "failed"
    UNVERIFIED = "unverified"


class ToolReadbackStatus(_StringEnum):
    VERIFIED = "VERIFIED"
    READBACK_NOT_REQUIRED = "READBACK_NOT_REQUIRED"
    FAILED = "FAILED"
    NOT_PERFORMED = "NOT_PERFORMED"


class ToolClaimBindingStatus(_StringEnum):
    VERIFIED_RESULT_BOUND = "VERIFIED_RESULT_BOUND"
    VERIFIED_READBACK_BOUND = "VERIFIED_READBACK_BOUND"
    INVALID_RESULT_DETACHED = "INVALID_RESULT_DETACHED"


class TechnicalStatus(_StringEnum):
    GREEN = "GREEN_TECHNICALLY_READY"
    YELLOW = "YELLOW_CHANGES_OR_VERIFICATION_REQUIRED"
    RED = "RED_DO_NOT_MERGE"


@dataclass(frozen=True, slots=True)
class AIGOVValidationProvenance:
    contract_type: str
    contract_version: str
    schema_id: str
    schema_sha256: str
    payload_sha256: str
    semantic_validator_version: str


def _freeze(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, Mapping):
        frozen: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("AIGOV mappings require string keys")
            frozen[key] = _freeze(item)
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    raise TypeError(f"unsupported AIGOV value type: {type(value).__name__}")


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


_MODEL_FACTORY_TOKEN = object()
_VALIDATED_MODELS: weakref.WeakSet[_AIGOVContract] = weakref.WeakSet()


class _AIGOVContract:
    """Factory-controlled immutable model for one inactive AIGOV contract."""

    __slots__ = (
        "_payload",
        "_canonical_json",
        "_provenance",
        "__weakref__",
    )
    CONTRACT_TYPE = ""

    def __init__(self, *_: object, **__: object) -> None:
        raise TypeError(
            f"{type(self).__name__} can only be created by load_aigov_contract()"
        )

    def __setattr__(self, _name: str, _value: object) -> None:
        raise AttributeError(f"{type(self).__name__} is immutable")

    @property
    def contract_type(self) -> str:
        return self.CONTRACT_TYPE

    @property
    def contract_version(self) -> str:
        return str(self._payload["contract_version"])

    @property
    def activation_state(self) -> str:
        return str(self._payload["activation_state"])

    @property
    def schema_id(self) -> str:
        return self._provenance.schema_id

    @property
    def provenance(self) -> AIGOVValidationProvenance:
        return self._provenance

    @property
    def payload(self) -> Mapping[str, Any]:
        return self._payload

    def field(self, name: str) -> Any:
        return self._payload[name]

    def __getitem__(self, name: str) -> Any:
        return self._payload[name]

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._payload)

    def to_json(self) -> str:
        return self._canonical_json

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(contract_type={self.CONTRACT_TYPE!r}, "
            f"payload_sha256={self._provenance.payload_sha256!r})"
        )

    def __eq__(self, other: object) -> bool:
        return (
            type(self) is type(other)
            and isinstance(other, _AIGOVContract)
            and self._canonical_json == other._canonical_json
            and self._provenance == other._provenance
        )

    def __hash__(self) -> int:
        return hash((type(self), self._canonical_json, self._provenance))

    def __copy__(self) -> _AIGOVContract:
        return self

    def __deepcopy__(self, _memo: dict[int, object]) -> _AIGOVContract:
        return self

    def __reduce__(self):
        raise TypeError("validated AIGOV contract capabilities are not pickleable")


class RepositoryReviewPolicy(_AIGOVContract):
    __slots__ = ()
    CONTRACT_TYPE = "repository_review_policy"


class ReviewPolicyResolution(_AIGOVContract):
    __slots__ = ()
    CONTRACT_TYPE = "review_policy_resolution"


class ObligationAuthorityBinding(_AIGOVContract):
    __slots__ = ()
    CONTRACT_TYPE = "obligation_authority_binding"


class ClassificationRecord(_AIGOVContract):
    __slots__ = ()
    CONTRACT_TYPE = "classification_record"


class ScopeRecord(_AIGOVContract):
    __slots__ = ()
    CONTRACT_TYPE = "scope_record"


class ReviewExecution(_AIGOVContract):
    __slots__ = ()
    CONTRACT_TYPE = "review_execution"


class ReviewReceiptCore(_AIGOVContract):
    __slots__ = ()
    CONTRACT_TYPE = "review_receipt_core"


class PublicationAttempt(_AIGOVContract):
    __slots__ = ()
    CONTRACT_TYPE = "publication_attempt"


class PolicyTransitionRecord(_AIGOVContract):
    __slots__ = ()
    CONTRACT_TYPE = "policy_transition_record"


class MergeReadinessRecord(_AIGOVContract):
    __slots__ = ()
    CONTRACT_TYPE = "merge_readiness_record"


class PostMergeClosure(_AIGOVContract):
    __slots__ = ()
    CONTRACT_TYPE = "post_merge_closure"


class ToolExecutionAttestation(_AIGOVContract):
    __slots__ = ()
    CONTRACT_TYPE = "tool_execution_attestation"


MODEL_BY_CONTRACT = MappingProxyType(
    {
        model.CONTRACT_TYPE: model
        for model in (
            RepositoryReviewPolicy,
            ReviewPolicyResolution,
            ObligationAuthorityBinding,
            ClassificationRecord,
            ScopeRecord,
            ReviewExecution,
            ReviewReceiptCore,
            PublicationAttempt,
            PolicyTransitionRecord,
            MergeReadinessRecord,
            PostMergeClosure,
            ToolExecutionAttestation,
        )
    }
)

AIGOVContract: TypeAlias = Union[
    RepositoryReviewPolicy,
    ReviewPolicyResolution,
    ObligationAuthorityBinding,
    ClassificationRecord,
    ScopeRecord,
    ReviewExecution,
    ReviewReceiptCore,
    PublicationAttempt,
    PolicyTransitionRecord,
    MergeReadinessRecord,
    PostMergeClosure,
    ToolExecutionAttestation,
]


def _mint_validated_contract(
    *,
    contract_type: str,
    payload: Mapping[str, Any],
    provenance: AIGOVValidationProvenance,
    factory_token: object,
) -> AIGOVContract:
    if factory_token is not _MODEL_FACTORY_TOKEN:
        raise TypeError("AIGOV model factory token is invalid")
    model_type = MODEL_BY_CONTRACT[contract_type]
    canonical_json = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    value = object.__new__(model_type)
    object.__setattr__(value, "_payload", _freeze(payload))
    object.__setattr__(value, "_canonical_json", canonical_json)
    object.__setattr__(value, "_provenance", provenance)
    _VALIDATED_MODELS.add(value)
    return value


def is_validated_aigov_contract(value: object) -> bool:
    return (
        type(value) in tuple(MODEL_BY_CONTRACT.values())
        and isinstance(value, _AIGOVContract)
        and value in _VALIDATED_MODELS
    )
