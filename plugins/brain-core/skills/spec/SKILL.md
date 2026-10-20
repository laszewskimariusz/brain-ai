---
name: spec
description: Write a feature specification by interviewing the owner — goal, scope, out of scope, acceptance criteria, end-to-end verification — saved to docs/spec/<feature>.md. Triggers - "spec", "write a spec", "requirements", "what should it do", "user stories".
---
# spec — interview → docs/spec/<feature>.md

Goal: a document a fresh session (or the developer agent) can implement without asking questions.

## Procedure
1. Read the project's CLAUDE.md, existing specs in `docs/spec/` and the code in the area — do not ask what you can read.
2. Interview the owner **one question at a time**, multiple choice with your recommendation first. Topics in order:
   - why (the user's problem, who uses it),
   - the smallest scope that delivers value,
   - what we are NOT doing,
   - acceptance criteria,
   - how we verify end to end (a concrete browser or CLI scenario).
   Make technical decisions yourself and record them; ask only about business and product.
3. Write `docs/spec/<feature-slug>.md` from the template. No placeholders ("TBD") — anything missing becomes a question.
4. Show the owner a 5–8 line summary and the path. After approval, propose an implementation plan.

## Template
```markdown
# <Feature>
Status: draft | accepted (date, by whom)
## Goal
<problem, user, value — 2–4 sentences>
## Scope
- <behaviour 1>
## Out of scope
- <what we do not do and why>
## Interfaces and files
- <screens / endpoints / tables / files it touches>
## Acceptance criteria
- GIVEN … WHEN … THEN …
## End-to-end verification
1. <step, expected result>
## Decisions
- <decision — reason>
```

## Rules
- More than three days of work → split into separate specs.
- Every acceptance criterion must be checkable by a test or an end-to-end step.
- Business decisions belong to the owner — quote their words under Decisions.
