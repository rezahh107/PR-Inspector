# Technical Handoff Template

The deterministic renderer produces these sections from `review-package.json` plus the single canonical `DECISION_PROJECTION.json`:

1. Review Identity
2. Decision Header, including projected owner action, recipient, and prompt kind
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
16. Owner-Card Consistency Map from the canonical projection
17. Validation Metadata
18. Final Technical Decision and canonical next-action kind

This artifact preserves the complete technical package and evidence boundary. `NEXT_ACTION_PROMPT.en.md` is a recipient-specific operational projection and does not replace this handoff. Neither artifact may maintain an independent decision mapping.
