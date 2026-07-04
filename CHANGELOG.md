# Changelog

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
- Added the review contract and operational pipeline.
- Added Persian owner and English technical report templates.
- Added structural repository validation and maintenance files.
