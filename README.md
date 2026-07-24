# PR Inspector

PR Inspector is a versioned, evidence-based pull-request review protocol for non-technical project owners, technical reviewers, and downstream AI agents.

## Start here

Ask the reviewing model to read [`BOOTSTRAP.md`](BOOTSTRAP.md). The bootstrap verifies the active immutable protocol and requests a target repository plus pull-request number.

## Authoritative output model

Every completed review validates one canonical package and computes one canonical structured decision projection. Technical status, approval state, governance enforcement, and merge authorization are separate states.

Repository code validates artifacts, provenance, identities, lifecycle sequences, and prompt semantic completeness. Human or specialist reviewers supply judgment. PR Inspector records evidence but never approves or merges.

Repository authority is determined from live `main`. A post-package integration must consume `VerifiedReviewCompletion` and return owner-facing output through `official_owner_delivery`; manual concatenation and reconstructed Candidate output are unsupported. Profile-selection commands remain a separate verified artifact.

## Active v1.12.0 authority model

The active runtime accepts caller intent as `ReviewRequest` and bounded reviewer analysis as `ReviewAssessment`. One `ReviewEvidenceSource` collects exact repository/PR identity, Base, Head, merge base, changed files, checks, review surfaces, timestamps, and evidence. `assemble_review_package` deterministically creates one `CanonicalReviewPackage`; `review-package.json` is an official output rather than an authoritative input.

The `minimal` profile requires correctness evidence such as exact-Head required checks but no cryptographic, key-management, GitHub-App, or repository-settings framework. The official runtime constructs its evidence source and verified protocol context internally, paginates all check and review surfaces, represents missing configured checks as `UNKNOWN`, and blocks Green until every collected external review source is reconciled. The `strict` profile may additionally require governance evidence. Preview rendering remains a non-authoritative `DECLARATION`. Raw paths, mappings, arbitrary JSON, and prebuilt package objects cannot enter public completion.

The immutable `v1.11.1` snapshot remains historical and retains only its original assurance. It is not retroactively reclassified.

Repository-settings enforcement remains `insufficient_evidence`. Successful CI does not prove branch protection, Rulesets, required reviews, CODEOWNERS enforcement, stale-approval dismissal, bypass restrictions, or merge-queue enforcement.

## Governed planning

Repository-required planning infrastructure lives under `planning/` with structural schemas under `schemas/planning/` and semantic enforcement in `pr_inspector/planning_governance.py`. It is outside the active protocol `load_order`, defines no active PR-review rule, does not activate AIGOV, and does not alter runtime review behavior. The active protocol remains authoritative.

Before registered implementation work, read the current dashboard, durable execution plan, canonical registry, current Scope, and relevant Impact. Prompts, PR descriptions, chat history, branches, commits, and Execution Attempts are not planning sources of truth. Exact-head validation, owner-only Merge, exact-main validation, and post-Merge reconciliation are separate evidence gates.

## Validation

```bash
python -m pip install ".[dev]"
python scripts/validate_repository_v2.py
python scripts/validate_planning_governance.py --check-static
python -m pytest -q tests/test_planning_governance.py
python -m pytest -q tests/test_behavioral_rule_coverage.py
python -m pytest -q tests/test_v1_12_verified_review_authority.py
python -m pytest -q tests/test_repository_closure.py
python -m pytest -q tests/test_v1_11_1_output_authority.py
python -m pytest
```

## Active protocol

`v1.12.0`

`CURRENT_VERSION` selects [`protocols/v1.12.0/`](protocols/v1.12.0/), protected by [`release-locks/v1.12.0.sha256`](release-locks/v1.12.0.sha256). The immutable `v1.11.1` snapshot and earlier releases remain addressable historical releases.

## License

Apache License 2.0. See [`LICENSE`](LICENSE).
