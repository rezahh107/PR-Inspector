---
status: planning_pilot
active_protocol_rule: false
blocking: false
---

# Scope Claim Audit Pilot

Protocol context: `v1.5.0`

This document is planning-only. It is not part of the active protocol `load_order`, does not define an active review rule, does not add schema fields, and does not change validator, release-lock, CI, or blocking behavior.

If this document conflicts with `BOOTSTRAP.md`, `protocol-manifest.yaml`, the active `PR_REVIEW_CONTRACT.md`, active policies, active schemas, deterministic validators, or release locks, the active protocol wins.

## 1. Purpose

Scope Claim Audit investigates whether a PR claim, title, body, handoff, or implementation summary under-reports the real diff scope, especially on contract-sensitive surfaces.

The target question is:

```text
Does a PR claim or description under-report the real diff scope — especially on contract-sensitive surfaces — making the change look smaller, simpler, or lower-risk than the actual diff evidence supports?
```

This matters in LLM-driven engineering workflows because a model may implement a change and then summarize its own work as smaller, safer, or more complete than the diff proves.

Boundary rules:

- Large PRs are not automatically bad.
- Scope expansion is not automatically bad.
- The problem is under-reported or misleading scope.
- This pilot is advisory only.
- This pilot does not replace CI, tests, schema validation, release-lock checks, evidence rules, or PR-Inspector intent-fit.

## 2. Relationship to v1.5.0 Intent Fit

Intent Fit asks:

```text
Did the implementation evidence support the stated intended behavior?
```

Scope Claim Audit asks:

```text
Did the PR claim accurately represent the actual scope and risk surface of the diff?
```

Scope Claim Audit is a candidate future complement to `PRR-INTENT-001`, not a replacement. Intent fit can be satisfied while scope is still under-described. Conversely, a PR can honestly declare a broad scope and still fail intent fit.

## 3. Human-Authored vs Model-Generated Claims

The pilot separates two failure paths.

### Human-authored description path

Problem:

```text
A human author may unintentionally describe the PR as smaller, safer, or narrower than it is.
```

Expected fixture type:

```text
Human-written title/body under-reports a real contract-sensitive diff.
```

### Model-generated description path

Problem:

```text
An LLM may systematically summarize its own work as smaller, cleaner, or more complete than the diff supports.
```

Expected fixture type:

```text
Model-generated handoff, PR body, repair report, or implementation summary under-reports schema, validator, lock, CI, or contract-surface changes.
```

PR-Inspector especially cares about the model-generated path because the repository is part of an LLM-driven engineering workflow. Model-generated summaries should be treated as claim evidence, not as proof of actual diff scope.

## 4. Evidence Layers

The pilot separates deterministic diff facts from interpretive claim classification.

### Layer A — deterministic diff facts

Layer A is machine-checkable.

Possible sources:

- `GitHub.list_pr_changed_filenames`
- `GitHub.fetch_pr_patch`
- `GitHub.fetch_pr_file_patch`
- `GitHub.get_pr_diff`
- `GitHub.compare_commits`
- GitHub PR files REST API
- GitHub connector changed-file list
- local `git diff --stat`, if available
- workflow-generated JSON evidence

Layer A should capture:

```yaml
files_changed:
additions:
deletions:
changed_file_paths:
changed_file_statuses:
contract_surfaces_changed:
schema_files_changed:
validator_files_changed:
release_lock_files_changed:
workflow_files_changed:
test_fixture_files_changed:
package_metadata_changed:
docs_changed:
generated_output_changed:
```

Layer A must not require LLM interpretation. It can classify path patterns into candidate surface buckets, but it must not decide whether prose is misleading.

### Layer B — interpretive claim classification

Layer B is LLM-assisted and uncertain.

Possible sources:

- `GitHub.get_pr_info`
- `GitHub.fetch_pr`
- `GitHub.fetch_pr_comments`
- `GitHub.list_pull_request_reviews`
- PR title
- PR body
- implementation summary
- handoff document
- assistant-generated repair report
- commit messages if explicitly selected

Layer B should capture:

