---
name: project-init
description: Set up a project repo for the brain-ai workflow — a short CLAUDE.md and a .claude/settings.json that enables the brain-core plugin and denies secret reads — plus a portfolio entry for the brain. Triggers - "project init", "set up this repo", "add the kit", "onboard this project".
---
# project-init — the project kit

## Procedure
1. `git rev-parse --show-toplevel` — you must be at the repo root. No repo → ask whether to `git init`.
2. Gather facts. Read the repo first (`package.json`, Dockerfile, migrations, README, an existing CLAUDE.md); ask the owner only for the rest:
   - slug, name, goal in 1–2 sentences,
   - deploy target, databases, secret key names (never values), boundaries.
3. Write `CLAUDE.md` from the template, fitted to the repo, at most 100 lines. Describe what the code cannot tell; no file-tree tours.
4. If `CLAUDE.md` exists: do NOT overwrite — show the differences and write after approval.
5. Write `.claude/settings.json` from the template. It is a protected path:
   - interactive session — write it (the user approves); merge into an existing file (`extraKnownMarketplaces`, `enabledPlugins`, `permissions.deny`), delete nothing;
   - headless or no approval — do NOT work around it; print the merged JSON in the report.
6. Create `docs/spec/.gitkeep` and `docs/plans/.gitkeep`; add `.claude/settings.local.json` to `.gitignore`.
7. Print a portfolio entry for the brain's `portfolio.yaml` (slug, name, repo, workdir, stage, deploy, notes).
8. Report: created files, anything not written and why, next step `/brain-core:spec <first-feature>`.

## Rules
- Do not commit unless told to.
- No secrets in CLAUDE.md or settings — key names only.

## Template: CLAUDE.md
```markdown
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
```

## Template: .claude/settings.json
```json
{
  "extraKnownMarketplaces": {
    "brain-ai": {
      "source": {
        "source": "github",
        "repo": "laszewskimariusz/brain-ai",
        "ref": "v4.0.1"
      }
    }
  },
  "enabledPlugins": {
    "brain-core@brain-ai": true
  },
  "permissions": {
    "deny": [
      "Read(**/.env)",
      "Read(**/.env.local)",
      "Read(**/.env.development)",
      "Read(**/.env.dev)",
      "Read(**/.env.production)",
      "Read(**/.env.prod)",
      "Read(**/.env.staging)",
      "Read(**/.env.stage)",
      "Read(**/.env.test)",
      "Read(**/.env.ci)",
      "Read(**/.env.preview)",
      "Read(**/.env.*.local)",
      "Read(**/.secrets)",
      "Read(**/.secrets.*)",
      "Read(**/*.pem)",
      "Read(**/*.p12)",
      "Read(**/*.pfx)",
      "Read(**/id_rsa)",
      "Read(**/id_ed25519)",
      "Read(**/id_ecdsa)",
      "Read(**/id_dsa)",
      "Read(~/.ssh/**)",
      "Read(**/.netrc)",
      "Read(**/.pgpass)",
      "Read(**/.git-credentials)",
      "Read(~/.aws/credentials)",
      "Bash(env)",
      "Bash(printenv*)"
    ]
  },
  "sandbox": {
    "enabled": true,
    "filesystem": {
      "denyRead": [
        "./**/.env",
        "./**/.env.local",
        "./**/.env.development",
        "./**/.env.dev",
        "./**/.env.production",
        "./**/.env.prod",
        "./**/.env.staging",
        "./**/.env.stage",
        "./**/.env.test",
        "./**/.env.ci",
        "./**/.env.preview",
        "./**/.env.*.local",
        "./**/.secrets",
        "./**/.secrets.*",
        "./**/*.pem",
        "./**/*.p12",
        "./**/*.pfx",
        "./**/id_rsa",
        "./**/id_ed25519",
        "./**/id_ecdsa",
        "./**/id_dsa",
        "~/.ssh"
      ]
    },
    "autoAllowBashIfSandboxed": false
  }
}
```
