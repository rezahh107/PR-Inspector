# Changelog

## 1.11.1

- Completed the v1.11 corrected activation by making official projection, derived outputs, artifact validation, `VerifiedReviewCompletion`, and `official_owner_delivery` the sole post-package authority.
- Preserved Candidate-era `minimal` / `strict` intake, verified target/live-Head handling, Head-drift orchestration, review-surface pagination, annotation provenance, bot reconciliation, and sealed evidence helpers behind an explicit allowlist.
- Converted legacy Candidate output entrypoints into deterministic fail-closed migration tombstones and removed them from supported exports.
- Added a structured canonical action contract and independent semantic prompt validation for identity, action kind, recipient, modification authority, reasons, findings, evidence, required actions/tests, mandatory re-review, prohibited actions, and profile-command separation.
- Added historical PR #22 → PR #26 → PR #28 regressions and closure checks preventing future parallel output authority or PR #27-style broad re-exports.
- Added the immutable `v1.11.1` protocol snapshot and release lock while preserving `v1.11.0` byte-for-byte.
- External ChatGPT/project/connector execution remains a separate acceptance boundary and is not claimed by repository tests alone.

## 1.10.2

- Added the immutable v1.10.2 protocol snapshot and active release lock for atomic owner delivery.
- Defined and schema-validated the canonical owner-delivery accessor, exact prompt composition, CLI stdout/stderr behavior, and failure semantics.
- Made prompt-required use of the compact owner accessor fail closed with `CompletionError`; warning filters cannot bypass the invariant.
- Added dedicated Behavioral Rule Coverage, mutation fixtures, adversarial accessor tests, CLI partial-output tests, and exact-head CI coverage.
- Preserved the released v1.10.1 protocol snapshot and release lock byte-for-byte.

## Earlier releases

The immutable history for earlier versions remains available in Git history and versioned protocol snapshots.
