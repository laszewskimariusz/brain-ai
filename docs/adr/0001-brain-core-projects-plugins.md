---
id: adr-0001-brain-core-projects-plugins
status: accepted
date: 2026-10-16
---
# ADR 0001 — Brain core, projects apart, agents as plugins

## CONTEXT

v3 kept projects, agents and shared knowledge in one place. Agents existed as files on several machines and in a repo that had fallen months behind. Personas were written for older models. A 60-day measurement ([why-v4.md](../why-v4.md)) showed subagents caused most of the cost, six personas were never used, custom indexes were barely read, and no session ever started inside a project repo.

Platform facts that shaped the options:
- A subagent pays off when it isolates work: output that would flood the context, restricted tools, or self-contained tasks.
- Skills load progressively: only name and description sit in context until used.
- `CLAUDE.md` should stay under ~200 lines; imports do not reduce cost.
- A plugin marketplace is a git repo with `.claude-plugin/marketplace.json`; projects enable it in `.claude/settings.json`.
- Only `permissions.deny` and `PreToolUse` hooks enforce anything. Subagents from plugins ignore their own hooks, so guards must sit at plugin level.

## DECISION

1. **Brain = core.** It keeps infrastructure, decisions, research and a hand-edited `portfolio.yaml` (slug, repo, working copy, stage, deploy, notes). No project code.
2. **One repo per project** with a kit: `CLAUDE.md` (≤100 lines) and `.claude/settings.json` that enables the marketplace and plugin and denies secret reads.
3. **Agents, skills and guards ship as a versioned plugin** (`brain-core`) from one marketplace repo. Seven role agents with pinned models (architect on the strongest model, the rest mid-tier); four process skills; a `PreToolUse` secret guard.
4. **Two machines.** A coordinator for planning and tracking; a build machine for working copies, builds, tests and parallel agents.
5. **Removed:** personas, the generated manifest and search index, the frontmatter hook, the second memory layer.

## REASON

- The biggest lever on cost is the subagents' model and the size of session start, not the number of agents.
- Native mechanisms (plugins, rules, per-repo memory) replace machinery we maintained but nobody read.
- One versioned plugin from one marketplace removes drift between machines.
- Moving heavy work off the coordinator keeps it responsive.

Rejected:
- **Copying agents into every repo** — drifts within a month.
- **A full spec-kit framework** — too heavy for one owner plus agents; brainstorm → plan → test-first covers the same ground.
- **Keeping all personas** — a third were dead weight in context.

## CONSEQUENCE

- Working on a project means a session in that project's repo on the build machine, not a `cd` from the brain.
- Updating agents is a plugin release (new version in `plugin.json`, entry in the changelog).
- Old links into v3 paths stay historical; history is not rewritten.
- Rollback: v3 remains available at tag `v3.0.0`.