```yaml
claim_source:
claim_author_type: human_authored | model_generated | mixed | unknown
claim_excerpt:
inferred_claim_type:
classification_confidence:
classification_rationale:
uncertainty_reason:
```

Layer B uncertainty must never be converted into a hard mismatch claim. When claim evidence is weak, vague, unavailable, or ambiguous, the result should be `not_assessable` or a low-confidence advisory signal, not a blocking finding.

## 5. Minimum Semantic Children

Minimum semantic children are the smallest required fields that prevent a model from producing a shallow verdict without representing the actual concept being audited.

A field like this is insufficient:

```json
{ "scope_congruence": "mismatch" }
```

For this pilot, the minimum semantic children are planning candidates:

```yaml
claim_source:
claim_author_type:
claim_excerpt:
inferred_claim_type:
classification_confidence:
deterministic_diff_facts:
changed_sensitive_surfaces:
underreported_scope_signal:
signal_confidence:
uncertainty_reason:
why_it_matters:
recommended_action:
blocking: false
```

These are not active schema fields. They are candidate semantic children for later fixture design, schema design, or advisory report design if the pilot produces useful signal.

## 6. Sensitive / Contract Surfaces

Candidate PR-Inspector sensitive surfaces are intentionally small and repository-specific:

```yaml
protocol:
  - "protocols/**"
schema:
  - "protocols/**/schemas/**"
  - "schemas/**"
validator:
  - "pr_inspector/**"
release_lock:
  - "release-locks/**"
manifest_version:
  - "CURRENT_VERSION"
  - "protocol-manifest.yaml"
package_metadata:
  - "pyproject.toml"
  - "pr_inspector/__init__.py"
tests_fixtures:
  - "tests/**"
  - "fixtures/**"
render_output:
  - "golden rendered artifacts or deterministic render snapshots, if present"
workflow:
  - ".github/workflows/**"
scripts:
  - "scripts/**"
docs:
  - "docs/**"
```

This list should not be hardcoded into a validator yet. If promoted later, it should become a versioned artifact. If promoted to active enforcement later, it should be covered by a release lock or equivalent version-control mechanism.

## 7. GitHub-Native Evidence and Reporting Channels

This section documents future implementation primitives only. None of this is implemented by this planning document.

Official GitHub documentation basis reviewed for this pilot:

- Pull request metadata and diff/patch media types: <https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#get-a-pull-request>
- Pull request changed files API: <https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#list-pull-requests-files>
- Compare commits API, including merge-base and file details: <https://docs.github.com/en/rest/commits/commits?apiVersion=2022-11-28#compare-two-commits>
- `pull_request` workflow event and activity types: <https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull_request>
- GitHub Actions `github.event` and `github.event_path`: <https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#github-context>
- `GITHUB_STEP_SUMMARY`: <https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands#adding-a-job-summary>
- Workflow artifacts: <https://docs.github.com/en/actions/tutorials/store-and-share-data>
- Workflow `permissions`: <https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#permissions>
- Workflow `concurrency` and `cancel-in-progress`: <https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#concurrency>
- Required status checks / protected branches: <https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches#require-status-checks-before-merging>

Future implementation candidates:

```yaml
claim_text_source:
  primary_tools:
    - GitHub.get_pr_info
    - GitHub.fetch_pr
  possible_fields:
    - title
    - body
    - draft
    - head_sha
    - base_sha

diff_fact_source:
  primary_tools:
    - GitHub.list_pr_changed_filenames
    - GitHub.fetch_pr_patch
    - GitHub.fetch_pr_file_patch
    - GitHub.get_pr_diff
    - GitHub.compare_commits

ci_evidence_source:
  primary_tools:
    - GitHub.fetch_commit_workflow_runs
    - GitHub.get_commit_combined_status
    - GitHub.fetch_workflow_run_jobs
    - GitHub.fetch_workflow_job_steps
    - GitHub.fetch_workflow_job_logs
    - GitHub.fetch_workflow_run_artifacts
    - GitHub.download_workflow_artifact

future_workflow_events:
  pull_request:
    types:
      - opened
      - edited
      - synchronize
      - reopened
      - ready_for_review

future_actions_primitives:
  event_payload:
    - github.event
    - github.event_path
  summary:
    - GITHUB_STEP_SUMMARY
  artifacts:
    - actions/upload-artifact
  safety:
    - permissions: read-only
    - avoid pull_request_target
    - no secrets required
    - concurrency with cancel-in-progress

future_reporting:
  advisory_summary:
    channel: GITHUB_STEP_SUMMARY
  raw_json:
    channel: workflow artifact
  committed_report:
    allowed: false_by_default

future_escalation:
  required_check:
    allowed: future_only_after_pilot_success
```

