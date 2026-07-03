# Technical Handoff Package

## 1. Review Identity

```yaml
inspector_repository: rezahh107/PR-Inspector
inspector_commit_sha: 3333333333333333333333333333333333333333
protocol_version: v1.4.0
target_repository: example/project
pr_number: 42
base_branch: main
base_sha: 2222222222222222222222222222222222222222
head_branch: feature
reviewed_head_sha: 1111111111111111111111111111111111111111
merge_base_sha: 2222222222222222222222222222222222222222
review_started: 2026-07-03T10:00:00Z
review_completed: 2026-07-03T10:10:00Z
review_validity: CURRENT
execution_mode: CI_EVIDENCE_ONLY
review_mode: FULL
```

> This review is valid only for the reviewed head SHA above.

## 2. Decision Header

```yaml
technical_status: GREEN_TECHNICALLY_READY
risk_classification: LOW
approval_requirement: NO_ADDITIONAL_TECHNICAL_APPROVAL
blocking_findings_count: 0
next_required_action: Merge after normal owner confirmation.
```

Sensitive domains: none

## 3. Capability Manifest

- `ci_status_logs`: `AVAILABLE`
- `credential_access`: `UNAVAILABLE`
- `dependency_security_metadata`: `AVAILABLE`
- `git_github`: `AVAILABLE`
- `network`: `AVAILABLE`
- `pr_metadata_diff`: `AVAILABLE`
- `production`: `UNAVAILABLE`
- `repository_read`: `AVAILABLE`
- `shell_sandbox`: `AVAILABLE_BUT_NOT_USED`
- `test_execution`: `AVAILABLE_BUT_NOT_USED`

## 4. Scope and Coverage

```yaml
total_changed_files: 2
total_changed_lines: 40
coverage_complete: true
scope_limit_reason: null
```

- **files_fully_reviewed:** src/a.py, tests/test_a.py
- **files_partially_reviewed:** none
- **files_not_reviewed:** none
- **files_reviewed_outside_diff:** src/caller.py
- **high_risk_areas_reviewed:** none
- **high_risk_areas_not_reviewed:** none
- **excluded_generated_or_vendor_files:** none

## 5. Change Summary

- **Previous behavior:** The old parser accepted one format.
- **Intended behavior:** Accept the new format without breaking the old one.
- **Actual implementation:** Parser and tests support both formats.
- **Mismatch:** none

## 6. Evidence Records

### EVD-001

- Type: `CI`
- Source: GitHub Actions / test
- Head SHA: `1111111111111111111111111111111111111111`
- Result: `PASS`
- Excerpt: 24 passed
- Reference: ci://run/1
- SHA-256: none
- Redactions: none
- Limitations: none

## 7. Merge-Blocking Findings

None.

## 8. Non-Blocking Findings

None.

## 9. Files Reviewed Outside the Diff

- src/caller.py

## 10. Unverified Areas

None.

## 11. Required Actions Before Merge

None.

## 12. Out-of-Scope Observations

None.

## 13. Owner-Card Consistency Map

| Technical field | Owner-facing value |
|---|---|
| Status / validity | 🟢 سبز — از نظر فنی آماده است |
| Next owner action | ادغام می‌تواند پس از تأیید لازم انجام شود. |
| Specialist required | no |

## 14. Validation Metadata

- Canonical package SHA-256: `afc77ef04aea87617915d1ceecdfda7873836ee6f757005e92fc75cb9cf70b17`
- Canonicalization: sorted-key compact UTF-8 JSON with LF terminator, version 1
- Schema: JSON Schema Draft 2020-12

## 15. Final Technical Decision

- Status: `GREEN_TECHNICALLY_READY`
- Risk: `LOW`
- Approval: `NO_ADDITIONAL_TECHNICAL_APPROVAL`
- Validity: `CURRENT`
- Exact next action: Merge after normal owner confirmation.
