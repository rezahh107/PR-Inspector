from __future__ import annotations

import json
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from .diagnostics import Diagnostic

ROOT = Path(__file__).resolve().parents[1]
CURRENT_VERSION = (ROOT / "CURRENT_VERSION").read_text(encoding="utf-8").strip()
SCHEMA_PATH = (
    ROOT
    / f"protocols/{CURRENT_VERSION}/schemas/rereview-sequence.schema.json"
)

IMPLEMENTED_PENDING_REREVIEW = "implemented_pending_rereview"
REREVIEW_COMPLETED = "pr_inspector_rereview_completed"
ACCEPTANCE_EVENTS = {
    "technically_accepted",
    "merge_authorized",
    "merged",
}


@lru_cache(maxsize=1)
def _sequence_validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _schema_diagnostics(sequence: Any) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    try:
        validator = _sequence_validator()
    except (OSError, json.JSONDecodeError, SchemaError) as exc:
        return [
            Diagnostic(
                "PRI-SEQUENCE-SCHEMA-001",
                f"/{SCHEMA_PATH.relative_to(ROOT)}",
                f"cannot load rereview sequence schema: {exc}",
            )
        ]

    for error in validator.iter_errors(sequence):
        path = "/" + "/".join(str(item) for item in error.absolute_path)
        diagnostics.append(
            Diagnostic("PRI-SEQUENCE-SCHEMA-001", path, error.message)
        )
    return sorted(set(diagnostics))


def validate_rereview_sequence(sequence: Mapping[str, Any]) -> list[Diagnostic]:
    """Require an identity-bound CURRENT re-review before accepting a repaired head."""

    schema_diagnostics = _schema_diagnostics(sequence)
    if schema_diagnostics:
        return schema_diagnostics

    events = sequence["events"]
    diagnostics: list[Diagnostic] = []
    seen_event_ids: set[str] = set()
    pending_heads: dict[tuple[str, int], str] = {}
    passed_heads: dict[tuple[str, int], str] = {}

    for index, event in enumerate(events):
        path = f"/events/{index}"
        event_id = event["event_id"]
        event_type = event["event_type"]
        key = (event["target_repository"], event["pr_number"])
        resulting_head = event["resulting_head_sha"]

        if event_id in seen_event_ids:
            diagnostics.append(
                Diagnostic(
                    "PRI-SEQUENCE-007",
                    f"{path}/event_id",
                    f"replayed lifecycle event_id {event_id}",
                )
            )
            continue
        seen_event_ids.add(event_id)

        if event_type == IMPLEMENTED_PENDING_REREVIEW:
            pending_heads[key] = resulting_head
            passed_heads.pop(key, None)
            continue

        if event_type == REREVIEW_COMPLETED:
            expected_head = pending_heads.get(key)
            if expected_head is None:
                diagnostics.append(
                    Diagnostic(
                        "PRI-SEQUENCE-002",
                        path,
                        (
                            "re-review does not match an "
                            "implemented_pending_rereview event for the same "
                            "repository and pull request"
                        ),
                    )
                )
                continue

            identity_matches = (
                resulting_head == expected_head
                and event["reviewed_head_sha"] == expected_head
            )
            if not identity_matches:
                diagnostics.append(
                    Diagnostic(
                        "PRI-SEQUENCE-003",
                        path,
                        (
                            "re-review resulting_head_sha and reviewed_head_sha "
                            "must both equal the pending repaired head"
                        ),
                    )
                )

            if event["review_validity"] != "CURRENT":
                diagnostics.append(
                    Diagnostic(
                        "PRI-SEQUENCE-004",
                        f"{path}/review_validity",
                        "only a CURRENT re-review can unlock acceptance",
                    )
                )

            if event["review_result"] != "PASSED":
                diagnostics.append(
                    Diagnostic(
                        "PRI-SEQUENCE-005",
                        f"{path}/review_result",
                        "only a PASSED re-review can unlock acceptance",
                    )
                )

            if (
                identity_matches
                and event["review_validity"] == "CURRENT"
                and event["review_result"] == "PASSED"
            ):
                passed_heads[key] = expected_head
            continue

        if event_type in ACCEPTANCE_EVENTS:
            expected_head = pending_heads.get(key)
            if expected_head is None:
                continue
            if resulting_head != expected_head:
                diagnostics.append(
                    Diagnostic(
                        "PRI-SEQUENCE-006",
                        f"{path}/resulting_head_sha",
                        (
                            f"{event_type} targets {resulting_head}, but the "
                            f"pending repaired head is {expected_head}"
                        ),
                    )
                )
                continue
            if passed_heads.get(key) != expected_head:
                diagnostics.append(
                    Diagnostic(
                        "PRI-SEQUENCE-001",
                        path,
                        (
                            f"{event_type} is forbidden until a later CURRENT "
                            "PASSED PR Inspector re-review is bound to the same "
                            "repository, pull request, and repaired head"
                        ),
                    )
                )

    return sorted(set(diagnostics))