Repository and bootstrap evidence candidates:

```text
GitHub.get_repo
GitHub.fetch_file
GitHub.search
GitHub.search_branches
GitHub.fetch_commit
GitHub.compare_commits
```

PR metadata and claim-source evidence candidates:

```text
GitHub.get_pr_info
GitHub.fetch_pr
GitHub.fetch_pr_comments
GitHub.list_pull_request_reviews
GitHub.list_pull_request_review_threads
GitHub.get_users_recent_prs_in_repo
GitHub.search_prs
```

Diff and changed-file evidence candidates:

```text
GitHub.list_pr_changed_filenames
GitHub.fetch_pr_patch
GitHub.fetch_pr_file_patch
GitHub.get_pr_diff
GitHub.compare_commits
```

CI and workflow evidence candidates:

```text
GitHub.fetch_commit_workflow_runs
GitHub.get_commit_combined_status
GitHub.fetch_workflow_run_jobs
GitHub.fetch_workflow_job_steps
GitHub.fetch_workflow_job_logs
GitHub.fetch_workflow_run_artifacts
GitHub.download_workflow_artifact
```

Confirmed or expected GitHub Connector write tools, if explicitly authorized and supported by the active repository workflow:

```text
GitHub.create_branch
GitHub.create_file
GitHub.update_file
GitHub.create_pull_request
GitHub.update_pull_request
```

GitHub API primitives such as commit statuses or check runs may be useful for future implementation only if the connector or workflow environment explicitly supports them. They are not required for this planning pilot and must not be treated as available connector tools without verification.

This pilot should avoid `pull_request_target` for any future workflow that reads or evaluates untrusted PR code. A future advisory workflow should prefer read-only permissions, no secrets, exact head SHA binding, stale-run cancellation, `GITHUB_STEP_SUMMARY` for human-readable advisory output, and workflow artifacts for raw JSON evidence.

## 8. Pilot Fixture Strategy

The pilot should prove useful signal with adversarial fixtures and calibrated real PR cases. It must not calibrate only on PRs already known to be bad, because that would create confirmation bias.

### Synthetic/adversarial fixtures

Minimum examples:

1. Description says `docs only`, but diff changes schema or validator.
2. Description says `small typo fix`, but diff changes package metadata or workflow.
3. Model-generated handoff says `baseline complete`, but diff includes placeholder lock hashes or incomplete verification.
4. Description correctly says schema, validator, tests, and release lock changed; expected result is no mismatch.
5. Ambiguous description such as `cleanup`; expected result is `not_assessable` unless claim evidence is strong.

### Real PR calibration cases

Require at least:

1. One positive/suspicious real PR with known contract-sensitive scope.
2. One true-negative real PR whose description appears complete and honest.
3. Optional ambiguous real PR.

Possible discovery tools:

```text
GitHub.get_users_recent_prs_in_repo
GitHub.search_prs
GitHub.get_pr_info
GitHub.fetch_pr
GitHub.list_pr_changed_filenames
GitHub.fetch_pr_patch
GitHub.get_pr_diff
GitHub.compare_commits
```

If PR #20 from `rezahh107/EV4-Project-Gate` is used, it should be labeled only as a positive/suspicious calibration subject, not sufficient proof of pilot value.

## 9. Result Categories

Advisory-only result values:

```yaml
scope_claim_result:
  - congruent
  - scope_expanded_but_declared
  - scope_underreported
  - mismatch
  - not_assessable
```

Meanings:

