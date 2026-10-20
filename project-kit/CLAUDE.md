<!-- Project kit template: copy to the repo root and fill the {{…}} fields, or run /brain-core:project-init. -->
# {{NAME}}

{{GOAL — 1–2 sentences: what it is, for whom, what value}}

- Slug: `{{SLUG}}` · brain-ai plugin: `brain-core` (enabled in `.claude/settings.json`)
- Shared knowledge (infrastructure, decisions) lives in the brain repo, not here.

## Stack
{{what is actually in the repo}}

## Commands
| What | Command |
|---|---|
| dev | `{{DEV}}` |
| test | `{{TEST}}` |
| typecheck / lint | `{{CHECK}}` |
| build | `{{BUILD}}` |

## Data and secrets
{{databases and services: where they run, which environment may be touched}}
- Secrets by key name only ({{KEY_NAMES}}); the value goes into a variable, never to the screen or into files.

## Deploy
{{where and how; "only when the owner says so"}}

## Boundaries
{{what not to touch: production database, generated files, invariants}}
- Never delete or weaken existing tests.
- Commit, push and deploy only when the owner says so.

## Done when
{{the checks this repo needs before work counts as finished}}

## Workflow
`/brain-core:spec <feature>` → `docs/spec/` → plan in `docs/plans/` → developer agent → reviewer agent → end-to-end check.