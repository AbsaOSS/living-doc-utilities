# Rendering

## Purpose

Transform and generator authors read this page. It defines which field each view shows and how coverage is
counted.

Read before: [Component checks](component-checks.md) · Next: [Errors and warnings](errors.md)

## Contents

- [Records and presentation](#records-and-presentation)
- [Fields by view](#fields-by-view)
- [Coverage](#coverage)
- [Planned work summary](#planned-work-summary)

## Records and presentation

- Every authored field is carried at its authored level in `generator-ready`; nothing is expanded, inherited or flattened → `contracts/generator_ready.py::Content`
- The view filter that builds a `generator-ready` document selects records only → transforms
- The release view drops `planned` and `in_review` entities and acceptance criteria, and a Feature by its derived state → transforms
- A generator decides presentation from the document's declared view, `inner` or `release` → `contracts/common.py::View`
  - Why: one transform then serves both views' record sets, and each generator presents them freely.

## Fields by view

| Field | Inner view | Release view |
|---|---|---|
| User Story / Functionality `state` | status badge | status badge |
| Feature `state` (derived) | status badge marked "derived" | `DEPRECATED` badge only, when deprecated |
| Feature `stub_reason` | "surface not yet instrumented: …" | hidden |
| Entity `not_in_scope`, `preconditions` | under the entity | under the entity |
| AC `not_in_scope`, `preconditions` (AC-level extension) | under the AC as "also …" | under the AC as "also …" |
| Entity / AC `deprecated` state | `DEPRECATED` badge + deprecation date + reason | `DEPRECATED` badge only |
| AC `removal_planned` | "removal planned v*X*" | "removal planned v*X*" |
| AC `planned` with a target version | "planned v*X.Y.Z*" | not applicable: filtered out |
| AC `planned` without a version | "backlog" | not applicable: filtered out |
| AC header | always the canonical rendering: `AC:<id> (v<x.y.z> - <state>)` or `AC:<id> (planned)` | same |
| AC `aspect` | aspects listed under the AC | same |
| AC `rationale`, `placeholder_values`; Functionality `rationale` | under the AC / Functionality | same |
| `source_ref.area_path`, `source_ref.iteration_path` | small text under the entity | hidden |
| `source_ref.native_type`, `source_ref.tracker_state` | hidden | hidden |

- `shown_paths(contract_id, view)` encodes which cells are shown, as field paths → `contracts/testing.py::shown_paths`
  - Why: generator tests assert against the table itself, not a copy that drifts.
- It covers the three contracts a generator renders; `ui-test-catalog` has no view-dependent field → `contracts/testing.py::shown_paths`
- The canonical AC header is rendered by the model, with the `v` added back → `contracts/common.py::AcceptanceCriterion.canonical_header`

## Coverage

Coverage is computed per aspect → `contracts/coverage_matrix.py::AcCoverage._check_status_matches_aspects`.

| Status | Means |
|---|---|
| `covered` | with aspects: every aspect has a linked scenario; without aspects: the criterion has one |
| `partially_covered` | with aspects only: some aspect has no linked scenario; a per-aspect breakdown follows |
| `not_covered` | without aspects: no linked scenario |

- An aspect's own status is `covered` or `not_covered` → `contracts/coverage_matrix.py::AspectCoverage`
- `covered` is evidence-backed: `covered` if and only if `scenario_ids` has an entry → `contracts/coverage_matrix.py::_check_status_evidence`
- Counted criteria are `active` and `deprecated`, in both views → `contracts/coverage_matrix.py::CountedState`
- A coverage matrix's `document.view` changes presentation only, never which criteria are counted.
- `in_review` criteria are not counted; a linked scenario is the warning `IN_REVIEW_AC_HAS_TESTS`, and the link is kept → `contracts/codes.py::Code`
  - Why: collection runs against `master`, where tests for work in review do not exist yet.
  - A test for one on `master` usually means the work merged and its state was not updated.
- `planned` criteria, backlog or targeted, are not counted; a linked scenario is the warning `PLANNED_AC_HAS_TESTS` → `contracts/codes.py::Code`
  - Why: tests ahead of implementation are fine; counting unbuilt work would depress the coverage figure.

## Planned work summary

- The coverage matrix always carries a planned-work summary: `total`, `backlog` and `by_target_version` → `contracts/coverage_matrix.py::PlannedSummary`
- Only the inner view renders it → `contracts/testing.py::shown_paths`
- Each planned criterion is backlog (no target version) or targets exactly one version → `contracts/coverage_matrix.py::PlannedSummary`
- So `total` equals `backlog` plus the sum of `by_target_version` → `contracts/coverage_matrix.py::PlannedSummary._check_total_equals_backlog_plus_targeted`
