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
| `pr_inspector.official_review.complete_review` | official high-level package API | Performs live identity reads, validation, staging, atomic publication, pre-commit rollback, publication commit, and bounded obsolete-backup cleanup. |
| `pr_inspector.official_review.verify_completed_review` | official existing-bundle verifier | Requires a verifier-created live head source, captures exact artifact bytes, validates that snapshot, and reads GitHub before and after bundle validation. |
| `official_owner_result`, `official_technical_handoff`, `official_next_action_prompt` | official output accessors | Accept only `VerifiedReviewCompletion`; recheck the live head, fully validate captured artifact bytes, and return only those verified bytes. |
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
→ complete staged-directory validation
→ fresh prepublication head recheck
→ atomic directory publication
→ post-publication captured-byte bundle validation
→ fresh final head recheck
→ publication commit point
→ bounded obsolete-backup cleanup
→ verifier-created completion receipt
→ accessor-time live-head recheck
→ full validation of a captured byte snapshot
→ return only captured verified bytes
```

A changed head before publication prevents publication. A changed head or failed endpoint after publication but before the commit point restores the prior directory. Partial payloads, non-canonical identity, network failure, invalid artifacts, or any other failed pre-commit gate return `IncompleteReview` with diagnostics only.

## Publication commit and cleanup invariant

The new official bundle becomes committed only after all four conditions succeed:

1. staged bundle validation;
2. atomic publication;
3. post-publication bundle validation;
4. final live GitHub-head verification.

Before that point, recovery is quarantine-first: the failed published directory is atomically renamed to a unique quarantine path, the previous backup is restored, and quarantine cleanup occurs only after restoration succeeds. If quarantine rename fails, the manifest is removed first so leftover files cannot remain an authoritative bundle; explicit deletion is then attempted and verified.

After the commit point, the prior backup is obsolete cleanup material. Recursive deletion may partially mutate it before raising. Therefore cleanup failure must never pass that backup to rollback. The new official bundle remains intact and authoritative; `PRI-COMPLETE-009` is retained in `VerifiedReviewCompletion.cleanup_diagnostics`, and any partial backup residue remains available for bounded diagnosis.

## Verified-byte accessor invariant

Bundle verification captures the exact bytes and relevant path types for every official artifact before validation. It validates a temporary snapshot constructed from those bytes with the complete existing pipeline: package schema and semantics, deterministic projection, rendered-byte equality, prompt routing, manifest structure, and final-byte hashes.

The verified `_Bundle` carries those immutable bytes. Official accessors perform the live-head recheck and full snapshot verification, compare the resulting identities and hashes to the completion receipt, and then parse or decode `bundle.artifact_bytes`. They never reopen the source artifact after verification, eliminating the validation-to-read TOCTOU window.

## Completion and output claims

`VerifiedReviewCompletion` binds the repository, PR, reviewed head, canonical package hash, package file hash, projection hash, manifest hash, all official artifact hashes, and a canonical GitHub PR-payload receipt hash. It may also carry explicit non-authoritative cleanup diagnostics after successful publication.

The opaque markers prevent accidental use of booleans, dictionaries, or low-level renderer results as completion. They are not cryptographic signatures or hostile same-process security boundaries.

## External integration obligation

An external ChatGPT/project/connector integration that wants to present an **official PR Inspector result** must:

1. invoke the supported official CLI or package boundary;
2. require a successful process result and verifier-created completion;
3. display owner/technical/prompt content only through official accessors or from the validated published bundle;
4. never synthesize status, next action, or prompt-ready wording directly;
5. preserve failure output as incomplete/blocked rather than converting it into Green/Yellow/Red prose;
6. surface `cleanup_diagnostics` without treating cleanup residue as publication rollback.

The repository cannot enforce these rules against unrelated free-form chat output. That remaining obligation belongs to the external orchestration layer.

## TOCTOU limitation

GitHub head identity is exact at each observed API receipt. No client can eliminate the final network-to-display race entirely. The implementation narrows it through initial, prepublication, post-publication, and accessor-time reads and fails closed on every observed drift. Artifact content has the stronger invariant: bytes returned by an accessor are exactly the bytes captured and fully validated by that accessor invocation.
