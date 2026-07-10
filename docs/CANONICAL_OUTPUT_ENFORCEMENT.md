# Canonical Artifact and Official-Output Boundary

Status: candidate implementation boundary for `v1.9.0` on the stacked repair branch. The released default-branch authority remains whatever live `main`, `CURRENT_VERSION`, the manifest, and release lock select.

## Boundary classification

```yaml
repository_execution_bug: true
repository_protocol_gap: true
supported_cli_bypass: true
external_interface_noncompliance: true
project_integration_gap: true
mixed_boundary_defect: true
```

The repository defect was real but bounded: the supported render CLI validated only the package, wrote directly into the destination, and printed success without independently validating the completed directory or re-reading the live GitHub PR head. Separately, arbitrary ChatGPT or connector orchestration can ignore repository code and type authoritative-looking prose directly; Python code in this repository cannot prevent that external behavior.

## Supported-path map

| path | classification | boundary |
|---|---|---|
| `scripts/render_review_v2.py` | official supported entry point | Must construct a live GitHub PR-head source and call `complete_review`; no direct writer import. |
| `pr_inspector.official_review.complete_review` | official high-level package API | Performs live identity reads, validation, staging, atomic publication, rollback, and final head recheck. |
| `pr_inspector.official_review.verify_completed_review` | official existing-bundle verifier | Requires a verifier-created live head source and reads GitHub before and after bundle validation. |
| `official_owner_result`, `official_technical_handoff`, `official_next_action_prompt` | official output accessors | Accept only `VerifiedReviewCompletion`; revalidate bytes and live head before returning content. |
| `decision_projection.project_decision` | internal composition API | Canonical decision derivation only; not completion evidence. |
| `derived_outputs.build_review_artifacts` | internal composition API | In-memory deterministic construction; not completion evidence. |
| `derived_outputs.write_review_artifacts` | internal composition API | Low-level writer; never an official completion signal. |
| `derived_outputs.render_next_action_prompt` | internal composition API | Deterministic renderer; direct text is not an official prompt-ready claim. |
| `scripts/validate_review_v2.py` | official validation-only entry point | Read-only directory validation; does not announce a completed live review. |
| fixtures/tests | test-only helper | Never live review evidence. |
| templates/policies | documentation-only path | Never generated completion evidence. |
| arbitrary chat/model prose | external interface outside repository control | Must be governed by project integration; repository code cannot technically block it. |

## Official completion sequence

```text
canonical package bytes
→ fresh canonical GitHub PR API payload
→ package schema + semantic validation
→ live repository/PR/head identity match
→ canonical projection
→ deterministic artifacts in sibling staging
→ manifest from final staged bytes
→ complete directory validation
→ fresh prepublication head recheck
→ atomic directory publication
→ post-publication bundle validation
→ fresh final head recheck
→ verifier-created completion receipt
→ live-rechecking official accessors
```

A changed head before publication prevents publication. A changed head or failed endpoint after publication restores the prior directory. Partial payloads, non-canonical identity, network failure, invalid artifacts, or any other failed gate return `IncompleteReview` with diagnostics only.

## Rollback invariant

After a post-publication failure, PR Inspector atomically renames the failed directory to a unique quarantine path before restoring the previous backup. Quarantine cleanup occurs only after restoration succeeds. If quarantine rename fails, the manifest is removed first so leftover files cannot remain an authoritative bundle; explicit deletion is then attempted and verified.

Backup restore, deletion, quarantine, and cleanup failures are returned as diagnostics. The implementation does not use `ignore_errors=True` as rollback evidence and does not claim restoration unless the backup rename established the official path. Failed restoration retains backup/quarantine evidence and leaves the official path absent or non-authoritative.

## Completion and output claims

`VerifiedReviewCompletion` binds the repository, PR, reviewed head, canonical package hash, package file hash, projection hash, manifest hash, all official artifact hashes, and a canonical GitHub PR-payload receipt hash. Official accessors re-read both the bundle and live PR head.

The opaque markers prevent accidental use of booleans, dictionaries, or low-level renderer results as completion. They are not cryptographic signatures or hostile same-process security boundaries.

## External integration obligation

An external ChatGPT/project/connector integration that wants to present an **official PR Inspector result** must:

1. invoke the supported official CLI or package boundary;
2. require a successful process result and verifier-created completion;
3. display owner/technical/prompt content only through official accessors or from the validated published bundle;
4. never synthesize status, next action, or prompt-ready wording directly;
5. preserve failure output as incomplete/blocked rather than converting it into Green/Yellow/Red prose.

The repository cannot enforce these rules against unrelated free-form chat output. That remaining obligation belongs to the external orchestration layer.

## TOCTOU limitation

GitHub head identity is exact at each observed API receipt. No client can eliminate the final network-to-display race entirely. The implementation narrows it through initial, prepublication, post-publication, and accessor-time reads and fails closed on every observed drift.
