# decisions/

One file per architecture decision: `NNNN-short-title.md`.

```markdown
---
id: adr-NNNN-short-title
status: proposed | accepted | superseded by NNNN
date: YYYY-MM-DD
---
# ADR-NNNN — Title

## CONTEXT
What forces the decision: the problem, constraints, measurements.

## DECISION
What we do. Specific enough to implement.

## REASON
Why this option beats the alternatives (list the rejected ones).

## CONSEQUENCE
What gets easier, what gets harder, how to back out.
```

Write an ADR when a choice is expensive to reverse: a stack change, a data model, a new service, a security boundary.
