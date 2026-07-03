# Technical Handoff Package Template

## 1. Review Identity

```text
Inspector Repository:
Inspector Commit SHA:
Protocol Version:
Target Repository:
PR:
Base Branch:
Base SHA:
Head Branch:
Reviewed Head SHA:
Merge-Base SHA:
Review Started:
Review Completed:
Review Validity:
Execution Mode:
Review Mode:
```

> This review is valid only for the reviewed head SHA recorded above.

## 2. Decision Header

```yaml
technical_status:
risk_classification:
approval_requirement:
review_validity:
blocking_findings_count:
next_required_action:
```

## 3. Capability Manifest

For each contract capability, record `AVAILABLE`, `UNAVAILABLE`, `UNKNOWN`, or `AVAILABLE BUT NOT USED`.

## 4. Scope and Coverage

```yaml
total_changed_files:
total_changed_lines:
files_fully_reviewed:
files_partially_reviewed:
files_not_reviewed:
files_reviewed_outside_diff:
high_risk_areas_reviewed:
high_risk_areas_not_reviewed:
excluded_generated_or_vendor_files:
scope_limit_reason:
```

## 5. Change Summary

- Previous behavior:
- Intended behavior:
- Actual implementation:
- Mismatch:

## 6. Checks and Evidence Records

For each check:

```yaml
check_id:
check_name:
exact_command_or_ci_check:
working_directory:
execution_source:
reviewed_head_sha:
started_at:
completed_at:
tool_version:
exit_code_or_ci_conclusion:
relevant_output_excerpt:
full_log_reference:
log_hash:
redactions_applied:
limitations:
```

Separate executed, CI-inspected, unavailable, and mentioned-but-unverified checks.

## 7. Merge-Blocking Findings

For each:

```text
Finding ID:
Severity:
Evidence Label:
File and Location:
Symbol:
Relevant Code:
Issue:
Failure Scenario:
Recommended Fix:
Recommended Test:
Evidence Record Reference:
Applicable Rule IDs:
```

## 8. Non-Blocking Findings

Use the same structure.

## 9. Files Reviewed Outside the Diff

For each file, state relationship, reason, and result.

## 10. Unverified Areas

List missing context, inaccessible systems, unexecuted checks, dynamic behavior, remaining hypotheses, and Not Assessable areas.

## 11. Required Actions Before Merge

Ordered, concrete, verifiable checklist.

## 12. Out-of-Scope Observations

Useful unrelated observations only; they cannot change status.

## 13. Owner-Card Consistency Map

| Technical fact or material risk | Exact owner-facing sentence |
|---|---|

## 14. Final Technical Decision

Repeat status, risk, approval, validity, and exact next action.
