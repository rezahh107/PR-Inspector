# Design Basis

PR Inspector uses these primary references:

1. OpenAI Codex documentation for `AGENTS.md` discovery and instruction layering.
2. GitHub documentation for repository custom instructions and `AGENTS.md` support.
3. GitHub documentation for README structure and relative navigation.
4. GitHub documentation for safe GitHub Actions permissions and immutable action pinning.

Reference locations:

- `developers.openai.com/codex/guides/agents-md`
- `docs.github.com/.../add-repository-instructions`
- `docs.github.com/.../about-readmes`
- `docs.github.com/en/actions/reference/security/secure-use`

Internal design principles incorporated:

- keep the model entry point short;
- define a deterministic reading order;
- separate owner-facing and technical outputs;
- state uncertainty and enforcement status honestly;
- treat important behavioral rules as future validator targets.
