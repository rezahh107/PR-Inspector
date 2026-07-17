from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pr_inspector._governance_transport as governance_transport
from pr_inspector._governance_transport import fetch_github_api_response

ROOT = Path(__file__).resolve().parents[1]
HEAD = "1" * 40
REPOSITORY = "example/project"
PR_NUMBER = 42
API_VERSION = "2026-03-10"
_CACHED_SEQUENCE_CAPABILITY = None


class _FakeHttpResponse:
    def __init__(self, url: str, payload: object, status: int):
        self._url = url
        self._payload = copy.deepcopy(payload)
        self.status = status
        self.code = status

    def geturl(self) -> str:
        return self._url

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def close(self) -> None:
        pass


def fixture() -> dict[str, Any]:
    return json.loads(
        (ROOT / "fixtures/governance/verified-enforced.json").read_text(
            encoding="utf-8"
        )
    )


def urlopen_for_fixture(value: dict[str, Any] | None = None):
    source = copy.deepcopy(value or fixture())
    by_url = {
        item["url"]: item
        for item in source["responses"].values()
    }

    def fake_urlopen(request, timeout):
        item = by_url[request.full_url]
        return _FakeHttpResponse(
            item.get("response_url", item["url"]),
            item["payload"],
            item["status_code"],
        )

    return fake_urlopen


def _fetch_item(item: dict[str, Any], *, fetched_at: datetime):
    source = {"responses": {"single": copy.deepcopy(item)}}
    with patch.object(
        governance_transport.urllib.request,
        "urlopen",
        urlopen_for_fixture(source),
    ):
        return fetch_github_api_response(
            item["url"],
            token=None,
            api_version=API_VERSION,
            fetched_at=fetched_at,
        )


def responses(
    value: dict[str, Any] | None = None,
    *,
    fetched_at: datetime | None = None,
):
    source = copy.deepcopy(value or fixture())
    observed = fetched_at or datetime.now(timezone.utc)
    return {
        name: _fetch_item(item, fetched_at=observed)
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
    return _fetch_item(
        {
            "url": url,
            "status_code": 200,
            "payload": {"state": state, "role": "member", "url": url},
        },
        fetched_at=fetched_at or datetime.now(timezone.utc),
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
