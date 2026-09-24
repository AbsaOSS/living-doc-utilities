# Component checks

## Purpose

Maintainers of a collector, transform or generator read this page. It defines the checks every component's QA
runs, and the helpers in this library that run them: R12 and the lineage part of R11.

Read before: [Pipeline rules](pipeline-rules.md) · Next: [Rendering](rendering.md)

## Contents

- [R12: no component mirrors a contract](#r12-no-component-mirrors-a-contract)
- [Check 1: no vendored schemas](#check-1-no-vendored-schemas)
- [Check 2: one read path and one write path](#check-2-one-read-path-and-one-write-path)
- [Check 3: full-sample test](#check-3-full-sample-test)
- [R11: a transform proves it lost nothing](#r11-a-transform-proves-it-lost-nothing)
- [Example](#example)

## R12: no component mirrors a contract

- Outside this library, no repository commits a copy of a schema, and none defines its own contract model.
- Components import the shared models and validate against the schemas shipped in the installed library → `contracts/schema_export.py::load_schema`
- Every component's QA run carries the three checks below.
- A model-similarity heuristic, flagging models that look like contract records, was rejected.
  - Why: legitimate internal models look like records, and a mirror with renamed fields would escape it.

## Check 1: no vendored schemas

- The check fails on any git-tracked `*-schema.json` or `*.schema.json` outside `tests/` and an allow-list → `contracts/check_no_vendored_schemas.py::find_vendored_schemas`
  - Why: a vendored copy is a fork that looks like a cache; it stops tracking the library, and nothing reports it.
- Run it from a repository root: `python -m living_doc_utilities.contracts.check_no_vendored_schemas [--allow DIR]` → `contracts/check_no_vendored_schemas.py::main`
- It reads git's index, so a file not yet added is not seen → `contracts/check_no_vendored_schemas.py::find_vendored_schemas`
- This library allows only its own schema folder → `Makefile::no-vendored-schemas`

## Check 2: one read path and one write path

- Artifacts are read only with `read_artifact` and written only with `write_artifact` → `contracts/io.py::read_artifact`
- Each entry point asserts, and mypy checks, that input and result are shared contract types, never a `dict` → `contracts/registry.py::ContractResult`
  - Why: it catches a mirror model or raw-dict handling slipping back onto the data path.
- What the two helpers do: [Artifact rules, reading and writing](artifact-rules.md#reading-and-writing).

## Check 3: full-sample test

`full_sample(contract_id)` returns a valid, deterministic instance of any contract → `contracts/testing.py::full_sample`.
Its state-consistent records jointly fill every optional field:

- an active entity with every optional aspect set;
- a deprecated entity with its deprecation fields;
- a deprecated acceptance criterion with a planned-removal version;
- a planned acceptance criterion with a target version, and one without;
- a Feature with a derived state and a `stub_reason`;
- every [field prepared for Azure DevOps](entities-and-state.md#fields-prepared-for-azure-devops).

Two properties of the sample:

- No record carries a field its own state makes meaningless → `contracts/testing.py::full_sample`
  - Why: the sample stays something a real pipeline could produce.
- The sample takes no view: transforms filter it, generators set `document.view` → `contracts/testing.py::full_sample`

Each kind of component uses the sample differently:

- A transform runs over it in every view and shows no field loss (R11 below).
- A generator renders it per view and asserts what each view shows and hides → `contracts/testing.py::shown_paths`
- A collector runs over a fully authored fixture; every contract field has non-zero occupancy, bar documented exceptions.
  - Why: ordinary fixtures fill only what a test cares about; field loss hides behind them.

## R11: a transform proves it lost nothing

- Each transform declares its own lineage table in its own repository: every input path maps to an output path or to `Dropped(reason)` → `contracts/lineage.py::LineageTable`
  - Why: a table kept in another repository than its code goes stale on the first refactor.
- This library ships only the machinery; no transform's table lives here → `contracts/lineage.py::Dropped`
- `assert_complete(table, input_contract)` fails on any input leaf path the table says nothing about → `contracts/lineage.py::assert_complete`
  - Why: a newly added field cannot be forgotten.
- The transform-time check compares the input's `selected_stats` (R7) with the output's stats → `contracts/lineage.py::check_field_loss`
- A mapped path with input occupancy above 0 and output occupancy 0 is a hard `FIELD_LOSS`, naming each path → `contracts/lineage.py::check_field_loss`
- The comparison runs against the one documentation input, which makes it well defined → [One documentation source](pipeline-rules.md#one-project-one-pipeline-one-documentation-source)
- A partial drop, occupancy reduced but not to 0, is not an error at transform time; it is reported later.
  - Why: a transform cannot tell a legitimate record filter from a bug at that point.
- R11 guards transforms only; the authoring-to-collector stage has no JSON input to compare.
- That stage is guarded by golden-entity tests and snapshot CI instead → `tests/authoring/golden/test_golden_entities.py::test_golden_entities_match_hand_written_json`

## Example

```python
from living_doc_utilities.contracts.lineage import LineageTable, assert_complete
from living_doc_utilities.contracts.registry import record_roots
from living_doc_utilities.contracts.schema_export import field_occupancy_paths
from living_doc_utilities.contracts.testing import full_sample, shown_paths

sample = full_sample("generator-ready-v1.0.0")  # every optional field is set
inner = shown_paths("generator-ready-v1.0.0", "inner")
release = shown_paths("generator-ready-v1.0.0", "release")
assert "content.entities[].stub_reason" in inner - release

# A transform's own lineage table: every input leaf path is mapped (or Dropped).
paths = field_occupancy_paths(record_roots("doc-entities-v1.0.0"))
table = LineageTable({path: f"content.{path}" for path in paths})
assert_complete(table, "doc-entities-v1.0.0")
```
