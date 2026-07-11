# GitHub Governance Settings Plan

Status: code-side hardening implemented; repository settings not changed and not verified by this change.

## Current evidence boundary

The GitHub connector connection is verified for `rezahh107/PR-Inspector`, and the authenticated installation reports administrative repository access. The exposed connector actions provide repository metadata, files, pull requests, reviews, comments, commits, and CI evidence.

The currently exposed action set does not provide authoritative read endpoints for active GitHub Rulesets, branch protection, required pull-request reviews, required status-check configuration, stale-approval dismissal, bypass actors, or merge-queue requirements. Those settings therefore remain `insufficient_evidence` because their authoritative settings records were not exposed—not because GitHub was disconnected.

The repository contains a pull-request validation workflow and a CODEOWNERS entry (`* @rezahh107`), but repository files alone do not prove that GitHub requires pull requests, required checks, approvals, code-owner review, stale-approval dismissal, merge queue, or no-bypass enforcement. The historical PR #12 record showed successful CI and one `COMMENTED` bot review.

A schema-valid repository JSON file is not authoritative settings evidence. The governance verifier accepts only an opaque capability bound to canonical official GitHub API repository identity and fetched response receipts for settings, current-head reviews, and exact-head checks.

## Exact settings still required

1. Read and record the active Ruleset or branch-protection configuration for `main` through an authoritative settings-capable API or administrative interface.
2. Require pull requests for `main`.
3. Require the exact PR Inspector status checks and bind them to the expected GitHub App source.
4. Require at least one approving review from a reviewer other than the PR author.
5. Dismiss stale approvals when new commits are pushed and require approval of the most recent push.
6. Require code-owner review for `.github/workflows/**`, `BOOTSTRAP.md`, `CURRENT_VERSION`, `protocol-manifest.yaml`, `protocols/**`, `release-locks/**`, `pr_inspector/**`, and `scripts/**` using an independent team or reviewer group.
7. Disable or tightly enumerate bypass actors; apply protection to administrators where operationally acceptable.
8. Consider merge queue only if it solves concurrent-main drift for this repository.
9. Prevent a changed workflow from being the sole authority for approving itself; use protected required checks, reusable trusted workflow boundaries, or an independently controlled GitHub App/check.

No item above was applied because repository-settings changes require separate explicit authorization and an authoritative settings-capable interface.

## Official GitHub references

- https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets
- https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
- https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull_request_target
