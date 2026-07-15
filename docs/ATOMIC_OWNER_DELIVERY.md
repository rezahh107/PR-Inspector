# Atomic Owner Delivery

## Problem

The canonical review bundle already requires `NEXT_ACTION_PROMPT.en.md` exactly when `DECISION_PROJECTION.json#/next_action/prompt_required` is true. That artifact-level guarantee does not by itself prevent a caller from displaying only `OWNER_RESULT.fa.txt` and forgetting to deliver the prompt.

## Supported human-facing boundary

Human-facing consumers must call:

```python
from pr_inspector.official_review import official_owner_delivery

text = official_owner_delivery(verified_completion)
```

The accessor performs one live-head recheck and one full verified-byte snapshot validation. It then returns:

- the exact two-line Persian owner result when no action prompt is required; or
- the exact two-line Persian owner result, a fixed Persian heading, and the complete verified `NEXT_ACTION_PROMPT.en.md` bytes when a prompt is required.

The prompt is not regenerated, summarized, reconstructed, or read from disk after verification.

## Fail-closed behavior

`official_owner_result` is intentionally unavailable for prompt-required decisions. It raises `CompletionError` and directs the caller to `official_owner_delivery`. This prevents the supported owner-output API from producing a status message that says a prompt is ready while omitting the prompt itself.

The delivery accessor also rejects:

- a caller-created or forged completion object;
- a missing required prompt;
- a forbidden prompt on a no-prompt decision;
- live PR-head drift;
- artifact, projection, manifest, or final-byte drift.

Machine consumers that explicitly need the standalone canonical artifact can use the verified completion object's low-level artifact accessor. That path is not the supported human-facing delivery boundary.

## CLI contract

`scripts/render_review_v2.py` writes only the complete owner delivery to stdout after successful official completion. Operational success metadata is written to stderr. The script computes and verifies the entire delivery before writing any owner-facing bytes, so a delivery failure cannot leave a misleading partial success response on stdout.

## Scope

This hardening does not change canonical decision derivation, prompt routing, artifact names, schemas, released protocol snapshots, or release locks. It closes an omission in the supported official-output consumption boundary by making co-delivery mandatory for prompt-required owner responses.

## Validation

Dedicated tests cover:

- exact owner-result plus prompt co-delivery;
- rejection of owner-only access when a prompt is required;
- unchanged two-line delivery for no-prompt decisions;
- rejection of missing required prompts; and
- rejection of forged completion objects.
