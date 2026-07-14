# Owner Output UX Policy

## Decision source

Both the existing Owner Decision Card and the direct Owner Result consume `DECISION_PROJECTION.json`. They do not independently map technical status, approval, findings, or validity.

## Two-line contract

`OWNER_RESULT.fa.txt` is UTF-8, contains exactly two LF-terminated visible Persian lines, exactly one status icon, no heading, link, SHA, path, rule ID, evidence detail, or third line. Text comes only from the finite owner-message registry keyed by `owner_readiness.message_key`.

## Merge-now

The Green technical-readiness message is permitted only for canonical `next_action.kind: merge_now`:

```text
🟢 وضعیت: از نظر فنی آماده
آمادگی فنی تأیید شده؛ حفاظت ادغام در GitHub جداگانه بررسی شود.
```

`merge_now` requires current validity, technical Green, `NO_ADDITIONAL_TECHNICAL_APPROVAL`, and no pending structured action.

## Yellow actions

Yellow messages distinguish one practical action without jargon:

- owner confirmation;
- human technical review;
- specialist review;
- missing evidence verification;
- repair;
- repair plus verification;
- fresh review for stale/unknown identity.

A stale package must say the report is old and that a fresh-review prompt is ready; it must not say a repair prompt is ready.

## Red actions

Red is used only when the canonical technical status is `RED_DO_NOT_MERGE`. The second line distinguishes repair from repair plus verification.

## Internal failure

A schema, semantic, projection, manifest, release-lock, or final-head failure prevents a completed owner decision. An invalid artifact set must not emit a misleading completed Green/Yellow/Red result.

The Green result does not claim `merge_authorized`, required reviews, required checks, or bypass-resistant repository settings.
