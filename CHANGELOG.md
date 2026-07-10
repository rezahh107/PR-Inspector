# Changelog

## 1.8.0

- Added one canonical deterministic `DECISION_PROJECTION.json` consumed by semantic validation, owner rendering, technical handoff, action routing, and artifact validation.
- Added a versioned canonical decision-reason registry with stable technical effects, action effects, recipients, modification authority, prompt kinds, and recovery actions.
- Separated technical status from owner readiness and approval state.
- Limited Green merge-now wording to current technical Green reviews with no additional approval and no pending structured action.
- Added finite two-line Persian owner messages for owner confirmation, human review, specialist review, verification, repair, repair plus verification, stale review, Red states, and internal blocked state.
- Routed mandatory human and specialist approval to dedicated handoffs that explicitly cannot be satisfied or claimed by model output.
- Made verification and stale-review artifacts non-modifying; repair discovery during verification requires a fresh canonical decision.
- Added projection-backed bounded `repair` and separately enforced `repair_and_verify` behavior.
- Removed the active and legacy competing technical-status mappings; compatibility status calls delegate to the canonical projection.
- Added a versioned Behavioral Rule Coverage matrix with dedicated mutation fixtures, focused CI enforcement, and a sequence gate for mandatory post-repair PR Inspector re-review.
- Added structured CI object-identity schema, fixtures, validator, recorder, exact-head assertion, synthetic-merge distinction, workflow run, job, SHA, and tree traceability.
- Added `artifact-manifest.json` schema v2 behavior: canonical package hash, actual package-file hash, and hashes recomputed from final bytes reread from disk.
- Added rejection coverage for byte mutation, CRLF, BOM, trailing-newline drift, stale manifests, projection drift, unregistered reason codes, prompt injection, recipient drift, exact-head overclaim, and premature acceptance.
- Added focused Behavioral Rule Coverage tests, focused artifact byte tests, and full-suite CI across Python 3.10–3.14.
- Added the decision projection, reason registry, coverage matrix, schemas, policies, templates, and pipeline to the active v1.8 load order and release lock.
- Preserved the released v1.7.0 snapshot and release lock byte-for-byte.

## 1.7.0

- Added optional canonical `external_review_intake` for untrusted external PR review suggestions.
- Added semantic validation for accepted external suggestions: evidence, finding links, repair instructions, known references, and inaccessible-source reporting.
- Rendered External Review Suggestions Considered in the Technical Handoff from JSON only.
- Rendered only accepted external suggestions in the implementer-facing Repair Handoff.
- Added focused fixtures and tests for accepted, rejected, missing-evidence, and unknown-finding external suggestions.

## 1.6.0

- Added an optional canonical `repair_handoff` carrier for downstream implementer-model repair guidance.
- Rendered the Repair Handoff for Implementer Model section in `TECHNICAL_HANDOFF.en.md` from `review-package.json` only.
- Added semantic validation that rejects repair handoff references to unknown findings or rule IDs not attached to the referenced finding.
- Added a focused valid fixture and regression tests for repair handoff rendering and reference validation.

## 1.5.0

- Added the v1.5.0 protocol snapshot as a vertical-slice upgrade from v1.4.0.
- Activated exactly one correctness / intent-fit rule: `PRR-INTENT-001`.
- Added the `intent_fit` semantic carrier to the review package schema.
- Added semantic validation that prevents full intent-satisfaction claims without concrete implementation evidence.
- Added focused valid and invalid fixtures for satisfied, missing, hypothesis-only, and not-assessable intent-fit states.

## 1.4.0

- Added immutable full-protocol snapshots and SHA-256 release locks.
- Added a canonical JSON review package using JSON Schema Draft 2020-12.
- Added deterministic semantic validation for SHA validity, decision gates, sensitive approvals, evidence links, counts, and output consistency.
- Added deterministic Persian owner-card and English technical-handoff renderers.
- Added a synthetic golden fixture plus negative mutation tests for critical gate behavior.
- Added a Python 3.10–3.14 CI matrix with pinned project dependencies.
- Added an end-to-end command-line workflow and Apache-2.0 licensing.

## 1.3.0

- Added the repository bootstrap and active-version manifest.
- Added Persian owner and English technical report templates.
- Added structural repository validation and maintenance files.
