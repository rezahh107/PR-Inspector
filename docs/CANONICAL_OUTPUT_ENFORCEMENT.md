# Canonical Artifact and Output Enforcement

Status: implementation boundary for the active `v1.9.0` protocol.

## Confirmed execution paths

| path | classification | current role | enforcement decision |
|---|---|---|---|
| `scripts/render_review_v2.py` | confirmed bypass before this repair | Supported package-to-artifact CLI validated the package and wrote artifacts, but did not prove final bundle validation or atomic completion. | Route exclusively through `complete_review`; emit only bounded incomplete output on failure. |
| `pr_inspector.derived_outputs.write_review_artifacts` | public low-level API by design | Deterministic file writer used by tests and composition. It does not validate the package or represent completed official output. | Retain as a primitive; never return or imply official completion. |
| `pr_inspector.derived_outputs.build_review_artifacts` | public low-level API by design | In-memory deterministic artifact construction used by validators and tests. | Retain as a primitive; dictionaries are not completion proofs. |
| `pr_inspector.derived_outputs.render_next_action_prompt` | potential misuse | Renders one projection-bound prompt for composition and tests. | Official prompt access requires `VerifiedReviewCompletion`; direct rendering cannot support a prompt-ready claim. |
| `pr_inspector.render.render_owner` | potential misuse | Low-level deterministic Owner Decision Card renderer. | Official owner output requires verified completion. |
| `pr_inspector.render.render_handoff` | potential misuse | Low-level deterministic Technical Handoff renderer. | Official technical output requires verified completion. |
| `pr_inspector.decision_projection.project_decision` | public low-level API by design | Sole canonical deterministic decision derivation. | Remains the only projection implementation, but a projection object alone is not a completed review. |
| `scripts/validate_review_v2.py` | validation-only supported path | Independently validates a review directory. | Remains read-only validation; it does not expose an official result. |
| fixtures and tests | test-only path | Exercise deterministic rendering and validation. | Must not be represented as live completed reviews. |
| protocol templates and examples | documentation-only path | Describe output form and legacy examples. | Never treated as generated artifacts or completion evidence. |

## Decision and artifact field sources

- Schema validation: `pr_inspector.validation_v2.validate_package`.
- Semantic validation: `pr_inspector.semantic_v2.validate_semantics`, invoked by `validate_package`.
- Canonical projection: `pr_inspector.decision_projection.project_decision`.
- Projection invariant and schema/equality checks: `validate_projection_invariants` and `validation_v2._projection_diagnostics`.
- Conditional prompt creation: `derived_outputs.build_review_artifacts` calls `render_next_action_prompt` only when `projection.next_action.prompt_required` is true.
- Artifact completeness and deterministic byte checks: `validation_v2.validate_directory`.
- Manifest structure, canonical package hash, final-file hashes, and prompt routing: `validation_v2._manifest_diagnostics`.
- Owner and technical views: low-level renderers consume the canonical projection; official exposure is performed only by accessors on `VerifiedReviewCompletion`.

## Root cause

The repository already had strong deterministic package, projection, artifact, and manifest validators, but no single supported completion boundary connected them. The render CLI validated only the input package, wrote directly to the destination, and printed success without independently validating the final directory. Therefore a caller could confuse a low-level rendering result or partial output directory with an official completed review.

## Selected architecture

`pr_inspector.official_review.complete_review` is the sole supported official package-to-output boundary.

It requires:

1. canonical package bytes;
2. caller-observed target repository, PR number, and reviewed head SHA;
3. schema and semantic validation;
4. deterministic projection and artifact rendering into a fresh sibling staging directory;
5. complete artifact, conditional prompt, manifest, byte, and hash validation;
6. verifier-created `VerifiedReviewCompletion`;
7. atomic directory replacement;
8. post-publication revalidation and fail-closed rollback.

Official owner output, technical output, and next-action prompt are exposed only through a valid completion capability. Each accessor revalidates the directory and rejects mutation after completion.

## Rollback invariant

A post-publication failure never treats recursive deletion as proof of recovery. Recovery executes in this order:

1. atomically rename the failed published directory to a unique sibling quarantine path;
2. restore the previous backup to the official path;
3. clean quarantine only after restoration succeeds, or after a no-backup rollback has made the official path non-authoritative;
4. retain backup and quarantine paths plus explicit diagnostics when restoration or cleanup fails.

If quarantine rename fails, the implementation removes or invalidates `artifact-manifest.json` before attempting explicit deletion. A failed deletion may leave files behind, but the official path must not remain a schema- and manifest-valid authoritative bundle. Restoration, deletion, quarantine, and cleanup errors are returned as `IncompleteReview` diagnostics and are never described as successful rollback.

## Failure boundary

Any read, parse, schema, semantic, identity, projection, render, artifact, manifest, publication, rollback, cleanup, or post-publication validation failure returns `IncompleteReview`. That object carries diagnostics and bounded failure messages only. It deliberately has no technical status, approval requirement, owner readiness, action, or prompt fields.

Partial staging directories are non-authoritative. Existing completed output is not replaced unless the new staged bundle validates. After post-publication failure, the official path contains either the restored prior output or no authoritative bundle.

## Security claim boundary

The opaque marker prevents accidental completion claims through booleans, dictionaries, or low-level renderer returns. It is not a hostile same-process security boundary, cryptographic signature, OS harness, or downstream enforcement mechanism.
