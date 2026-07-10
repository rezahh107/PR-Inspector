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
→ CANONICAL_DECISION_PROJECTION
→ SEMANTIC_VALIDATION_AGAINST_PROJECTION
→ CANONICAL_ARTIFACT_RENDER
→ ACTION_ARTIFACT_ROUTING
→ WRITE_FINAL_ARTIFACT_BYTES
→ MANIFEST_FROM_FINAL_BYTES
→ ARTIFACT_AND_PROJECTION_VALIDATION
→ FINAL_SHA_RECHECK
→ COMPLETE
```

A failed required transition enters `BLOCKED` and does not emit a completed owner decision.

## Required sequence

1. Verify active version, load order, schemas, reason registry, Behavioral Rule Coverage matrix, and release lock.
2. Pin target repository, PR, base/head, and merge-base identity.
3. Declare real capabilities and execution mode.
4. Collect evidence, impact radius, external review intake, intent fit, and break attempts.
5. Build `review-package.json` and validate its schema.
6. Compute one canonical `DECISION_PROJECTION.json` from structured package fields.
7. Validate package technical status against that same projection.
8. Render Owner Decision Card, Technical Handoff, two-line Owner Result, and the recipient-specific action artifact from the projection.
9. Write final non-manifest bytes.
10. Re-read those bytes and generate `artifact-manifest.json`.
11. Independently validate projection schema/equality, prompt routing, exact bytes, and manifest hashes.
12. Record CI tested-object identity without rewriting merge SHA as head SHA.
13. Re-read the live PR head. A change makes the review stale and requires rebuilding all artifacts.
14. Expose the two-line result to the owner and technical artifacts separately.

No renderer, validator, or prompt generator may maintain a competing status/action registry.


## Post-review governance sequence

After technical artifacts are complete, any `merge_authorized` event additionally requires authoritative GitHub settings, current-head check, review, author-identity, stale-approval, specialist, and bypass evidence. This is separate from the review projection and never permits PR Inspector to approve or merge.
