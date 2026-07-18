from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, order=True, slots=True)
class AIGOVDiagnostic:
    """Deterministic diagnostic emitted by inactive AIGOV validation."""

    code: str
    contract_type: str
    path: str
    invariant: str
    reason: str
    evidence_path: str = ""

    def line(self) -> str:
        evidence = f" [{self.evidence_path}]" if self.evidence_path else ""
        return (
            f"{self.code} {self.contract_type} {self.path}: "
            f"{self.invariant}: {self.reason}{evidence}"
        )


class AIGOVValidationError(ValueError):
    """Raised when schema or semantic validation rejects an AIGOV payload."""

    def __init__(self, diagnostics: Iterable[AIGOVDiagnostic]):
        ordered = tuple(
            sorted(
                diagnostics,
                key=lambda item: (
                    item.code,
                    item.contract_type,
                    item.path,
                    item.invariant,
                    item.reason,
                    item.evidence_path,
                ),
            )
        )
        if not ordered:
            raise ValueError("AIGOVValidationError requires at least one diagnostic")
        self.diagnostics = ordered
        super().__init__("; ".join(item.line() for item in ordered))


def diagnostic(
    code: str,
    contract_type: str,
    path: str,
    invariant: str,
    reason: str,
    *,
    evidence_path: str = "",
) -> AIGOVDiagnostic:
    return AIGOVDiagnostic(
        code=code,
        contract_type=contract_type,
        path=path,
        invariant=invariant,
        reason=reason,
        evidence_path=evidence_path,
    )
