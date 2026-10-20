# brain-ai

Public repo: a brain template, a project kit and the `brain-core` Claude Code plugin (marketplace `brain-ai`). This repo is developed with its own plugin.

- Plugin under development: `plugins/brain-core/` — run sessions with `claude --plugin-dir plugins/brain-core` so agents, skills and the secret guard load from the working tree.
- Versions: `plugins/brain-core/.claude-plugin/plugin.json` (semver) + git tag `vX.Y.Z` + `CHANGELOG.md`.

## Commands
| What | Command |
|---|---|
| tests | `python -m pytest -q tests` (needs `pytest`, `pyyaml`) |
| guard tests | `bash tests/guard/guard.test.sh` |
| publication guard | `GUARD_HISTORY_SINCE=v3.0.0 bash scripts/guard.sh` (needs private patterns, see below) |
| validate manifests | `claude plugin validate .` and `claude plugin validate plugins/brain-core` |
| install check | `HOME=$(mktemp -d) claude plugin marketplace add <abs path or laszewskimariusz/brain-ai>` then `claude plugin install brain-core@brain-ai` |

## Rules
- Everything here is public. No internal hostnames, IPs, domains, secret-manager names, tracker URLs, private project or client names, persona names or personal data. The guard reads its patterns from the `GUARD_PRIVATE_PATTERNS` secret (CI) or an untracked `.guard-private` file — never put them in tracked files.
- Planning notes and specs that mention internal context live outside the repo.
- Test first: write the failing test, watch it fail, then implement. Secret-looking test values are assembled at runtime.
- Numbers in docs only from measured data; say where they come from.
- Commit and push only when the owner says so. Publishing a release needs the owner's approval.

## Done when
- `pytest` green, guard tests green, publication guard clean, both `claude plugin validate` pass.
- Docs and CHANGELOG match the code; README commands work.

## Workflow
`/brain-core:spec <change>` → plan → `developer` agent (test-first) → `security` + `reviewer` agents → owner approval → tag + release.
