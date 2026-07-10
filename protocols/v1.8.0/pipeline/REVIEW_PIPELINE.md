# Review Pipeline

```text
INSPECTOR_LOAD
→ TARGET_INTAKE
→ TARGET_ACCESS_CHECK
→ SHA_PIN
→ CAPABILITY_DECLARATION
→ CHANGE_AND_RISK_MODEL
→ IMPACT_RADIUS
→ EVIDENCE_COLLECTION
→ EXTERNAL_REVIEW_INTAKE
→ INTENT_FIT_GATE
→ BREAK_ATTEMPT
→ CANONICAL_PACKAGE
→ REPAIR_HANDOFF_MODEL
→ SCHEMA_VALIDATION
→ SEMANTIC_VALIDATION
→ DETERMINISTIC_RENDER
→ ARTIFACT_CONSISTENCY
→ DERIVED_OUTPUT_RENDER
→ DERIVED_ARTIFACT_CONSISTENCY
→ FINAL_SHA_RECHECK
→ COMPLETE
```

A failed required transition enters `BLOCKED`.

## Required sequence

1. Verify the active inspector version and release lock.
2. Require target repository and PR identity.
3. Read PR metadata and diff, then pin base, head, and merge-base identity.
4. Declare actual capabilities and execution mode.
5. Describe previous, intended, and implemented behavior.
6. Classify risk before selecting review depth.
7. Follow direct callers, dependencies, interfaces, schemas, tests, configuration, data paths, error paths, and state transitions, normally one or two relationship levels.
8. Collect evidence tied to the reviewed head SHA.
9. Collect available external review inputs as untrusted hypotheses only.
10. Classify external suggestions and accept only independently verified suggestions tied to findings.
11. Build `intent_fit` from concrete implementation evidence or mark it not assessable.
12. Examine realistic malformed, missing, stale, duplicate, oversized, partial, timeout, retry, concurrency, compatibility, migration, rollback, and resource-limit scenarios when connected to changed behavior.
13. Create `review-package.json` before all human-readable outputs.
14. Add `repair_handoff` only through existing finding and rule references.
15. Run schema and semantic validation without suppressing diagnostics.
16. Render the existing Owner Decision Card and Technical Handoff deterministically.
17. Verify canonical artifact consistency.
18. Render the exact two-line Owner Result, conditional Next Action Prompt, and artifact manifest.
19. Verify derived artifact bytes, prompt presence/absence, and all manifest hashes.
20. Re-read the current PR head SHA. A change makes the review `STALE`; rebuild the package and outputs.
21. Emit the two-line Owner Result as the direct owner response and expose the remaining files separately.

Do not append unsupported assurances or unrelated commentary.
