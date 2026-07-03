# Owner Output UX Policy

## Goal

The Owner Decision Card is a decision interface, not a compressed engineering report.

It must tell a non-technical owner:

- what changed;
- the most important real-world consequence;
- what was checked;
- what remains unknown;
- the single next action;
- whether a specialist is required.

## Smart filtering

Normally hide code excerpts, paths, line numbers, symbols, SHAs, commands, raw logs, stack traces, capability fields, evidence labels, Rule IDs, and internal workflow details.

Show a technical identifier only when the owner must copy, locate, or communicate it. Move technical detail to the handoff rather than deleting it.

## Fixed format

Use only `templates/OWNER_DECISION_CARD.fa.md`.

- Target: 120–220 Persian words.
- Maximum: 250 words.
- Use short sentences and plain Persian.
- End after the next action and specialist requirement.

## Practical translation

Translate technical findings into their practical effect on users, business, data, or service operation. Preserve seriousness without exaggerating or weakening it.

## Uncertainty

Clearly separate what was checked, inferred, and unavailable. Never claim complete safety. Do not use numerical confidence percentages.

## Mental imagery

Use at most one short analogy, no more than two sentences, only when it genuinely improves understanding.

## No hidden-state claims

Do not claim permanent memory, hidden state, or automatic handoff unless a real mechanism exists. State that the Technical Handoff Package must be supplied to the next model.

## Validity

The card is invalid when it lacks a status, practical consequence, remaining uncertainty, one concrete next action, specialist requirement, or consistency with the technical handoff.
