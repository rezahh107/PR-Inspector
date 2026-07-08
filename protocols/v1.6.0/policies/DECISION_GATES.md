# Deterministic Decision Gates

Apply gates in this order. The semantic validator implements the same ordering.

## Validity

- Exact confirmed head SHA → `CURRENT`.
- Changed head SHA → `STALE`.
- Missing or unconfirmed head SHA → `UNKNOWN`.
- Non-current validity blocks Green and renders the white invalid owner status.

## Red

Return `RED_DO_NOT_MERGE` when any applies:

- a required check has result `FAIL`;
- a Critical finding is `REPRODUCED` or `CODE_SUPPORTED`;
- a High finding is `REPRODUCED`;
- any explicit red-gate flag is present, including data loss, data corruption, severe financial or production risk, implementation contradiction, a missing mandatory safeguard, or falsified evidence.

## Yellow

When no Red gate applies, return `YELLOW_CHANGES_OR_VERIFICATION_REQUIRED` when any applies:

- a required check is missing, unknown, or not run;
- an important blocking Hypothesis remains;
- a High `CODE_SUPPORTED` or High `HYPOTHESIS` finding remains;
- a blocking Medium finding remains;
- review mode is `PARTIAL`;
- a `NOT_ASSESSABLE` finding remains;
- validity is not `CURRENT`;
- a high-risk functional area is unreviewed;
- coverage is incomplete;
- intent fit is missing, not assessable, not satisfied, only partially satisfied, or contains unsupported satisfaction claims;
- same-PR `repair_handoff` is present.

## Green

Return `GREEN_TECHNICALLY_READY` only when no Red or Yellow reason exists, validity is current, required checks passed with evidence, coverage is complete, no high-risk area is unreviewed, implementation matches intended behavior with concrete intent-fit evidence, and no same-PR repair handoff remains.

Green is not a guarantee and does not replace required human approval.
