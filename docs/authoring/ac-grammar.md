# Acceptance-criterion grammar

## Purpose

Anyone who writes, parses or renders an acceptance criterion reads this page. It defines the header forms, the
block extensions, and when a criterion is dropped or converted.

Read before: [Normalisation](normalisation.md) · Next: [Parsers](parsers.md)

## Contents

- [Header](#header)
- [Block](#block)
- [Extensions](#extensions)
- [Dropped criteria](#dropped-criteria)
- [Legacy descoped criteria](#legacy-descoped-criteria)
- [Rendering the header](#rendering-the-header)
- [Example](#example)

## Header

`parse_acceptance_criteria(text, entity_id)` reads every criterion in already-normalised text → `authoring/ac_grammar.py::parse_acceptance_criteria`.
It accepts only the canonical form that [normalisation](normalisation.md) produces; it has no tolerance of its own.

| Header | State | Stored `version` / `removal_planned` |
|---|---|---|
| `AC:<id> (planned)` | `planned` backlog, no target version | none / none |
| `AC:<id> (v<x.y.z> - planned)` | `planned`, targeted at a version | `x.y.z` / none |
| `AC:<id> (v<x.y.z> - in_review)` | `in_review` | `x.y.z` / none |
| `AC:<id> (v<x.y.z> - active)` | `active` | `x.y.z` / none |
| `AC:<id> (v<x.y.z> - deprecated - removal planned v<x.y.z>)` | `deprecated` | `x.y.z` / `x.y.z` |

- `<id>` is the entity id, a hyphen and a sequence number, e.g. `US-001-01` → `contracts/common.py::AC_ID_PATTERN`
- Only a User Story or a Functionality owns criteria, so `<id>` starts `US-` or `FUNC-`; `FEAT-001-01` is rejected → `tests/contracts/test_common.py::test_acceptance_criterion_id_rejects_a_prefix_that_owns_no_criteria`
- Other modules check an id with one helper, never their own pattern → `authoring/ac_grammar.py::is_valid_ac_id`
- A version is required unless the state is `planned` → `contracts/common.py::AcceptanceCriterion._check_version_required_unless_planned`
- `removal planned` is required on `deprecated` and allowed nowhere else → `contracts/common.py::AcceptanceCriterion._check_removal_planned_only_when_deprecated`
- The stored version drops the header's `v` ([version format](../contracts/entities-and-state.md#version-format)).
- A header may follow a comment leader: `###` in an issue body, `#` in a `.feature` file, `*` in a PageObject → `authoring/ac_grammar.py::parse_acceptance_criteria`
- `entity_id` is used only in warning context; that an id belongs to its entity is checked on the model → `contracts/common.py::check_ac_ids_owned`

## Block

A criterion's block is the lines after its header. In a parser the frame bounds it, so the grammar finds no boundary itself → `authoring/ac_grammar.py::parse_frame_criteria`.

- In a parser it ends where the [frame](parsers.md#common-behaviour) ends it: at the next criterion header, at a key at the key level or a `# ===` rule in a `.feature` header, at any heading in an issue body → `authoring/framing.py::criterion_blocks`
- Over bare text, `parse_acceptance_criteria` finds the blocks itself: a block ends at the next `AC:` line, a `===` banner line, or a Markdown `##` to `######` heading → `authoring/ac_grammar.py::parse_acceptance_criteria`
  - An `AC:` line deeper than the open bullet item's `- ` is that item's wrapped text and ends nothing → `tests/authoring/test_ac_grammar.py::test_a_line_wrapped_deeper_than_a_criterion_item_is_never_an_ac_header`
- A criterion with nothing under its header is dropped with `MALFORMED_AC`, "has no description line"; the other criteria are read (`D22`) → `tests/authoring/test_ac_grammar.py::test_a_criterion_with_nothing_under_its_header_is_reported_and_the_rest_is_read`
- Each line keeps its indent: only the comment leader (`#`, `###`, `*`) and one following space are removed → `authoring/ac_grammar.py::parse_acceptance_criteria`
  - Why: what a block line belongs to is read from its indent ([Extensions](#extensions)).
- Blank lines are skipped, not treated as an end.
  - Why: an issue-body criterion heading gets one blank line before its bullets.
- Lines inside a fenced code block are skipped → `authoring/normalize.py::compute_fence_flags`

## Extensions

Each block line fills one field of the criterion → `contracts/common.py::AcceptanceCriterion`.

| Block line | Fills |
|---|---|
| the first `- ` bullet | `description` (required) |
| `- Aspect: a, b` | `aspect`, a list |
| `- Rationale: text` | `rationale` |
| `- <name>: value, value` | `placeholder_values[<name>]`; the name is lowercased with spaces and hyphens as `_` |
| a `preconditions:` line, then bullets | `preconditions` |
| a `not_in_scope:` line, then bullets | `not_in_scope` |
| a line with no bullet marker, right after a description, rationale, `preconditions:` or `not_in_scope:` line | appended to that field |
| a line deeper than a description, rationale, `preconditions` or `not_in_scope` item's `- ` | that item's text: wrapped text is joined with a space; a nested `- ` item is kept as extracted, as in a [bullet-list field](parsers.md#common-behaviour) |
| a line deeper than an `Aspect:` or placeholder item's `- ` | nothing: `UNPARSED_AC_LINE` |
| any other bare `<key>:` line with a deeper line right under it, e.g. `notes:` | nothing: `UNPARSED_AC_LINE`, for it and each line deeper than it |
| a line whose indent fits no level (see below) | nothing: `MISINDENTED_LINE`, for it and each line deeper than it |
| any other line | nothing: `UNPARSED_AC_LINE` |

The block's content level is the indent of its first bullet → `authoring/ac_grammar.py::_ExtensionReader`.
A line fits no level when it is shallower than the content level, or sits between a nested sub-list's key and its
items (`- Aspect:` at 5 under `preconditions:` at 4 with items at 6) → `tests/authoring/test_ac_grammar.py::test_a_bullet_between_a_sub_key_and_its_items_is_misindented_and_dropped`

The first item of a sub-list decides how far the list reaches → `authoring/ac_grammar.py::_SubList`:

| Sub-list items | Layout | The list ends at |
|---|---|---|
| deeper than `preconditions:` / `not_in_scope:` | nested, the `.feature` canon | the first line at or above the key's indent; that line is read as a criterion line |
| at the key's own indent | flat, every issue body | the next sub-list key, or the end of the block: every later bullet joins the list, in line order |

```gherkin
#   AC:US-001-01 (v1.0.0 - active)
#     - Valid credentials land on the dashboard.
#     preconditions:
#       - An account exists.
#     - Aspect: security
```

This gives `preconditions = ["An account exists."]` and `aspect = ["security"]`, with no warning → `tests/authoring/test_ac_grammar.py::test_a_bullet_back_at_criterion_level_closes_an_indented_sub_list`

- The same block written flat, with `- An account exists.` at the key's indent, puts `Aspect: security` into `preconditions` → `tests/authoring/test_ac_grammar.py::test_flat_sub_list_keeps_every_later_bullet_in_line_order`
- A line deeper than an item's `- ` is that item's text: a sub-key or `<key>:` there is not read as a key → `authoring/ac_grammar.py::_ExtensionReader`
- A nested precondition stays in its parent's entry: `["An account exists.\n  - It is not locked."]` → `tests/authoring/test_ac_grammar.py::test_a_nested_precondition_item_is_kept_in_its_parents_string`
- An unknown bare key is reported with exactly the lines deeper than it; none of them fills a field, and the next line at or above its indent is read normally → `tests/authoring/test_ac_grammar.py::test_unknown_sub_key_is_reported_with_exactly_the_lines_deeper_than_it`
  - Why: the canon allows `notes:` at entity level only; a nested note reading `Owner: x` would otherwise become a placeholder value.
- A bare `<key>:` with no deeper line right under it is a wrapped line, not a key: `- The dashboard shows the` then `following:` is one description → `tests/authoring/test_ac_grammar.py::test_a_bare_key_with_nothing_deeper_under_it_is_wrapped_text`
  - Why: without an indent the two cannot be told apart, so the line is read as it always was; a flat `notes:` is read the same way, its bullets as criterion lines → `tests/authoring/test_ac_grammar.py::test_a_flat_unknown_key_is_read_as_wrapped_text_and_its_bullets_as_criterion_lines`
- A placeholder name must match `^[A-Za-z_][A-Za-z0-9_]*$` after that rewrite → `contracts/common.py::PLACEHOLDER_NAME_PATTERN`

## Dropped criteria

A criterion is skipped with a `MALFORMED_AC` warning when → `authoring/ac_grammar.py::_build_ac`:

- a line starts with `AC:` but is not `AC:<id> (...)`;
- the id is missing or not id-shaped;
- the parentheses are empty or hold more than three segments;
- a version segment lacks its lowercase `v`, or a third segment is not `removal planned v<x.y.z>`;
- the state is not one of the four, or the version is not `x.y.z`;
- a version is missing on a state other than `planned`;
- `removal planned` is missing on `deprecated`, or present on another state;
- the block has no description bullet;
- in a scenario file, an `@AC:` tag has an invalid criterion id, an empty segment, a segment that is not `<param>:<value>`, `aspect` given twice, or an `aspect` value that contains `:` ([Parsers, scenarios](parsers.md#scenarios)).

In a parser, each line of a dropped criterion's block is reported too, one `AUTHORING_WARNING` per line, unless another warning already names it → `tests/authoring/test_accounting.py::test_every_line_of_a_dropped_criterion_is_reported_and_the_next_criterion_is_read`

## Legacy descoped criteria

- `AC:<id> (v<x.y.z> - descoped)` is converted to a version-less `planned` criterion, with a `LEGACY_AC_STATE` warning → `authoring/ac_grammar.py::_build_ac`
  - Why: the retired state still appears in older documents; converting keeps the criterion instead of dropping it.
- Any other `descoped` shape is `MALFORMED_AC` → `authoring/ac_grammar.py::_build_ac`
- In a converted block, `descoped_reason:` becomes `rationale` → `authoring/ac_grammar.py::_parse_extensions`
- `descoped_at:` and `future_release:` lines are dropped; the model has no field for them → `authoring/ac_grammar.py::_parse_extensions`

## Rendering the header

- `canonical_header()` renders `AC:<id> (v<x.y.z> - <state>)`, adding ` - removal planned v<x.y.z>` on `deprecated` → `contracts/common.py::AcceptanceCriterion.canonical_header`
- A version-less criterion renders as `AC:<id> (planned)` → `contracts/common.py::AcceptanceCriterion.canonical_header`
  - Why: a generator renders a header without importing `authoring`.

## Example

```python
from living_doc_utilities.authoring.ac_grammar import parse_acceptance_criteria
from living_doc_utilities.authoring.normalize import SourceFormat, normalize

text = """## Acceptance Criteria

### AC:US-001-01 (V1.0 – Active)

- A customer who submits valid credentials lands on the dashboard.
- Aspect: desktop, mobile
"""
normalized = normalize(text, SourceFormat.ISSUE_BODY, "DocumentedUserStory")
criteria, warnings = parse_acceptance_criteria(normalized.text, entity_id="US-001")

assert criteria[0].canonical_header() == "AC:US-001-01 (v1.0.0 - active)"
assert criteria[0].aspect == ["desktop", "mobile"]
assert warnings == []
```
