# Architecture

## Pieces

| Piece | Holds | Lives in |
|---|---|---|
| Brain | infrastructure notes, decisions (ADRs), research, `portfolio.yaml` | its own repo, cloned on the coordinator |
| Marketplace | the `brain-core` plugin: agents, skills, hooks | this repo (or your fork) |
| Project | code + kit (`CLAUDE.md`, `.claude/settings.json`, `docs/spec`, `docs/plans`) | one repo per project |
| Coordinator | the owner's main session: portfolio, cross-project decisions | a small, always-on machine |
| Build machine | working copies, builds, tests, parallel agents | a machine with CPU and memory to spare |

## Flow of a feature

```mermaid
sequenceDiagram
  participant O as Owner
  participant S as Project session
  participant Dev as developer agent
  participant Rev as reviewer agent
  O->>S: /brain-core:spec feature
  S->>O: one question at a time
  S->>S: docs/spec/feature.md, then a plan in docs/plans/
  S->>Dev: brief (spec + plan)
  Dev->>S: code + test evidence
  S->>Rev: diff + spec
  Rev->>S: APPROVE or MUST FIX list
  S->>O: end-to-end check, ready to ship
```

## Why the split

- **Context stays small.** A project session loads that project's `CLAUDE.md` and the plugin's skill descriptions — not the whole brain.
- **One source of truth for agents.** Updating an agent means releasing a new plugin version (`plugin.json` + changelog); every project picks it up from the same marketplace instead of carrying its own copy.
- **Heavy work does not starve the coordinator.** Builds and fan-out run on the build machine.

## Guards

1. `permissions.deny` in every project kit: no reading `.env`, `.secrets`, key files; no `env`/`printenv`.
2. The plugin's `PreToolUse` secret guard: blocks literal secrets in writes, secret-file reads and environment dumps.
3. In CI: tests, a private-pattern scan of the tree and history, and gitleaks.
