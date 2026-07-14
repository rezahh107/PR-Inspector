from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pr_inspector._governance_transport import _mint_response

ROOT = Path(__file__).resolve().parents[1]
HEAD = "1" * 40
REPOSITORY = "example/project"
PR_NUMBER = 42
_CACHED_SEQUENCE_CAPABILITY = None


def fixture() -> dict[str, Any]:
    return json.loads(
        (ROOT / "fixtures/governance/verified-enforced.json").read_text(
            encoding="utf-8"
        )
    )


def responses(
    value: dict[str, Any] | None = None,
    *,
    fetched_at: datetime | None = None,
):
    source = copy.deepcopy(value or fixture())
    observed = fetched_at or datetime.now(timezone.utc)
    return {
        name: _mint_response(
            request_url=item["url"],
            response_url=item["url"],
            status_code=item["status_code"],
            fetched_at=observed,
            payload=item["payload"],
        )
        for name, item in source["responses"].items()
    }


def membership_response(
    reviewer: str = "independent-reviewer",
    *,
    state: str = "active",
    fetched_at: datetime | None = None,
):
    url = (
        "https://api.github.com/orgs/example-org/teams/security-reviewers/"
        f"memberships/{reviewer}"
    )
    return _mint_response(
        request_url=url,
        response_url=url,
        status_code=200,
        fetched_at=fetched_at or datetime.now(timezone.utc),
        payload={"state": state, "role": "member", "url": url},
    )


def sequence_capability():
    global _CACHED_SEQUENCE_CAPABILITY
    if _CACHED_SEQUENCE_CAPABILITY is not None:
        return _CACHED_SEQUENCE_CAPABILITY
    from pr_inspector.governance import (
        verify_github_governance_source,
        verify_governance_record,
    )
    from pr_inspector.sequence_enforcement import (
        SEQUENCE_ENFORCEMENT_CHECK_CONTEXT,
        verify_sequence_ci_enforcement,
        verify_sequence_producer_evidence,
    )

    value = fixture()
    value["responses"]["checks"]["payload"]["check_runs"][0]["name"] = (
        SEQUENCE_ENFORCEMENT_CHECK_CONTEXT
    )
    required = value["responses"]["branch_protection"]["payload"][
        "required_status_checks"
    ]
    required["checks"][0]["context"] = SEQUENCE_ENFORCEMENT_CHECK_CONTEXT
    required["contexts"] = [SEQUENCE_ENFORCEMENT_CHECK_CONTEXT]
    source = verify_github_governance_source(
        responses(value),
        expected_repository=REPOSITORY,
        expected_pr_number=PR_NUMBER,
        expected_head_sha=HEAD,
    )
    governance = verify_governance_record(
        source,
        expected_repository=REPOSITORY,
        expected_pr_number=PR_NUMBER,
        expected_head_sha=HEAD,
    )
    producer = verify_sequence_producer_evidence(
        governance,
        check_context=SEQUENCE_ENFORCEMENT_CHECK_CONTEXT,
        app_id=15368,
        workflow_path=".github/workflows/validate-rereview-sequence.yml",
        workflow_sha="2" * 40,
        validator_command="python scripts/validate_rereview_sequence.py sequence.json --review EVENT=review",
    )
    _CACHED_SEQUENCE_CAPABILITY = verify_sequence_ci_enforcement(
        governance,
        check_context=SEQUENCE_ENFORCEMENT_CHECK_CONTEXT,
        app_id=15368,
        producer_evidence=producer,
    )
    return _CACHED_SEQUENCE_CAPABILITY
