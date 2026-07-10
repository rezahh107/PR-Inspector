# Derived Output Policy

## Boundary

The derived layer runs only after the canonical package has passed schema and semantic validation and after the existing canonical Owner Decision Card and Technical Handoff have been deterministically rendered.

`review-package.json` remains the sole source of truth. The derived layer is not a decision engine and does not modify the package.

## Artifacts

Always generate:

- `OWNER_RESULT.fa.txt`
- `artifact-manifest.json`

Generate `NEXT_ACTION_PROMPT.en.md` exactly once for Yellow or Red. It is forbidden for Green.

## Structural action mode

Derive action mode without free-text matching:

- `rerun_review`: `review_validity` is not `CURRENT`.
- `repair`: confirmed repair carriers or supported blocking defects exist without separate unresolved verification gaps.
- `verify`: unresolved execution/evidence/coverage only, with no confirmed repair carrier.
- `repair_and_verify`: both confirmed repair work and unresolved verification gaps exist.

A stale or unknown package must not authorize code repair. Its prompt may only require a fresh PR Inspector review and may carry old findings as non-authorizing historical context.

## Prompt section order

The prompt contains these fixed sections in order:

1. `[ROLE AND AUTHORITY]`
2. `[AUTHORITATIVE REVIEW IDENTITY]`
3. `[TRUST BOUNDARY]`
4. `[MISSION]`
5. `[FINDINGS AND EVIDENCE]`
6. `[INVARIANT EXTRACTION]`
7. `[ADJACENT IMPACT AUDIT]`
8. `[TECHNICAL DECISION AUTHORITY]`
9. `[SCOPE CONTROL]`
10. `[ADVERSARIAL SELF-AUDIT]`
11. `[VALIDATION AND EVIDENCE]`
12. `[IMPLEMENTER OUTPUT]`
13. `[MANDATORY PR INSPECTOR RE-REVIEW]`

Package-derived free text is serialized as untrusted data. Accepted external suggestions may appear only through validated `external_review_intake`. Repair guidance resolves through existing finding IDs, rule IDs, and `repair_handoff`.

The self-audit is explicitly not independent. Finding status remains `implemented_pending_rereview` until the repaired exact head is reviewed again by PR Inspector.

## Artifact manifest

The manifest records:

- canonical review package path and canonical SHA-256;
- Owner Decision Card path and SHA-256;
- Technical Handoff path and SHA-256;
- simple Owner Result path and SHA-256;
- whether the action prompt was generated, its path and SHA-256, and the structural action mode.

For Green, prompt generation, path, hash, and action mode are null/not applicable.
