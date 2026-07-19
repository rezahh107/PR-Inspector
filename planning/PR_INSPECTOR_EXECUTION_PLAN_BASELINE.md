# PR Inspector Governed Execution Baseline

Status: repository-required planning infrastructure.

This document is outside the active protocol `load_order`, defines no active PR-review rule, does not activate AIGOV, and does not alter runtime review behavior. If planning material conflicts with the active protocol, the active protocol wins.

## Conceptual model

```text
Program
└── Initiative
    └── Task
        └── Work Package
            └── Execution Attempt
```

A Program is a durable governed body of work. An Initiative is a bounded strategic objective. A Task is an evidence-closeable outcome. A Work Package is a PR-sized implementation unit with exact scope. An Execution Attempt is non-authoritative metadata and is never equivalent to a Task.

## Lifecycle distinctions

```text
documented != implemented
registered != authorized
authorized != dependency-eligible
dependency-eligible != started
started != implemented
implemented != exact-head validated
exact-head validated != merged
merged != post-merge verified
post-merge verified != Task complete
PR opened != material progress
CI green != Merge enforcement
```

Program states: `proposed`, `active`, `complete`, `superseded`, `cancelled`.

Task states: `registered`, `authorized`, `blocked`, `in_progress`, `implemented`, `complete`, `superseded`, `cancelled`.

Work Package states: `planned`, `dependency_blocked`, `ready`, `implementing`, `implemented_pending_exact_head_validation`, `exact_head_validated`, `merged`, `post_merge_verified`, `closed`.

## Authority and evidence

1. JSON Schemas define structural validity.
2. `pr_inspector/planning_governance.py` defines semantic, dependency, lifecycle, evidence, path, and cross-file rules.
3. `planning/tasks/task-registry.v1.json` is the canonical Program, Initiative, Task, and Work Package registry.
4. The current Scope defines the exact allowed implementation boundary.
5. Impact records state material effects and remaining obligations.
6. This baseline preserves durable meanings and historical boundaries.
7. `PR_INSPECTOR_EXECUTION_PLAN.md` preserves the active durable task graph.
8. `NEXT_WORK.md` is a synchronized dashboard, not an independent authority.
9. Prompts, PR descriptions, chat history, branches, commits, and Execution Attempts are not planning sources of truth.

Task completion requires evidence predicates. Prose, prompts, branches, commits, PR creation, and ordinary CI are insufficient by themselves. Exact-head validation, owner-only Merge, exact-main validation, and bounded post-Merge reconciliation are separate lifecycle steps. Repository-settings Merge enforcement is not inferred from green CI.

## Scope revision

The Scope revision is `sha256:` plus SHA-256 of UTF-8 JSON serialized with sorted keys, compact separators, and `ensure_ascii=false`, after removing the top-level `scope_revision` field. The final hash therefore never recursively includes itself.

Committed paths are normalized POSIX repository-relative paths. Absolute paths, backslashes, empty segments, `.`, `..`, NUL bytes, duplicates, and repository escape are invalid. A pattern ending in `/**` matches only the named segment subtree; `foo/**` never matches `foobar`.

## Legacy work

```yaml
legacy_work:
  automatically_imported: false
  completion_credit: false
  authority: none
  inspection_when_relevant: allowed
  reuse_requires:
    - live_repository_revalidation
    - new_scope
    - current_task_authorization
    - current_validation
    - fresh_review
```

Closed PR #33 remains closed and unmerged. Its branch is not a continuation point, its implementation is not imported, and its findings are neither resolved nor dismissed by this Foundation.
