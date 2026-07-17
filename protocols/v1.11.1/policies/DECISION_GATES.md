# Deterministic Decision Gates

Version: `v1.11.1`

## One authoritative projection

`pr_inspector.decision_projection.project_decision` is the only active implementation that derives technical status, owner readiness, reason codes, recipient, modification authority, prompt routing, inspection profile, governance decision, and governance follow-up. Free text and Candidate compatibility code cannot create or alter authority.

## Status and action precedence

Registered Red effects outrank Yellow effects; otherwise the review is Green. Non-current identity routes to `rerun_review`. Repair plus verification reasons route to `repair_and_verify`; repair reasons route to `repair`; verification reasons route to `verify`. Mandatory human or specialist approval remains a non-modifying handoff. Only current Green with no pending action and no additional approval routes to `merge_now`.

## Authority invariants

- `repair`, `repair_and_verify`: bounded same-PR modification authority.
- `verify`: reviewer-only; no patch, commit, refactor, or behavior change.
- `rerun_review`: fresh review only; previous findings are non-authorizing history.
- human/specialist review: cannot be satisfied by a model.
- governance follow-up: informational only and never technical repair authority.

## Candidate compatibility

Candidate helpers are pre-package only. Candidate projection, rendering, artifact building, verification, manifest generation, owner delivery, and prompt-required stdout are prohibited active authorities and fail closed.
