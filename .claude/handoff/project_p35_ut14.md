---
name: project-p35-ut14
description: "P35-UT14 / issue #192 (0.7.0: AcCoverage.keyword, ContractWarning.source_url, check_input unshipped-id fix) — state on 2026-10-19, uncommitted"
metadata:
  node_type: memory
  type: project
  originSessionId: c78ae2b6-569d-44a1-880c-bb859467f2a5
  modified: 2026-10-19T20:06:17.596Z
---

P35-UT14 = issue #192, branch `feature/192-coverage-keyword-name` (off master `a1f084e`). Owner said **no commit**. All work is uncommitted.

State when stopped on 2026-10-19 (the session hit its usage limit):
- **Done:** code (`coverage_matrix.py` keyword + `_check_keyword_has_aspects`; `envelope.py` source_url, `DEC-77` removed from the docstring; `schema_export.py` rule; `compat.py` `_with_utilities_versions` helper + INVALID_CONTRACT_ID check before load_schema; `testing.py` `_PAYMENT_FIELD_KEYWORD`, `_blob_url`/`_COLLECTED_SHA`, shown_paths). Schemas regenerated. Docs: rendering.md, component-checks.md, errors.md, plus a bullet in artifact-rules.md § R5 that the brief did not list. 0.7.0 bump in pyproject, README, api.md:71-76/143, copilot-instructions:85 (`DEC-41` dropped). api.md:145 bump example deliberately left alone, since 0.6.0 left it too.
- **Tests:** the test-author agent added tests in 7 files under tests/contracts. Its last report was "508 pass" in tests/contracts. It was stopped before running the lint/format gates.
- **pr.md** (repo root) is drafted. Its `## Acceptance criteria` section is still a placeholder.

The owner later asked for a WIP commit so the work could move to another machine. It holds all of the above plus a copy of this note at `.claude/handoff/project_p35_ut14.md` and `pr.md`. Delete the handoff copy before the final merge (owner's call). pr.md is the PR body source, not a repo file.

**How to apply (next session):** run `make qa` and fix the test files if lint or black fail. Run the `DEC-91` grep from the brief. Verify each AC against the code. Fill the AC table in pr.md. Then report. Do not commit. See [[env-stale-global-install]]: the installed metadata version reads 0.5.0 locally, so mock `installed_utilities_version` in tests.
