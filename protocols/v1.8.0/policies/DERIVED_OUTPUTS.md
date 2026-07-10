# Derived Output Policy

## Boundary

The derived layer runs only after the canonical package has passed schema and semantic validation and after the existing canonical Owner Decision Card and Technical Handoff have been deterministically rendered.

`review-package.json` remains the sole source of truth. The derived layer is not a decision engine and does not modify the package.

## Artifacts

Always generate:

- `OWNER_RESULT.fa.txt`
- `artifact-manifest.json`

Generate `NEXT_ACTION_PROMPT.en.md` exactly once for Yellow or Red. It is forbidden for Green.

## Owner-result projection

The owner result uses only the three approved outputs in `OWNER_OUTPUT_UX.md`.

- Current Green uses the conservative Green wording and preserves every approval requirement.
- Current Yellow uses the Yellow wording.
- Current Red uses the Red wording.
- `STALE` or `UNKNOWN` validity takes precedence and uses the Yellow wording because the only authorized next step is a fresh review.

## Structural action mode

Derive action mode without free-text matching and only after canonical validation:

- `rerun_review`: `review_validity` is not `CURRENT`.
- `repair`: confirmed repair carriers or confirmed implementation defects exist without a separate unresolved verification gap.
- `verify`: unresolved execution, evidence, coverage, intent, hypothesis, or not-assessable gaps exist with no confirmed repair obligation.
- `repair_and_verify`: both confirmed repair work and unresolved verification gaps exist.

The classifier must cover every structured predicate that can produce the canonical Red or Yellow status. In particular:

- confirmed Critical findings, reproduced High findings, code-supported High findings, confirmed blocking Medium findings, failed required checks, red-gate flags, validated `repair_handoff`, and accepted external repair carriers are repair reasons;
- unknown or not-run required checks, hypotheses, not-assessable findings, partial review, incomplete coverage, unreviewed high-risk areas, unverified areas, and incomplete or unsupported intent evidence are verification reasons.

Canonical `required_actions` are rendered as recorded obligations but are never parsed as classification keywords.

A stale or unknown package must not authorize code repair. Its prompt may only require a fresh PR Inspector review and may carry old findings as non-authorizing historical context.

## Operational mode enforcement

The prompt must make the selected action mode operational, not merely display its name.

- `repair` grants bounded repair authority and requires evidence for the repaired exact head.
- `verify` authorizes inspection, safe command execution, and evidence collection only. It must prohibit repository edits. If verification discovers a defect, the implementer records it and requests a fresh PR Inspector decision instead of silently repairing it.
- `repair_and_verify` separately requires repair of confirmed defects and resolution of every verification reason.
- `rerun_review` suspends repair authority and permits only current-head review regeneration.

Each mode must render its structured repair reasons, verification reasons, and canonical required actions.

## Prompt section order

The prompt contains these fixed sections in order:

1. `[ROLE AND AUTHORITY]`
2. `[AUTHORITATIVE REVIEW IDENTITY]`
3. `[TRUST BOUNDARY]`
4. `[MISSION]`
5. `[FINDINGS AND EVIDENCE]`
6. `[INVARIANT EXTRACTION]`
7. `[ADJACENT IMPACT AUDIT]`
8. `[TECHNICAL DECISION AUTHORITY]`
9. `[SCOPE CONTROL]`
10. `[ADVERSARIAL SELF-AUDIT]`
11. `[VALIDATION AND EVIDENCE]`
12. `[IMPLEMENTER OUTPUT]`
13. `[MANDATORY PR INSPECTOR RE-REVIEW]`

Package-derived free text is serialized as untrusted data. Accepted external suggestions may appear only through validated `external_review_intake`. Repair guidance resolves through existing finding IDs, rule IDs, and `repair_handoff`.

The self-audit is explicitly not independent. Finding status remains `implemented_pending_rereview` until the repaired exact head is reviewed again by PR Inspector.

## Artifact manifest and byte validation

The manifest records:

- canonical review package path and canonical SHA-256;
- Owner Decision Card path and SHA-256;
- Technical Handoff path and SHA-256;
- simple Owner Result path and SHA-256;
- whether the action prompt was generated, its path and SHA-256, and the structural action mode.

Validation must:

1. compare every rendered artifact's actual bytes with deterministic UTF-8 LF bytes;
2. parse the written `artifact-manifest.json` rather than trusting an in-memory replacement;
3. recompute SHA-256 from each referenced on-disk artifact byte sequence;
4. reject CRLF conversion, missing final LF, altered bytes, stale paths, stale hashes, missing conditional artifacts, and forbidden Green prompts.

For `review-package.json`, the manifest hash remains the declared canonical sorted-key compact UTF-8 JSON hash, not the incidental pretty-printed file byte hash.

For Green, prompt generation, path, hash, and action mode are null/not applicable.

## Exact-head CI evidence

A pull-request workflow that is cited as exact-head evidence must explicitly check out `github.event.pull_request.head.sha`, print the expected and actual SHA, and fail when `git rev-parse HEAD` differs. A synthetic merge ref may be useful integration evidence but must not be described as exact-head execution.
