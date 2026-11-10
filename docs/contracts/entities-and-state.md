# Entities and state

## Purpose

This page defines how an entity is identified, which state it has, how versions are stored, and which Azure
DevOps fields are ready.

Read before: [Documentation contracts](../contracts.md) · Next: [Schema rules](schema-rules.md)

## Contents

- [Entity identity](#entity-identity)
- [State and state origin](#state-and-state-origin)
- [Version format](#version-format)
- [Fields prepared for Azure DevOps](#fields-prepared-for-azure-devops)

## Entity identity

Every entity carries two identifiers, and they are not interchangeable.

- `entity_id` is the authored id (`US-001`, `FEAT-001`, `FUNC-001`) and the only join key
  - Why: scenario links, coverage rows and transform indexing all join on it.
- An item whose title has no parseable `entity_id` is not emitted: the collector reports `MISSING_ENTITY_ID` and counts it in `entities_skipped`
  - Why: an entity nothing can link to silently under-reports coverage; a named skip is visible.
- `source_ref` is provenance only: `system`, `native_id`, `native_type`, `url`, `tracker_state`, `area_path`, `iteration_path`
  - Why: the tracker's own id is never a join key; it lets a reader navigate back to the item.
- Cross-project identity is the pair (`metadata.source.project_id`, `entity_id`)
- An `entity_id` is unique within a project; a repeat in one run is `DUPLICATE_ENTITY_ID`, never settled by precedence
- `source_ref.tracker_state` holds the tracker's own state and never decides the documented state
  - Why: a closed issue can still be valid documentation.
- An acceptance-criterion id is its entity's id, a hyphen and a sequence number (`US-001-01`)

How a parser finds the id in a title: [Parsers, finding the entity id](../authoring/parsers.md#finding-the-entity-id).

## State and state origin

An entity's and an acceptance criterion's `state` is one of four values, as the [glossary](https://github.com/AbsaOSS/living-doc/blob/master/docs/reference/glossary.md#acceptance-criterion-ac) defines them.

| `state` | Meaning |
|---|---|
| `planned` | Agreed, not built yet; an acceptance criterion names a target version, or none (backlog) |
| `in_review` | Built on a branch, not yet accepted into `master` |
| `active` | Accepted, part of the shipped solution |
| `deprecated` | Shipped behaviour on its way out; an acceptance criterion carries `removal_planned` |

Every entity also carries `state_origin`.

| `state_origin` | Used by |
|---|---|
| `authored` | a User Story and a Functionality: a human writes the state |
| `derived` | a Feature: the state is never authored |

- The type decides the origin; any other pairing fails validation
- A written Feature status is reported as `IGNORED_AUTHORED_KEY` and dropped
  - Why: a Feature's lifecycle lives in its Functionalities and their criteria; an authored status would drift.
- A Feature that exists but is not instrumented yet says so with `stub_reason`: a fact about the surface, not a status
- `state_origin` lets a consumer tell the two apart without knowing the type; a generator marks a derived state → [Rendering](rendering.md#fields-by-view)

How the state is derived: [Parsers, status derivation](../authoring/parsers.md#status-derivation).

## Version format

- A stored version has no leading `v`: `1.4.0`, never `v1.4.0`
  - Why: a version then compares and sorts without stripping a prefix; the generator adds the `v`.
- The contract id is the one stored string with a `v`, as a literal part of the id: `doc-entities-v1.0.0`
- An author may write `V1.2` or `1.2`; normalisation reshapes it before validation → [Rule 4](../authoring/normalisation.md#rule-4-version-form)

## Fields prepared for Azure DevOps

The v1 contracts carry the fields the Azure DevOps collector needs, so it ships without a contract change.

| Field | Prepared for | Written by the GitHub collector |
|---|---|---|
| `source_ref.native_type` | work-item type | the documentation label |
| `source_ref.area_path`, `source_ref.iteration_path` | Azure DevOps classification nodes | `null` |
| `source_ref.native_id`, typed as a string | Azure DevOps ids and GitHub issue numbers in one field | the issue number, as a string |
| `metadata.source.organizations[]` | Azure DevOps organisations | every configured `organization-name` |
| `metadata.source.repositories[]` | `org/project` entries | `org/repo` |
| `metadata.source.systems` accepting `AzureDevOps` | mixed-system pipelines | only `GitHub` |
| `metadata.source.extraction_mode` | `markdown` or `field-map` extraction | `null` |
| `cardinality.entities_skipped` | work items dropped in an excluded state | items skipped for a missing entity id |

- Only the string type of `native_id` could not be deferred
  - Why: integer to string after artifacts exist is a breaking change; the two id kinds are not interchangeable.
