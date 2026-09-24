# Documentation contracts

## Purpose

Anyone who reads or writes a contract file starts here. This page names the six contracts, states the principle
and every contract rule in one line, and links to the page that defines each rule.

Read before: [README](../README.md) · Next: [Entities and state](contracts/entities-and-state.md)

## Contents

- [Principle](#principle)
- [Contracts](#contracts)
- [Rules](#rules)
- [Pages](#pages)

## Principle

The pydantic models are the source of truth; the JSON Schemas are generated from them. A rule number is a
stable id quoted in code, and a rule's rationale is part of the contract. A reader decides from the file alone
whether it can read it, never from the tool that wrote it. Before v1 there is no digest and no version range: a
skew fails loudly, naming both library versions. After v1, contracts get an interval check in R5 step 2 instead.

## Contracts

Six contracts are exchanged; [Artifact rules, contracts](contracts/artifact-rules.md#contracts) defines their files and record roots.

- `doc-entities-v1.0.0`, issue-tracker collector output → `contracts/doc_entities.py::CONTRACT_ID`
- `doc-source-v1.0.0`, source-scanning collector output → `contracts/doc_source.py::CONTRACT_ID`
- `ui-tests-v1.0.0`, source-scanning collector output → `contracts/ui_tests.py::CONTRACT_ID`
- `generator-ready-v1.0.0`, transform output → `contracts/generator_ready.py::CONTRACT_ID`
- `coverage-matrix-v1.0.0`, transform output → `contracts/coverage_matrix.py::CONTRACT_ID`
- `ui-test-catalog-v1.0.0`, transform output → `contracts/ui_test_catalog.py::CONTRACT_ID`

## Rules

Each line names a rule, where the code realises it, and the page that defines it. Numbers are ids, not an order.

- R1: a schema declares its dialect → `contracts/schema_export.py::SCHEMA_DIALECT` · [schema rules](contracts/schema-rules.md#r1-a-schema-declares-its-dialect)
- R2: a schema identifies itself with `$id` → `contracts/schema_export.py::ID_TEMPLATE` · [schema rules](contracts/schema-rules.md#r2-a-schema-identifies-itself-with-an-id)
- R3: no `$schema_version` key → `tests/contracts/test_schema_export.py::test_no_schema_version_dollar_key_anywhere_in_the_package` · [schema rules](contracts/schema-rules.md#r3-no-schema-version-key)
- R4: a file declares its contract in `schema_version` → `contracts/doc_entities.py::DocEntitiesResult` · [artifact rules](contracts/artifact-rules.md#r4-a-file-declares-its-contract)
- R5: consumers check an input in a fixed order → `contracts/compat.py::check_input` · [artifact rules](contracts/artifact-rules.md#r5-consumers-check-an-input-in-a-fixed-order)
- R6: every file carries `schema_version` and the metadata envelope → `contracts/envelope.py::Metadata` · [artifact rules](contracts/artifact-rules.md#r6-every-file-carries-a-schema-version-and-the-envelope)
- R7: transform provenance in `metadata.source_inputs[]` → `contracts/envelope.py::SourceInputEntry` · [artifact rules](contracts/artifact-rules.md#r7-transform-provenance-in-source-inputs)
- R8: legacy provenance shapes are retired outright → `contracts/common.py::ContractModel` · [artifact rules](contracts/artifact-rules.md#r8-legacy-provenance-shapes-are-retired)
- R9: records are closed; maps are typed and keyed → `contracts/schema_export.py::find_schema_violations` · [schema rules](contracts/schema-rules.md#r9-records-are-closed-maps-are-typed-and-keyed)
- R10: validators are selected from the schema → `contracts/validation.py::validate` · [schema rules](contracts/schema-rules.md#r10-validators-are-selected-from-the-schema)
- R11: every file carries its own stats → `contracts/stats.py::compute_stats` · [artifact rules](contracts/artifact-rules.md#r11-every-file-carries-its-own-stats)
- R11: a transform proves it lost nothing → `contracts/lineage.py::check_field_loss` · [component checks](contracts/component-checks.md#r11-a-transform-proves-it-lost-nothing)
- R12: no component mirrors a contract; each proves it carries every field → `contracts/testing.py::full_sample` · [component checks](contracts/component-checks.md#r12-no-component-mirrors-a-contract)
- R13: a collector collects everything it was configured for, or fails → `github/decorators.py::safe_call_decorator` · [pipeline rules](contracts/pipeline-rules.md#r13-a-collector-collects-everything-it-was-configured-for-or-fails)

Named rules:

- Each contract declares its record roots in its own module → `contracts/registry.py::CONTRACTS` · [artifact rules](contracts/artifact-rules.md#contracts)
- Entity identity: `entity_id` joins, `source_ref` only points back → `contracts/common.py::EntityCore` · [entities and state](contracts/entities-and-state.md#entity-identity)
- State and `state_origin`: a Feature's state is always derived → `contracts/doc_entities.py::Entity._check_state_origin` · [entities and state](contracts/entities-and-state.md#state-and-state-origin)
- Version format: no leading `v` in a stored version → `contracts/common.py::VERSION_PATTERN` · [entities and state](contracts/entities-and-state.md#version-format)
- Fields prepared for Azure DevOps → `contracts/common.py::SourceRef` · [entities and state](contracts/entities-and-state.md#fields-prepared-for-azure-devops)
- The metadata envelope is one model for all six contracts → `contracts/envelope.py::Metadata` · [artifact rules](contracts/artifact-rules.md#the-metadata-envelope)
- One read path and one write path → `contracts/io.py::write_artifact` · [artifact rules](contracts/artifact-rules.md#reading-and-writing)
- One project, one pipeline, one documentation source → toolkit · [pipeline rules](contracts/pipeline-rules.md#one-project-one-pipeline-one-documentation-source)
- Project id → `contracts/envelope.py::PROJECT_ID_PATTERN` · [pipeline rules](contracts/pipeline-rules.md#project-id)
- Collector output layout → collectors · [pipeline rules](contracts/pipeline-rules.md#collector-output-layout)
- Rendering rules: the view filter selects records, the generator presents → `contracts/testing.py::shown_paths` · [rendering](contracts/rendering.md#fields-by-view)
- Coverage is computed per aspect and backed by evidence → `contracts/coverage_matrix.py::AcCoverage` · [rendering](contracts/rendering.md#coverage)
- Errors and warnings: one registry, one page → `contracts/codes.py::ALL_CODES` · [errors](contracts/errors.md#codes)

## Pages

Read in this order; each page defines its facts once.

| Page | Defines |
|---|---|
| [Entities and state](contracts/entities-and-state.md) | identity, `state` / `state_origin`, version format, Azure DevOps fields |
| [Schema rules](contracts/schema-rules.md) | R1, R2, R3, R9, R10: the shape of every exported schema |
| [Artifact rules](contracts/artifact-rules.md) | the contract table, R4 to R8, R11 stats, the envelope, reading and writing |
| [Pipeline rules](contracts/pipeline-rules.md) | project scope, project id, output layout, R13 and retries |
| [Component checks](contracts/component-checks.md) | R12 checks and helpers, R11 lineage and field loss |
| [Rendering](contracts/rendering.md) | fields by view, coverage, planned work summary |
| [Errors and warnings](contracts/errors.md) | every code, the validation order |
