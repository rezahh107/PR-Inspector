# Owner Output UX Policy

The Persian Owner Decision Card remains a decision interface, not a compressed engineering report.

It must state what changed, the practical risk, what was checked, what remains unknown, exactly one next action, and whether specialist review is required. Its existing deterministic rendering remains intact.

## Default direct owner result

The default owner-facing result is a separate UTF-8 text artifact named `OWNER_RESULT.fa.txt`. It contains exactly two LF-terminated lines and no additional visible text.

Only the following three byte-exact outputs are allowed.

Green:

```text
🟢 وضعیت: آمادهٔ مرج
مشکل فنی مهمی باقی نمانده است؛ پس از تأییدهای لازم ادغام شود.
```

The Green wording is deliberately conservative. It reports technical readiness but never bypasses `PROJECT_OWNER_CONFIRMATION`, `HUMAN_TECHNICAL_REVIEW_REQUIRED`, or `SECURITY_OR_DOMAIN_SPECIALIST_REQUIRED`. It is not automatic merge authorization.

Yellow:

```text
🟡 وضعیت: هنوز آماده نیست
بخشی از کار باید اصلاح یا اثبات شود؛ پرامپت اقدام آماده است.
```

Red:

```text
🔴 وضعیت: ادغام نشود
یک مشکل جدی پیدا شده است؛ پرامپت اصلاح آماده است.
```

When `review_validity` is `STALE` or `UNKNOWN`, validity takes precedence at the simple owner surface and the approved Yellow output is emitted regardless of the stored non-Green technical status. This does not create a fourth output. The corresponding prompt must use `action_mode: rerun_review` and must not authorize repair from obsolete evidence.

No alternative wording is allowed in default owner mode. Do not append headings, greetings, links, paths, hashes, findings, jargon, explanations, recommendations, follow-up questions, artifact descriptions, or a third line.

The interface may expose generated artifacts as attachments or file cards without adding text to the Owner Result.
