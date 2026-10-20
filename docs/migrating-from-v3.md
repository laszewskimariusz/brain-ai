# Migrating from v3

v3 is frozen at tag [`v3.0.0`](https://github.com/laszewskimariusz/brain-ai/tree/v3.0.0).

## What was removed and why

| v3 | v4 | Why |
|---|---|---|
| 19 agent personas copied into `~/.claude/agents/` | 7 role agents in the `brain-core` plugin | a third were never called; personas do not improve results |
| `manifest.json`, `_search.json`, `regen-manifest.py` | plain files + `grep` | read ~28 times in 60 days |
| frontmatter-format hook | removed | blocked 0 writes |
| slash commands for memory rotation and consolidation | removed; one memory | two memories loaded on every start |
| templates for a brain-in-one-repo | `brain-template/` + `project-kit/` | projects live in their own repos |

## Steps

1. Remove the v3 agent files from `~/.claude/agents/` (keep a copy if you customised them).
2. Install the plugin: `/plugin marketplace add laszewskimariusz/brain-ai`, then `/plugin install brain-core@brain-ai`.
3. Move each project into its own repo and run `/brain-core:project-init` there.
4. Copy `brain-template/` into your brain repo; move ADRs into `decisions/`, research into `knowledge/`, and list projects in `portfolio.yaml`.
5. Trim the brain's `CLAUDE.md` below 2 KB; move long procedures into skills.
