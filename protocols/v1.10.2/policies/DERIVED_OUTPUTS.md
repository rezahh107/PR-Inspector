# Derived Output Policy

## Boundary

The derived layer runs only after the canonical package passes schema and semantic validation. It receives one canonical decision projection and translates it; it does not decide again.

## Projection

`DECISION_PROJECTION.json` is deterministic and schema-validated. It records technical reason codes, owner readiness, next-action kind, recipient, code authority, prompt requirement, prompt kind, review validity, and reviewed head SHA. Every reason is registered in `DECISION_REASON_REGISTRY.yaml`.

## Authoritative action text

The Technical Handoff renders one finite English action text keyed only by `DECISION_PROJECTION.json#/next_action/kind`.

`decision.next_required_action` remains in `review-package.json` solely for legacy package compatibility. It is non-authoritative, is not rendered as an instruction, is never labeled exact or canonical, and cannot override projection-derived status, recipient, modification authority, or action text.

## Artifact routing

Always generate Owner Decision Card, Technical Handoff, Owner Result, projection, and manifest. Generate `NEXT_ACTION_PROMPT.en.md` only when `next_action.prompt_required` is true.

- `merge_now`: no prompt.
- `owner_confirmation`: no model prompt.
- `human_technical_review`: human technical handoff.
- `specialist_review`: security/domain specialist handoff.
- `repair`: bounded implementer prompt.
- `verify`: non-modifying reviewer prompt.
- `repair_and_verify`: bounded repair plus separate evidence obligations.
- `rerun_review`: fresh-review prompt with historical findings only.

## Verify

The verification artifact identifies exact unresolved reason codes and subjects. It authorizes inspection, safe validation, and evidence collection only. It prohibits repository changes, patching, committing, refactoring, and behavior changes. If repair becomes necessary, the recipient records that fact and stops for a fresh canonical decision.

## Human boundary

Human and specialist handoffs explicitly state that model output cannot satisfy or claim the required approval. PR Inspector performs no approval or merge.

## Trust boundary

Target and package free text is JSON-serialized as untrusted data after the fixed trust-boundary section. It cannot create prompt sections or override protocol instructions.

A schema-valid lifecycle event remains untrusted. Inspector identity, review success, protocol identity, and artifact hashes become actionable only after the provenance verifier consumes authoritative GitHub repository/commit responses and validates the actual review artifact directory.

## Artifact byte integrity

Non-manifest files are written first. The manifest hashes bytes reread from disk. Validation independently checks actual file bytes, paths, prompt routing, projection equality, canonical package hash, supplied package-file hash, BOM, newline, and encoding behavior.

## CI identity

Exact-head claims require a structured identity record where `tested_ref_type` is `pull_request_head`, `synthetic_merge` is false, and `tested_sha == reviewed_head_sha`. Merge refs remain synthetic evidence even when trees happen to match.

## Mandatory re-review

Repair output remains `implemented_pending_rereview`. It does not close findings.

The sequence gate consumes schema-v2 structured lifecycle events plus a separate mapping of opaque `VerifiedReviewEvidence` capabilities. The event declares protocol version and hashes for `review-package.json`, `DECISION_PROJECTION.json`, and `artifact-manifest.json`, but declarations alone never unlock acceptance.

`verify_review_directory` validates deterministic review artifacts, recomputes hashes, confirms target/PR/head/protocol/inspector identity, and binds the result to a verified GitHub repository/commit response. `validate_rereview_sequence` then compares every declared field with that verified evidence.

Missing evidence, forged inspector repository or commit, missing artifacts, mismatched hashes, wrong PR/head, stale validity, replay, or a non-Green/non-mergeable canonical projection blocks the corresponding acceptance or merge event.

The operational adapter requires live GitHub API evidence. Without that external evidence source, the gate fails closed. No cryptographic-signature, OS-harness, downstream, or production enforcement is claimed.


## Governance-derived output

Governance evidence is validated independently from `DECISION_PROJECTION.json`. The technical projection cannot claim branch protection, required reviews, required checks, bypass resistance, or merge authorization. When settings are unverified, the lifecycle validator reports: `merge readiness appears satisfied, but repository-level enforcement is unverified`.


## Atomic owner-facing access

The active machine-readable owner-delivery contract is `policies/OWNER_DELIVERY_CONTRACT.json`. The implementation validates it against `schemas/owner-delivery-contract.schema.json` and derives the canonical accessor names, artifact names, prompt heading, composition separator, compact-access behavior, and CLI stream contract from it.

All owner-facing bytes come from one fully reverified in-memory artifact snapshot. Prompt-required compact access fails closed with `CompletionError`; it is never enforced through a warning. A no-prompt delivery is byte-for-text identical to the two-line Owner Result. The CLI must finish delivery verification before writing stdout, so any failure leaves stdout empty.
