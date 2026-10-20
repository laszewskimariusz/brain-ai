---
name: test-plan
description: Plan what to test and how for a feature — map every acceptance criterion to unit, integration or end-to-end tests, list edge cases, save docs/plans/<feature>-tests.md. Triggers - "test plan", "what should we test", "coverage plan".
---
# test-plan — what we test and how

## Procedure
1. From the spec (`docs/spec/…`) list the acceptance criteria → each gets at least one test or end-to-end step.
2. Pick the level:
   - **unit** — pure logic (validators, calculations),
   - **integration** — against a real database and real APIs (never a mocked database),
   - **end-to-end** — user paths with real login.
3. Edge cases: empty / maximum / special characters / concurrency / network failure / missing permissions.
4. Save the plan to `docs/plans/<feature>-tests.md` (table: criterion → test → level → file).
5. The developer agent writes and runs the tests test-first; heavy end-to-end suites run on the build machine.

## Rules
- Test behaviour ("the user sees X"), not implementation.
- Arrange-Act-Assert, one reason to fail per test, tests independent of order.
- A flaky test is a bug to fix (race, time, data), not a reason to retry.
- Mock only at the boundary (external APIs, time, file system).
- Never disable bot protection on a deployed environment to make tests pass; use test keys locally.
- Results are facts: `42 passed, 0 failed` plus the command. Never "tests passed" without output.
