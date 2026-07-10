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

Only verifier-created opaque governance evidence sourced from the official GitHub API may unlock `merge_authorized`. The verifier recomputes the status; a caller cannot self-assert `verified_enforced`.

A valid current-head approval is an `APPROVED` review by a non-bot reviewer who is not the PR author and whose commit ID equals the exact target head. `COMMENTED`, `CHANGES_REQUESTED`, author comments, bot comments, generated files, and approvals on older heads do not count.

Specialist review records reviewer identity separately from qualification evidence. When qualification is not authoritatively verified, the honest state is `human_governance_required`, not automated specialist enforcement.

## Bypass and self-validation

Bypass actors MUST be recorded. Unknown or non-empty bypass capability prevents a claim of fully verified protection. A workflow changed by the same PR may provide advisory CI evidence, but it cannot by itself prove an independent protected boundary. Required-check configuration and its expected GitHub App source must be observed separately.

## Failure language

When code-side readiness is satisfied but settings evidence is missing or partial, emit exactly:

`merge readiness appears satisfied, but repository-level enforcement is unverified`

Never emit `merge is protected from bypass` without authoritative settings and bypass evidence.