- `congruent`: the claim and deterministic diff facts appear aligned at the pilot's review depth.
- `scope_expanded_but_declared`: the diff touches broader or sensitive surfaces, but the PR claim clearly declares that scope.
- `scope_underreported`: the claim makes the PR sound materially smaller, narrower, safer, or less contract-sensitive than deterministic diff facts suggest.
- `mismatch`: a stronger advisory result requiring both deterministic sensitive-surface evidence and material claim under-reporting.
- `not_assessable`: claim evidence is missing, vague, contradictory, or too weak to classify safely.

`mismatch` requires both:

```text
1. deterministic diff facts showing a meaningful sensitive-surface change;
2. claim evidence that materially under-reports that change.
```

A large diff alone is not a mismatch. A vague claim alone is not a mismatch. Layer B uncertainty is not proof.

## 10. Success Metrics

Success should be measured by signal quality, not alert count.

```yaml
true_signal:
  description: "The audit identifies a materially under-reported scope that would improve review focus or PR description."

false_positive:
  description: "The audit flags a PR whose description was actually adequate or whose diff expansion was mechanical/noise."

actionability:
  description: "The recommendation tells the maintainer exactly what to clarify or review."

friction:
  description: "The audit does not create blocking noise or require heavy manual triage."

calibration_goal:
  description: "The pilot should demonstrate useful signal on both adversarial fixtures and real PR true-negative cases before promotion."
```

A good pilot should improve reviewer attention without creating a generic code-review checklist or a new merge barrier.

## 11. Non-Goals

The pilot does not:

- judge whether the implementation approach is architecturally best;
- replace CI;
- fail PRs;
- block merge;
- enforce schema;
- add a new active PR-Inspector protocol rule;
- treat large PRs as bad;
- treat scope expansion as bad;
- treat uncertainty as proof;
- require enterprise security tooling;
- require broad GitHub Actions hardening;
- claim validation, CI, or test results without direct evidence.

## 12. Promotion Criteria

Promotion to schema/validator candidate requires:

```yaml
required_before_promotion:
  - at least one useful adversarial signal
  - at least one real true-negative calibration case
  - low false-positive risk
  - clearly defined sensitive surfaces
  - stable minimum semantic children
  - actionable output format
  - explicit decision on advisory vs blocking
```

Promotion to active protocol rule requires:

```yaml
required_for_active_rule:
  - versioned protocol update
  - schema carrier
  - semantic validator rule
  - valid fixture
  - invalid fixture
  - CI validation
  - release lock update if required by repository protocol
  - documented migration path
```

Any active promotion must follow the repository's behavioral-release process. This planning document alone cannot promote or enforce the rule.

## 13. Suggested Future Output Shape

Illustrative only; not schema-approved:

```json
{
  "scope_claim_audit": {
    "claim_source": "pr_body",
    "claim_author_type": "model_generated",
    "claim_excerpt": "small docs cleanup",
    "inferred_claim_type": "docs_only",
    "classification_confidence": "medium",
    "deterministic_diff_facts": {
      "source_tools": [
        "GitHub.get_pr_info",
        "GitHub.list_pr_changed_filenames",
        "GitHub.fetch_pr_patch"
      ],
      "files_changed": 7,
      "changed_sensitive_surfaces": [
        "schema",
        "validator"
      ],
      "non_docs_files_changed": [
        "protocols/v1.5.0/schemas/review-package.schema.json",
        "pr_inspector/semantic.py"
      ]
    },
    "scope_claim_result": "scope_underreported",
    "signal_confidence": "medium",
    "uncertainty_reason": "Claim text is brief, but it explicitly says docs cleanup while non-doc contract files changed.",
    "why_it_matters": "Reviewer may under-review schema and validator effects.",
    "recommended_action": "Update PR description to explicitly mention schema and validator changes.",
    "blocking": false
  }
}
```

## Planning Boundary Check

This pilot design follows the repository's planning-only quality-boundary pattern:

- It stays outside the active protocol `load_order`.
- It does not define active review behavior.
- It separates prompt-level influence from system-level enforcement.
- It treats future schema, validator, fixture, CI, and release-lock work as separate promotion steps.
- It requires true-negative calibration before promotion.
- It keeps uncertainty explicit.
