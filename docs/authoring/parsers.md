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
- Every authored line no field reads is reported, one warning per line → `authoring/accounting.py`
  - A line that breaks its header's format is `AUTHORING_ERROR`: a line with no comment marker inside the header, a second line under a single-value key, a header that never closes, a key below the header, an `AC:` header outside `acceptance_criteria:`, a PageObject header line between an early `*/` and the header's real end → `tests/authoring/test_accounting.py::test_a_line_with_text_and_no_comment_marker_inside_a_feature_header_is_not_read`
  - A line a structural problem already names is reported once, by that problem, not again by the unread-line sweep → `tests/authoring/test_framing.py::test_a_line_a_structural_problem_names_is_reported_once`
  - Any other unread line no more specific code covers is `AUTHORING_WARNING`: text in no section, a key or `##` heading written twice (only the first is read; every line of the later one is reported), a value continued after a blank line, a code block inside a criterion, a line of a dropped criterion → `tests/authoring/test_accounting.py::test_a_key_written_twice_reads_the_first_value_and_reports_the_later_one`
  - Both are warnings: parsing goes on, and a format check decides what fails it ([codes](../contracts/errors.md#codes)) → `tests/authoring/test_accounting.py::test_both_authoring_codes_are_warnings_so_a_parser_never_stops`
  - An HTML comment, and the prose a cross-reference header may open with, are not content and are not reported → `tests/authoring/test_accounting.py::test_issue_body_text_before_the_first_heading_is_reported_but_an_html_comment_is_not`
- A warning about a line sets its 1-based `line_no`, and its context keeps the line or its text (`line=`); the collector, which knows the file, fills `path` ([how codes are reported](../contracts/errors.md#how-codes-are-reported)) → `tests/authoring/test_accounting.py::test_every_line_warning_of_a_broken_header_names_its_input_line`
- A warning sets every location field its parser knows: `entity_id`, `ac_id` when the criterion's id is valid, `line_no` → `tests/authoring/test_warning_location.py::test_a_warning_carries_the_location_its_parser_knows`
  - A header `MALFORMED_AC` names the header's line, and the criterion when its id is valid, even on a header too malformed to parse.
  - Every line inside a criterion names that criterion when its id is valid: a line the grammar cannot read, a line of a dropped criterion, a code block, an `AC:` line read as text, a criterion under a repeated key → `authoring/ac_grammar.py::criterion_ids`
  - A scenario names no entity: a tag's `MALFORMED_AC` names the tag's line, and the criterion when the tag's id is valid.
  - `MISSING_ENTITY_ID` names only the line of a banner's title or rule: its entity was never emitted. An issue title has no line.
  - A warning about a whole entity (a status mismatch, a relation) names only the entity.
- No authoring module uses `logging` → `tests/authoring/test_warning_coverage.py::test_no_authoring_module_uses_the_logging_module`
- `None` with `MISSING_ENTITY_ID` means the title or banner had no id; none of the document's fields are extracted, and nothing of it is normalised → `authoring/identity.py::derive_entity_id`
- A parsed entity has every entity field except `source_ref`, `tags` and `timestamps`; the collector fills those → `authoring/issue_body.py::ParsedEntity`
  - Why: a parser only ever sees document text.
- `state` and `state_origin` stay empty until [status derivation](#status-derivation) runs → `authoring/issue_body.py::ParsedEntity`
- An authored value that fails its field's validation is dropped with a warning (`MALFORMED_STATUS` for a status) → `authoring/issue_body.py::_build_parsed_entity`
- Every parser reads its sections from the frame built in normalisation's [three phases](normalisation.md#where-normalisation-runs): rule 6, then the frame, then the other rules → `authoring/framing.py::sections`
  - Why: the normaliser and the parser read one result, so they cannot disagree about where a section or a list runs.
  - A boundary is structural, never read from a line's prose; no parser finds one itself.
- Every parser reads a line's indent before deciding what the line belongs to; one line model serves them all → `authoring/framing.py::indented`
  - Why: indentation is significant in every authored input (the canon's [Indentation](https://github.com/AbsaOSS/living-doc/blob/master/docs/guides/living-doc-header-types.md#indentation) rule); a stripped line has lost its level.
  - The indent is counted after the comment marker and at most one space (`# `, ` * `); [rule 6](normalisation.md#rule-6-whitespace) has already turned a tab or non-breaking space into spaces: one per tab in a header, to GitHub's tab stop of 4 in an issue body.
- In a bullet-list field, a line deeper than an open item's `- ` is that item's text: never a key, an `AC:` header or a section's end, whatever it reads like → `authoring/framing.py::BulletItemTracker`
  - Example: `#   - Migrated accounts carry` then `#     status: deprecated until re-verified.` is one `business_value` item; no `status` key is read.
  - A blank line ends nothing, with or without its comment marker: not an item, not a key's section, as in a Markdown list → `tests/authoring/test_framing.py::test_a_blank_comment_line_in_a_feature_header_ends_nothing_either`
  - An item's wrapped `AC:` line yields no criterion → `tests/authoring/test_framing.py::test_d20_an_ac_shaped_wrapped_line_in_a_bullet_item_is_that_items_text_and_no_criterion`
  - A PageObject header's one bullet-list key is `notes:`, declared where the frame reads it → `authoring/normalize.py::PO_BULLET_KEYS`
- In a header a key sits at the key level, the indent of its first key; a line shaped `key:` any deeper is content, never a key → `tests/authoring/test_feature_header.py::test_a_key_shaped_line_deeper_than_the_key_level_is_content_not_a_key`
  - Example: `#   - Fewer support calls.` then `#   status: deprecated` at the item's level is one `business_value` item, read flat; no state is read.
- A scalar key's value continues on a line deeper than the key, as the canon wraps `purpose:`; a line at the key's own level fits no level and is `AUTHORING_WARNING` → `authoring/accounting.py::scalar_lines`
  - A key whose value is one token takes no further line: a deeper line under it is `AUTHORING_ERROR` and is not read, so the value stays valid → `tests/authoring/test_accounting.py::test_a_single_value_key_reports_a_further_line_and_keeps_its_value`
  - A text value and an id list may wrap; a part after a blank line is read with `AUTHORING_WARNING` → `tests/authoring/test_accounting.py::test_a_text_value_wraps_silently_and_continues_after_a_blank_line_with_a_warning`

  | Format | One token | Text or id list, may wrap |
  |---|---|---|
  | `.feature` header | `source`, `status`, `deprecated_at`, `superseded_by`, `parent`, `func_type` | `deprecation_reason` |
  | PageObject header | `surface_type`, `route`, `page-object`, `parent-feat`, `superseded_by`, `status`, `deprecated_at` | `purpose`, `stub-reason`, `deprecation_reason`, `owners`, `user_stories`, `functionalities`, `external_dependencies`, `feature_dependencies`, `wizard-steps` |

- A bullet-list field holds one string per top-level item. Its first `- ` sets the item level; each line is read by its indent → `authoring/issue_body.py::_read_bullets`

  | Line | Read as |
  |---|---|
  | `- ` at the item level | the next item |
  | no marker, at the item level | joined onto the open item with a space (the flat layout) |
  | no marker, deeper than the item's `- `, before any nested item | the item's wrapped text, joined with a space |
  | `- ` deeper than the item's `- `, and every line after it in that item | kept in the item's string as extracted: on its own line, indented relative to the item's `- ` |
  | shallower than the item level, or a nested `- ` back between two open levels | nothing: `MISINDENTED_LINE`, for it and every line deeper than it |

  - Example: `- Parent.` then `  - Child.` gives the one entry `"Parent.\n  - Child."`, in an issue body and a `.feature` header alike → `tests/authoring/test_feature_header.py::test_a_nested_business_value_item_is_kept_in_its_parents_string_as_extracted`
  - Why: the contract has no field for a nested item, and nothing between the collector and a generator rewrites the string, so it stays as authored and the generator decides how to render it ([Rendering](../contracts/rendering.md#records-and-presentation)).
  - An id-list field never nests; it is read as comma-separated text → `authoring/issue_body.py::split_id_list`
- The same rule reads a criterion's `preconditions` and `not_in_scope` items ([grammar](ac-grammar.md#extensions)) → `authoring/normalize.py::ItemText`
- Text before a bullet-list field's first `- ` bullet is dropped with `UNPARSED_BULLET_LINE` → `authoring/issue_body.py::unparsed_bullet_warning`
- Both bullet-field warnings are built in one place → `authoring/issue_body.py::bullet_field_warnings`
- A header key's own-line text counts as before the first bullet → `authoring/feature_header.py::_read_keys`
- The `UNPARSED_BULLET_LINE` context names the contract field, not the authored key or heading → `authoring/issue_body.py::unparsed_bullet_warning`
- An id list is comma-separated; blank or `none` means empty → `authoring/issue_body.py::split_id_list`
- Every entity type carries an optional `notes` bullet list, the canon's [one place for human context](https://github.com/AbsaOSS/living-doc/blob/master/docs/guides/living-doc-glossary.md#core-entities) → `contracts/doc_entities.py::EntityContent`
  - Nothing ever reads a note's text: it drives no state, nothing is derived from it, and it is never validated, whatever it reads like (`status: deprecated` stays free text) → `tests/authoring/test_notes.py::test_a_field_shaped_note_changes_no_derived_state_and_raises_no_warning`
    - Why: anything that must drive behaviour has to be a typed field; a note exists so a recordable fact needs no new field.
    - It does not decide how its own file is read either: a note saying `parent-feat:` leaves a PageObject header a full header, and one saying `LIVING DOC` is not a banner title → `tests/authoring/test_notes.py::test_a_note_whose_wrapped_line_reads_as_parent_feat_does_not_make_a_cross_reference_header`, `::test_a_note_that_mentions_living_doc_is_still_a_note`
      - The title is found by position, not by its prose, so an item may quote the whole `LIVING DOC — <id> · <title>` form → `authoring/framing.py::Frame.title`, `tests/authoring/test_notes.py::test_a_note_quoting_a_whole_banner_title_is_still_a_note`
  - It is entity-level, plus a cross-reference page's own ([PageObject header](#pageobject-header)). A `notes:` inside a criterion block fills no criterion field and is reported instead ([grammar](ac-grammar.md#extensions)) → `tests/authoring/test_notes.py::test_an_ac_level_notes_key_in_an_issue_body_is_reported_and_reads_as_no_field`
  - `deprecation_reason` stays its own typed field and does not move into a note → `contracts/doc_entities.py::EntityContent`

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
| `## Notes` | `notes` (bullets) | `notes` (bullets) | `notes` (bullets) |
| `## Deprecated At` | `deprecated_at` | dropped: `IGNORED_AUTHORED_KEY` - a Feature has no deprecation date | `deprecated_at` |
| `## Deprecation Reason`, `## Superseded By` | the same-named field | the same-named field | the same-named field |

- A heading with no mapping is `UNKNOWN_SECTION`, not a failure → `authoring/issue_body.py::parse_issue_body`
- An `### AC:` heading opens a criterion wherever it appears, except as a bullet item's text; the frame bounds each criterion, and any other heading ends it → `authoring/framing.py::criterion_blocks`
  - Under a criterion item, a deeper line is that item's text, an `AC:` line too, which is reported → `tests/authoring/test_framing.py::test_an_ac_line_on_a_criterion_items_text_in_an_issue_body_is_reported`
- Only a `##` heading outside a fenced code block opens a section; a `###` heading is content of the section it sits in → `authoring/framing.py::frame_issue_body`
  - A heading may be indented by up to three spaces, as CommonMark reads it → `tests/authoring/test_framing.py::test_a_heading_indented_up_to_three_spaces_ends_a_criterion_as_commonmark_reads_it`
- An item nested one space deeper than its parent is reported: the parser nests it, GitHub shows a sibling (`D19`) → `tests/authoring/test_accounting.py::test_an_item_nested_one_space_deeper_is_reported_as_github_renders_it_a_sibling`

## Feature header

`parse_feature_header(text, entity_type)` reads a User Story's or Functionality's `.feature` header → `authoring/feature_header.py::parse_feature_header`.

- The header runs from the first `# ===` rule to the last; it holds `# key: value` lines, and `# key:` lines with an indented bullet list → `authoring/framing.py::frame_feature_header`
  - Nothing outside it is read: not a line above the first rule or below the last → `authoring/framing.py::frame_feature_header`
  - A key below the last rule, above `Feature:`, is `AUTHORING_ERROR` → `tests/authoring/test_accounting.py::test_a_key_below_the_closing_rule_is_reported`
  - A comment above the first rule is no header line and is not reported: Gherkin's `# language:` sits on line 1 → `tests/authoring/test_accounting.py::test_a_comment_above_the_opening_rule_is_no_header_line_and_is_not_reported`
  - A header with only one rule never closes. It is still read, up to its last comment line before a tag or `Feature:`, and is reported as `AUTHORING_ERROR` → `tests/authoring/test_framing.py::test_a_feature_header_with_one_rule_is_read_to_its_last_comment_line_and_reported`
- The title is the first line after the opening rule: `LIVING DOC — <id> · <title>` → `authoring/framing.py::Frame.title`
  - A header with no title there is `MISSING_ENTITY_ID`, whatever a later line reads like → `tests/authoring/test_framing.py::test_a_feature_header_title_is_the_line_after_the_opening_rule_not_any_line_reading_like_one`
  - A file with no rule above `Feature:` has no header at all: `MISSING_ENTITY_ID` says that no header was found → `tests/authoring/test_accounting.py::test_a_feature_file_with_no_header_says_no_header_was_found`
- The rule search stops at the file's `Feature:` line → `authoring/framing.py::frame_feature_header`
  - Why: a banner-shaped comment in the scenario body is never taken for the header's closing banner.
- Every criterion sits in `acceptance_criteria:`'s section, as the canon writes it: an `AC:` header outside that key is text and `AUTHORING_ERROR`, so the key always bounds the criteria → `tests/authoring/test_framing.py::test_an_ac_header_outside_the_criteria_key_is_no_criterion_and_the_keys_after_it_are_read`
- A criterion block runs from its `AC:` header to the next `AC:` header, a key at the key level, or a `# ===` rule → `tests/authoring/test_framing.py::test_a_key_at_the_key_level_ends_a_criterion_block_and_is_read`
  - A rule inside the header is an optional end of a block; the last rule ends the header → `tests/authoring/test_framing.py::test_a_rule_inside_the_header_ends_a_criterion_block_and_the_last_rule_ends_the_header`
  - The first `AC:` line sets the criterion level; an `AC:` line at another indent, or on an item's text, is no header and is reported → `tests/authoring/test_framing.py::test_an_ac_line_off_the_criterion_level_is_text_and_reported`
- A blank line ends nothing, with `#` or without it → `tests/authoring/test_framing.py::test_a_blank_line_without_a_comment_marker_in_a_feature_header_closes_nothing`
  - Why: a blank line inside a Markdown list does not end it either.
- A line with text and no `#` inside the header is not read and is `AUTHORING_ERROR`; Gherkin rejects such a line above `Feature:` too → `tests/authoring/test_accounting.py::test_a_line_with_text_and_no_comment_marker_inside_a_feature_header_is_not_read`
- An unknown key is `IGNORED_AUTHORED_KEY` → `authoring/feature_header.py::parse_feature_header`
- `acceptance_criteria:` is structural: its criteria are the frame's criterion blocks, so text on the key's own line fills no field and is `AUTHORING_WARNING` → `tests/authoring/test_accounting.py::test_an_acceptance_criteria_keys_own_line_text_is_reported`
  - Written bare, as the canon writes it, nothing is unread and nothing is reported → `tests/authoring/test_accounting.py::test_an_acceptance_criteria_key_written_bare_is_not_reported`

Keys → `authoring/feature_header.py::_KEYS_BY_TYPE`:

| Key | User Story | Functionality |
|---|---|---|
| `source`, `status`, `deprecated_at`, `deprecation_reason`, `superseded_by` | yes | yes |
| `preconditions`, `not_in_scope`, `notes` (bullets) | yes | yes |
| `acceptance_criteria` (read by the [grammar](ac-grammar.md)) | yes | yes |
| `business_value` (bullets) | yes | |
| `parent`, `func_type`, `rationale` | | yes |

## PageObject header

`parse_page_object(text)` reads a PageObject file's leading `/* ... */` comment → `authoring/page_object.py::parse_page_object`.
Its lines are `* key: value`, under the same `LIVING DOC — <id> · <title>` title, on the line after the comment opens.

- The comment ends at its first line that ends in `*/`; a `*/` inside a value does not end it → `authoring/framing.py::frame_page_object`
  - A key written on that last line is still read, without the comment's `*/` → `tests/authoring/test_framing.py::test_a_key_on_the_closing_line_is_still_read_without_the_close`
  - With no line ending in `*/` the comment never closes, and nothing in it is read → `tests/authoring/test_framing.py::test_an_unclosed_page_object_comment_leaves_its_lines_as_written`
  - It is reported as `AUTHORING_ERROR`, saying that nothing in it is read → `tests/authoring/test_accounting.py::test_an_unclosed_page_object_comment_is_reported_as_read_nowhere`
  - A value ending in `*/` closes the comment early when a later ` * ` line, before any code, closes it again: the header's real end is there, and each line up to it is `AUTHORING_ERROR` → `tests/authoring/test_accounting.py::test_header_lines_up_to_the_real_end_after_a_comment_that_closed_early_are_reported`
  - With no later close, the header ends where the comment did, and nothing after it is reported → `tests/authoring/test_accounting.py::test_a_comment_closed_by_a_value_with_no_later_close_ends_the_header_there`
- A `===` rule ends the open key; a blank ` *` line ends nothing → `tests/authoring/test_accounting.py::test_a_blank_star_line_in_a_notes_list_ends_nothing`
- A line inside the comment without ` * ` is not read and is `AUTHORING_ERROR`, as a `.feature` line without `#` is → `tests/authoring/test_accounting.py::test_a_page_object_line_without_its_star_is_reported`
  - The frame runs from the `/*` line through the `*/` line, so both delimiter lines are header lines too: text written beside either one carries no marker, is not read and is reported → `tests/authoring/test_accounting.py::test_text_beside_the_closing_delimiter_is_reported`, `::test_text_beside_the_opening_delimiter_is_reported`
  - Only what sits beside the delimiter counts, so the canon's `/* ===` and `=== */`, a bare ` */`, a key written on the closing line and a `/**` opening carry nothing of their own → `tests/authoring/test_accounting.py::test_a_delimiter_carries_no_authored_text_of_its_own`

| Shape | When | Known keys | Result |
|---|---|---|---|
| full header | no `parent-feat:` | `surface_type`, `route`, `owners`, `purpose`, `user_stories`, `functionalities`, `external_dependencies`, `feature_dependencies`, `page-object`, `wizard-steps`, `stub-reason`, `deprecation_reason`, `superseded_by`, `notes`, `status`, `deprecated_at` | a Feature plus its primary page |
| cross-reference header | `parent-feat:` present | `parent-feat`, `route`, `owners`, `purpose`, `page-object`, `functionalities`, `notes`, `status`, `deprecated_at` | one page, with its own notes, for an already-described Feature |

- The key sets are `authoring/page_object.py::_FULL_HEADER_KEYS` and `authoring/page_object.py::_CROSS_REFERENCE_KEYS`
- A cross-reference result names `parent_feat`; the collector appends its page to that Feature's `pages` → `authoring/page_object.py::PageObjectResult`
- `status:` and `deprecated_at:` are recognised only to be dropped as `IGNORED_AUTHORED_KEY`, in a full or a cross-reference header → `authoring/page_object.py::IGNORED_AUTHORED_KEYS`
- A full-header-only key (`surface_type`, `user_stories`, `external_dependencies`, `feature_dependencies`, `deprecation_reason`, `superseded_by`) on a cross-reference header is an unknown key, `IGNORED_AUTHORED_KEY` → `tests/authoring/test_page_object.py::test_full_header_only_key_on_a_cross_reference_header_is_an_unrecognised_key`
- `notes` is allowed on both. A full header's notes are the Feature's; a cross-reference header's notes are its page's own, kept on its `PageRef` with the page's other data and never merged into the Feature's → `tests/authoring/test_notes.py::test_a_note_on_a_cross_reference_page_object_header_stays_with_its_page`
  - Why: a cross-reference page is a part of its Feature with data of its own (route, owners, purpose, functionalities), and its notes describe that part.
- `notes` is the header's one bullet key; every other key's value is a scalar or an id list, joined from its lines → `authoring/page_object.py::_joined`
- `wizard-steps` is split on ` · ` → `authoring/page_object.py::parse_page_object`

## Scenarios

`parse_scenarios(text, entity_type)` reads a `.feature` file's Gherkin body → `authoring/scenario.py::parse_scenarios`.

- Each `Scenario:` or `Scenario Outline:` takes the `@AC:<id>[/<param>:<value>]` tags right before it → `authoring/scenario.py::_tags_to_ac_links`
- The tag format is closed: at most one `/<param>:<value>` follows the id (`DEC-76`) → `authoring/scenario.py::_parse_ac_tag`
  - The parameter is `aspect` or the criterion's keyword name ([Variants](ac-grammar.md#variants)); its value fills the link's `aspect`.
  - The name is not stored or checked against the criterion here.
    - Why: `AcLink` holds the value only (`D39`); a value the criterion does not declare is `STALE_AC_REF`, a transform's check.
  - The value stops at the next `/` and must not contain `:`.
  - Anything else a team tags a scenario with goes into ordinary Cucumber tags, e.g. `@priority_high`.
- A bare `@AC:<id>` links the whole criterion, every declared value: the link's `aspect` is `None` → `contracts/ui_tests.py::AcLink`
  - Why: a data-driven scenario runs every value at once; review confirms that it really does.
- A `# AC:` comment above a scenario is documentation only; only the `@AC:` tag links a scenario.
- Any other line between a tag block and the next scenario (`Rule:`, a step, `Examples:`) drops the pending tags → `authoring/scenario.py::parse_scenarios`
  - Why: a tag block links only the very next scenario, never one further down.
- A `Feature:` or `Background:` line also drops pending tags → `authoring/scenario.py::parse_scenarios`
- An `@AC:` tag is `MALFORMED_AC`, and skipped, when its criterion id is invalid, it has a second parameter, a segment is empty or not `<param>:<value>`, the name is invalid, or the value contains `:` → `tests/authoring/test_scenario.py::test_malformed_ac_tag_params_produce_a_warning_and_no_link`
- The collector fills each scenario's `scenario_id` and `source_ref` → `authoring/scenario.py::ParsedScenario`

## Finding the entity id

- An entity id is `US-<nnn>`, `FEAT-<nnn>` or `FUNC-<nnn>`, the canon's three prefixes → `tests/authoring/test_identity.py::test_each_canon_prefix_is_an_entity_id`
- `derive_entity_id(title)` takes the first such run as a whole word, so another tracker key before it is passed over (`BUG-7 fix for US-001` gives `US-001`) → `tests/authoring/test_identity.py::test_other_tracker_keys_are_not_entity_ids`
- A run glued to other letters, digits or `_` (`XUS-001`, `US-001abc`, `GH_US-001`) is not an id → `tests/authoring/test_identity.py::test_an_id_run_glued_to_other_word_characters_is_not_an_entity_id`
- A historical prefix is skipped: in `GH-US-001`, the match is `US-001` → `tests/authoring/test_identity.py::test_valid_title_prefixes_extract_us_001`
- No such run returns `(None, [MISSING_ENTITY_ID])`, even when the title names another key such as `JIRA-12`; a banner's parser adds the title's line, and the collector the file, and counts `entities_skipped` → `authoring/identity.py::derive_entity_id`
- Normalisation rules 5 and 5b find the id with the same pattern, so the ` · ` separator lands after the real id → `authoring/normalize.py::normalize_title`
- The same function serves an issue title, a `.feature` banner and a PageObject banner → `authoring/identity.py::derive_entity_id`
- One helper reads the title text from the banner's title line, in both banner formats → `authoring/identity.py::extract_living_doc_title`

## Status derivation

`derive_statuses(entities)` settles every entity's `state` and `state_origin` once, after a run's entities are parsed → `authoring/status.py::derive_statuses`.
The state vocabulary: [Entities and state](../contracts/entities-and-state.md#state-and-state-origin).

- A User Story or Functionality keeps its authored state, with `state_origin` `authored` → `authoring/status.py::_derive_us_or_func`
- With no authored state, it is derived from its own criteria by the majority rule, with `MISSING_STATUS`; the origin stays `authored` → `authoring/status.py::_derive_us_or_func`
- An authored state that contradicts its own criteria gets `STATUS_AC_MISMATCH`; the authored value wins → `authoring/status.py::_is_mismatch`
- A Feature is always derived, from its Functionalities alone → `authoring/status.py::_derive_feature`:
  - the majority of its linked Functionalities: its `parent`, or listed in its `functionalities` when `parent` is absent;
  - with no linked Functionality, `planned` with `FEATURE_WITHOUT_FUNCTIONALITY` — the same answer the majority rule gives for an empty input, because no Functionality speaks for it.
- A linked User Story never stands in for a Functionality → `tests/authoring/test_status.py::test_feature_with_only_linked_user_stories_is_a_feature_without_functionality`
  - Why: a Feature is composed of its Functionalities; a User Story only links to it.
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
- Each fixture's header names the canon commit it was copied from; a refresh re-pins every fixture together → `tests/fixtures/golden/gh-issues/us-001-customer-login.md`
- The corpus is expected to raise exactly two warnings, both `FEATURE_WITHOUT_FUNCTIONALITY`: FEAT-002 links only a User Story and FEAT-003 links no entity, so neither has a Functionality to derive from → `tests/authoring/golden/test_golden_entities.py::test_golden_run_produces_exactly_the_expected_corpus_warnings`
  - In the source-code chain FEAT-003's `feature_dependencies` target is also `UNRESOLVED_RELATION`, expected until an API Feature has a source-code form → `tests/authoring/golden/test_golden_source_code_chain.py::test_a_ui_feature_dependency_is_unresolved_in_a_source_code_run_and_nothing_else`
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
