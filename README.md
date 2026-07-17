# PR Inspector

PR Inspector is a versioned, evidence-based pull-request review protocol for non-technical project owners, technical reviewers, and downstream AI agents.

## Start here

Ask the reviewing model to read [`BOOTSTRAP.md`](BOOTSTRAP.md). The bootstrap verifies the active immutable protocol and requests a target repository plus pull-request number.

## Authoritative output model

Every completed review validates one canonical package and computes one canonical structured decision projection. Technical status, approval state, governance enforcement, and merge authorization are separate states.

Repository code validates artifacts, provenance, identities, lifecycle sequences, and prompt semantic completeness. Human or specialist reviewers supply judgment. PR Inspector records evidence but never approves or merges.

Repository authority is determined from live `main`. A post-package integration must consume `VerifiedReviewCompletion` and return owner-facing output through `official_owner_delivery`; manual concatenation and reconstructed Candidate output are unsupported. Profile-selection commands remain a separate verified artifact.

## Current v1.11.1 status

The `v1.11.1` corrected-activation patch preserves dual-profile `minimal` / `strict` inspection while eliminating the independent Candidate output stack retained during the v1.11.0 rollout. Candidate compatibility is limited to pre-package intake, target, Head, review-surface, provenance, and evidence helpers. Official projection, artifact generation, verification, and owner delivery are the sole output authority.

Prompt-required output is both byte-canonical and semantically validated. Generic prompts, the historical PR #22 placeholder, manual composition, Candidate composition, and embedded profile-selection commands fail closed. `OWNER_PROFILE_COMMANDS.fa.txt` remains separate.

Repository-settings enforcement remains `insufficient_evidence`. Successful CI does not prove branch protection, Rulesets, required reviews, CODEOWNERS enforcement, stale-approval dismissal, bypass restrictions, or merge-queue enforcement.

## Validation

```bash
python -m pip install ".[dev]"
python scripts/validate_repository_v2.py
python -m pytest -q tests/test_behavioral_rule_coverage.py
python -m pytest -q tests/test_repository_closure.py
python -m pytest -q tests/test_v1_11_1_output_authority.py
python -m pytest
```

## Active protocol

`v1.11.1`

`CURRENT_VERSION` selects [`protocols/v1.11.1/`](protocols/v1.11.1/), protected by [`release-locks/v1.11.1.sha256`](release-locks/v1.11.1.sha256). The immutable `v1.11.0` snapshot and earlier releases remain addressable historical releases.

## License

Apache License 2.0. See [`LICENSE`](LICENSE).
