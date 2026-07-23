# Review Pipeline — v1.12.0

1. Validate caller intent as `ReviewRequest`.
2. Validate bounded reviewer analysis as `ReviewAssessment`.
3. Collect exact repository, PR, Base, Head, merge base, changed files, checks, comments, and evidence through one `ReviewEvidenceSource`.
4. Validate the evidence catalog and resolve every finding reference.
5. Load active protocol metadata as `ProtocolContext`.
6. Assemble one canonical package with `assemble_review_package`.
7. Derive the decision only through `pr_inspector.decision_projection.project_decision`.
8. Validate the assembled package.
9. Re-fetch live Head, stage canonical bytes and derived artifacts, validate hashes and manifest, atomically publish, and re-fetch Head.
10. Mint `VerifiedReviewCompletion` only after the full publication succeeds.
11. Expose owner output only through official completion accessors.
12. Require fresh independent PR Inspector re-review after repair.

Raw package paths, JSON bytes, mappings, prebuilt package objects, and preview output are outside this pipeline.
