# Schema rules

## Purpose

This page defines the shape every exported JSON Schema follows: rules R1, R2, R3, R9 and R10.

Read before: [Entities and state](entities-and-state.md) · Next: [Artifact rules](artifact-rules.md)

## Contents

- [Generated schemas](#generated-schemas)
- [R1: a schema declares its dialect](#r1-a-schema-declares-its-dialect)
- [R2: a schema identifies itself with an id](#r2-a-schema-identifies-itself-with-an-id)
- [R3: no schema version key](#r3-no-schema-version-key)
- [R9: records are closed, maps are typed and keyed](#r9-records-are-closed-maps-are-typed-and-keyed)
- [Cross-field rules](#cross-field-rules)
- [Date-times](#date-times)
- [R10: validators are selected from the schema](#r10-validators-are-selected-from-the-schema)

## Generated schemas

- The pydantic models are the source of truth; the schemas are generated from them
- The six schemas are committed and shipped as package data in `living_doc_utilities/contracts/schemas/`
  - Why: readers outside Python and CI need a file to validate against.
- A model change without a regenerated schema fails CI
- How to regenerate: [DEVELOPER.md, Regenerate](../../DEVELOPER.md#regenerate).

## R1: a schema declares its dialect

- The first key of every schema is `"$schema": "https://json-schema.org/draft/2020-12/schema"`
- Pydantic 2 emits 2020-12 shapes (`$defs`, `anyOf`) but no `$schema`; the export step adds it
  - Why: with no declared dialect, a validator picks its own default.

## R2: a schema identifies itself with an id

- Every schema sets `$id` to `https://absaoss.github.io/living-doc-utilities/schemas/<contract-id>-schema.json`
- The `$id` is an identifier, never a fetch target; validation uses the schema bundled with the installed library
  - Why: `$id` must be a URI; a namespaced one keeps two library versions' schemas apart in a registry.

## R3: no schema version key

- No schema carries `$schema_version`, and no custom `$`-prefixed key replaces it
  - Why: validators and generic tools ignore an unknown `$` key, so a consumer never sees it.
- The contract version lives in the artifact's own `schema_version` field → [R4](artifact-rules.md#r4-a-file-declares-its-contract)

## R9: records are closed, maps are typed and keyed

Every model rejects unknown fields (`extra="forbid"`). A schema holds two kinds of object:

| Kind | Examples | Schema shape |
|---|---|---|
| Record: fixed, named properties | an entity, an acceptance criterion, `metadata`, `producer`, `document`, `selection_summary`, `planned_summary`, `cardinality` | `additionalProperties: false` |
| Map: the keys are data | `entities_by_type`, `warnings_by_code`, `field_occupancy` | typed `additionalProperties` plus `propertyNames` |

Pydantic emits a `dict[str, int]` map like this:

```json
{ "type": "object", "additionalProperties": { "type": "integer" } }
```

- `additionalProperties: false` on a map would accept only `{}`, so every artifact with stats would fail
  - Why not fixed properties: each new type, code or field path would need a hand-written schema change.

Each map constrains its keys with `propertyNames`:

| Map | `propertyNames` |
|---|---|
| the file's own `metadata.stats.field_occupancy` | an `enum` of the contract's leaf paths, generated |
| `stats.cardinality.entities_by_type` | an `enum` of the documentation types |
| `source_inputs[].stats.field_occupancy`, `selected_stats.field_occupancy` | the pattern `^[a-z][a-z0-9_]*(\[\])?(\.[a-z][a-z0-9_]*(\[\])?)*$` |
| `stats.cardinality.warnings_by_code` | the pattern `^[A-Z][A-Z0-9_]*$` |
| coverage-matrix `planned_summary.by_target_version` | the pattern `^\d+\.\d+\.\d+$` ([version format](entities-and-state.md#version-format)) |

- A file's own occupancy keys are enumerated, so a mistyped path fails validation
- The audit copies in `source_inputs[]` hold another contract's paths (R7), so they get the generic pattern
  - Why: enumerating this contract's paths there would reject every valid audit entry.
- Warning codes are defined by each collector, so they are pattern-checked, not enumerated
- Pydantic renders a pattern map as bare `patternProperties`; the export step rewrites it to typed `additionalProperties` plus `propertyNames`
  - Why: bare `patternProperties` checks only matching keys and lets every other key through (verified on Pydantic 2.13).
- There is no third kind: a test fails on any object that is neither
- Limit: a closed record rejects an unknown field, but cannot see a consumer drop a defined field; R11 and R12 cover that → [Component checks](component-checks.md)

## Cross-field rules

- A model rule JSON Schema can express is exported as `allOf` with `if`/`then`/`else`
- Each `doc-source` root's items are `allOf` the `Entity` reference and a `const` on that root's `type`
  - Why: draft-07 and OpenAPI 3.0 tools ignore keywords beside a `$ref`.
- A transform output's schema also requires at least one `source_inputs[]` entry (R7)
- Five rules stay Pydantic-only: AC ids owned by their entity, the planned-summary total, the selection-summary total, the coverage summaries recomputed from their rows, repositories naming a listed organisation
- The read and write helpers re-validate with the model after the schema, so these five still fail

## Date-times

- Every `date-time` field carries an RFC 3339 `pattern` beside its `format`, so a value needs its offset
  - Why: `format` only annotates in 2020-12; without the pattern, the schema step and outside validators accept what the model rejects.
- The pattern checks the shape only; the model rejects an impossible date, such as month 13

## R10: validators are selected from the schema

- All structural validation goes through one helper, which picks the validator class with `validator_for(schema)`
- No call site hardcodes a validator class
  - Why: a hardcoded Draft-07 validator would ignore a 2020-12-only keyword and pass files it should reject.
