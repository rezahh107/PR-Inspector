from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator, TYPE_CHECKING

if TYPE_CHECKING:
    from .governance import VerifiedGovernanceEvidence
    from .sequence_enforcement import VerifiedSequenceEnforcement

_EVIDENCE_CONTEXT: ContextVar[tuple[object | None, object | None]] = ContextVar(
    "pr_inspector_evidence_context",
    default=(None, None),
)


def current_evidence() -> tuple[object | None, object | None]:
    return _EVIDENCE_CONTEXT.get()


@contextmanager
def evidence_scope(
    governance_evidence: VerifiedGovernanceEvidence | None = None,
    sequence_enforcement: VerifiedSequenceEnforcement | None = None,
) -> Iterator[None]:
    token = _EVIDENCE_CONTEXT.set((governance_evidence, sequence_enforcement))
    try:
        yield
    finally:
        _EVIDENCE_CONTEXT.reset(token)


__all__ = ["current_evidence", "evidence_scope"]
