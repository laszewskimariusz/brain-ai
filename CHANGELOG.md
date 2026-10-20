# Changelog

All notable changes to brain-ai are documented here. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [4.0.1] — 2026-10-20

Security hardening.

### Security
- The project kit turns the Bash sandbox on (`sandbox.enabled`) and hides the protected paths from shell commands with `sandbox.filesystem.denyRead`.
- One list of protected paths in the secret guard (`PROTECTED`) feeds the hook, the kit's `permissions.deny` and the sandbox; tests keep them in sync. `.env.production` and the other common stages, `.secrets.*`, `*.p12`, `*.pfx`, SSH keys and `~/.ssh` are now denied in every layer.
- `reviewer`, `security` and `researcher`: on top of their read-only tool lists, the hook makes a best-effort check inside those agents (`agent_type`) and blocks shell commands that change files, git state or dependencies, including inside `if`/`for` blocks, `bash -c`, `$(...)`, backticks and `eval`. Help, `--dry-run` and `--check` forms pass.
- The guard blocks copying secret files out (`cp` source, `scp`, `rsync`, `curl @file`, `tar`, …) and feeding them with `<`.
- An internal error while checking a covered tool now blocks (fails closed) instead of passing.

### Fixed
- False positives: `src/.env.ts` and other code files, and `*.key` files without a private key (such as `i18n/messages.key`), are no longer blocked.
- Password-in-URL detection also covers an empty user (`redis://:pw@host`) and `mongodb+srv://`.
- Unreadable hook input passes with a one-line warning instead of silently.
- `portfolio_status.py`: git never prompts for credentials, `HEAD` answered with 405/501 is retried with `GET`, a portfolio entry that is not a mapping becomes an `invalid` row, checks run in parallel under one overall deadline.

### Changed
- The kit pins the release: `extraKnownMarketplaces.brain-ai.source.ref` is `v4.0.1`. README documents how to update.
- CI validates both manifests and installs the plugin from the checkout in a clean `HOME`; Claude Code and `gitleaks-action` are pinned.
- Docs describe the layers as sandbox (OS) → `permissions.deny` → hook (seat belt).

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
