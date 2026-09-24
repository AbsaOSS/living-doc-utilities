# Artifact rules

## Purpose

Anyone who reads or writes a contract file reads this page. It defines the six contract files, what each
file carries, and how it is read and written: rules R4 to R8 and the stats part of R11.

Read before: [Schema rules](schema-rules.md) · Next: [Pipeline rules](pipeline-rules.md)

## Contents

- [Contracts](#contracts)
- [R4: a file declares its contract](#r4-a-file-declares-its-contract)
- [R5: consumers check an input in a fixed order](#r5-consumers-check-an-input-in-a-fixed-order)
- [R6: every file carries a schema version and the envelope](#r6-every-file-carries-a-schema-version-and-the-envelope)
- [R7: transform provenance in source inputs](#r7-transform-provenance-in-source-inputs)
- [R8: legacy provenance shapes are retired](#r8-legacy-provenance-shapes-are-retired)
- [R11: every file carries its own stats](#r11-every-file-carries-its-own-stats)
- [The metadata envelope](#the-metadata-envelope)
- [Reading and writing](#reading-and-writing)

## Contracts

Each contract owns a file name, a contract id and one or more record roots. A record root is the array level that
holds the records; every field path starts there.

| Contract id (`schema_version`) | Artifact | Record roots | Written by | Read by |
|---|---|---|---|---|
| `doc-entities-v1.0.0` | `doc-entities.json` | `entities[]` | issue-tracker collectors | transforms |
| `doc-source-v1.0.0` | `doc-source.json` | `user_stories[]`, `features[]`, `functionalities[]` | the source-scanning collector | transforms |
| `ui-tests-v1.0.0` | `ui-tests.json` | `scenarios[]` | the source-scanning collector | transforms |
| `generator-ready-v1.0.0` | `generator-ready.json` | `content.entities[]` | transforms | generators |
| `coverage-matrix-v1.0.0` | `coverage-matrix.json` | `entities[]` | transforms | generators |
| `ui-test-catalog-v1.0.0` | `ui-test-catalog.json` | `feature_files[]` | transforms | generators |

- Each contract module declares `CONTRACT_ID` and `RECORD_ROOTS`; one registry collects them → `contracts/registry.py::CONTRACTS`
  - Why: stats, schema export and the test helpers read one declaration, so a renamed root leaves none behind.
- Both issue-tracker collectors, GitHub and Azure DevOps, write `doc-entities.json` → `contracts/doc_entities.py::DocEntitiesResult`
- The file name is the contract, never the source system; the writer is named in `metadata.producer.name` (R6) → `contracts/envelope.py::Producer`
- `generator-ready` carries the `doc-entities` entity model unchanged under `content.entities[]` → `contracts/generator_ready.py::Content`
- `ui-test-catalog` carries the `ui-tests` scenario model unchanged → `contracts/ui_test_catalog.py::FeatureFileCatalog`

## R4: a file declares its contract

- Every artifact has a required top-level `schema_version` equal to its contract id → `contracts/doc_entities.py::DocEntitiesResult`
- In the schema it is a `const`, never an `enum`; no deprecated alias is accepted → `tests/contracts/test_schema_export.py::test_schema_header_keys_match_r1_through_r4`
  - Why: an `enum` collects aliases that never go away; a `const` fails a stale producer, naming the expected id.
- Ids stay `-v1.0.0` until a v1 release; before that there is no version negotiation → [Documentation contracts, principle](../contracts.md#principle)

## R5: consumers check an input in a fixed order

A consumer decides from the file alone, never from the tool that wrote it → `contracts/compat.py::check_input`.
A contract id has the form `<contract-name>-v<major>.<minor>.<patch>` → `contracts/envelope.py::CONTRACT_ID_PATTERN`.

| Step | Check | On failure |
|---|---|---|
| 1 | `schema_version` is present and parses | hard `INVALID_CONTRACT_ID` |
| 2 | the contract is in the consumer's expected set, e.g. `doc-entities` or `doc-source` | hard `CONTRACT_MISMATCH`, naming the expected set |
| 3 | structural validation against the bundled schema | hard `SCHEMA_VALIDATION_FAILED`, naming the failing path and both utilities versions |

- The order matters: each step's message helps only once the previous step passed.
  - Why: a schema error on the wrong contract sends the reader after the wrong problem.
- Step 3 names the file's `metadata.producer.utilities_version` and the reader's own version → `contracts/compat.py::schema_validation_error`
- When the two versions differ, step 3 adds "the components run different utilities versions — align the pins" → `contracts/compat.py::schema_validation_error`
  - Why: loud and specific beats tolerant; a tolerant reader hides a skew in subtly wrong output.
- A skew that shows in the file fails at step 3: an unknown field, a missing required field, a value the schema rejects.
- A skew that leaves the file valid passes; before v1 there is no run-time alignment check.
- `metadata.producer.version` and `utilities_version` are audit information: quoted in messages, never compared → `contracts/envelope.py::Producer`
  - Why: one producer writes several contract versions; only the file's `schema_version` says it is readable.
- Keeping the fleet on one minor version is a CI job, not a reader's job → [Versioning](../api.md#versioning)

## R6: every file carries a schema version and the envelope

- Every artifact has a top-level `schema_version`, a `metadata` envelope and a `warnings[]` array → `contracts/doc_entities.py::DocEntitiesResult`
- `metadata.producer` names the tool that wrote this file, not the tool the data came from → `contracts/envelope.py::Producer`
  - Why: "which tool do I fix?" is then answerable from the file alone.
- For a transform output, the producer is the transform; upstream identity is kept in `source_inputs[]` (R7) → transforms

## R7: transform provenance in source inputs

- A transform output has one `source_inputs[]` entry per input file → `contracts/envelope.py::SourceInputEntry`
- An entry holds the input's `schema_version`, `producer`, `run`, `source`, `stats` and `selected_stats` → `contracts/envelope.py::SourceInputEntry`
- A transform output has at least one entry; a collector output carries `source_inputs: []`, never an absent key → `contracts/envelope.py::check_transform_source_inputs`
- An entry is an audit record of the input's paths, so its `field_occupancy` keys are pattern-checked (R9) → `contracts/envelope.py::AuditStats`
- `stats` covers the whole input; `selected_stats` covers the records the view filter kept → `contracts/envelope.py::SourceInputEntry`
  - Why: `stats` against `selected_stats` shows filtering; `selected_stats` against the output shows loss (R11).

## R8: legacy provenance shapes are retired

No component reads or writes these, under any historical name; closed records reject them → `contracts/common.py::ContractModel`.

- an `original_metadata` block;
- an `audit`-namespaced metadata block, including per-component entries inside it;
- a free-form trace array;
- a free-form run-context block.

The retirement has no alias window:

- A reader's fallback to a legacy field goes in the same change that adopts the envelope → transforms, generators
  - Why: a kept fallback lets a producer write the old shape unnoticed; removing the reader ends it.

## R11: every file carries its own stats

`metadata.stats` is `{cardinality, field_occupancy}` → `contracts/envelope.py::Stats`. The cardinality keys are:

| Key | Counts | Filled by |
|---|---|---|
| `entities` | entities emitted | `write_artifact` |
| `entities_by_type` | entities per documentation type (a map) | `write_artifact` |
| `acceptance_criteria` | acceptance criteria emitted | `write_artifact` |
| `scenarios` | test scenarios emitted | `write_artifact` |
| `warnings_by_code` | warnings per code (a map) | `write_artifact` |
| `sources_configured` | configured sources the run was asked to collect | the caller |
| `sources_failed` | configured sources that failed | the caller |
| `unresolved_refs` | references pointing outside the collected set | the caller |
| `entities_skipped` | records dropped before emission, e.g. no parseable entity id | the caller |

- A count that does not apply is `0`, never absent → `contracts/envelope.py::Cardinality`
- `write_artifact` computes the first five and carries the last four over from the caller → `contracts/stats.py::compute_stats`
- `field_occupancy` is keyed by record-relative path: it starts at a record root and marks each array level `[]` → `contracts/schema_export.py::field_occupancy_paths`
- `entities[].not_in_scope` and `entities[].acceptance_criteria[].not_in_scope` are two paths.
  - Why: the same field name at two levels is two different things to lose.
- `metadata`, `document` and `warnings` are not counted → `contracts/stats.py::compute_stats`
  - Why: counting them would make an envelope change look like a data change.
- A value is the number of records at that level with a non-empty value; `null`, `""`, `[]` and `{}` are empty → `contracts/stats.py::_is_empty`
- How a transform proves it lost nothing: [Component checks, R11](component-checks.md#r11-a-transform-proves-it-lost-nothing).

## The metadata envelope

`metadata` is one model shared by all six contracts; only the `field_occupancy` key enum differs → `contracts/envelope.py::Metadata`.

| Field | Holds | In code |
|---|---|---|
| `producer` | `name`, `version`, `build`, `utilities_version` of the writing tool (R6) | `contracts/envelope.py::Producer` |
| `run` | `run_id`, `run_attempt`, `actor`, `workflow`, `ref`, `sha`; audit only | `contracts/envelope.py::Run` |
| `source` | `project_id`, `systems`, `organizations`, `repositories`, `extraction_mode` | `contracts/envelope.py::Source` |
| `generated_at` | when the file was written | `contracts/envelope.py::Metadata` |
| `stats` | the file's own stats (R11) | `contracts/envelope.py::Stats` |
| `source_inputs` | one entry per transform input (R7) | `contracts/envelope.py::SourceInputEntry` |

- One model means an envelope fix lands in all six contracts at once → `tests/contracts/test_schema_export.py::test_metadata_is_one_shared_model_across_all_six_contracts`
- `source` is required on every output, and `source.project_id` everywhere → `contracts/envelope.py::Source`
- A transform output copies `source` from its one documentation input, plus the test input's systems.
- `source.systems` values are `GitHub` and `AzureDevOps`; `extraction_mode` is `markdown`, `field-map` or `null` → `contracts/envelope.py::Source`
- `organizations[]` lists every configured `organization-name` once; an organisation may have no repository → `contracts/envelope.py::Source`
- `repositories[]` entries are `org/repo` (GitHub) or `org/project` (Azure DevOps), and each `org` is in `organizations[]` → `contracts/envelope.py::Source._check_repositories_reference_known_organizations`
- `document` exists only on `generator-ready`, `coverage-matrix` and `ui-test-catalog`, and holds `document.view` → `contracts/common.py::ViewDocument`
- `generator-ready`'s `document` adds `title`, `version` and `selection_summary` → `contracts/generator_ready.py::Document`
- In `selection_summary`, `total_entities` equals `included_entities` plus `excluded_entities` → `contracts/generator_ready.py::SelectionSummary`

A collector output's `metadata`:

<!-- example: contracts/envelope.py::Metadata -->
```json
{
  "producer": {"name": "AbsaOSS/living-doc-collector-gh", "version": "0.2.0", "utilities_version": "0.5.0"},
  "run": {"run_id": "1234", "workflow": "docs", "ref": "refs/heads/master", "sha": "3f2c1ab"},
  "source": {
    "project_id": "payments",
    "systems": ["GitHub"],
    "organizations": ["absa"],
    "repositories": ["absa/payments-web"],
    "extraction_mode": null
  },
  "generated_at": "2026-10-01T12:00:00Z",
  "stats": {
    "cardinality": {"entities": 2, "entities_by_type": {"DocumentedUserStory": 2}, "acceptance_criteria": 5,
                    "scenarios": 0, "warnings_by_code": {"MISSING_STATUS": 1}, "sources_configured": 1,
                    "sources_failed": 0, "unresolved_refs": 0, "entities_skipped": 0},
    "field_occupancy": {"entities[].not_in_scope": 1}
  },
  "source_inputs": []
}
```

## Reading and writing

- `read_artifact(path, expected)` loads the file, runs R5 and returns the typed model, never a `dict` → `contracts/io.py::read_artifact`
- `write_artifact(result, path)` fills `metadata.stats` and `producer.utilities_version`, then validates in memory → `contracts/io.py::write_artifact`
- It writes to a temporary file in the destination directory, then renames it atomically, with LF line endings → `contracts/io.py::write_artifact`
- A failed validation leaves no file on disk → `contracts/io.py::write_artifact`
  - Why: a later step can never pick up a half-written or invalid artifact from a failed run.
- These two are the only sanctioned read and write paths (R12) → [Component checks](component-checks.md#check-2-one-read-path-and-one-write-path)

```python
from living_doc_utilities.contracts.codes import ContractError
from living_doc_utilities.contracts.io import read_artifact, write_artifact
from living_doc_utilities.contracts.testing import full_sample

write_artifact(full_sample("doc-entities-v1.0.0"), "out/doc-entities.json")  # fills stats and producer version

result = read_artifact("out/doc-entities.json", expected={"doc-entities", "doc-source"})

try:
    read_artifact("out/doc-entities.json", expected="ui-tests")
except ContractError as error:
    assert error.code.name == "CONTRACT_MISMATCH"
```
