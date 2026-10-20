# Brain — shared knowledge core

The brain holds what is shared across projects: infrastructure, decisions, research and the portfolio.
Projects live in their own repos with a project kit (`CLAUDE.md` + `.claude/settings.json`).
Agents and skills come from the `brain-core` plugin, not from this repo.

## Where to look
1. `portfolio.yaml` — every project: repo, working copy, stage, deploy. Status: `python3 scripts/portfolio_status.py portfolio.yaml`.
2. `infra/` — hosts, services, ports, owners. Key names only, never secret values.
3. `decisions/` — ADRs (CONTEXT / DECISION / REASON / CONSEQUENCE).
4. `knowledge/` — research notes, dated `YYYY-MM-DD-topic.md`.
5. Search with `grep -rl` before asking.

## Where to write
| What | Where |
|---|---|
| architecture decision, stack change | `decisions/NNNN-title.md` |
| research result | `knowledge/YYYY-MM-DD-topic.md` |
| host, service, runbook | `infra/` |
| project documents | the project's own repo, `docs/` |
| secrets | a secret manager; files hold key names only |

## Rules
- Coordinate here; build, test and run heavy jobs on the build machine.
- Commit only when the owner says so.
- Keep this file under 2 KB: every session loads it.
