# Documentation contracts

This file holds the normative rules for the six documentation contracts exchanged by the
Living Documentation ecosystem. Every collector, transform and generator writes and reads
artifacts that obey the rules below; `living-doc-utilities` owns the models, the exported
JSON Schemas, and the shared helpers that enforce them. Each contract's fields — names, types,
required or optional — are defined by its model and the JSON Schema generated from it.

Two reading notes:

- **The rationale is part of the contract.** Several rules exist because a specific failure
  was observed in a real pipeline run. A change that keeps a rule's letter while discarding
  its reason is a contract change, not a refactor.
- **Rule numbers are stable identifiers, not an order.** Rules are grouped below by what they
  govern (schema authoring, artifacts, alignment), so the numbering inside a section is not
  sequential. A rule is quoted by its number in code comments and error messages, and keeps
  that number wherever it is moved.

Contents:

- [1. Contracts](#1-contracts)
- [2. Schema authoring rules](#2-schema-authoring-rules)
- [3. Artifact rules](#3-artifact-rules)
- [4. Rendering rules](#4-rendering-rules)
- [5. Errors and warnings](#5-errors-and-warnings)
- [6. Alignment](#6-alignment)

## 1. Contracts

There are six contracts. Each one owns an artifact file name, a contract id, and one or more
**record roots** — the array levels that hold the contract's records, and the anchor for every
field path in this document.

| Contract id | Artifact | Record root(s) | Written by | Read by |
|---|---|---|---|---|
| `doc-entities-v1.0.0` | `doc-entities.json` | `entities[]` | issue-tracker collectors | transforms |
| `doc-source-v1.0.0` | `doc-source.json` | `user_stories[]`, `features[]`, `functionalities[]` | the source-scanning collector | transforms |
| `ui-tests-v1.0.0` | `ui-tests.json` | `scenarios[]` | the source-scanning collector | transforms |
| `generator-ready-v1.0.0` | `generator-ready.json` | `content.entities[]` | transforms | generators |
| `coverage-matrix-v1.0.0` | `coverage-matrix.json` | declared in `living_doc_utilities.contracts.coverage_matrix` | transforms | generators |
| `ui-test-catalog-v1.0.0` | `ui-test-catalog.json` | declared in `living_doc_utilities.contracts.ui_test_catalog` | transforms | generators |

Both issue-tracker collectors — GitHub and Azure DevOps — write `doc-entities.json`. The file
name is the contract, never the source system; producer identity lives in
`metadata.producer.name` instead (R6).

Each contract **declares its own record roots in its contract module**. The stats helper (R11),
the schema-export step (R9) and the shared test helpers (R12) all read the declaration from that
one place, so adding or renaming a record root cannot leave one of them behind.

### Entity identity

Every entity carries two identifiers, and they are not interchangeable.

- **`entity_id`** — the authored id: `US-001`, `FEAT-001`, `FUNC-001`. This is the join key for
  everything downstream: scenario links, coverage rows, transform indexing. An item whose title
  carries no parseable `entity_id` is **not emitted** — the collector reports `MISSING_ENTITY_ID`
  and counts it in `cardinality.entities_skipped`. Emitting an entity that nothing can link to
  produces a document that silently under-reports coverage, which is worse than a named skip.
- **`source_ref`** — provenance only:
  `{system, native_id, native_type, url, tracker_state, area_path, iteration_path}`. The tracker's
  own id is never a join key; it is there so a reader can navigate back to the item.

Cross-project identity is the pair (`metadata.source.project_id`, `entity_id`). An `entity_id` is
unique **within a project**, which is why the same id appearing twice in one run is an input error
(`DUPLICATE_ENTITY_ID`) rather than something a precedence rule resolves.

`source_ref.tracker_state` holds the tracker's own state — `open` / `closed`, or the Azure DevOps
work-item state. It is informational: a closed issue can be perfectly valid documentation, so
tracker state never decides an entity's documented state.

### State and `state_origin`

An entity's `state` is one of `planned`, `in_review`, `active`, `deprecated`. Every entity also
carries **`state_origin`**:

- `authored` — for a User Story and a Functionality, whose state is written by a human.
- `derived` — for a Feature, whose state is **never** authored.

A Feature is the structural node of a visible surface (a page, an API). Its behaviour — and
therefore its lifecycle — lives in its Functionalities and their acceptance criteria, so an
authored Feature status would be a second, drifting source of truth. A written Feature status is
reported as `IGNORED_AUTHORED_KEY` and dropped. A Feature that exists but is not yet instrumented
says so with **`stub_reason`**, which is a fact about the surface, not a status.

`state_origin` exists so a consumer can tell the two apart without knowing the entity type, and so
a generator can mark a derived state as derived (section 4).

### Version format

Every authored version value is stored **without a leading `v`**: `1.4.0`, never `v1.4.0`. The `v`
is a rendering convention added by the generator, so that a version can be compared and sorted
without stripping a prefix first.

The one place a `v` is part of a stored string is the contract id itself — `doc-entities-v1.0.0` —
where it is a literal part of the id, not a version field.

### Fields prepared for Azure DevOps

The v1 contracts carry the fields the Azure DevOps collector needs, so that collector can ship
without a contract change and without a coordinated fleet upgrade. The GitHub collector fills some
of them; the rest stay unused until the Azure DevOps collector fills them.

| Field | Prepared for | Written by the GitHub collector |
|---|---|---|
| `source_ref.native_type` | work-item type | populated — the documentation label |
| `source_ref.area_path`, `source_ref.iteration_path` | Azure DevOps classification nodes | `null` |
| `source_ref.native_id` **typed as a string** | Azure DevOps ids and GitHub issue numbers in one field | populated, as a string — a number is never written |
| `metadata.source.organizations[]` | Azure DevOps organisations | populated — every configured `organization-name` |
| `metadata.source.repositories[]` | `org/project` entries | populated, as `org/repo` |
| `metadata.source.systems` accepting `AzureDevOps` | mixed-system pipelines | only `GitHub` appears |
| `metadata.source.extraction_mode` | `markdown` or `field-map` extraction | `null` |
| `cardinality.entities_skipped` | work items dropped in an excluded state | populated — items skipped for a missing entity id |

Of these, only typing `native_id` as a string could not be deferred: changing a field from integer to
string after artifacts exist is a breaking schema change, and Azure DevOps ids are not
interchangeable with GitHub issue numbers.

## 2. Schema authoring rules

These rules govern the JSON Schemas exported from the contract models. The models are the source of
truth; the schemas are generated from them by the schema-export step and committed in
`living-doc-utilities` so that non-Python readers and CI have something to validate against.

### R1 — a schema declares its dialect

The first key of every exported schema is:

```json
"$schema": "https://json-schema.org/draft/2020-12/schema"
```

Pydantic 2 emits 2020-12-shaped output — `$defs`, `anyOf` — but does **not** emit `$schema` itself.
A schema whose dialect is undeclared is at the mercy of whichever default a validator picks, so the
schema-export step adds the key explicitly rather than relying on a downstream guess.

### R2 — a schema identifies itself with `$id`

Every schema sets:

```text
$id: https://absaoss.github.io/living-doc-utilities/schemas/<contract-id>-schema.json
```

This is an **identifier, never a fetch target**. Nothing in the pipeline resolves it over the
network; validation always runs against the schema bundled with the installed library. The URL form
is used because `$id` must be a URI, and a stable namespaced one keeps two schemas from two library
versions distinguishable in a validator's registry.

### R3 — `$schema_version` is abolished

No schema carries a `$schema_version` key, and **no custom `$`-prefixed key replaces it**. A
`$`-prefixed key that is not a JSON Schema keyword is invisible to validators and silently ignored
by every generic tool, which makes it exactly the wrong place for something a consumer must act on.
The contract version lives in the artifact's own top-level `schema_version` field (R4), where it is
a validated, required part of the data.

### R9 — every record object sets `additionalProperties: false`; every map is typed and keyed

Models use `extra="forbid"`. There are exactly **two** kinds of object in these schemas.

**Record objects** — objects with fixed, named properties: an entity, an acceptance criterion,
`metadata`, `producer`, `document`, `document.selection_summary`, `stats.cardinality`. These get
`additionalProperties: false`.

**Maps** — objects whose *keys are data*: `stats.cardinality.entities_by_type`,
`stats.cardinality.warnings_by_code`, `stats.field_occupancy`. Pydantic emits a `dict[str, int]` as:

```json
{ "type": "object", "additionalProperties": { "type": "integer" } }
```

For a map, `additionalProperties: false` would be a disaster in the literal sense: it accepts only
`{}`, so **every artifact that has stats would fail its pre-write validation**. The alternative —
enumerating fixed properties — would turn every new documentation type, every new warning code and
every new field path into a hand-written schema change.

So maps keep **typed `additionalProperties`** plus **`propertyNames`**, which constrains the keys
without enumerating them as properties:

| Map | `propertyNames` |
|---|---|
| own `metadata.stats.field_occupancy` | an **`enum`**, generated by the schema-export step, of that contract's leaf paths |
| `stats.cardinality.entities_by_type` | an **`enum`** of the documentation types |
| `metadata.source_inputs[].stats.field_occupancy` and `selected_stats.field_occupancy` | a **pattern**: `^[a-z][a-z0-9_]*(\[\])?(\.[a-z][a-z0-9_]*(\[\])?)*$` |
| `stats.cardinality.warnings_by_code` | a **pattern**: `^[A-Z][A-Z0-9_]*$` |

The enum-versus-pattern split is the point of the rule. A file's **own** `field_occupancy` keys are
paths of that file's own contract, so they can be enumerated exactly — and a mistyped path then
fails validation instead of quietly counting nothing. The `source_inputs[]` and `selected_stats`
copies are an **audit record of another contract's paths** (R7), so enumerating this contract's
paths there would reject every valid audit entry; they get the generic path pattern instead, which
still catches a malformed path. Warning codes are defined by each collector, so they are
pattern-checked, not enumerated.

**Pattern maps need post-processing.** Pydantic renders a pattern-keyed map as `patternProperties`,
with neither `additionalProperties` nor `propertyNames` (verified against Pydantic 2.13). A bare
`patternProperties` constrains only the values of *matching* keys and silently permits every
non-matching key — the opposite of the intent. The schema-export step therefore rewrites that shape
into typed `additionalProperties` plus `propertyNames: {pattern}`.

**There is no third kind.** A test walks every exported schema and fails on any object that has
neither `additionalProperties: false` nor typed `additionalProperties` together with
`propertyNames`. Untyped or `true` `additionalProperties`, and bare `patternProperties`, never
appear in a published schema.

One limit, stated here so it is not assumed away: `additionalProperties: false` makes a producer's
pre-write validation reject an undefined field, and makes consumer validation (R5 step 3) reject a
file carrying unknown fields. It **cannot** detect a consumer silently *dropping* a field that is
defined and populated. That failure mode is covered by R11 and R12 instead.

### R10 — validators are selected from the schema

All structural validation goes through one shared helper that selects the validator class with
`jsonschema.validators.validator_for(schema)`. No call site hardcodes a validator class.

Draft-07 and 2020-12 agree on every keyword these schemas use today, so this rule buys nothing right
now — which is precisely why it is written down. The day a schema starts using a 2020-12-only
keyword, a hardcoded Draft-07 validator would not fail; it would **ignore the keyword** and pass
files it should have rejected. Selecting the validator from the schema's declared dialect (R1) makes
that impossible.

### R12 — no component mirrors a contract; each proves it carries every field

Outside `living-doc-utilities`, no repository commits a copy of a schema and none defines its own
contract model. Components import the shared contract models and validate against the schemas
shipped inside the installed library. Three checks belong in **every** component's QA run.

**1. No vendored schemas.** A check fails on any committed `*-schema.json` or `*.schema.json`
outside test directories and an explicit allow-list. Only `living-doc-utilities` keeps the canonical
schemas. A vendored copy is a fork that looks like a cache: it stops tracking the library the moment
the library changes, and nothing reports it.

**2. One read path, one write path, typed.** Artifacts are read only through the one shared read
helper and written only through the one shared write helper. Every entry point asserts — and `mypy`
checks — that both its input and its result are the shared contract types, never a raw `dict`. This
check exists to catch a mirror model or raw-dict handling slipping back onto the data path, which is
the exact defect the rule was written after.

**3. Full-sample test.** A shared helper returns a valid instance built from **state-consistent
records** that *jointly* populate every optional field:

- an active entity with every optional aspect set;
- a deprecated entity with its deprecation fields;
- a deprecated acceptance criterion with a planned-removal version;
- a planned acceptance criterion with a target version, and another without one;
- a Feature with a derived state and a `stub_reason`;
- every field prepared for Azure DevOps.

No record carries a field that its own state makes meaningless, so the sample stays something the
pipeline could genuinely produce. Each kind of component then uses it differently:

- **transforms** run over it in every view and must show no field loss;
- **generators** render it per view and assert that every field that view should show appears, and
  that every field section 4 says to hide does not;
- **collectors** run over a fully authored fixture, and every contract field must have non-zero
  occupancy except an explicit, documented exception.

This is what makes R11's runtime check meaningful in CI. Ordinary test fixtures populate the fields a
test happens to care about, so field loss can hide behind them indefinitely; only a sample that
populates everything turns "nothing was lost" into a statement with content.

A model-similarity heuristic — flagging component models that look like contract records — was
considered and **rejected**: legitimate internal models (coverage-matrix rows, for instance) look
exactly like contract records, and a mirror with renamed fields would escape the heuristic anyway.

## 3. Artifact rules

### R4 — a data file declares its contract

Every artifact has a required top-level `schema_version` equal to its contract id:

| Contract | `schema_version` |
|---|---|
| doc-entities | `doc-entities-v1.0.0` |
| doc-source | `doc-source-v1.0.0` |
| ui-tests | `ui-tests-v1.0.0` |
| generator-ready | `generator-ready-v1.0.0` |
| coverage-matrix | `coverage-matrix-v1.0.0` |
| ui-test-catalog | `ui-test-catalog-v1.0.0` |

In the schema this is a **`const`**, never an `enum`. An `enum` is how alias values accumulate: one
deprecated id is accepted "for now", the migration never finishes, and consumers end up branching on
which alias they were handed. A `const` accepts exactly one value, so a stale producer fails at step
1 or 2 of R5 with a message that names what was expected. **No deprecated alias value is accepted
for any of the six ids.**

Ids stay at `-v1.0.0` until a v1 release; section 6 explains why there is no version negotiation
before then.

### R5 — consumers check an input in a fixed order

Contract id format: `<contract-name>-v<major>.<minor>.<patch>`. One shared check runs for every
consumer. It decides whether the consumer can read a file from the file itself — its `schema_version`
and its structure — never from the tool that wrote it:

| Step | Check | On failure |
|---|---|---|
| 1 | `schema_version` present and parses | **hard** `INVALID_CONTRACT_ID` |
| 2 | contract id is in the consumer's expected set (e.g. a documentation input accepts `doc-entities` or `doc-source`) | **hard** `CONTRACT_MISMATCH` naming the expected set |
| 3 | structural validation against the bundled schema | **hard** `SCHEMA_VALIDATION_FAILED`, naming the failing path, the file's `metadata.producer.utilities_version` and the consumer's own utilities-library version; if they differ, adds "the components run different utilities versions — align the pins" |

The order matters: each step's message is only useful once the previous step has passed. Reporting a
schema violation on a file that is not even the right contract sends the reader after the wrong
problem.

`metadata.producer.version` is **audit information only**: it records which release of which tool
wrote the file, and no step checks it. One producer can write more than one contract version and one
contract has several producers, so a tool's release says nothing about whether a file is readable;
the file's `schema_version` does.

There is **no digest and no contract version range before v1**. Contracts evolve in place with no
external customers yet; a skew fails at step 3 with the cause named explicitly — including both
utilities-library versions, so the reader is pointed at the pins rather than at the data. CI and
release tooling keep the fleet aligned instead (section 6), rather than each consumer carrying
negotiation logic it would exercise once.

**After v1**, step 2 becomes an interval check on the contract version the file declares, and a file
outside the accepted interval is read leniently with a warning rather than rejected. That warning goes
to the consumer's own `warnings[]` output rather than only to a log, so it survives into the artifact
and reaches whoever reads the result.

### R6 — every artifact carries `schema_version` plus the metadata envelope

Every artifact has a top-level `schema_version`, a `metadata` envelope (below) and a `warnings[]`
array.

`metadata.producer` names the tool that **wrote this specific file** — not the tool the data
originally came from. For a transform output that is the transform, never the upstream collector.
Upstream identity is not lost: it is recorded per input in `metadata.source_inputs[]` (R7). Keeping
`producer` about the writer is what makes "which tool do I go fix?" answerable from the file alone.

### R7 — transformation provenance in `metadata.source_inputs[]`

A transform output carries one `source_inputs[]` entry per input file, holding that input's
`schema_version`, `producer`, `run`, `source`, `stats` and `selected_stats`. A collector output —
which has no artifact input — carries `source_inputs: []`, not an absent key.

`source_inputs[]` is an **audit record**: its field paths belong to the *input's* contract, not to
the output's. That is why its `field_occupancy` maps are pattern-keyed rather than enum-keyed (R9) —
enumerating the output contract's paths there would reject every honest audit entry.

`selected_stats` records the stats computed over only the records the transform's view filter kept
for that input, alongside `stats` for the whole input. The pair is what makes a drop legible: a
difference between `stats` and `selected_stats` is filtering, while a difference between
`selected_stats` and the output is loss (R11).

### R8 — legacy provenance shapes are retired outright

No component reads or writes any of these, under any of their historical names:

- an `original_metadata` block;
- an `audit`-namespaced metadata block, including per-component entries nested inside it;
- a free-form trace array;
- a free-form run-context block.

There is **no alias window**. Anything that previously read one of these as a fallback — for example
a generator reading a legacy field as a version fallback — drops that fallback in the same change
that adopts the envelope. A retained fallback is what lets a producer keep writing the old shape
unnoticed; removing the reader is what makes the retirement real.

### R11 — every artifact carries its own stats; a transform proves it lost nothing

**`metadata.stats = { cardinality, field_occupancy }`.**

`cardinality` is a record object with these keys. A count that does not apply to a given producer is
`0`, never absent:

| Key | Counts |
|---|---|
| `entities` | entities emitted |
| `entities_by_type` | entities per documentation type (a map) |
| `acceptance_criteria` | acceptance criteria emitted |
| `scenarios` | test scenarios emitted |
| `warnings_by_code` | warnings per code (a map) |
| `sources_configured` | configured sources the run was asked to collect (both collectors) |
| `sources_failed` | configured sources that failed (both collectors) |
| `unresolved_refs` | references that pointed outside the collected set (both collectors) |
| `entities_skipped` | records dropped before emission — for example an item with no parseable entity id |

**`field_occupancy`** is keyed by **record-relative path**, starting at the record root of the
contract, with `[]` marking each array level:

| Contract | Path prefix |
|---|---|
| `doc-entities` | `entities[]` |
| `doc-source` | `user_stories[]`, `features[]`, `functionalities[]` |
| `ui-tests` | `scenarios[]` |
| `generator-ready` | `content.entities[]` |
| `coverage-matrix`, `ui-test-catalog` | the record roots declared in `living_doc_utilities.contracts.coverage_matrix` and `living_doc_utilities.contracts.ui_test_catalog` |

So `entities[].not_in_scope` and `entities[].acceptance_criteria[].not_in_scope` are distinct paths,
which is the point: the same field name at two levels is two different things to lose.

`metadata`, `document` and `warnings` are **not** counted — they describe the file rather than the
documented system, and counting them would make an envelope change look like a data change.

The value is the number of records at that level with a **non-empty** value. `null`, `""`, `[]` and
`{}` all count as empty; a present-but-empty field is not carried information.

**Lineage tables are declared by the transform owner, checked by a shared helper.** Each transform
declares its own table — input path to output path, or an explicit *dropped, with reason* — in the
repository that owns that transform, because the table changes whenever the transform's code does.
`living-doc-utilities` ships only the machinery: a completeness check (every input leaf path must
have an entry, so a newly added field cannot be forgotten) and the field-loss detection below. A
lineage table maintained in a different repository from the code it describes is a table that goes
stale on the first refactor.

**Transform-time check.** A transform computes occupancy over the records its view filter kept for
that input — the `selected_stats` of R7 — and compares them with its output. A **mapped** path with
input occupancy greater than 0 and output occupancy 0 is a hard **`FIELD_LOSS`** error naming the
path, the input and the output. The comparison runs against the **one documentation input** (see
*One project, one pipeline, one documentation source* below), which is what makes a single
input-to-output comparison well defined.

A *partial* drop — occupancy reduced but not to zero — is **not** an error at transform time. At that
point the transform cannot distinguish a legitimate record-level filter from a bug, so partial drops
are reported separately, downstream, rather than failing a run that is behaving correctly.

**Scope.** R11 guards **transforms**. The authoring-to-collector stage has no JSON input to compare
against, so it cannot be guarded this way; it is guarded by golden-entity tests and snapshot CI
instead.

### R13 — a collector collects everything it was configured for, or fails

**The unit of failure is a configured source** — one repository, one repository path, one
project-plus-query. If any fetch belonging to that source still fails after retries, or a configured
path does not exist, the **whole source** fails. A partially collected source is never emitted: a
document that is quietly missing half a repository is indistinguishable from a document about a
smaller project, and it is the one failure mode a reader cannot detect.

Each source is collected by its own function returning its own result, and the run decides overall
success only after every source has been attempted. One failure therefore never discards sources that
were already collected.

**Configuration errors fail at start** with `INVALID_CONFIGURATION`, naming the input and the reason.
A missing or malformed project id and a malformed repository or project entry fail before any network
request; a token rejected by the first request fails the same way, and no further request is made.
There is no reason to spend a rate limit discovering a typo.

**Explicit retries, one shared policy**, identical on every collector: up to **5 attempts**,
exponential backoff starting at **2 seconds** with jitter, a single wait capped at **60 seconds**
(a rate-limit reset capped at **15 minutes**); every HTTP call uses a **10 second** connect timeout
and a **60 second** read timeout.

| Signal | Action |
|---|---|
| connection error, timeout | retry |
| HTTP 429, 500, 502, 503, 504 | retry, honouring `Retry-After` |
| HTTP 403 with rate-limit-remaining at 0 | wait until the reset time, retry |
| HTTP 403 / 429 with `Retry-After` (secondary rate limit) | wait `Retry-After`, retry |
| a rate-limited GraphQL error returned with HTTP 200 | treat as a primary rate limit |
| HTTP 401 on the first request | no retry; the run fails at start with `INVALID_CONFIGURATION` |
| HTTP 401 after the first request, or a GraphQL scope/permission error | no retry; source fails; the message names the missing scope |
| GraphQL not-found error, HTTP 404 | no retry; source fails |

**The default is hard failure**: the run names the source and the cause, exits non-zero, and writes
**no output file at all**. Writing a short file and exiting zero is what turns a collection outage
into a silent documentation regression.

**Opt-in partial mode** changes only the disposition: a failed source is instead recorded as a
warning and the run continues. It still fails overall if *every* source failed, because that is an
outage, not a partial result.

**Failure is visible downstream.** `sources_configured` and `sources_failed` appear on every
collector output. A transform copies them into its own audit record and forwards **every** input
warning into its own `warnings[]`, naming the input each came from — so a partial collection is still
legible in the final document, several steps away from where it happened.

**Empty is not failed.** A source that answers successfully with zero entities is a warning
(`EMPTY_SOURCE`), not an error. A repository with no documentation yet is a normal state.

**No silent swallowing in shared code.** The shared GitHub call decorator logs and **re-raises** every
exception; it never turns a failure into `None`. A `None` that means "failed" and a `None` that means
"absent" are indistinguishable at the call site, and the retry policy above cannot act on a value.

### The metadata envelope

```jsonc
{
  "schema_version": "generator-ready-v1.0.0",
  "metadata": {
    "producer": { "name": "AbsaOSS/living-doc-toolkit", "version": "0.2.0", "build": "…", "utilities_version": "0.5.1" },
    "run":      { "run_id": "…", "run_attempt": "…", "actor": "…", "workflow": "…", "ref": "…", "sha": "…" },
    "source":   { "project_id": "payments", "systems": ["GitHub"], "organizations": ["…"], "repositories": ["org/repo"], "extraction_mode": null },
    "generated_at": "2026-10-01T12:00:00Z",
    "stats": {
      "cardinality":     { "entities": 42, "entities_by_type": { "DocumentedUserStory": 18 }, "acceptance_criteria": 118, "scenarios": 0, "warnings_by_code": {}, "sources_configured": 3, "sources_failed": 0, "unresolved_refs": 0, "entities_skipped": 0 },
      "field_occupancy": { "content.entities[].not_in_scope": 5, "content.entities[].acceptance_criteria[].aspect": 17 }
    },
    "source_inputs": [
      {
        "schema_version": "doc-entities-v1.0.0",
        "producer": { "name": "AbsaOSS/living-doc-collector-gh", "version": "0.2.0", "utilities_version": "0.5.1" },
        "run": { "…": "…" },
        "source": { "project_id": "payments", "systems": ["GitHub"], "organizations": ["…"], "repositories": ["org/repo"] },
        "stats":          { "cardinality": { "…": 0 }, "field_occupancy": { "entities[].not_in_scope": 5 } },
        "selected_stats": { "cardinality": { "…": 0 }, "field_occupancy": { "entities[].not_in_scope": 5 } }
      }
    ]
  },
  "warnings": [ { "code": "MISSING_STATUS", "message": "…", "context": "…" } ],
  "document": { "title": "…", "version": "…", "view": "release",
                "selection_summary": { "total_entities": 0, "included_entities": 0, "excluded_entities": 0,
                                       "total_acceptance_criteria": 0, "included_acceptance_criteria": 0, "excluded_acceptance_criteria": 0 } },
  "content":  { "entities": [ ] }
}
```

Reading that example:

- **`metadata` is one shared model for all six contracts**, parametrised only in its
  `field_occupancy` key enum, which differs per contract (R9). One model means an envelope fix lands
  everywhere at once.
- **`source` is required on every collector output**, and **`source.project_id` is required
  everywhere**. On a transform output, `source` is copied from the one documentation input, plus the
  test input's systems when there is one.
- `source.systems` values are `GitHub` and `AzureDevOps`. `organizations[]` lists every organisation
  of the run once, as the `organization-name` configured on the collector. `repositories[]` entries
  are `org/repo` (GitHub) or `org/project` (Azure DevOps), and each entry's `org` must be listed in
  `organizations[]`; an organisation may be listed without any repository or project.
  `extraction_mode` is `markdown`, `field-map`, or `null`.
- **`document` appears only on `generator-ready`, `ui-test-catalog` and `coverage-matrix`** — the
  three contracts a generator turns into a document. It holds what the generator titles and filters
  by, including `document.view`.
- Every entity's `source_ref` is
  `{system, native_id (string), native_type, url, tracker_state, area_path, iteration_path}`; every
  entity carries `state_origin` — `authored` for a User Story or Functionality, `derived` for a
  Feature — and a Feature also carries `stub_reason`.

**The one shared write helper** fills `metadata.stats` and the producer's utilities-library version,
validates the artifact **in memory**, and only then writes it — via a temporary file plus an atomic
rename. A failed validation therefore leaves **no file on disk**, so a downstream step cannot pick up
a half-written or invalid artifact from a failed run.

### Collector output layout

Artifacts are written to `<output-path>/<mode>/<artifact>.json`, where `output-path` is an input on
both collectors with a per-collector default — for example
`output/collector-gh/doc-issues/doc-entities.json`.

A collector clears only its **own** `<output-path>/<mode>/` directory, never a shared parent, so two
collectors writing into one output tree cannot delete each other's results.

The file name is always the contract name, never the source system; the source lives in `metadata`.
Project separation is a pipeline-configuration concern — give each project its own output location —
not a path convention baked into the tools.

### One project, one pipeline, one documentation source

A pipeline run documents **exactly one project**.

A transform run takes **exactly one documentation file**: either the issue-tracker document or the
source-scanned document, never both. Several repositories or organisations belonging to one project
are collected within a single collector run instead, which is where they can be de-duplicated
coherently.

Test data may come from a different system than the documentation — Azure DevOps work items with
`.feature` files on GitHub is a supported combination.

Multiple documentation sources per run is **explicitly deferred** until a transform has merge logic
for them. Merging two documentation sources means deciding what happens when both describe the same
entity, and until that decision exists, accepting two inputs would mean picking a winner silently.
Two documentation files in one run are therefore rejected with `MULTIPLE_DOCUMENTATION_SOURCES`, and
two different *kinds* of documentation with `MIXED_DOCUMENTATION_SOURCES`.

### Project id

Every collector has a **required project-id input** — lowercase alphanumeric plus hyphen, starting
with an alphanumeric. It is set once per pipeline, passed to every step, and written into every
artifact's `metadata.source.project_id`.

A transform and every generator take the project id **from their own inputs**, never from separate
configuration. Configuration that restates a value present in the data is configuration that can
contradict it. A mismatch across inputs — or an input with no project id — is a hard
`PROJECT_MISMATCH`.

## 4. Rendering rules

Every authored field is carried at its **authored level** in the `generator-ready` contract; nothing
is expanded, inherited or flattened on the way through. The view filter that builds a
`generator-ready` document selects **records** only: the release view drops `planned` and `in_review`
entities and acceptance criteria, and drops a Feature by its derived state. A generator then decides
**presentation** from the document's declared view.

Separating the two is what lets one transform serve both views' record sets consistently while each
generator stays free to present them differently.

| Field | Inner view | Release view |
|---|---|---|
| User Story / Functionality `state` | status badge | status badge |
| Feature `state` (derived) | status badge marked "derived" | `DEPRECATED` badge only, when deprecated |
| Feature `stub_reason` | "surface not yet instrumented: …" | hidden |
| Entity `not_in_scope`, `preconditions` | under the entity | under the entity |
| AC `not_in_scope`, `preconditions` (AC-level extension) | under the AC as "also …" | under the AC as "also …" |
| Entity / AC `deprecated` state | `DEPRECATED` badge + deprecation date + reason | `DEPRECATED` badge only |
| AC `removal_planned` | "removal planned v*X*" | "removal planned v*X*" |
| AC `planned` with a target version | "planned v*X.Y.Z*" | not applicable — filtered out |
| AC `planned` without a version | "backlog" | not applicable — filtered out |
| AC header | always the canonical rendering: `AC:<id> (v<x.y.z> - <state>)` or `AC:<id> (planned)` | same |
| AC `aspect` | aspects listed under the AC | same |
| AC `rationale`, `placeholder_values`; Functionality `rationale` | under the AC / Functionality | same |
| `source_ref.area_path`, `source_ref.iteration_path` | small text under the entity | hidden |
| `source_ref.native_type`, `source_ref.tracker_state` | hidden | hidden |

A shared test helper encodes exactly which cells above are "shown" for a given contract and view, so
generator tests assert against the table rather than against a copy of it that drifts.

### Coverage

Coverage is computed **per aspect**:

- an acceptance criterion **with** aspects is `covered` only when **every** aspect has at least one
  linked scenario; otherwise it is `partially_covered`, with a per-aspect breakdown;
- an acceptance criterion **without** aspects keeps a plain `covered` / `not_covered`.

Counted acceptance criteria: `active` and `deprecated`, in **both** views. A coverage matrix's
`document.view` changes presentation only, never which criteria are counted.

Not counted:

- `in_review` acceptance criteria. Collection and every step after it run against `master`, and the
  tests for work still in review are not there yet, so counting those criteria would report them as
  uncovered. A scenario linked to an `in_review` criterion is a **warning**
  (`IN_REVIEW_AC_HAS_TESTS`), not an error: it is only reported, the link is kept and the criterion
  stays uncounted. A test for it on `master` usually means the work has merged and the criterion's
  state was not updated.
- `planned` acceptance criteria, whether backlog or targeted. A scenario linked to a planned criterion
  is a **warning** (`PLANNED_AC_HAS_TESTS`), not an error — writing tests ahead of implementation is
  legitimate practice, and counting unimplemented work would depress a coverage figure that is
  supposed to describe what exists.

A supplementary planned-work summary — totals, backlog versus targeted, and a breakdown per target
version — is always carried in the artifact, and rendered only in the inner view.

## 5. Errors and warnings

Warnings go into a `warnings[]` array. Hard errors are raised as structured errors with a code, a
message and context. **This section is the single source of truth for every code below**; nothing
elsewhere redefines one.

### Shared input validation

Called by every transform command before any transform runs. Within a step, **every** occurrence is
reported; the first failing step ends validation, so a reader is never handed a cascade of errors
caused by the first one.

Order:

1. `MISSING_INPUT`
2. the R5 steps 1–3, per input
3. `UNKNOWN_PRODUCER`
4. `PROJECT_MISMATCH`
5. `MULTIPLE_DOCUMENTATION_SOURCES`, `MIXED_DOCUMENTATION_SOURCES`
6. `DUPLICATE_ENTITY_ID`, `DUPLICATE_AC_ID`

| Code | When | Example |
|---|---|---|
| `MISSING_INPUT` | a needed input is absent | a coverage run given no documentation or no test input |
| `INVALID_CONTRACT_ID` | `schema_version` missing or unparseable | hand-edited JSON without `schema_version` |
| `CONTRACT_MISMATCH` | not a contract the slot expects | a test-catalog file passed where documentation is expected |
| `SCHEMA_VALIDATION_FAILED` | structural validation fails | a missing required field; an unknown field from a newer library version |
| `UNKNOWN_PRODUCER` | no adapter recognises the producer name | a file from an unknown tool |
| `PROJECT_MISMATCH` | inputs carry different project ids, or one has none | two collector runs with mismatched project ids |
| `MULTIPLE_DOCUMENTATION_SOURCES` | more than one documentation file, whatever wrote them | two documentation files from two collector runs |
| `MIXED_DOCUMENTATION_SOURCES` | documentation of two different kinds present at once | an issue-tracker document plus a source-scanned document |
| `DUPLICATE_ENTITY_ID` | the same entity id appears twice | the same story id in two repositories of one project |
| `DUPLICATE_AC_ID` | the same AC id appears twice | the same AC id twice under one entity |

The `MIXED_*`, `MULTIPLE_*` and `DUPLICATE_*` codes always list **every** occurrence at once, with a
hint — never a precedence rule that silently picks a winner. Picking a winner is how one of two
identically-numbered stories disappears from a document without anyone noticing.

### Transform-time hard error

`FIELD_LOSS` — a mapped field populated in the input is empty in the output. See R11.

### Transform warnings

| Code | When |
|---|---|
| `PLANNED_AC_HAS_TESTS` | a scenario links a `planned` acceptance criterion |
| `IN_REVIEW_AC_HAS_TESTS` | a scenario links an `in_review` acceptance criterion; reported only, the criterion stays uncounted |
| `STALE_AC_REF` | a scenario references an unknown acceptance criterion, or an undeclared aspect |

In addition, **every input warning is forwarded unchanged** into the transform's own `warnings[]`,
with the input named in its context.

### Collectors

| Code | Kind | When |
|---|---|---|
| `INVALID_CONFIGURATION` | hard, at start | project id missing or malformed; malformed repository/project entry; token rejected by the first request. Context names the input and the reason |
| `SOURCE_UNAVAILABLE` | hard; warning in partial mode | source unfetchable after retries, a configured path missing, or a token lacking a required scope |
| `SCHEMA_VALIDATION_FAILED` | hard | output fails pre-write validation; no file written |
| `EMPTY_SOURCE` | warning | source answered with zero entities |
| `MALFORMED_AC` | warning; AC skipped | AC header with no id, unknown state, or missing version on a non-planned state |
| `LEGACY_AC_STATE` | warning; AC kept | a retired state value falls back to unversioned `planned` |
| `UNPARSED_AC_LINE` | warning | an AC-block line couldn't be assigned after normalisation |
| `UNKNOWN_SECTION` | warning | an unrecognised heading in an issue body |
| `MISSING_ENTITY_ID` | warning; item not emitted | a title with no recognised entity-id prefix |
| `IGNORED_AUTHORED_KEY` | warning | a key the contract doesn't carry, including a written Feature status |
| `MISSING_STATUS` | warning; status derived | a User Story / Functionality with no authored status |
| `STATUS_AC_MISMATCH` | warning; authored value wins | authored status contradicts the entity's own ACs |
| `ORPHAN_FEATURE` | warning; state set to `active` | a Feature with no Functionality and no User Story in the run |
| `RELATION_MISMATCH` | warning | a Functionality's declared parent and its Feature's declared children disagree |
| `UNRESOLVED_RELATION` | warning | a relation points outside the collected set |
| `NO_SOURCE_URL` | warning | a source file outside a git checkout, so no URL can be derived |
| `HTML_CONTENT_DROPPED` | warning (Azure DevOps) | HTML-to-markdown conversion dropped an image, script or unknown tag |
| `DUPLICATE_AC_SOURCE` | warning (Azure DevOps) | an AC present in both the description and a dedicated field |
| `EXCLUDED_STATE` | warning; item not emitted (Azure DevOps) | a work item in an excluded state |

### Generators

`INVALID_CONTRACT_ID`, `CONTRACT_MISMATCH` and `SCHEMA_VALIDATION_FAILED` are hard, exactly as above.

`TEMPLATE_KEY_MISSING` is **hard**: a template that misses a required key fails the run. It is never
rendered as an empty section, because an empty section in a published document reads as "there is
nothing here" rather than "this failed to render".

`URL_FETCH_REFUSED` is logged but **non-fatal**: the renderer refused to fetch an image or URL
outside the template's own directory.

## 6. Alignment

There is **no digest and no contract version range before a v1 release**. Contracts evolve in place
and there are no external customers, so the cost of a negotiation mechanism would be paid every
release while the benefit stayed hypothetical.

A skew between components' utilities-library versions fails loudly at validation (R5 step 3) — R9's
`additionalProperties: false` together with required fields catches it — and the message names both
the producer's and the consumer's utilities-library version and, when they differ, advises that the
pins be aligned. It is the only version check before v1: the producer's own release version is audit
information and is never checked. Loud and specific beats tolerant: a tolerant reader turns a skew
into subtly wrong output that nobody traces back to a pin.

Alignment is enforced where it is cheap. CI installs each component in its own isolated environment
against its own pin and reports the pins in use: a **warning** between release gates, an **error** at
every gate, milestone and release. A contract change made between gates follows the documented
contract-change process.

After v1, contracts are versioned with an interval check instead, and R5's step 2 changes
accordingly.
