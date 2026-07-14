from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from ._governance_transport import _mint_response
from .governance import (
    VerifiedGovernanceEvidence,
    verify_github_governance_source,
    verify_governance_record,
)
from .sequence_enforcement import (
    SEQUENCE_ENFORCEMENT_CHECK_CONTEXT,
    VerifiedSequenceEnforcement,
    verify_sequence_ci_enforcement,
    verify_sequence_producer_evidence,
)


def _responses_from_fixture(path: Path):
    value = json.loads(path.read_text(encoding="utf-8"))
    responses = value.get("responses")
    if not isinstance(responses, dict):
        raise ValueError("governance evidence fixture must contain a responses object")
    observed = datetime.now(timezone.utc)
    return {
        name: _mint_response(
            request_url=item["url"],
            response_url=item["url"],
            status_code=item["status_code"],
            fetched_at=observed,
            payload=item["payload"],
        )
        for name, item in responses.items()
    }


def mint_evidence_from_governance_fixture(
    path: Path,
    *,
    repository: str,
    pr_number: int,
    head_sha: str,
    sequence_app_id: int,
    sequence_workflow_path: str,
    sequence_workflow_sha: str,
    sequence_validator_command: str,
) -> tuple[VerifiedGovernanceEvidence, VerifiedSequenceEnforcement]:
    """Mint opaque evidence from raw GitHub response receipts for CLI operation.

    The fixture is treated as raw receipt material, not as a serialized capability:
    governance and sequence capabilities are minted in-process only after the same
    verifiers used by the Python API bind repository, PR, exact head, check/App,
    immutable workflow identity, and validator command execution.
    """

    source = verify_github_governance_source(
        _responses_from_fixture(path),
        expected_repository=repository,
        expected_pr_number=pr_number,
        expected_head_sha=head_sha,
    )
    governance = verify_governance_record(
        source,
        expected_repository=repository,
        expected_pr_number=pr_number,
        expected_head_sha=head_sha,
    )
    producer = verify_sequence_producer_evidence(
        governance,
        check_context=SEQUENCE_ENFORCEMENT_CHECK_CONTEXT,
        app_id=sequence_app_id,
        workflow_path=sequence_workflow_path,
        workflow_sha=sequence_workflow_sha,
        validator_command=sequence_validator_command,
    )
    sequence = verify_sequence_ci_enforcement(
        governance,
        check_context=SEQUENCE_ENFORCEMENT_CHECK_CONTEXT,
        app_id=sequence_app_id,
        producer_evidence=producer,
    )
    return governance, sequence
