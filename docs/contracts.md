# Documentation contracts

## Purpose

This page is the hub of the contract rules: it names the six contracts, states the principle and every contract
rule in one line, and links to the page that defines each rule.

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

- `doc-entities-v1.0.0`, issue-tracker collector output
- `doc-source-v1.0.0`, source-scanning collector output
- `ui-tests-v1.0.0`, source-scanning collector output
- `generator-ready-v1.0.0`, transform output
- `coverage-matrix-v1.0.0`, transform output
- `ui-test-catalog-v1.0.0`, transform output

## Rules

Each line names a rule and the page that defines it. Numbers are ids, not an order.

- R1: a schema declares its dialect · [schema rules](contracts/schema-rules.md#r1-a-schema-declares-its-dialect)
- R2: a schema identifies itself with `$id` · [schema rules](contracts/schema-rules.md#r2-a-schema-identifies-itself-with-an-id)
- R3: no `$schema_version` key · [schema rules](contracts/schema-rules.md#r3-no-schema-version-key)
- R4: a file declares its contract in `schema_version` · [artifact rules](contracts/artifact-rules.md#r4-a-file-declares-its-contract)
- R5: consumers check an input in a fixed order · [artifact rules](contracts/artifact-rules.md#r5-consumers-check-an-input-in-a-fixed-order)
- R6: every file carries `schema_version` and the metadata envelope · [artifact rules](contracts/artifact-rules.md#r6-every-file-carries-a-schema-version-and-the-envelope)
- R7: transform provenance in `metadata.source_inputs[]` · [artifact rules](contracts/artifact-rules.md#r7-transform-provenance-in-source-inputs)
- R8: legacy provenance shapes are retired outright · [artifact rules](contracts/artifact-rules.md#r8-legacy-provenance-shapes-are-retired)
- R9: records are closed; maps are typed and keyed · [schema rules](contracts/schema-rules.md#r9-records-are-closed-maps-are-typed-and-keyed)
- R10: validators are selected from the schema · [schema rules](contracts/schema-rules.md#r10-validators-are-selected-from-the-schema)
- R11: every file carries its own stats · [artifact rules](contracts/artifact-rules.md#r11-every-file-carries-its-own-stats)
- R11: a transform proves it lost nothing · [component checks](contracts/component-checks.md#r11-a-transform-proves-it-lost-nothing)
- R12: no component mirrors a contract; each proves it carries every field · [component checks](contracts/component-checks.md#r12-no-component-mirrors-a-contract)
- R13: a collector collects everything it was configured for, or fails · [pipeline rules](contracts/pipeline-rules.md#r13-a-collector-collects-everything-it-was-configured-for-or-fails)

Named rules:

- Each contract declares its record roots in its own module · [artifact rules](contracts/artifact-rules.md#contracts)
- Entity identity: `entity_id` joins, `source_ref` only points back · [entities and state](contracts/entities-and-state.md#entity-identity)
- State and `state_origin`: a Feature's state is always derived · [entities and state](contracts/entities-and-state.md#state-and-state-origin)
- Version format: no leading `v` in a stored version · [entities and state](contracts/entities-and-state.md#version-format)
- Fields prepared for Azure DevOps · [entities and state](contracts/entities-and-state.md#fields-prepared-for-azure-devops)
- The metadata envelope is one model for all six contracts · [artifact rules](contracts/artifact-rules.md#the-metadata-envelope)
- One read path and one write path · [artifact rules](contracts/artifact-rules.md#reading-and-writing)
- One project, one pipeline, one documentation source → toolkit · [pipeline rules](contracts/pipeline-rules.md#one-project-one-pipeline-one-documentation-source)
- Project id · [pipeline rules](contracts/pipeline-rules.md#project-id)
- Collector output layout → collectors · [pipeline rules](contracts/pipeline-rules.md#collector-output-layout)
- Rendering rules: the view filter selects records, the generator presents · [rendering](contracts/rendering.md#fields-by-view)
- Coverage is computed per aspect and backed by evidence · [rendering](contracts/rendering.md#coverage)
- Every entity and the whole matrix carry a coverage summary computed from the rows · [rendering](contracts/rendering.md#coverage-summary)
- Errors and warnings: one registry, one page · [errors](contracts/errors.md#codes)

## Pages

Read in this order; each page defines its facts once.

| Page | Defines |
|---|---|
| [Entities and state](contracts/entities-and-state.md) | identity, `state` / `state_origin`, version format, Azure DevOps fields |
| [Schema rules](contracts/schema-rules.md) | R1, R2, R3, R9, R10: the shape of every exported schema |
| [Artifact rules](contracts/artifact-rules.md) | the contract table, R4 to R8, R11 stats, the envelope, reading and writing |
| [Pipeline rules](contracts/pipeline-rules.md) | project scope, project id, output layout, R13 and retries |
| [Component checks](contracts/component-checks.md) | R12 checks and helpers, R11 lineage and field loss |
| [Rendering](contracts/rendering.md) | fields by view, coverage, coverage summary, planned work summary |
| [Errors and warnings](contracts/errors.md) | every code, the validation order |
