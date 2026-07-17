# Owner Output UX — v1.11.1

`OWNER_RESULT.fa.txt` remains the compact deterministic owner result. When the canonical projection requires a prompt, the complete owner-facing result is returned only by `official_owner_delivery` from one `VerifiedReviewCompletion` snapshot.

Profile-selection commands are not part of the action prompt or compact owner result. They remain in the separately verified `OWNER_PROFILE_COMMANDS.fa.txt` artifact and are exposed by `official_owner_profile_commands`.

Manual composition, Candidate composition, and model-authored replacement prompts are unsupported and must not be presented as official output.
