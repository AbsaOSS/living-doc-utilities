# Parsers

## Purpose

Collector authors read this page. It defines the one layout each parser accepts, how an entity id is found,
how state is derived, how relations are checked, and the golden fixtures.

Read before: [Acceptance-criterion grammar](ac-grammar.md) · Next: [URLs and HTML](urls-and-html.md)

## Contents

- [Common behaviour](#common-behaviour)
- [Issue body](#issue-body)
- [Feature header](#feature-header)
- [PageObject header](#pageobject-header)
- [Scenarios](#scenarios)
- [Finding the entity id](#finding-the-entity-id)
- [Status derivation](#status-derivation)
- [Relations](#relations)
- [Golden fixtures](#golden-fixtures)
- [Example](#example)

## Common behaviour

- Each parser accepts one layout, the canon of `AbsaOSS/living-doc`'s [glossary](https://github.com/AbsaOSS/living-doc/blob/master/docs/guides/living-doc-glossary.md) and [header types](https://github.com/AbsaOSS/living-doc/blob/master/docs/guides/living-doc-header-types.md).
- Each parser returns `(parsed, warnings)` and never raises on malformed input; every information-losing skip is a coded warning → `tests/authoring/test_warning_coverage.py::test_information_losing_skip_produces_a_coded_warning_and_no_log_record`
  - Why: a caller always has a structured way to see what was lost.
- No authoring module uses `logging` → `tests/authoring/test_warning_coverage.py::test_no_authoring_module_uses_the_logging_module`
- `None` with `MISSING_ENTITY_ID` means the title or banner had no id; the rest of the document's fields are never extracted, though feature-header and PageObject input is already normalised by then → `authoring/identity.py::derive_entity_id`
- A parsed entity has every entity field except `source_ref`, `tags` and `timestamps`; the collector fills those → `authoring/issue_body.py::ParsedEntity`
  - Why: a parser only ever sees document text.
- `state` and `state_origin` stay empty until [status derivation](#status-derivation) runs → `authoring/issue_body.py::ParsedEntity`
- An authored value that fails its field's validation is dropped with a warning (`MALFORMED_STATUS` for a status) → `authoring/issue_body.py::_build_parsed_entity`
- A bullet list joins a following line with no marker onto the previous item → `authoring/issue_body.py::extract_bullets`
- An id list is comma-separated; blank or `none` means empty → `authoring/issue_body.py::split_id_list`

## Issue body

`parse_issue_body(text, title, entity_type)` reads a GitHub issue body → `authoring/issue_body.py::parse_issue_body`.
Each `##` heading maps by slug (lowercase, spaces and underscores as `_`) to a field → `authoring/issue_body.py::_SECTIONS_BY_TYPE`.

| Heading | User Story | Feature | Functionality |
|---|---|---|---|
| `## Description` | `narrative` | `purpose` | `narrative` |
| `## Status` | `state` | dropped: `IGNORED_AUTHORED_KEY` | `state` |
| `## Business Value` | `business_value` (bullets) | | |
| `## Acceptance Criteria` | the [grammar](ac-grammar.md) | | the [grammar](ac-grammar.md) |
| `## Preconditions` | `preconditions` (bullets) | | `preconditions` (bullets) |
| `## Not In Scope` | `not_in_scope` (bullets) | | `not_in_scope` (bullets) |
| `## Surface Type` | | `surface_type` | |
| `## Owners` | | `owners` (id list) | |
| `## User Stories` | | `user_stories` (id list) | |
| `## Functionalities` | | `functionalities` (id list) | |
| `## External Dependencies` | | `external_dependencies` (id list) | |
| `## Feature Dependencies` | | `feature_dependencies` (id list) | |
| `## Parent Feature` | | | `parent` |
| `## Func Type` | | | `func_type` |
| `## Rationale` | | | `rationale` (one bullet) |
| `## Deprecated At`, `## Deprecation Reason`, `## Superseded By` | the same-named field | the same-named field | the same-named field |

- A heading with no mapping is `UNKNOWN_SECTION`, not a failure → `authoring/issue_body.py::parse_issue_body`
- The grammar reads the whole normalised text, so an `### AC:` heading counts wherever it appears → `authoring/issue_body.py::parse_issue_body`
- Headings inside a fenced code block are not sections → `authoring/issue_body.py::_split_h2_sections`

## Feature header

`parse_feature_header(text, entity_type)` reads a User Story's or Functionality's `.feature` header → `authoring/feature_header.py::parse_feature_header`.

- Two `# ===` banner lines bracket a block of `# key: value` lines, and `# key:` lines with an indented bullet list.
- The first content line is the title: `LIVING DOC — <id> · <title>` → `authoring/identity.py::extract_living_doc_title`
- The banner search stops at the file's `Feature:` line → `authoring/feature_header.py::_extract_header_block`
  - Why: a banner-shaped comment in the scenario body is never taken for the header's closing banner.
- An unknown key is `IGNORED_AUTHORED_KEY` → `authoring/feature_header.py::parse_feature_header`

Keys → `authoring/feature_header.py::_KEYS_BY_TYPE`:

| Key | User Story | Functionality |
|---|---|---|
| `source`, `status`, `deprecated_at`, `deprecation_reason`, `superseded_by` | yes | yes |
| `preconditions`, `not_in_scope` (bullets) | yes | yes |
| `acceptance_criteria` (read by the [grammar](ac-grammar.md)) | yes | yes |
| `business_value` (bullets) | yes | |
| `parent`, `func_type`, `rationale` | | yes |

## PageObject header

`parse_page_object(text)` reads a PageObject file's leading `/* ... */` comment → `authoring/page_object.py::parse_page_object`.
Its lines are `* key: value`, under the same `LIVING DOC — <id> · <title>` title.

| Shape | When | Known keys | Result |
|---|---|---|---|
| full header | no `parent-feat:` | `surface_type`, `route`, `owners`, `purpose`, `user_stories`, `functionalities`, `external_dependencies`, `feature_dependencies`, `page-object`, `wizard-steps`, `stub-reason`, `status` | a Feature plus its primary page |
| cross-reference header | `parent-feat:` present | `parent-feat`, `route`, `owners`, `purpose`, `page-object`, `functionalities`, `status` | one page for an already-described Feature |

- The key sets are `authoring/page_object.py::_FULL_HEADER_KEYS` and `authoring/page_object.py::_CROSS_REFERENCE_KEYS`
- A cross-reference result names `parent_feat`; the collector appends its page to that Feature's `pages` → `authoring/page_object.py::PageObjectResult`
- `status:` is recognised only to be dropped as `IGNORED_AUTHORED_KEY` → `authoring/page_object.py::IGNORED_AUTHORED_KEYS`
- A full-header-only key (`surface_type`, `user_stories`, `external_dependencies`, `feature_dependencies`) on a cross-reference header is an unknown key, `IGNORED_AUTHORED_KEY` → `tests/authoring/test_page_object.py::test_full_header_only_key_on_a_cross_reference_header_is_an_unrecognised_key`
- `wizard-steps` is split on ` · ` → `authoring/page_object.py::parse_page_object`

## Scenarios

`parse_scenarios(text, entity_type)` reads a `.feature` file's Gherkin body → `authoring/scenario.py::parse_scenarios`.

- Each `Scenario:` or `Scenario Outline:` takes the `@AC:<id>[/<param>:<value>...]` tags right before it → `authoring/scenario.py::_tags_to_ac_links`
- The tag format is open: any number of `/<param>:<value>` segments may follow the id → `authoring/scenario.py::_parse_ac_tag`
  - `aspect` fills the link's `aspect`; its value stops at the next `/` and must not contain `:`.
  - Any other parameter is accepted without a warning and not stored.
    - Why: `AcLink` has no field for one; the canon's AC custom keyword (`@AC:<id>/<placeholder-name>:<value>`) is defined only in its header templates, so its value is not stored yet.
- A `# AC:` comment above a scenario is documentation only; only the `@AC:` tag links a scenario.
- Any other line between a tag block and the next scenario (`Rule:`, a step, `Examples:`) drops the pending tags → `authoring/scenario.py::parse_scenarios`
  - Why: a tag block links only the very next scenario, never one further down.
- A `Feature:` or `Background:` line also drops pending tags → `authoring/scenario.py::parse_scenarios`
- An `@AC:` tag is `MALFORMED_AC` when its criterion id is invalid, a segment is empty or not `<param>:<value>`, `aspect` is given twice, or the `aspect` value contains `:` → `authoring/scenario.py::_parse_ac_tag`
- The collector fills each scenario's `scenario_id` and `source_ref` → `authoring/scenario.py::ParsedScenario`

## Finding the entity id

- An entity id is `US-<nnn>`, `FEAT-<nnn>` or `FUNC-<nnn>`, the canon's three prefixes → `tests/authoring/test_identity.py::test_each_canon_prefix_is_an_entity_id`
- `derive_entity_id(title)` takes the first such run as a whole word, so another tracker key before it is passed over (`BUG-7 fix for US-001` gives `US-001`) → `tests/authoring/test_identity.py::test_other_tracker_keys_are_not_entity_ids`
- A run glued to other letters, digits or `_` (`XUS-001`, `US-001abc`, `GH_US-001`) is not an id → `tests/authoring/test_identity.py::test_an_id_run_glued_to_other_word_characters_is_not_an_entity_id`
- A historical prefix is skipped: in `GH-US-001`, the match is `US-001` → `tests/authoring/test_identity.py::test_valid_title_prefixes_extract_us_001`
- No such run returns `(None, [MISSING_ENTITY_ID])`, even when the title names another key such as `JIRA-12`; the collector adds location context and counts `entities_skipped` → `authoring/identity.py::derive_entity_id`
- Normalisation rules 5 and 5b find the id with the same pattern, so the ` · ` separator lands after the real id → `authoring/normalize.py::normalize_title`
- The same function serves an issue title, a `.feature` banner and a PageObject banner → `authoring/identity.py::derive_entity_id`
- One helper finds the `LIVING DOC — ` title line in both banner formats → `authoring/identity.py::extract_living_doc_title`

## Status derivation

`derive_statuses(entities)` settles every entity's `state` and `state_origin` once, after a run's entities are parsed → `authoring/status.py::derive_statuses`.
The state vocabulary: [Entities and state](../contracts/entities-and-state.md#state-and-state-origin).

- A User Story or Functionality keeps its authored state, with `state_origin` `authored` → `authoring/status.py::_derive_us_or_func`
- With no authored state, it is derived from its own criteria by the majority rule, with `MISSING_STATUS`; the origin stays `authored` → `authoring/status.py::_derive_us_or_func`
- An authored state that contradicts its own criteria gets `STATUS_AC_MISMATCH`; the authored value wins → `authoring/status.py::_is_mismatch`
- A Feature is always derived, in order → `authoring/status.py::_derive_feature`:
  1. `deprecated` if the Feature has `deprecated_at`;
  2. else the majority of its linked Functionalities (its `parent`, or listed in its `functionalities` when `parent` is absent);
  3. else the majority of its linked User Stories;
  4. else `active`, with `ORPHAN_FEATURE`.
- Non-Features are settled first, so a Feature reads settled states whatever the input order → `authoring/status.py::derive_statuses`

The majority rule → `authoring/status.py::_majority_state`:

1. `active` if any input is `active`;
2. else `in_review` if any input is `in_review`;
3. else `deprecated` if every input is `deprecated`, a signal of uniform retirement;
4. else `planned`, including an empty input.

An authored state contradicts its criteria when → `authoring/status.py::_is_mismatch`:

| Authored | Contradicted by |
|---|---|
| `planned` | any `active` or `deprecated` criterion |
| `active` | criteria exist, but none is `active` or `deprecated` |
| `deprecated` | any `active`, `in_review` or `planned` criterion |
| `in_review` | never |

## Relations

`check_relations(entities)` runs once per collector run, over the whole collected set → `authoring/relations.py::check_relations`.

| Declared by | Field | Expected target type |
|---|---|---|
| Feature | `user_stories` | `DocumentedUserStory` |
| Feature | `functionalities` | `DocumentedFunctionality` |
| Feature | `feature_dependencies` | `DocumentedFeature` with `surface_type` `API` |
| Functionality | `parent` | `DocumentedFeature` |
| any entity | `superseded_by` | the declaring entity's own type |

- A target outside the set is `UNRESOLVED_RELATION` → `authoring/relations.py::check_relations`
- A target of another type is `RELATION_TYPE_MISMATCH`; context names the entity, field, target, actual and expected type → `authoring/relations.py::_type_mismatch`
- A Feature's functionality whose `parent` names another Feature is `RELATION_MISMATCH` → `authoring/relations.py::check_relations`
- A Functionality missing from its parent's non-empty `functionalities` list is `RELATION_MISMATCH`; an empty or absent list means nothing was declared → `authoring/relations.py::check_relations`
- A `feature_dependencies` target that is a Feature with no `API` surface is `RELATION_TYPE_MISMATCH`; the expected type is `API DocumentedFeature` → `authoring/relations.py::_feature_dependency_warning`
- A Feature naming itself in `feature_dependencies` is `RELATION_MISMATCH` → `authoring/relations.py::_feature_dependency_warning`
- A Feature's `feature_dependencies` is exactly what is authored on it; nothing is derived from its Functionalities, and the reverse direction is not computed → `tests/authoring/test_relations.py::test_a_feature_keeps_exactly_its_authored_feature_dependencies`
- In a source-code run, a `UI` Feature's `feature_dependencies` target is `UNRESOLVED_RELATION`, and that is expected: an `API` Feature has no source-code form until the API endpoint header exists (roadmap "Post-v1") → `tests/authoring/golden/test_golden_source_code_chain.py::test_a_ui_feature_dependency_is_unresolved_in_a_source_code_run_and_nothing_else`

## Golden fixtures

- `tests/fixtures/golden/` holds the canonical documents of `AbsaOSS/living-doc`'s `docs/examples/`, copied verbatim under a provenance header, plus hand-written expected entities → `tests/authoring/golden/test_golden_entities.py::test_golden_entities_match_hand_written_json`
- Other repositories compare their parsers' output against these → `living-doc-collector-gh`, `living-doc-toolkit`, `living-doc-collector-ad`

## Example

```python
from living_doc_utilities.authoring.issue_body import parse_issue_body
from living_doc_utilities.authoring.status import derive_statuses

body = """## Description

As a customer, I can sign in.

## Acceptance Criteria

### AC:US-001-01 (v1.0.0 - active)

- Valid credentials land on the dashboard.
"""
parsed, warnings = parse_issue_body(body, "US-001 · Customer Login", "DocumentedUserStory")
entities, status_warnings = derive_statuses([parsed])  # once, over every entity of a run

assert entities[0].state == "active"
assert [warning.code for warning in status_warnings] == ["MISSING_STATUS"]
```
