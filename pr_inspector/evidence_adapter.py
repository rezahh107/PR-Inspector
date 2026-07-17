from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ._governance_transport import fetch_github_api_response
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


def _fixture_endpoint_urls(path: Path) -> dict[str, str]:
    value = json.loads(path.read_text(encoding="utf-8"))
    responses = value.get("responses")
    if not isinstance(responses, dict):
        raise ValueError("governance evidence fixture must contain a responses object")
    endpoints: dict[str, str] = {}
    for name, item in responses.items():
        if not isinstance(name, str) or not name or not isinstance(item, dict):
            raise ValueError("governance evidence fixture contains an invalid response entry")
        url = item.get("url")
        if not isinstance(url, str) or not url:
            raise ValueError(f"governance evidence fixture endpoint {name} has no URL")
        endpoints[name] = url
    return endpoints


def _fetch_responses_from_fixture_urls(
    path: Path,
    *,
    token: str | None,
    api_version: str,
) -> dict[str, Any]:
    return {
        name: fetch_github_api_response(
            url,
            token=token,
            api_version=api_version,
        )
        for name, url in _fixture_endpoint_urls(path).items()
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
    token: str | None = None,
    api_version: str = "2022-11-28",
) -> tuple[VerifiedGovernanceEvidence, VerifiedSequenceEnforcement]:
    """Fetch and verify live evidence for the endpoint set declared by a fixture.

    The file supplies endpoint names and canonical URLs only. Its status codes and payloads
    are untrusted and ignored; every capability is minted by the operational HTTPS fetch
    boundary from the response actually observed during this invocation.
    """

    source = verify_github_governance_source(
        _fetch_responses_from_fixture_urls(
            path,
            token=token,
            api_version=api_version,
        ),
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
