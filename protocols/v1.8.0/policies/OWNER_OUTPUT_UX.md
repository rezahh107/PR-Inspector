# Owner Output UX Policy

The Persian Owner Decision Card remains a decision interface, not a compressed engineering report.

It must state what changed, the practical risk, what was checked, what remains unknown, exactly one next action, and whether specialist review is required. Its existing deterministic rendering remains intact.

## Default direct owner result

The default owner-facing result is a separate UTF-8 text artifact named `OWNER_RESULT.fa.txt`. It contains exactly two LF-terminated lines and no additional visible text.

Green:

```text
🟢 وضعیت: آمادهٔ مرج
مشکل فنی مهمی باقی نمانده است؛ مرج کن.
```

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

No alternative wording is allowed in default owner mode. Do not append headings, greetings, links, paths, hashes, findings, jargon, explanations, recommendations, follow-up questions, artifact descriptions, or a third line.

The interface may expose generated artifacts as attachments or file cards without adding text to the Owner Result.
