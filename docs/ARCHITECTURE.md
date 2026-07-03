# Architecture

## Design goal

A new model should reach the correct first response without repository-wide exploration.

## Layers

```text
User command
  → BOOTSTRAP.md
  → protocol-manifest.yaml
  → versioned contract
  → policies
  → operational pipeline
  → fixed output templates
```

## Why both `AGENTS.md` and `BOOTSTRAP.md`?

- `AGENTS.md` is automatically discoverable by several coding agents and stays short.
- `BOOTSTRAP.md` is the explicit cross-tool entry point.
- Both point to the same manifest to prevent divergent instruction chains.

## Why a manifest?

The manifest supplies one active version, one canonical contract, deterministic load order, required outputs, forbidden default actions, and the validation command. Models should not choose their own reading order.

## Why modular files?

High-priority rules remain close to the entry point. Details are separated by role: security, decision gates, owner UX, technical output, and pipeline.

## Versioning

Released contract directories are immutable. A behavioral change requires a new version directory, version-pointer update, manifest update, changelog entry, and validator update.

## Enforcement boundary

The current validator checks structural consistency. It does not yet prove semantic compliance of generated reports. A future report schema and semantic validator should enforce Critical gates.
