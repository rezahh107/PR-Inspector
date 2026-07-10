# Changelog

## 1.8.0

- Added a deterministic derived output layer after canonical review validation and rendering.
- Added the exact two-line Persian `OWNER_RESULT.fa.txt` with Green, Yellow, and Red outputs only.
- Added conditional deterministic `NEXT_ACTION_PROMPT.en.md` generation for Yellow and Red; Green forbids the prompt.
- Added structural `action_mode` derivation for `repair`, `verify`, `repair_and_verify`, and stale-safe `rerun_review`.
- Added an artifact manifest with canonical-package and rendered-artifact SHA-256 values.
- Added prompt authority, research, trust-boundary, invariant, adjacent-impact, self-audit, evidence, and mandatory PR Inspector re-review controls.
- Added deterministic, prompt-injection, stale-package, manifest-hash, and canonical-artifact regression tests.
- Preserved the released v1.7.0 snapshot and existing canonical review artifacts.

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
