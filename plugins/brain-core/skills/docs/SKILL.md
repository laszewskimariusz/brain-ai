---
name: docs
description: Documentation and product copy — README, changelog, API docs, UI copy, SEO basics — written from the code as it is, with every command checked. Triggers - "docs", "README", "changelog", "write documentation", "UI copy".
---
# docs — documentation and copy

## Procedure
1. Settle the audience and language from the project's CLAUDE.md.
2. Read the source of truth (code, `package.json`, scripts, `.env.example`) — documentation describes what exists, not the plan.
3. Write short: sentences under 20 words, active voice, no "innovative" or "revolutionary".
4. Check every command in the document (run it, or mark it as unchecked).

## Patterns
- **README**: what it is (1–2 sentences) → quick start (≤3 copy-paste steps) → stack → environment variables (table: name, required, description — never values) → deploy → licence.
- **Changelog** (Keep a Changelog): `## [x.y.z] — YYYY-MM-DD` with Added / Changed / Fixed / Security.
- **UI copy**: a button is verb + object ("Delete project"); an error says what happened and what to do; an empty state invites an action; loading always has text.
- **SEO**: title under 60 characters with the keyword first, meta description under 160 with a call to action, one H1, descriptive `alt`, Open Graph image 1200×630.

## Rules
- Outdated documentation is worse than none — fix it or delete it.
- No secrets or environment values in examples (`<your-value>`).
