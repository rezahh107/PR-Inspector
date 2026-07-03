# Review Pipeline

## State machine

```text
INSPECTOR_LOAD
  → TARGET_INTAKE
  → TARGET_ACCESS_CHECK
  → SHA_PIN
  → CAPABILITY_DECLARATION
  → FUNNEL_REVIEW
  → EVIDENCE_REVIEW
  → BREAK_ATTEMPT
  → DECISION
  → OWNER_CARD
  → TECHNICAL_HANDOFF
  → CONSISTENCY_CHECK
  → COMPLETE
```

A failed required transition enters `BLOCKED`; do not skip forward.

## 1. Inspector load

Complete `BOOTSTRAP.md`. Record inspector version and commit SHA when available.

## 2. Target intake

Require exactly:

- target repository URL or `owner/name`;
- PR number or URL.

Do not request unrelated background unless it becomes a named unverified requirement during review.

## 3. Target access check

Confirm that the repository, PR metadata, and diff are readable. If not, return a short Persian blocked message and do not fabricate a review.

## 4. SHA pin

Capture base SHA, reviewed head SHA, and merge-base when available before substantive analysis.

If head SHA changes during review, stop, mark validity `STALE`, produce the white invalid Owner Card, and do not reuse earlier conclusions.

## 5. Capability declaration

Declare capabilities and execution mode required by the contract.

## 6. Funnel review

### 6.1 Understand

Read PR metadata, changed filenames, diff or patches, changed tests, configuration, dependencies, schemas, migrations, deletions, and exposed interfaces.

State previous, intended, and implemented behavior.

### 6.2 Classify risk

Apply contract sensitivity criteria before deciding review depth.

### 6.3 Map impact radius

Starting from changed symbols and files, follow imports, dependencies, callers, interfaces, implementations, schemas, tests, configuration, data paths, error paths, permission paths, and state transitions.

Default depth is one or two direct relationship levels. Record every file read outside the diff and why.

### 6.4 Inspect evidence

Inspect checks available for the exact reviewed head SHA. Do not equate a named check with a passed check.

### 6.5 Try to break

Examine malformed, missing, stale, duplicate, oversized, and partial data; external failures; timeout and retry; concurrency; partial failure; backward compatibility; access boundaries; data exposure; resource limits; migrations; rollback; and production-only differences.

Every scenario must connect to changed behavior.

## 7. Decision

Apply `policies/DECISION_GATES.md`. Determine status, risk, approval, and validity separately.

## 8. Output

1. Emit Owner Decision Card first using its exact Persian template.
2. Emit Technical Handoff Package second using its exact English template.
3. Check that both have the same status, risk, approval, validity, blocking consequence, and next action.

## 9. Completion

Do not append a long explanation of the pipeline. End after both deliverables.

## Blocked messages

### Inspector load failure

```text
❌ PR Inspector بارگذاری نشد.
دلیل: [مورد مشخص]
هیچ بررسی‌ای آغاز نشده است.
```

### Target access failure

```text
❌ دسترسی به ریپو یا PR هدف ممکن نیست.
دلیل: [مورد مشخص]
هیچ نتیجه‌ای دربارهٔ PR صادر نشد.
```
