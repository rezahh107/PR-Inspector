# Deterministic Review-Package Authority

## Rule

`review-package.json` is an official output of the PR Inspector runtime. It is not an authoritative caller input.

The only active assembly flow is:

```text
ReviewRequest
→ ReviewEvidenceSource.collect()
→ ReviewFacts
+ ReviewAssessment
+ ProtocolContext
→ assemble_review_package()
→ CanonicalReviewPackage
→ project_decision()
→ build_review_artifacts()
→ bundle validation and atomic publication
→ VerifiedReviewCompletion
```

The implementation uses ordinary frozen dataclasses and deterministic pure functions. It does not use signatures, HMAC, keys, capability tokens, or hostile-process defenses.

## Field authority

Every canonical package field is assigned exactly one authority class through `pr_inspector.verified_review.FIELD_AUTHORITY`:

- **A — machine-collected fact:** repository/PR identity, Base, Head, merge base, changed files, checks, evidence, timestamps, and available capabilities.
- **B — reviewer assessment:** findings, rationale, affected surfaces, owner-facing explanation, limitations, and suggested actions.
- **C — deterministic derived value:** coverage, check projection, intent fit, reconciliation, technical status, reason codes, recommendation, approval requirement, and next action.
- **D — verified protocol/static metadata:** schema version, protocol version, inspection profile, Inspector identity, and static policy metadata.

No field is caller-authoritative by omission. `ReviewRequest.execution_options` rejects factual and decision fields. `ReviewAssessment` rejects unknown properties and cannot carry status, risk, recommendation, reason codes, completion state, Base, Head, CI, or evidence truth.

## Evidence catalog

`EvidenceRecord` is a deterministic correctness index. Each ID is derived from canonical record content. Every record must match the review repository, PR, and Head. Conflicting duplicate IDs, missing finding references, cross-repository references, cross-PR references, and cross-Head references fail with a bounded diagnostic.

`CODE_SUPPORTED` requires collected CODE/DIFF evidence. `REPRODUCED` requires failing collected CI/EXECUTION evidence. `HUMAN_JUDGMENT` and `HYPOTHESIS` remain attributed reviewer assessments and do not become machine facts.

## Decision and publication authority

`pr_inspector.decision_projection.project_decision` remains the sole decision authority. The assembler seeds only schema-required decision fields, invokes the canonical projection, and writes the projection result back into the package before validation.

The same canonical package bytes are used for projection, rendering, hashing, staging, validation, and publication. Live Head is checked before staging, immediately before publication, and after publication. Head drift or any assembly/render/validation/publication failure produces no new official bundle and preserves a previously valid bundle.

## Legacy and preview

The v1.12 public `complete_review` boundary accepts only `ReviewRequest`, `ReviewAssessment`, and `ReviewEvidenceSource`. Raw paths, mappings, JSON bytes, and prebuilt package objects return `PRI-PACKAGE-AUTHORITY-001` and cannot publish or mint completion.

`render_unverified_preview` remains a non-authoritative `DECLARATION` with `official_completion=false`.
