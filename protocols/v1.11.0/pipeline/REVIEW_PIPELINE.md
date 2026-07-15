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
→ PUBLICATION_COMMIT_POINT
→ OBSOLETE_BACKUP_CLEANUP
→ VERIFIED_BYTE_ACCESS
→ ATOMIC_OWNER_DELIVERY
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
13. The official completion boundary fetches the canonical GitHub PR payload, binds repository/PR/head identity, and re-reads the live head immediately before publication.
14. Publish only a fully validated sibling staging directory, revalidate the published bundle, and re-read the live GitHub head again. Any observed drift or endpoint failure before the commit point rolls back publication and returns an incomplete result.
15. Establish the publication commit point only after staged validation, atomic publication, post-publication bundle validation, and the final live-head verification all succeed.
16. Treat the prior backup as obsolete cleanup material after the commit point. Cleanup failure or partial cleanup is recorded explicitly and may retain residue, but must not roll back, replace, quarantine, or invalidate the new verified official bundle.
17. For every official accessor, recheck the live head and perform full bundle verification against an in-memory snapshot of the exact artifact bytes. Return, decode, or parse only those captured verified bytes; never reopen an artifact after verification.
18. Compose owner-facing output according to the locked owner-delivery contract. Prompt-required compact access raises `CompletionError`; the canonical CLI writes no stdout until the complete atomic delivery is verified.

No renderer, validator, or prompt generator may maintain a competing status/action registry.

## Post-review governance sequence

After technical artifacts are complete, any `merge_authorized` event additionally requires a freshly fetched, payload-derived GitHub governance bundle: repository and PR identity, branch protection and active rulesets, context-plus-GitHub-App required checks, exact-head check runs, current reviews and author identity, applicable authoritative specialist team membership, and known bypass actors. The sequence CLI must pass the resulting sealed evidence capability into `validate_rereview_sequence`. Missing, partial, stale, replayed, or producer-ambiguous evidence fails closed. This is separate from the review projection and never permits PR Inspector to approve or merge.

## Security-profile step

Before technical status and action routing, assess the structured `security_profile` carrier with any exact-bound verifier-created governance evidence. Add its registered reasons to the single canonical projection; do not accept helper or manually injected output.
