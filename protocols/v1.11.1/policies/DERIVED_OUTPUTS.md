# Derived Outputs — v1.11.1

All derived artifacts are deterministic functions of the canonical package and official projection:

- `DECISION_PROJECTION.json`
- `OWNER_DECISION_CARD.fa.md`
- `TECHNICAL_HANDOFF.en.md`
- `OWNER_RESULT.fa.txt`
- `OWNER_PROFILE_COMMANDS.fa.txt`
- conditional `NEXT_ACTION_PROMPT.en.md`
- `artifact-manifest.json`

`pr_inspector.derived_outputs.build_review_artifacts` is the sole artifact builder and `render_next_action_prompt` is the sole prompt renderer. Hash integrity is necessary but not sufficient: prompt-required output must also pass `pr_inspector.prompt_semantics.validate_prompt_semantics`.

Candidate compatibility code must not independently render, verify, hash, or compose any authoritative output.
