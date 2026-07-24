# Review Pipeline — v1.12.0

1. Validate caller intent as `ReviewRequest` and bounded reviewer analysis as `ReviewAssessment`.
2. Construct `OfficialReviewRuntime` internally; callers cannot inject sources, facts, live Head, or `ProtocolContext`.
3. Verify the active Inspector repository, release lock, canonical hashes, repository identity, and exact Inspector commit.
4. Resolve and verify the target checkout against the live PR repository and exact Head.
5. Collect all check-run pages and all pages of issue comments, review submissions, and inline review comments.
6. Represent every missing configured required check as required `UNKNOWN`; reject incomplete enumeration.
7. Resolve every finding evidence reference and every external-review disposition. Unclassified collected sources produce `INCOMPLETE` reconciliation and block technical Green.
8. Assemble one canonical package with `assemble_review_package`.
9. Derive the decision only through `pr_inspector.decision_projection.project_decision`.
10. Validate the assembled package.
11. Re-fetch live Head, stage canonical bytes and derived artifacts, validate hashes and manifest, atomically publish, and re-fetch Head.
12. Mint `VerifiedReviewCompletion` only after the full publication succeeds and expose owner output only through official completion accessors.
13. Require fresh independent PR Inspector re-review after repair.

Raw package paths, JSON bytes, mappings, prebuilt package objects, caller-provided sources or facts, protocol contexts, verified-Head objects, and preview output are outside the public pipeline.
