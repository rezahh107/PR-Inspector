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
10. Repair Handoff for Implementer Model
11. Files Reviewed Outside the Diff
12. Unverified Areas
13. Required Actions Before Merge
14. Out-of-Scope Observations
15. Owner-Card Consistency Map
16. Validation Metadata
17. Final Technical Decision

The Repair Handoff section is rendered from `repair_handoff` when present; otherwise it renders as `None.`. The rendered handoff is byte-compared with deterministic output during validation.
