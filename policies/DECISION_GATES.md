# Decision Gates

Apply these gates in order. Do not choose status by tone or overall impression.

## Review validity

- Missing or unconfirmed head SHA → `UNKNOWN`.
- Changed head SHA → `STALE`.
- Only an exact current head SHA → `CURRENT`.
- `STALE` or `UNKNOWN` cannot be Green.

## Red gates

Return `RED — DO NOT MERGE` when any applies:

- required build or test failed;
- Critical finding is Reproduced or Code-Supported;
- High finding is Reproduced;
- clear unauthorized-access, data-loss, data-corruption, severe financial, or severe production risk exists;
- implementation clearly contradicts intended behavior;
- mandatory Sensitive safeguard is missing;
- evidence was materially falsified.

## Yellow gates

Return `YELLOW — CHANGES OR VERIFICATION REQUIRED` when no Red gate applies and any applies:

- a required test, check, context, or CI result is missing;
- important Hypothesis remains;
- High Code-Supported or High Hypothesis remains unresolved;
- meaningful Medium issue requires correction;
- review mode is Partial;
- relevant behavior is Not Assessable;
- validity is Unknown;
- high-risk functional scope was not fully reviewed.

## Green gates

Return `GREEN — TECHNICALLY READY` only when all apply:

- validity is Current;
- review is Full, or exclusions are proven generated or vendor artifacts;
- required checks passed with evidence;
- no unresolved Critical or High blocker exists;
- no important verification gap remains;
- no functional high-risk area is unreviewed;
- implementation matches intended behavior;
- both outputs are complete and consistent.

Green is not a guarantee.

## Approval gates

- Sensitive → at least `HUMAN TECHNICAL REVIEW REQUIRED`.
- Authentication, authorization, protected credentials, cryptography, payments, regulated or personal data, destructive migrations, production security, backup or recovery, or supply-chain trust → normally `SECURITY OR DOMAIN SPECIALIST REQUIRED`.
- A model cannot be the sole approval for Sensitive work.

## Owner-facing mapping

- Green → `🟢 سبز — از نظر فنی آماده است`
- Yellow → `🟡 زرد — فعلاً متوقف شود`
- Red → `🔴 قرمز — ادغام نشود`
- Stale or blocking Unknown validity → `⚪ گزارش نامعتبر — بررسی باید تکرار شود`
