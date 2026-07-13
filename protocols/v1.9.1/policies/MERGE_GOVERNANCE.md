# Merge Governance and Authorization

## Status vocabulary

- `implementation_complete`: bounded implementation work is finished; no claim about review or merge protection.
- `technical_green`: the canonical technical projection is `GREEN_TECHNICALLY_READY`.
- `GREEN_MERGE_RECOMMENDED`: current exact-head technical evidence and the active minimum enforcement path support a bounded recommendation.
- `repository_settings_enforced`: authoritative GitHub settings evidence proves required repository-hosted gates independently block merge.
- `merge_authorized`: all active technical, lifecycle, approval, CI, specialist, and repository-hosted requirements for this stronger claim are satisfied.
- `merged`: GitHub authoritatively reports that the pull request was merged.

None of these states implies a later state.

## Personal minimum-security profile

The default profile is:

```text
personal_ai_operated_strong_governance_minimum_security
```

A dedicated GitHub App, private key, exact numeric `app_id` Check Runs, branch protection, repository rulesets, merge queue, CODEOWNERS approval, and repository-hosted exact-source enforcement are `optional_hardening` unless a documented trigger activates them.

Their absence alone does not block technical review or `GREEN_MERGE_RECOMMENDED`.

## AIGOV-MERGE-001

Minimum enforcement is:

```text
sequence_ci_enforced
OR
repository-hosted enforcement
```

The preferred default is `sequence_ci_enforced`. Repository-hosted enforcement is optional hardening under the personal profile.

## Enforcement ladder extension

`repository_settings_enforced` is a project-specific extension meaning that an active GitHub ruleset, branch protection, required pull-request review, required status check, merge queue, CODEOWNERS review requirement, or equivalent repository-hosted rule independently prevents merge while the condition is unsatisfied. Ordinary CI is not repository-settings enforcement.

The complete classification ladder is:

`prose_only`, `schema_backed`, `validator_backed`, `fixture_tested`, `advisory_ci_observed`, `ci_enforced`, `sequence_ci_enforced`, `runtime_monitor_enforced`, `os_harness_enforced`, `downstream_contract_enforced`, `repository_settings_enforced`.

## Authoritative evidence

Only verifier-created opaque governance evidence sourced from fresh HTTPS responses from the official GitHub API may unlock `repository_settings_enforced` or `merge_authorized`. A caller-authored normalized record or canonical-looking URL list is comparison input at most and cannot mint a capability.

Required repository-hosted checks are identities, not names: each configured context MUST be paired with the expected GitHub App ID and matched to a successful exact-head check run from that same App. This requirement applies only when proving the stronger repository-hosted claim; it is not an independent prerequisite for the default bounded recommendation.

A valid current-head approval is an `APPROVED` review by a non-bot reviewer who is not the PR author and whose commit ID equals the exact target head. Such approval is required only when the active protocol or an external requirement activates it.

Specialist review records reviewer identity separately from qualification evidence. A boolean or reviewer label is not qualification evidence.

## Activation triggers

Repository-hosted controls become required when:

- the target repository explicitly requires them;
- a security-profile trigger is active;
- an external legal, contractual, organizational, or production obligation applies;
- the target claims repository-hosted enforcement is active;
- the decision claims `repository_settings_enforced` or `merge_authorized`.

Missing required enforcement remains blocking for the stronger result.

## Bypass and self-validation

Bypass actors MUST be derived from fetched protection and active-ruleset payloads when repository-hosted enforcement is being proved. Unknown or non-empty bypass capability prevents that stronger claim. A workflow changed by the same PR may provide advisory CI evidence, but it cannot by itself prove an independent protected boundary.

## Failure language

When code-side readiness is satisfied but a stronger settings claim lacks evidence, emit exactly:

`merge readiness appears satisfied, but repository-level enforcement is unverified`

Never emit `merge is protected from bypass` without authoritative settings and bypass evidence.
