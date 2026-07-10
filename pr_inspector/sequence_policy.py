from __future__ import annotations

from typing import Iterable

from .diagnostics import Diagnostic

IMPLEMENTED_PENDING_REREVIEW = "implemented_pending_rereview"
REREVIEW_PASSED = "pr_inspector_rereview_passed"
ACCEPTANCE_EVENTS = {
    "technically_accepted",
    "merge_authorized",
    "merged",
}


def validate_rereview_sequence(events: Iterable[str]) -> list[Diagnostic]:
    """Require a later PR Inspector pass before any acceptance event."""

    seen_pending = False
    seen_rereview = False
    diagnostics: list[Diagnostic] = []
    for index, event in enumerate(events):
        if event == IMPLEMENTED_PENDING_REREVIEW:
            seen_pending = True
            seen_rereview = False
            continue
        if seen_pending and event == REREVIEW_PASSED:
            seen_rereview = True
            continue
        if (
            seen_pending
            and event in ACCEPTANCE_EVENTS
            and not seen_rereview
        ):
            diagnostics.append(
                Diagnostic(
                    "PRI-SEQUENCE-001",
                    f"/events/{index}",
                    (
                        f"{event} is forbidden after "
                        "implemented_pending_rereview until a later "
                        "pr_inspector_rereview_passed event"
                    ),
                )
            )
    return sorted(set(diagnostics))
