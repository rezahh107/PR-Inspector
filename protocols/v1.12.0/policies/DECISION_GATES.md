# Decision Gates — v1.12.0

## Sole authority

`pr_inspector.decision_projection.project_decision` is the only active decision authority. Package-authored decision labels and Candidate compatibility code cannot mint status or action authority.

## Output authority gate

After `review-package.json`, only official projection, derived outputs, verified completion, and official owner delivery are permitted. Any independent Candidate projection, prompt renderer, artifact builder, verifier, or owner composition is a repository-closure failure.

## Technical and governance separation

Minimal governance is `NOT_REQUESTED`. Strict governance is additive and fail-closed. Governance gaps cannot create technical repair authority or change validated technical findings.

## Action authority

- `repair` and `repair_and_verify`: bounded modification allowed.
- `verify`: evidence collection only; no modification.
- `rerun_review`: fresh review only; no repair.
- human/specialist handoffs: no model-authored approval.

## Prompt gate

Prompt-required output is valid only when final bytes match the official renderer and independent semantic validation succeeds. Empty, heading-only, generic, identity-free, reason-free, finding-free, test-free, or rereview-free prompts fail closed.
