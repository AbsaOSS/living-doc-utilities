# Schema rules

## Purpose

Anyone who changes a contract model reads this page. It defines the shape every exported JSON Schema follows:
rules R1, R2, R3, R9 and R10.

Read before: [Entities and state](entities-and-state.md) · Next: [Artifact rules](artifact-rules.md)

## Contents

- [Generated schemas](#generated-schemas)
- [R1: a schema declares its dialect](#r1-a-schema-declares-its-dialect)
- [R2: a schema identifies itself with an id](#r2-a-schema-identifies-itself-with-an-id)
- [R3: no schema version key](#r3-no-schema-version-key)
- [R9: records are closed, maps are typed and keyed](#r9-records-are-closed-maps-are-typed-and-keyed)
- [Cross-field rules](#cross-field-rules)
- [R10: validators are selected from the schema](#r10-validators-are-selected-from-the-schema)

## Generated schemas

- The pydantic models are the source of truth; the schemas are generated from them → `contracts/schema_export.py::generate_schema`
- The six schemas are committed and shipped as package data in `living_doc_utilities/contracts/schemas/` → `contracts/schema_export.py::SCHEMAS_DIR`
  - Why: readers outside Python and CI need a file to validate against.
- A model change without a regenerated schema fails CI → `tests/contracts/test_schema_export.py::test_committed_schema_is_up_to_date`
- How to regenerate: [DEVELOPER.md, Regenerate](../../DEVELOPER.md#regenerate).

## R1: a schema declares its dialect

- The first key of every schema is `"$schema": "https://json-schema.org/draft/2020-12/schema"` → `contracts/schema_export.py::SCHEMA_DIALECT`
- Pydantic 2 emits 2020-12 shapes (`$defs`, `anyOf`) but no `$schema`; the export step adds it → `contracts/schema_export.py::generate_schema`
  - Why: with no declared dialect, a validator picks its own default.

## R2: a schema identifies itself with an id

- Every schema sets `$id` to `https://absaoss.github.io/living-doc-utilities/schemas/<contract-id>-schema.json` → `contracts/schema_export.py::ID_TEMPLATE`
- The `$id` is an identifier, never a fetch target; validation uses the schema bundled with the installed library → `contracts/schema_export.py::load_schema`
  - Why: `$id` must be a URI; a namespaced one keeps two library versions' schemas apart in a registry.

## R3: no schema version key

- No schema carries `$schema_version`, and no custom `$`-prefixed key replaces it → `tests/contracts/test_schema_export.py::test_no_schema_version_dollar_key_anywhere_in_the_package`
  - Why: validators and generic tools ignore an unknown `$` key, so a consumer never sees it.
- The contract version lives in the artifact's own `schema_version` field → [R4](artifact-rules.md#r4-a-file-declares-its-contract)

## R9: records are closed, maps are typed and keyed

Every model rejects unknown fields (`extra="forbid"`) → `contracts/common.py::ContractModel`. A schema holds two kinds of object:

| Kind | Examples | Schema shape |
|---|---|---|
| Record: fixed, named properties | an entity, an acceptance criterion, `metadata`, `producer`, `document`, `selection_summary`, `planned_summary`, `cardinality` | `additionalProperties: false` |
| Map: the keys are data | `entities_by_type`, `warnings_by_code`, `field_occupancy` | typed `additionalProperties` plus `propertyNames` |

Pydantic emits a `dict[str, int]` map like this:

```json
{ "type": "object", "additionalProperties": { "type": "integer" } }
```

- `additionalProperties: false` on a map would accept only `{}`, so every artifact with stats would fail.
  - Why not fixed properties: each new type, code or field path would need a hand-written schema change.

Each map constrains its keys with `propertyNames`:

| Map | `propertyNames` | In code |
|---|---|---|
| the file's own `metadata.stats.field_occupancy` | an `enum` of the contract's leaf paths, generated | `contracts/schema_export.py::_inject_own_field_occupancy_enum` |
| `stats.cardinality.entities_by_type` | an `enum` of the documentation types | `contracts/common.py::DocType` |
| `source_inputs[].stats.field_occupancy`, `selected_stats.field_occupancy` | the pattern `^[a-z][a-z0-9_]*(\[\])?(\.[a-z][a-z0-9_]*(\[\])?)*$` | `contracts/envelope.py::AUDIT_FIELD_PATH_PATTERN` |
| `stats.cardinality.warnings_by_code` | the pattern `^[A-Z][A-Z0-9_]*$` | `contracts/envelope.py::WARNING_CODE_PATTERN` |
| coverage-matrix `planned_summary.by_target_version` | the pattern `^\d+\.\d+\.\d+$` ([version format](entities-and-state.md#version-format)) | `contracts/common.py::VERSION_PATTERN` |

- A file's own occupancy keys are enumerated, so a mistyped path fails validation → `tests/contracts/test_schema_export.py::test_mistyped_path_in_own_field_occupancy_fails_schema_validation`
- The audit copies in `source_inputs[]` hold another contract's paths (R7), so they get the generic pattern → `tests/contracts/test_schema_export.py::test_another_contracts_path_inside_source_inputs_audit_field_occupancy_passes`
  - Why: enumerating this contract's paths there would reject every valid audit entry.
- Warning codes are defined by each collector, so they are pattern-checked, not enumerated → `contracts/envelope.py::WARNING_CODE_PATTERN`
- Pydantic renders a pattern map as bare `patternProperties`; the export step rewrites it to typed `additionalProperties` plus `propertyNames` → `contracts/schema_export.py::_rewrite_pattern_maps`
  - Why: bare `patternProperties` checks only matching keys and lets every other key through (verified on Pydantic 2.13).
- There is no third kind: a test fails on any object that is neither → `contracts/schema_export.py::find_schema_violations`
- Limit: a closed record rejects an unknown field, but cannot see a consumer drop a defined field; R11 and R12 cover that → [Component checks](component-checks.md)

## Cross-field rules

- A model rule JSON Schema can express is exported as `allOf` with `if`/`then`/`else` → `contracts/schema_export.py::_CROSS_FIELD_RULES`
- A transform output's schema also requires at least one `source_inputs[]` entry (R7) → `contracts/schema_export.py::_inject_cross_field_constraints`
- Four rules stay Pydantic-only: AC ids owned by their entity, the planned-summary total, the selection-summary total, repositories naming a listed organisation → `contracts/schema_export.py::_inject_cross_field_constraints`
- The read and write helpers re-validate with the model after the schema, so these four still fail → `contracts/io.py::_model_validate_or_raise`

## R10: validators are selected from the schema

- All structural validation goes through one helper, which picks the validator class with `validator_for(schema)` → `contracts/validation.py::validate`
- No call site hardcodes a validator class → `contracts/validation.py::validate`
  - Why: a hardcoded Draft-07 validator would ignore a 2020-12-only keyword and pass files it should reject.
