import json
from pathlib import Path

import pytest

from pr_inspector.sequence_policy import validate_rereview_sequence

ROOT = Path(__file__).resolve().parents[1]


def _codes(sequence: dict) -> set[str]:
    return {
        diagnostic.code
        for diagnostic in validate_rereview_sequence(sequence)
    }


@pytest.mark.parametrize(
    "event_type",
    ("technically_accepted", "merge_authorized", "merged"),
)
def test_orphan_acceptance_event_is_rejected(event_type: str):
    sequence = {
        "schema_version": 2,
        "events": [
            {
                "event_id": f"evt-orphan-{event_type}",
                "event_type": event_type,
                "target_repository": "example/project",
                "pr_number": 42,
                "resulting_head_sha": "1" * 40,
            }
        ],
    }

    assert _codes(sequence) == {"PRI-SEQUENCE-001"}


def test_removing_pending_event_from_valid_sequence_is_rejected():
    sequence = json.loads(
        (
            ROOT
            / "fixtures"
            / "rereview-sequence"
            / "valid.json"
        ).read_text(encoding="utf-8")
    )
    sequence["events"] = sequence["events"][1:]

    observed = _codes(sequence)

    assert "PRI-SEQUENCE-001" in observed
    assert "PRI-SEQUENCE-002" in observed
