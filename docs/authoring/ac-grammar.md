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
- Other modules check an id with one helper, never their own pattern → `authoring/ac_grammar.py::is_valid_ac_id`
- A version is required unless the state is `planned` → `contracts/common.py::AcceptanceCriterion._check_version_required_unless_planned`
- `removal planned` is required on `deprecated` and allowed nowhere else → `contracts/common.py::AcceptanceCriterion._check_removal_planned_only_when_deprecated`
- The stored version drops the header's `v` ([version format](../contracts/entities-and-state.md#version-format)).
- A header may follow a comment leader: `###` in an issue body, `#` in a `.feature` file, `*` in a PageObject → `authoring/ac_grammar.py::parse_acceptance_criteria`
- `entity_id` is used only in warning context; that an id belongs to its entity is checked on the model → `contracts/common.py::check_ac_ids_owned`

## Block

A criterion's block is the lines after its header → `authoring/ac_grammar.py::parse_acceptance_criteria`.

- It ends at the next `AC:` line, a `===` banner line, or a Markdown `##` to `######` heading.
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
| a line with no bullet marker | appended to the field the previous line filled |
| any other line | nothing: `UNPARSED_AC_LINE` |

- After a `preconditions:` or `not_in_scope:` line, every later bullet of the block joins that list → `authoring/ac_grammar.py::_parse_extensions`
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
- in a scenario file, an `@AC:` tag is malformed ([Parsers, scenarios](parsers.md#scenarios)).

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
