# Maintenance Guide

## Behavioral release

1. Copy the previous snapshot into `protocols/vNEXT/`.
2. Document every behavioral change and preserve unchanged rules.
3. Update contract, policies, pipeline, templates, schema, and semantic rules together.
4. Add positive and negative fixtures for every changed rule.
5. Update `CURRENT_VERSION`, `protocol-manifest.yaml`, `CHANGELOG.md`, and package metadata.
6. Generate `release-locks/vNEXT.sha256` only after the snapshot is final.
7. Run repository validation and the complete test suite.
8. Open a pull request and require successful CI before merge.

## Implementation-only change

An implementation fix may retain the protocol version only when it does not alter accepted or rejected review behavior. Add a regression test and do not modify locked protocol files.

## Governed planning maintenance

Planning infrastructure is repository-required and outside the active protocol `load_order`. It defines no active review rule, does not activate AIGOV, and does not alter runtime review behavior. The active protocol remains authoritative if any planning document conflicts with it.

Before executing a registered task, read `planning/NEXT_WORK.md`, `planning/PR_INSPECTOR_EXECUTION_PLAN.md`, `planning/tasks/task-registry.v1.json`, the current Scope, and relevant Impact records. Update machine state and bounded Markdown snapshots together. Chat history and PR descriptions are not planning sources of truth.

A Work Package implementation is not complete merely because a branch, commit, PR, or green ordinary CI exists. Exact-head validation, owner-only Merge, exact-main validation, and bounded post-Merge lifecycle reconciliation require separate evidence.

## Release gates

- all active canonical files are version-scoped;
- the release lock covers every active canonical file;
- the schema is valid under JSON Schema Draft 2020-12;
- the golden package is accepted;
- negative mutations are rejected with stable diagnostic IDs;
- deterministic rendering and artifact comparison pass;
- CI passes on all supported Python versions;
- documentation and changelog match actual implementation.

## Commands

```bash
python -m pip install ".[dev]"
python scripts/validate_repository_v2.py
python scripts/validate_planning_governance.py --check-static
python -m pytest -q tests/test_planning_governance.py
python -m pytest
python scripts/validate_review_v2.py fixtures/golden-green --package-only
```

## Prohibited maintenance actions

- silently rewriting a released protocol snapshot;
- changing a release lock to hide an unauthorized snapshot edit;
- weakening a gate without a new protocol version and tests;
- representing synthetic fixtures as real reviews;
- claiming CI, fixture, or runtime validation that was not executed.
