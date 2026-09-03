---
description: Implement a Phase 0 / roadmap task end to end, from its spec to a PR-ready description.
argument-hint: <task-id> (e.g. P0-UTIL-3) [path-or-URL to the task list, if not the default]
---

You are driving a single roadmap task to completion in `living-doc-utilities`.
Follow these steps **in this exact order**. Do not skip or reorder them.

Task ID: `$1`
Task-list source (optional override): `$2`

## 1. Read the task

- Locate task `$1` in the Phase 0 task list (`living-doc/docs/specs/phase-0-tasklist.md`)
  or the roadmap (`living-doc/docs/specs/roadmap.md`). If `$2` is given, read it there.
- Read the task's **prompt** and its **acceptance criteria** in full. Also read the
  linked GitHub issue if the task names one.
- Write the acceptance criteria out as a numbered checklist you will verify against code
  in step 5. Do not start work until this list is explicit.

## 2. Read every file the task references — before writing any code

- Open every spec, doc, config, and source file named in the task prompt, its "Spec refs"
  line, and its acceptance criteria. Follow one hop of cross-references (a spec section that
  points at another spec section).
- Read the existing code the change touches and the tests that already cover it, so the
  implementation matches repo patterns (`.github/copilot-instructions.md`,
  `.github/copilot-review-rules.md`).
- If the task is ambiguous after reading, stop and ask — do not guess.

## 3. Implement to the spec exactly

- Make the smallest change that satisfies the spec. Match existing structure, naming,
  logging style (lazy `%` formatting, no `print`), and import conventions.
- Add or update tests for every new or changed code path (success + failure). Use the
  `test-author` agent for the test surface.
- Do not change externally-visible contracts (public class/function signatures, the
  serialized issue JSON shape and its `type` discriminator, `Issues.make_issue_key()`'s
  format, `get_action_input()` / `set_action_output()` behaviour, contract-sensitive
  strings) unless the task explicitly calls for it — and bump `pyproject.toml` `version`
  when it does.
- If a design-doc section is being implemented, apply `.claude/rules/docs-lifecycle.md` in
  this same change: move that section's content into the live docs (`README.md` /
  `DEVELOPER.md`).

## 4. Run the `make qa` loop until green

- Run `make qa` (format-check, lint, types, test — the same targets CI runs).
- Fix every failure and re-run. Repeat until `make qa` exits clean:
  Pylint ≥ 9.5, Black clean, mypy clean, `pytest --cov-fail-under=80` passing.
- Do not lower a threshold, add an inline lint disable, or `# type: ignore` to get past a
  gate unless the repo documents that exception.

## 5. Verify each acceptance criterion against the actual code

For every criterion on your step 1 checklist, confirm the **literal claim** by reading the
code that now exists — **not** by checking that a same-named test is green.

- "returns a typed `X`" → read the function's real return annotation.
- "serialized as `field_name`" → read the actual key written in `to_dict()`.
- "load falls back to empty on error" → confirm the `except` returns `cls()` before any
  re-raise.
- "input is validated in one place" → confirm there is exactly one validation site.
- "file X exists / contains Y" → open X and confirm Y is literally present.

Record each criterion as met (with the `file:line` that proves it) or not met. If any
criterion is not met, return to step 3.

## 6. Write the PR description

Write a PR description (to `pr.md` in the repo root unless told otherwise) with exactly
these sections, per `CONTRIBUTING.md`:

- `## Overview` — what changed and why.
- `## Release Notes` — at least one real user-facing bullet (no `TBD`).
- `## Related` — `Closes #<issue>` for the task's issue.

Include a short "Acceptance criteria" checklist mapping each criterion to the `file:line`
that satisfies it (from step 5).

## 7. Stop

Do not open the PR, push, or commit. Report: what changed, the `make qa` result, and the
acceptance-criteria verification table. Then stop.
