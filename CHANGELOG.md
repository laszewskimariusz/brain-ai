# Changelog

All notable changes to brain-ai are documented here. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [4.0.0] — 2026-10-20

Rewrite based on 60 days of usage data. See [docs/why-v4.md](docs/why-v4.md).

### Added
- Claude Code plugin marketplace `brain-ai` with the `brain-core` plugin: 7 role agents with pinned models (architect, developer, reviewer, security, devops, designer, researcher), 4 skills (`spec`, `test-plan`, `docs`, `project-init`) and a `PreToolUse` secret guard.
- `project-kit/`: `CLAUDE.md` and `.claude/settings.json` that enable the plugin and deny secret reads.
- `brain-template/`: shared core with a `CLAUDE.md` under 2 KB, `portfolio.yaml`, `decisions/`, `knowledge/`, `infra/`.
- `scripts/portfolio_status.py`: latest commit and HTTP status for every project.
- Tests (pytest) and CI: manifests, agents, skills, secret guard, kit, docs; private-pattern scan and gitleaks.
- Docs: why v4, architecture, ADR 0001, migration from v3.

### Removed
- 19 agent personas, slash commands, the frontmatter-format hook, generated manifests and search index, memory rotation scripts, v3 templates and examples.

## [3.0.0] — 2026-05-22

File-based memory framework with 19 agent personas. Frozen at tag [`v3.0.0`](https://github.com/laszewskimariusz/brain-ai/tree/v3.0.0); see its CHANGELOG for earlier releases.
