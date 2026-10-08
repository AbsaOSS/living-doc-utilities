# Rendering

## Purpose

Transform and generator authors read this page. It defines which field each view shows, how coverage is
counted, and how the coverage figure is computed.

Read before: [Component checks](component-checks.md) · Next: [Errors and warnings](errors.md)

## Contents

- [Records and presentation](#records-and-presentation)
- [Fields by view](#fields-by-view)
- [Coverage](#coverage)
- [Coverage summary](#coverage-summary)
- [Planned work summary](#planned-work-summary)

## Records and presentation

- Every authored field is carried at its authored level in `generator-ready`; nothing is expanded, inherited or flattened → `contracts/generator_ready.py::Content`
- A bullet-list entry may hold a nested item as extracted, on its own line and indented under its parent (`"Parent.\n  - Child."`); a generator decides how to render it ([Parsers, common behaviour](../authoring/parsers.md#common-behaviour))
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
| What was not loaded from the input (`warnings[]`) | under the entity its `entity_id` names: code, message, line, a link to the source line; once for the document when it names no entity or one the document does not hold: code, message, file, line | hidden |

- `shown_paths(contract_id, view)` encodes which cells are shown, as field paths → `contracts/testing.py::shown_paths`
  - Why: generator tests assert against the table itself, not a copy that drifts.
- What was not loaded is the canon's rule; this row only maps it onto the warning's fields ([living-doc document types, *What was not loaded*](https://github.com/AbsaOSS/living-doc/blob/master/docs/guides/living-doc-document-types.md#technical-project)) → `contracts/envelope.py::ContractWarning`
  - A warning's `ac_id` and `context` are never shown; `entity_id` only places it → `contracts/testing.py::shown_paths`
- It covers the three contracts a generator renders; `ui-test-catalog` has no view-dependent field → `contracts/testing.py::shown_paths`
- The canonical AC header is rendered by the model, with the `v` added back → `contracts/common.py::AcceptanceCriterion.canonical_header`

## Coverage

Coverage is computed per aspect → `contracts/coverage_matrix.py::AcCoverage._check_status_matches_aspects`.

| Status | Means |
|---|---|
| `covered` | with aspects: every aspect has a linked scenario; without aspects: the criterion has one |
| `partially_covered` | with aspects only: some aspects have a linked scenario, others do not |
| `not_covered` | with aspects: no aspect has a linked scenario; without aspects: the criterion has none |

- A `partially_covered` criterion shows covered/declared aspects, e.g. **1/3**, before its per-aspect breakdown → `contracts/coverage_matrix.py::AcCoverage.covered_aspects`
- A keyword criterion's breakdown is labelled with the keyword's name, its one `placeholder_values` key, not "Aspect" ([Variants](../authoring/ac-grammar.md#variants)) → generators
- A bare `@AC:<id>` link covers every aspect of the criterion: a producer lists its scenario under each aspect's `scenario_ids` (`DEC-76`) → toolkit

- An aspect's own status is `covered` or `not_covered` → `contracts/coverage_matrix.py::AspectCoverage`
- `covered` is evidence-backed by `scenario_ids` for an `AspectCoverage` and for an `AcCoverage` with no aspects: `covered` if and only if `scenario_ids` has an entry → `contracts/coverage_matrix.py::_check_status_evidence`
  - When an `AcCoverage` has aspects, its `status` is derived from the aspects instead (see table above), and its own top-level `scenario_ids` is not checked — it can be empty on a `covered` row → `contracts/testing.py::_coverage_matrix_sample`
- Counted criteria are `active` and `deprecated`, in both views → `contracts/coverage_matrix.py::CountedState`
- A coverage matrix's `document.view` changes presentation only, never which criteria are counted.
- `in_review` criteria are not counted; a linked scenario is the warning `IN_REVIEW_AC_HAS_TESTS`, and the link is kept → `contracts/codes.py::Code`
  - Why: collection runs against `master`, where tests for work in review do not exist yet.
  - A test for one on `master` usually means the work merged and its state was not updated.
- `planned` criteria, backlog or targeted, are not counted; a linked scenario is the warning `PLANNED_AC_HAS_TESTS` → `contracts/codes.py::Code`
  - Why: tests ahead of implementation are fine; counting unbuilt work would depress the coverage figure.

## Coverage summary

- Every entity and the whole matrix carry a required `summary`: `counted_acs`, `covered_acs`, `partially_covered_acs`, `not_covered_acs` and `coverage_pct` → `contracts/coverage_matrix.py::CoverageSummary`
- Each counted row weighs: `covered` 1, `not_covered` 0, `partially_covered` its covered aspects over its declared aspects → `contracts/coverage_matrix.py::AcCoverage.weight`
- `coverage_pct` is the sum of the weights over `counted_acs`, times 100 → `contracts/coverage_matrix.py::CoverageSummary.from_rows`
  - The weights are summed as exact fractions and rounded once, to one decimal, half up.
  - So `100.0` can be rounded up from 99.95 or more; full coverage is `covered_acs` equal to `counted_acs`.
  - It is `null` when `counted_acs` is 0.
- A `deprecated` row counts like an `active` one → `contracts/coverage_matrix.py::CountedState`
- The matrix summary is computed from every row of every entity, never from the entities' percentages → `contracts/coverage_matrix.py::CoverageMatrixResult._check_summary_matches_every_row`
  - Why: an entity with 1 row must not weigh as much as an entity with 10.
- Every field is recomputed from the rows; a summary that disagrees with them fails validation → `contracts/coverage_matrix.py::EntityCoverage._check_summary_matches_rows`
  - The schema carries only the fields' types and bounds ([cross-field rules](schema-rules.md#cross-field-rules)).
- A producer writes exactly what `CoverageSummary.from_rows` returns, so no generator computes a figure → `contracts/coverage_matrix.py::CoverageSummary.from_rows`
- Both views show every summary → `contracts/testing.py::shown_paths`

```python
from living_doc_utilities.contracts.coverage_matrix import AcCoverage, AspectCoverage, CoverageSummary


def aspect(name, *scenario_ids):
    status = "covered" if scenario_ids else "not_covered"
    return AspectCoverage(aspect=name, status=status, scenario_ids=list(scenario_ids))


rule = [aspect("minimum-length", "SCN-2"), aspect("character-classes"), aspect("no-username")]
rows = [
    AcCoverage(ac_id="FUNC-001-01", state="active", status="covered", scenario_ids=["SCN-1"]),
    AcCoverage(ac_id="FUNC-001-02", state="active", status="not_covered"),
    AcCoverage(ac_id="FUNC-001-03", state="active", status="partially_covered", aspects=rule),
]
summary = CoverageSummary.from_rows(rows)

assert (rows[2].covered_aspects(), len(rows[2].aspects)) == (1, 3)  # shown as 1/3
assert summary.coverage_pct == 44.4  # 1 + 0 + 1/3 over three rows
```

## Planned work summary

- The coverage matrix always carries a planned-work summary: `total`, `backlog` and `by_target_version` → `contracts/coverage_matrix.py::PlannedSummary`
- Only the inner view renders it → `contracts/testing.py::shown_paths`
- Each planned criterion is backlog (no target version) or targets exactly one version → `contracts/coverage_matrix.py::PlannedSummary`
- So `total` equals `backlog` plus the sum of `by_target_version` → `contracts/coverage_matrix.py::PlannedSummary._check_total_equals_backlog_plus_targeted`
