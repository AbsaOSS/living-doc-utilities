# Errors and warnings

## Purpose

Anyone who raises or handles a code reads this page. It is the one definition of every error and warning code:
its kind, the component that emits it, and when.

Read before: [Rendering](rendering.md) · Next: back to [Documentation contracts](../contracts.md)

## Contents

- [How codes are reported](#how-codes-are-reported)
- [Codes](#codes)
- [Shared input validation order](#shared-input-validation-order)
- [Forwarded warnings](#forwarded-warnings)

## How codes are reported

- Every code is registered once, with its kind and emitter → `contracts/codes.py::ALL_CODES`
- A test keeps the table below equal to the registry, kind and emitter included → `tests/contracts/test_codes.py::test_error_page_lists_exactly_the_registered_codes`
- A hard error is raised with a code, a message and an optional context → `contracts/codes.py::ContractError`
- A warning is an entry in the artifact's `warnings[]`: `code`, `message`, `context` → `contracts/envelope.py::ContractWarning`
- Nothing elsewhere redefines a code; other pages name it and link here → [one fact, one page](../../DEVELOPER.md#depth)

## Codes

Kinds and emitters are the values of `contracts/codes.py::CodeKind` and `contracts/codes.py::Emitter`.

| Code | Kind | Emitter | When | Effect |
|---|---|---|---|---|
| `INVALID_CONTRACT_ID` | error | utilities | `schema_version` missing or unparseable (hand-edited JSON); on write, an unknown id | R5 step 1 fails |
| `CONTRACT_MISMATCH` | error | utilities | not a contract the slot expects (a test catalog where documentation is expected) | R5 step 2 fails; names the expected set |
| `SCHEMA_VALIDATION_FAILED` | error | utilities | schema or model validation fails (a missing field; an unknown field from a newer library) | R5 step 3 fails; on write, no file is written |
| `MISSING_INPUT` | error | toolkit | a needed input is absent (a coverage run with no documentation or no test input) | validation stops |
| `UNKNOWN_PRODUCER` | error | toolkit | no adapter recognises the producer name (a file from an unknown tool) | validation stops |
| `PROJECT_MISMATCH` | error | toolkit | inputs carry different project ids, or one has none | validation stops |
| `MULTIPLE_DOCUMENTATION_SOURCES` | error | toolkit | more than one documentation file, whatever wrote them | lists every occurrence |
| `MIXED_DOCUMENTATION_SOURCES` | error | toolkit | documentation of two kinds at once (issue-tracker plus source-scanned) | lists every occurrence |
| `DUPLICATE_ENTITY_ID` | error | toolkit | the same entity id twice (one story id in two repositories of a project) | lists every occurrence |
| `DUPLICATE_AC_ID` | error | toolkit | the same acceptance-criterion id twice under one entity | lists every occurrence |
| `FIELD_LOSS` | error | transform | a mapped field populated in the input is empty in the output ([R11](component-checks.md#r11-a-transform-proves-it-lost-nothing)) | run fails; names every lost path |
| `PLANNED_AC_HAS_TESTS` | warning | transform | a scenario links a `planned` criterion | criterion not counted |
| `IN_REVIEW_AC_HAS_TESTS` | warning | transform | a scenario links an `in_review` criterion | link kept; criterion not counted |
| `STALE_AC_REF` | warning | transform | a scenario references an unknown criterion or an undeclared aspect | reported |
| `INVALID_CONFIGURATION` | error | collector | project id missing or malformed; malformed repository or project entry; token rejected by the first request | run fails at start; names the input and reason |
| `SOURCE_UNAVAILABLE` | error | collector | a source unfetchable after retries, a configured path missing, or a token lacking a scope | source fails; a warning in partial mode |
| `EMPTY_SOURCE` | warning | collector | a source answered with zero entities | reported |
| `MALFORMED_AC` | warning | collector | a criterion header or `@AC:` tag that cannot be mapped ([conditions](../authoring/ac-grammar.md#dropped-criteria)) | criterion or tag skipped |
| `LEGACY_AC_STATE` | warning | collector | a retired state value, `descoped` | criterion kept as version-less `planned` |
| `UNPARSED_AC_LINE` | warning | collector | a criterion-block line that fits no field after normalisation | line dropped |
| `UNKNOWN_SECTION` | warning | collector | an unrecognised `##` heading in an issue body | section dropped |
| `MISSING_ENTITY_ID` | warning | collector | a title with no recognised entity-id prefix | item not emitted |
| `IGNORED_AUTHORED_KEY` | warning | collector | a key the contract does not carry, including a written Feature status | value dropped |
| `MALFORMED_STATUS` | warning | collector | a `## Status` or `status:` value that is not one of the four states | value dropped; falls through to `MISSING_STATUS` |
| `MISSING_STATUS` | warning | collector | a User Story or Functionality with no authored status | status derived |
| `STATUS_AC_MISMATCH` | warning | collector | the authored status contradicts the entity's own criteria | authored value wins |
| `ORPHAN_FEATURE` | warning | collector | a Feature with no Functionality and no User Story in the run | state set to `active` |
| `RELATION_MISMATCH` | warning | collector | a Functionality's declared parent and its Feature's declared children disagree | reported |
| `UNRESOLVED_RELATION` | warning | collector | a relation points outside the collected set | reported |
| `RELATION_TYPE_MISMATCH` | warning | collector | a relation resolves to an entity of the wrong type ([expected types](../authoring/parsers.md#relations)) | context names entity, field, target, actual and expected type |
| `NO_SOURCE_URL` | warning | collector | a source file outside a git checkout, so no URL can be derived | reported |
| `HTML_CONTENT_DROPPED` | warning | collector | Azure DevOps HTML conversion dropped content ([kinds](../authoring/urls-and-html.md#html-to-markdown-conversion)) | one warning per call, with counts |
| `DUPLICATE_AC_SOURCE` | warning | collector | Azure DevOps: a criterion in both the description and a dedicated field | reported |
| `EXCLUDED_STATE` | warning | collector | Azure DevOps: a work item in an excluded state | item not emitted |
| `TEMPLATE_KEY_MISSING` | error | generator | a template misses a required key | run fails |
| `URL_FETCH_REFUSED` | warning | generator | the renderer refused to fetch an image or URL outside the template's own directory | logged; not fatal |

- Generators read through `read_artifact`, so R5's three errors apply to them unchanged → `contracts/io.py::read_artifact`
- `TEMPLATE_KEY_MISSING` is never rendered as an empty section → generators
  - Why: an empty section in a published document reads as "nothing here", not "this failed".
- `SOURCE_UNAVAILABLE` is hard by default and a warning only in a collector's opt-in partial mode → [R13](pipeline-rules.md#r13-a-collector-collects-everything-it-was-configured-for-or-fails)

## Shared input validation order

Every transform command runs these steps before any transform → toolkit:

1. `MISSING_INPUT`
2. [R5](artifact-rules.md#r5-consumers-check-an-input-in-a-fixed-order) steps 1 to 3, per input
3. `UNKNOWN_PRODUCER`
4. `PROJECT_MISMATCH`
5. `MULTIPLE_DOCUMENTATION_SOURCES`, `MIXED_DOCUMENTATION_SOURCES`
6. `DUPLICATE_ENTITY_ID`, `DUPLICATE_AC_ID`

- Within a step every occurrence is reported; the first failing step ends validation → toolkit
  - Why: a reader never gets a cascade of errors caused by the first one.
- The `MIXED_*`, `MULTIPLE_*` and `DUPLICATE_*` codes list every occurrence at once, with a hint → toolkit
  - Why: a precedence rule that picks a winner makes one of two same-numbered stories vanish unnoticed.

## Forwarded warnings

- A transform forwards every input warning unchanged into its own `warnings[]`, naming the input in the context → toolkit
