---
description: Verify a branch is PR-ready — acceptance criteria checked against code, QA gates green, reviewer pass. Outputs one yes/no.
argument-hint: <task-id> (e.g. P0-UTIL-3) [path-or-URL to the task list, if not the default]
---

You are the final gate before a PR is opened. This is the **verify-only** companion to
`/implement-task` — assume a human (or a prior run) did most of the implementation and you
are applying the same rigor as a last check. Do not implement features here; only verify,
and list fixes if it is not ready.

Task ID: `$1`
Task-list source (optional override): `$2`

## 1. Re-check every acceptance criterion against code

- Read task `$1`'s acceptance criteria from the Phase 0 task list or roadmap (or `$2`).
- For each criterion, confirm the **literal claim** against the code that currently exists
  on this branch — read the return annotation, the serialized field name, the guard
  position, the single validation site, the actual file contents. **Do not** accept "a
  test with that name passes" as evidence.
- Produce a table: criterion → met / not met → the `file:line` that proves it (or the gap).

## 2. Run the QA gates

- Run `make qa`. Record the result: Pylint score, Black, mypy, coverage %.
- Any red gate ⇒ not PR-ready.

## 3. Run the reviewer agent

- Run the `reviewer` agent (`.github/agents/reviewer.agent.md`) over the branch diff.
- Fold its Blocker / Important findings into the verdict. Nits are noted, not blocking.

## 4. Output a single verdict

Print exactly one of:

- `PR-READY: yes` — all acceptance criteria met against code, `make qa` green, no reviewer
  blockers. Follow with the criterion→`file:line` table.
- `PR-READY: no` — followed by a specific, ordered fix list: each item names the failing
  criterion or gate, the `file:line`, and the concrete change needed.

Do not open the PR, push, or commit.
