# PR Inspector

PR Inspector is a versioned, evidence-based pull-request review protocol for non-technical project owners, technical reviewers, and downstream AI agents.

## Start here

Ask the reviewing model to read [`BOOTSTRAP.md`](BOOTSTRAP.md). The bootstrap verifies the selected immutable protocol and requests a target repository plus pull-request number.

## Authoritative output model

Every completed review validates one canonical package and computes one canonical structured decision projection. Technical status, bounded merge recommendation, repository-settings enforcement, merge authorization, and merge completion are separate states.

Repository code validates artifacts, provenance, identities, lifecycle sequences, and the active security profile. PR Inspector records evidence but never approves or merges.

## Current v1.9.1 candidate status

Repository authority is determined from live `main`. This branch selects the `v1.9.1` candidate for validation. Live `main` at base SHA `65e6b1b46c3e8da7c782c666cd3562947f2b7923` remains authoritative for activation and currently carries `v1.9.0`. The candidate is not independently reviewed, merge-authorized, or merged.

`v1.9.1` adds the default `personal_ai_operated_strong_governance_minimum_security` profile. Valid sequence enforcement can support `GREEN_MERGE_RECOMMENDED` without a dedicated GitHub App, branch protection, rulesets, merge queue, CODEOWNERS approval, or repository-hosted exact-source enforcement. Those controls remain mandatory when a stronger trigger or claim activates them.

Repository-settings enforcement is not claimed. Successful CI does not prove branch protection, Rulesets, required reviews, CODEOWNERS enforcement, stale-approval dismissal, bypass restrictions, merge authorization, or merge completion.

## Governance truth

A documented requirement is not machine evidence, and machine evidence is not GitHub-enforced protection. A bounded Green recommendation does not prove `repository_settings_enforced`, `merge_authorized`, or `merged`.

PR #12 remains historical provenance for the merged v1.8.0 release; historical comments are not rewritten as approvals.

## Validation

```bash
python -m pip install ".[dev]"
python scripts/validate_repository_v2.py
python -m pytest -q tests/test_behavioral_rule_coverage.py
python -m pytest -q tests/test_governance_enforcement.py
python -m pytest -q tests/test_personal_minimum_security_profile.py
python -m pytest -q tests/test_repository_closure.py
python -m pytest -q tests/test_canonical_output_enforcement.py
python -m pytest -q tests/test_canonical_output_atomicity.py
python -m pytest
```

Pull-request CI checks out the triggering PR head, asserts the tested SHA, records object identity, and distinguishes exact-head evidence from synthetic merge evidence.

## Active protocol

`v1.9.1`

`CURRENT_VERSION` selects the candidate snapshot under [`protocols/v1.9.1/`](protocols/v1.9.1/) in this checkout, protected by [`release-locks/v1.9.1.sha256`](release-locks/v1.9.1.sha256). Activation is not inferred from a branch: live `main`, a merged commit, and post-merge verification remain authoritative. Earlier snapshots, including v1.8.0 and v1.9.0, remain immutable historical releases.

## License

Apache License 2.0. See [`LICENSE`](LICENSE).
