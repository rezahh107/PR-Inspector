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
