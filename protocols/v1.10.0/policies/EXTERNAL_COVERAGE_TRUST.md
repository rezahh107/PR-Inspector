# External Coverage Trust Gate Policy

Version: `v1.10.0`

This policy defines the active security-boundary invariants for PRF-013 external Coverage trust bootstrap. The gate is bootstrap-only: it may emit exact-head identity evidence and a no-proof attestation, but it must not authorize proof credit or trusted ingestion.

## Required invariants

1. OIDC authority must match the GitHub Actions issuer and expected audience, and the authenticated caller repository/workflow must match either the approved target workflow or the approved issuer-side independent workflow mode.
2. The GitHub REST API pull-request payload must agree with event or explicit independent-policy identity for repository, repository ID, PR number, base SHA, and current head SHA.
3. `run_id` and `run_attempt` from OIDC claims and the workflow environment must be positive and equal.
4. The reusable issuer identity must come from `job_workflow_sha`, use the expected workflow path, and be treated as immutable implementation identity.
5. Target workflow validation must parse YAML structurally with duplicate-key rejection. Comments, malformed YAML, anchors, scalar/list roots, non-mapping jobs, non-mapping steps, and wrong-step bindings cannot satisfy the gate.
6. The target caller must use the exact reusable-workflow pin and must not provide caller-selected repository, PR, base, head, or issuer identity inputs.
7. Workflow and validation-job permissions must be exactly `contents: read`; the external reusable job must be exactly `contents: read`, `pull-requests: read`, and `id-token: write`.
8. Security-relevant `uses` entries must be pinned to full 40-character commit SHAs; checkout must use the approved immutable `actions/checkout` SHA.
9. All checkouts that validate target code must set `persist-credentials: false` and must use the externally verified exact-head ref.
10. The validation job is an exact allowlisted two-step topology: one immutable exact-head checkout, followed immediately by one `bash` validation command step. No workflow/job/step execution-context drift (`env`, `defaults`, `container`, `services`, `working-directory`, checkout shell/env overrides, `PATH`, `NODE_OPTIONS`, `GITHUB_ENV`, `BASH_ENV`, or equivalent injection), arbitrary pre-validation run steps, asynchronous execution, or failure suppression is allowed.
11. The validation command step must receive exactly the live `COVERAGE_REPOSITORY`, `COVERAGE_PR_NUMBER`, `COVERAGE_BASE_SHA`, and `COVERAGE_HEAD_SHA` values from external trust outputs on that same step, then reset to the verified head, clean untracked files, verify HEAD and clean status, install dependencies with `npm ci`, and run `npm run validate:coverage` in that same fail-propagating boundary.
12. Attestation is blocked if the checked-out target worktree is dirty or contains untracked files.
13. Malformed, unreadable, invalid-UTF-8, or partial `planning/coverage/**/*.json` trees block attestation.
14. Proof credit and trusted ingestion remain unauthorized during bootstrap; emitted attestations must keep `proof_credit_authorized=false`.
15. One-off PR #43 manual verification must not be part of the initial issuer release unless it can pin an already canonical, GitHub-resolvable issuer commit.
16. Successful integration requires fresh exact-head GitHub Actions evidence bound to the resulting PR head and the same resolvable issuer SHA. Local tests alone do not satisfy integration evidence.

## Release order

This v1.10.0 candidate follows the standalone path: it is limited to the external Coverage bootstrap boundary and does not claim that `personal_ai_operated_strong_governance_minimum_security` or any stronger governance profile is active. Stronger governance/profile work remains separate and unmerged unless introduced by a later independently reviewed release.
