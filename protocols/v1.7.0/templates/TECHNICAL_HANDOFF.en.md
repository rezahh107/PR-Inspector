# Technical Handoff Template

The renderer produces these sections from `review-package.json`:

1. Review Identity
2. Decision Header
3. Capability Manifest
4. Scope and Coverage
5. Change Summary
6. Intent Fit Evidence
7. Evidence Records
8. Merge-Blocking Findings
9. Non-Blocking Findings
10. External Review Suggestions Considered
11. Repair Handoff for Implementer Model
12. Files Reviewed Outside the Diff
13. Unverified Areas
14. Required Actions Before Merge
15. Out-of-Scope Observations
16. Owner-Card Consistency Map
17. Validation Metadata
18. Final Technical Decision

The External Review Suggestions section is rendered from `external_review_intake` when present; otherwise it renders as `None.`.

The Repair Handoff section is rendered from `repair_handoff` and accepted `external_review_intake.suggestions` only. Rejected, duplicate, deferred, insufficient-evidence, and out-of-scope external suggestions are never rendered as repair instructions. The rendered handoff is byte-compared with deterministic output during validation.
