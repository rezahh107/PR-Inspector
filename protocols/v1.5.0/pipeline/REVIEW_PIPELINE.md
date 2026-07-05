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
→ INTENT_FIT_GATE
→ BREAK_ATTEMPT
→ CANONICAL_PACKAGE
→ SCHEMA_VALIDATION
→ SEMANTIC_VALIDATION
→ DETERMINISTIC_RENDER
→ ARTIFACT_CONSISTENCY
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
9. Build `intent_fit` by connecting the stated intent to concrete implementation evidence, or mark it `not_assessable` when intent is missing or insufficient.
10. Examine realistic malformed, missing, stale, duplicate, oversized, partial, timeout, retry, concurrency, compatibility, migration, rollback, and resource-limit scenarios when connected to changed behavior.
11. Create `review-package.json` before human-readable outputs.
12. Run schema and semantic validation without suppressing diagnostics.
13. Render both Markdown artifacts deterministically.
14. Re-read the current PR head SHA. A change makes the review `STALE`; rebuild the package and outputs.
15. Emit Owner Card first, Technical Handoff second, and provide the JSON package as the canonical artifact.

Do not append unsupported assurances or unrelated commentary.
