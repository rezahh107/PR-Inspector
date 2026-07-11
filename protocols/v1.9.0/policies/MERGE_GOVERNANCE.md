# Merge Governance and Authorization

## Status vocabulary

- `implementation_complete`: bounded implementation work is finished; no claim about review or merge protection.
- `technically_accepted`: a current exact-head PR Inspector review is technically Green.
- `approval_complete`: all required current-head human approvals are authoritatively observed.
- `governance_enforced`: authoritative GitHub settings evidence proves the required merge gates independently block merge.
- `merge_authorized`: technical acceptance, approval completion, required exact-head CI, specialist evidence when applicable, and governance enforcement are all satisfied.
- `merged`: GitHub authoritatively reports that the pull request was merged.

None of these states implies a later state.

## Enforcement ladder extension

`repository_settings_enforced` is a project-specific extension meaning that an active GitHub ruleset, branch protection, required pull-request review, required status check, merge queue, CODEOWNERS review requirement, or equivalent repository-hosted rule independently prevents merge while the condition is unsatisfied. Ordinary CI is not repository-settings enforcement.

The complete classification ladder is:

`prose_only`, `schema_backed`, `validator_backed`, `fixture_tested`, `advisory_ci_observed`, `ci_enforced`, `sequence_ci_enforced`, `runtime_monitor_enforced`, `os_harness_enforced`, `downstream_contract_enforced`, `repository_settings_enforced`.

## Authoritative evidence

Only verifier-created opaque governance evidence sourced from fresh HTTPS responses from the official GitHub API may unlock `merge_authorized`. The verifier derives the normalized record from the repository, pull-request, branch-protection, ruleset, review, check-run, and applicable team-membership payloads. A caller-authored normalized record or canonical-looking URL list is comparison input at most and cannot mint a capability. Response receipts older than the bounded freshness window, future-dated receipts, missing endpoints, partial payloads, and replay attempts fail closed.

Required checks are identities, not names: each configured context MUST be paired with the expected GitHub App ID and matched to a successful exact-head check run from that same App. A same-name check from another producer does not satisfy the gate.

A valid current-head approval is an `APPROVED` review by a non-bot reviewer who is not the PR author and whose commit ID equals the exact target head. `COMMENTED`, `CHANGES_REQUESTED`, author comments, bot comments, generated files, and approvals on older heads do not count.

Specialist review records reviewer identity separately from qualification evidence. A boolean or reviewer label is not qualification evidence. When specialist review is required, the verifier requires an active authoritative GitHub team-membership payload for a current valid reviewer; otherwise the honest state is `human_governance_required`.

## Bypass and self-validation

Bypass actors MUST be derived from the fetched protection and active-ruleset payloads. Unknown or non-empty bypass capability prevents a claim of fully verified protection. A workflow changed by the same PR may provide advisory CI evidence, but it cannot by itself prove an independent protected boundary. The operational sequence CLI MUST fetch and verify the governance payload bundle, bind the resulting evidence ID to the exact merge event, and pass the sealed capability to `validate_rereview_sequence`; a `merge_authorized` sequence without that verified input fails closed.

## Failure language

When code-side readiness is satisfied but settings evidence is missing or partial, emit exactly:

`merge readiness appears satisfied, but repository-level enforcement is unverified`

Never emit `merge is protected from bypass` without authoritative settings and bypass evidence.
