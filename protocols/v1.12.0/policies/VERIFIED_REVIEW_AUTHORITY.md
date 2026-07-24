# Deterministic Review-Package Authority

## Rule

`review-package.json` is an official output of the PR Inspector runtime. It is never an authoritative caller input.

```text
ReviewRequest + ReviewAssessment + output directory
→ _create_official_runtime()
→ verified ProtocolContext
→ complete paginated GitHub collection
→ ReviewFacts + explicit external-review dispositions
→ assemble_review_package()
→ project_decision()
→ canonical artifact construction and atomic publication
→ VerifiedReviewCompletion
```

The public `complete_review` signature contains no `evidence_source`, `ReviewFacts`, live-Head object, canonical package, or `ProtocolContext`. The private `_complete_review_with_runtime` function is excluded from `__all__` and exists only for production delegation and deterministic internal tests.

The implementation uses ordinary frozen dataclasses and synchronous standard-library HTTP. It adds no signatures, HMAC, keys, capability-token system, sealed transport, or hostile-process defense.

## Field authority

Every canonical package field is assigned exactly one authority class through `pr_inspector.verified_review.FIELD_AUTHORITY`:

- **A — machine-collected fact:** repository/PR identity, Base, Head, merge base, changed files, complete checks, review surfaces, evidence, timestamps, and available capabilities.
- **B — reviewer assessment:** findings, rationale, affected surfaces, owner-facing explanation, limitations, suggested actions, and external-review dispositions.
- **C — deterministic derived value:** coverage, check projection, intent fit, external-review reconciliation, technical status, reason codes, recommendation, approval requirement, and next action.
- **D — verified protocol/static metadata:** schema version, protocol version, inspection profile, Inspector identity, Inspector commit, and static policy metadata.

No field is caller-authoritative by omission. `ReviewRequest.execution_options` permits only a non-authoritative checkout-location hint. `ReviewAssessment` rejects unknown properties and cannot carry status, risk, recommendation, reason codes, completion state, Base, Head, CI, or evidence truth.

## Protocol and evidence verification

The official runtime reuses canonical repository validation before loading `ProtocolContext`. It verifies active version alignment, active manifest status, entrypoint, trust policy, release lock and canonical hashes, immutable historical releases, Inspector repository identity and numeric ID, and existence of the exact Inspector commit in the locked repository. Failure returns a bounded incomplete-review diagnostic; no unverified fallback is permitted.

GitHub collection follows every page with `per_page=100`, rejects malformed payloads, loops, page-limit overflow, network failure, and check-run `total_count` mismatch. Observed failed checks remain `FAIL`; pending checks remain `UNKNOWN`; missing configured required checks are synthesized as required `UNKNOWN` evidence. Incomplete check enumeration cannot assemble a package.

Issue comments, review submissions, and inline review comments are collected as distinct untrusted evidence kinds. Every collected source must be classified by one `ExternalReviewDisposition`. Unknown sources, duplicate dispositions, unknown classes, and unknown linked findings fail. Unclassified sources remain explicit in `uninspected_source_ids`, set reconciliation to `INCOMPLETE`, and produce `RSN-EXTERNAL-REVIEW-INCOMPLETE`, which blocks technical Green without authorizing repair.

## Decision and publication authority

`pr_inspector.decision_projection.project_decision` remains the sole decision authority. The same canonical package bytes are used for projection, rendering, hashing, staging, validation, and publication. Live Head is checked before staging, immediately before publication, and after publication. Head drift or any assembly/render/validation/publication failure produces no new official bundle and preserves a previously valid bundle.

## Legacy and preview

Raw paths, mappings, JSON bytes, and prebuilt package objects return `PRI-PACKAGE-AUTHORITY-001` and cannot publish or mint completion. `render_unverified_preview` remains a non-authoritative `DECLARATION` with `official_completion=false`.
