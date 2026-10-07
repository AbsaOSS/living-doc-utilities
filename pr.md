# #186: AC keyword as an alias of Aspect, the coverage summary and the warning fields

## Overview

`P35-UT13` brings `utilities` in line with the canon at `living-doc` `a80649b` (#48, `DEC-71`, `DEC-76`) and, for
warnings, at `aa04313` (#50, `DEC-77`). It also adds the coverage summary (`DEC-74`). It is the first half of
`0.6.0`. `P35-UT12` (`OUTPUT_PATH`) adds the second half.

- **Header grammar** (`authoring/ac_grammar.py`). A `- <name>: <values>` bullet is the criterion's keyword only when
  the description names `{<name>}`. Names are compared folded: case, `-`, `_` and space are equal. A keyword is the
  other spelling of `Aspect:`. Its values fill `aspect`, and `placeholder_values` keeps `{<slug>: values}`.
  - A bullet the description does not name is `UNPARSED_AC_LINE`, and so is a keyword named `aspect`.
  - `Aspect:` plus a keyword, two keywords, or `Aspect:` twice is `MALFORMED_AC`, and the criterion is dropped.
    The canon allows one variant declaration per criterion, and its own checker fails on any second one, a second
    `Aspect:` included (`living-doc` `tools/examples_check.py::_declare_variant`). Before, a second `Aspect:`
    silently replaced the first.
- **Scenario tags** (`authoring/scenario.py`). The format is closed: `@AC:<id>[/<param>:<value>]`.
  - The one parameter is `aspect` or a valid keyword name, and its value fills `AcLink.aspect`.
  - A second parameter is `MALFORMED_AC`, and the tag is skipped.
  - A bare tag stays `AcLink(aspect=None)`: the whole criterion, every declared value.
  - The name is not stored (`D39`).
- **Coverage contract** (`contracts/coverage_matrix.py`). A row with aspects is `covered`, `not_covered` (none
  covered) or `partially_covered`. The schema rule mirrors this.
  - New required `CoverageSummary` on every `EntityCoverage` and on `CoverageMatrixResult`. It holds the counts by
    status and `coverage_pct`.
  - `coverage_pct` sums the row weights as `Fraction`s: `covered` 1, `not_covered` 0, `partially_covered` covered
    aspects over declared aspects. It rounds once, to one decimal, half up, and is `None` with no counted row.
  - The root summary is computed from every row of every entity, never from the entities' percentages.
  - Validators recompute every field. The schema carries types and bounds only (Pydantic-only, like `PlannedSummary`).
  - `CoverageSummary.from_rows(rows)` is what a producer writes. The contract id stays `coverage-matrix-v1.0.0`.
- **Warning fields** (`contracts/envelope.py`, `DEC-77`). `ContractWarning` gains four optional fields that say where
  a warning belongs: `entity_id`, `ac_id` (`AC_ID_PATTERN`, only for a valid id), `line_no` (`ge=1`) and `path`
  (the input file relative to its scan root). `context` keeps its free text, unchanged. All six schemas regenerate.
  - `authoring` fills what it knows through one builder, `accounting.located`. A header `MALFORMED_AC` names the
    entity, the line and, when the id is valid, the criterion; a tag `MALFORMED_AC` names the line and the
    criterion; `MISSING_ENTITY_ID` names only the line; an entity-level warning names only the entity.
  - Following the canon ("its criterion when the criterion has a valid id", header types § Indentation), every line
    inside a criterion also names it: `UNPARSED_AC_LINE`, `MISINDENTED_LINE`, a dropped criterion's lines, a code
    block, an `AC:` line read as text, a criterion under a repeated key. `ac_grammar.criterion_ids(frame)` maps each
    criterion's lines to its valid id; the three line sweeps in `accounting` take that map from the parser.
  - `path` is never set here; a collector fills it (`P35-AC1a`).
  - `_dropped_lines` now reads `line_no` from the field instead of parsing it out of `context`.
- **`full_sample`** (`contracts/testing.py`). No AC carries both kinds now.
  - `US-001-01` declares `Aspect:` only.
  - The new `US-001-04` declares the keyword `payment_field`, so its `aspect` equals the keyword's values.
  - The new `US-001-05` declares `Aspect:`, and no scenario covers it.
  - The coverage sample has a `covered`, a 1-of-3 `partially_covered`, a `not_covered` and a `deprecated` row.
    Its summaries are 44.4, 100.0, `None`, and 58.3 for the root, not the 72.2 mean.
  - `generator-ready` carries a dropped criterion's `MALFORMED_AC` (`US-001-06`) with all four fields, an
    `UNPARSED_AC_LINE` and a `MISSING_ENTITY_ID` that names no entity.
  - The samples agree, and a test holds them to it: every coverage row and scenario link names a criterion the
    entities hold, with its aspects, and the dropped `US-001-06` is in none of them. So `SCN-001` now links both of
    `US-001-01`'s aspects, and the coverage row lists both.
  - `shown_paths` shows every coverage summary in both views, and `warnings[].code`, `.message`, `.line_no` and
    `.path` in the inner view only.
- **Golden corpus** re-copied from `a80649b`; all 11 fixture headers are re-pinned. Only the `FUNC-001` pair changed
  upstream. `expected/func-001-…json` gains `FUNC-001-03`, hand-written from its issue body.
- **Docs**: `ac-grammar.md` has a new § Variants and the two new drop conditions. Also updated: `parsers.md`
  § Common behaviour (warning fields) and § Scenarios, `rendering.md` § Fields by view (what was not loaded),
  § Coverage and a new § Coverage summary (`100.0` can round up from 99.95), `errors.md` (the four fields),
  `component-checks.md` (the sample's warnings, and the samples agree), `schema-rules.md` (five Pydantic-only
  rules), the `contracts.md` hub and `api.md` (the new public helpers).
- **Version**: `pyproject.toml` is `0.6.0`, measured against `v0.5.0`. The pins in `README.md` and `docs/api.md` follow.

## Release Notes

`0.6.0` (draft; `P35-UT12` adds its breaking change before the owner releases):

- A named keyword on an acceptance criterion, e.g. `- rule: a, b, c` under a description naming `{rule}`, now fills
  `aspect` with its values, so coverage is per value, as for `Aspect:`. The name stays in `placeholder_values`.
- New drop conditions: a criterion that declares `Aspect:` and a keyword, two keywords, or `Aspect:` twice is
  `MALFORMED_AC` and is dropped. Before, a second `Aspect:` silently replaced the first.
- A `- <name>: <values>` bullet whose name the description does not name as `{<name>}` is now reported as
  `UNPARSED_AC_LINE` and is not stored. The same holds for a keyword named `aspect`. Before, it was stored in
  `placeholder_values` with no warning.
- A scenario tag with a second parameter, e.g. `@AC:US-1-01/aspect:a/priority:high`, is now `MALFORMED_AC` and is
  skipped. Before, it was accepted and the extra parameter was dropped. `@AC:<id>/<keyword>:<value>` now links that
  value; before, it linked the whole criterion.
- A `coverage-matrix` criterion with aspects and no covered aspect is now `not_covered`. Before, it had to be
  `partially_covered`.
- The coverage matrix carries a required `summary` on every entity and on the whole matrix: `counted_acs`,
  `covered_acs`, `partially_covered_acs`, `not_covered_acs` and `coverage_pct`.
  `CoverageSummary.from_rows(rows)` computes it.
- A warning carries the optional `entity_id`, `ac_id`, `line_no` and `path`, in every contract. The parsers fill
  the first three where they know them; `context` is unchanged.

**Migration**

- A `coverage-matrix` producer must write `summary` on every entity and on the root: `CoverageSummary.from_rows`
  over that entity's rows, and over every row of every entity. A file without it, or with one that disagrees with
  its rows, fails validation.
- A reader of `partially_covered` sees 0/n rows as `not_covered` now. A producer writes `not_covered` for them.
- A scenario tag with extra `/<param>:<value>` segments keeps one parameter: `aspect` or the criterion's keyword
  name. Anything else goes into ordinary Cucumber tags, e.g. `@priority_high`.
- The keyword rules are not breaking for a canonical input: the canon never allowed both declarations (`P35-LD16`).
  An input that relied on a free-form `- <label>: <value>` bullet now gets `UNPARSED_AC_LINE` for it.
- A `0.5.x` reader rejects a `0.6.0` artifact whose warnings carry the new fields (`extra="forbid"`), so every
  reader re-pins to `0.6.0`, which the summary already requires. A collector fills `path`; a consumer places a
  warning by the fields, never by parsing `context`.

## Related

Closes #186

## Acceptance criteria

| # | Criterion | Satisfied at |
|---|---|---|
| 1 | The three-value keyword AC with one covering scenario parses to `aspect == [three values]`, `placeholder_values == {name: values}`, the tag to `AcLink(aspect=<value>)` | `living_doc_utilities/authoring/ac_grammar.py:328-343` (`_read_keyword`), `living_doc_utilities/authoring/scenario.py:57-60`; tested `tests/authoring/test_ac_grammar.py:511`, `tests/authoring/golden/test_golden_feature_files.py:57-82` and `:85` |
| 2 | `Aspect:` + keyword, two keywords, `Aspect:` twice, two-parameter tag → `MALFORMED_AC`, dropped; name not in the text, keyword named `aspect` → `UNPARSED_AC_LINE`; open-segment cases follow the closed format; bare tag stays `AcLink(aspect=None)` | `ac_grammar.py:143` (`declares_two_variants`), `:419-425` (`_build_ac`), `:331` and `:334`; `scenario.py:53` (second parameter), `:55-56` (bare); tested `tests/authoring/test_ac_grammar.py:526`, `:543`, `:554`; `tests/authoring/test_accounting.py:349`; `tests/authoring/test_scenario.py:95` and `:135` |
| 3 | `full_sample` has no AC with both kinds, tested; schema regeneration gate green | `living_doc_utilities/contracts/testing.py:92-101` (`-01`, `Aspect:` only), `:113-120` (`-04`, keyword), `:121-127` (`-05`, `Aspect:` only); tested `tests/contracts/test_testing.py:145`, and `:171` (the samples agree); `tests/contracts/test_schema_export.py::test_committed_schema_is_up_to_date` passes for all six schemas |
| 4 | With aspects: none covered → `not_covered`, some → `partially_covered`; `partially_covered` with no covered aspect fails (Pydantic and schema) | `living_doc_utilities/contracts/coverage_matrix.py:87-97`; `living_doc_utilities/contracts/schema_export.py:208-214`; tested `tests/contracts/test_coverage_matrix.py:127`, `:136`; `tests/contracts/test_schema_export.py:418` (Pydantic + jsonschema) |
| 5 | `CoverageSummary` required on entity and root; disagreeing counts or `coverage_pct` fail; 1 + 0 + 1/3 over three rows = `44.4`; root ≠ mean of entity percentages | `coverage_matrix.py:120-144`, `:167-172`, `:208`, `:221-226`; tested `tests/contracts/test_coverage_matrix.py:248`, `:279`, `:305`, `:314` |
| 6 | Golden corpus re-copied from `a80649b` with the keyword AC and `FUNC-001-01`'s third aspect; `normalisation_cases.yaml` covers the name forms | `tests/fixtures/golden/**` (11 headers name `a80649bd…`, bodies byte-equal to the canon); `tests/fixtures/golden/expected/func-001-validate-password-strength.json:40`; `living_doc_utilities/authoring/normalisation_cases.yaml:673`, `:691`, `:709`, folded by `tests/authoring/test_ac_grammar.py:577` |
| 7 | `ContractWarning` has the optional `entity_id`, `ac_id` (`AC_ID_PATTERN`), `line_no` (`ge=1`), `path`; none of them still validates; an invalid `ac_id` or `line_no: 0` fails; six schemas regenerated | `living_doc_utilities/contracts/envelope.py:140-154`; `living_doc_utilities/contracts/schemas/*-v1.0.0-schema.json` (`ContractWarning`, all six); tested `tests/contracts/test_envelope.py:151`, `:158`, `:174`, `:181`, `:188` (the schema rejects what the model rejects) |
| 8 | Authoring warnings fill the fields they know, `context` keeps its text: header `MALFORMED_AC` valid id → `entity_id`, `ac_id`, `line_no`, no valid id → `entity_id`, `line_no`; `UNPARSED_AC_LINE`, `MISINDENTED_LINE`, `IGNORED_AUTHORED_KEY`, `AUTHORING_WARNING`, `AUTHORING_ERROR` → `entity_id`, `line_no`; `MISSING_ENTITY_ID` → `line_no`; tag `MALFORMED_AC` → `ac_id` (valid id), `line_no` | `living_doc_utilities/authoring/accounting.py:72-90` (`located`), used by `report` `:93`, `missing_title` `:100`, `at_title` `:109`, `structural_warnings` `:135`, `unplaced_lines` `:176`, `first_occurrences` `:261`; `ac_grammar.py:196-202` (`_ExtensionReader._warn`), `:358-361` (`_header_ac_id`), `:364-372` (`criterion_ids`), `:375-383` (`_malformed_header`), `:408`, `:411`, `:424`, `:451` (`_build_ac`), `:572` (`_dropped_lines`); `scenario.py:73-82`; `feature_header.py:153`, `issue_body.py:396` (the map, read before `first_occurrences`); tested `tests/authoring/test_warning_location.py:294` (25 cases, each code in the criterion plus the other modules), `:302` (a criterion under a repeated key), `:319` (context kept); `tests/authoring/test_accounting.py:42` (every line warning's `line_no` equals its context's) |
| 9 | `errors.md` names the four fields; `rendering.md` § Fields by view has the "what was not loaded" row; `shown_paths(generator-ready, inner)` holds the warning paths, `release` none; `full_sample(generator-ready)` carries the three warnings | `docs/contracts/errors.md:22-28`; `docs/contracts/rendering.md:45`, `:49-50`; `living_doc_utilities/contracts/testing.py:508-520` (`shown_paths`), `:320-352` (`_not_loaded_warnings`), `:372`; `docs/contracts/component-checks.md:52`; tested `tests/contracts/test_testing.py:334-352` (table rows), `:367`, `:372` |
| 10 | `rendering.md`, `parsers.md`, `ac-grammar.md`, `errors.md` updated; `make qa` green; `0.6.0` release-notes draft in the PR body | `docs/authoring/ac-grammar.md:106` (§ Variants), `:136-137`; `docs/authoring/parsers.md:34-40` (warning fields), `:199-211`; `docs/contracts/rendering.md:64-66`, `:79-114`; `docs/contracts/errors.md:54`, `:56`; `make qa`: Black, ruff, Pylint 9.91/9.92, mypy, deptry, 1147 passed, 98.72 % coverage, no vendored schema; the new `tests/authoring/test_warning_location.py` is untracked until committed, so it was linted on its own (ruff clean, Pylint 10.00, mypy clean); release notes above |

## Parser output, before (`v0.5.0`) and after

Issue example, header (`parse_acceptance_criteria(text, "FUNC-001")`):

```text
#   AC:FUNC-001-03 (v1.0.0 - active)
#     - Shows the failed {rule} under the password field.
#     - rule: minimum-length, character-classes, no-username
#   AC:FUNC-001-04 (v1.0.0 - active)        # Aspect: plus a keyword
#     - Shows the failed {rule}.
#     - Aspect: desktop, mobile
#     - rule: minimum-length
#   AC:FUNC-001-05 (v1.0.0 - active)        # bullet the text does not name
#     - Shows the failed check.
#     - rule: minimum-length
```

```text
BEFORE
  FUNC-001-03: aspect=[] placeholder_values={'rule': ['minimum-length', 'character-classes', 'no-username']}
  FUNC-001-04: aspect=['desktop', 'mobile'] placeholder_values={'rule': ['minimum-length']}
  FUNC-001-05: aspect=[] placeholder_values={'rule': ['minimum-length']}
  warnings: []
AFTER
  FUNC-001-03: aspect=['minimum-length', 'character-classes', 'no-username'] placeholder_values={'rule': ['minimum-length', 'character-classes', 'no-username']}
  FUNC-001-05: aspect=[] placeholder_values={}
  warnings: [('MALFORMED_AC', 'AC:FUNC-001-04 …'), ('UNPARSED_AC_LINE', "'- rule: minimum-length'")]
  warning fields (code, entity_id, ac_id, line_no):
    ('MALFORMED_AC', 'FUNC-001', 'FUNC-001-04', 4)
    ('UNPARSED_AC_LINE', 'FUNC-001', 'FUNC-001-05', 10)
```

Issue example, tags (`parse_scenarios`):

| Tag | Before | After |
|---|---|---|
| `@AC:FUNC-001-03` | `('FUNC-001-03', None)` | `('FUNC-001-03', None)` |
| `@AC:FUNC-001-03/rule:minimum-length` | `('FUNC-001-03', None)` | `('FUNC-001-03', 'minimum-length')` |
| `@AC:US-1-01/aspect:a/priority:high` | `('US-1-01', 'a')` | no link, `MALFORMED_AC` with `ac_id='US-1-01'`, `line_no` the tag's line |
| `@AC:US-1-01/priority:high` | `('US-1-01', None)` | `('US-1-01', 'high')`; toolkit reports `STALE_AC_REF` if undeclared |

Corpus `gherkin/liv_doc_func/func-001-validate-password-strength.feature` at `a80649b`:

```text
BEFORE
  FUNC-001-01: aspect=['minimum-length', 'character-classes', 'no-username'] placeholder_values={}
  FUNC-001-02: aspect=[] placeholder_values={}
  FUNC-001-03: aspect=[] placeholder_values={'rule': ['minimum-length', 'character-classes', 'no-username']}
  header warnings: []
  Password shorter than the minimum length is rejected       -> [('FUNC-001-01', 'minimum-length')]
  Password missing a required character class is rejected    -> [('FUNC-001-01', 'character-classes')]
  Password containing the username is rejected               -> [('FUNC-001-01', 'no-username')]
  Password shorter than the minimum length shows the …       -> [('FUNC-001-03', None)]
  scenario warnings: []
AFTER
  FUNC-001-01: aspect=['minimum-length', 'character-classes', 'no-username'] placeholder_values={}
  FUNC-001-02: aspect=[] placeholder_values={}
  FUNC-001-03: aspect=['minimum-length', 'character-classes', 'no-username'] placeholder_values={'rule': ['minimum-length', 'character-classes', 'no-username']}
  header warnings: []
  Password shorter than the minimum length is rejected       -> [('FUNC-001-01', 'minimum-length')]
  Password missing a required character class is rejected    -> [('FUNC-001-01', 'character-classes')]
  Password containing the username is rejected               -> [('FUNC-001-01', 'no-username')]
  Password shorter than the minimum length shows the …       -> [('FUNC-001-03', 'minimum-length')]
  scenario warnings: []
```

So `FUNC-001-03` becomes `partially_covered`, 1/3, as the canon says. The canon's own `_expected/` snapshot still
shows it `covered`; it catches up when its collector pin moves to `0.6.0` (`P35-AC1a`).

### Warnings on headers that already warned at `v0.5.0`

Run with `v0.5.0` (`git archive v0.5.0`, `4cc03c8`) and with this branch, each warning dumped as an artifact carries
it (`model_dump(mode="json")`).

```text
    1 | # =====
    2 | # LIVING DOC — US-001 · Sample
    3 | # =====
    4 | # status: Bogus
    5 | # unknown_key: x
    6 | # acceptance_criteria:
    7 | #   AC:US-001-01 (v1.0.0 - activ - x)
    8 | #     - d
    9 | #   AC:US-001-02 (v1.0.0 - active)
   10 | #     - d
   11 | #    odd line
   12 | # =====
   13 |
   14 | Feature: Sample
```

```text
BEFORE
{"code": "IGNORED_AUTHORED_KEY", "message": "'unknown_key:' is not a field this contract carries.", "context": "entity_id='US-001' line_no=5"}
{"code": "MALFORMED_AC", "message": "Acceptance-criterion header is malformed.", "context": "entity='US-001' line_no=7 header='#   AC:US-001-01 (v1.0.0 - activ - x)'"}
{"code": "AUTHORING_WARNING", "message": "Line of a dropped acceptance criterion is not read.", "context": "entity_id='US-001' line_no=8 line='#     - d'"}
{"code": "MISINDENTED_LINE", "message": "Acceptance-criterion block line at indent 3 fits no level and was dropped.", "context": "entity='US-001' header='#   AC:US-001-02 (v1.0.0 - active)' line_no=11 line='odd line'"}
{"code": "MALFORMED_STATUS", "message": "Authored 'state' value 'bogus' failed validation: Input should be 'planned', 'in_review', 'active' or 'deprecated'", "context": "entity_id='US-001' line_no=4"}
AFTER  (code, message, context identical; four keys added)
{… "entity_id": "US-001", "ac_id": null,        "line_no": 5,  "path": null}   IGNORED_AUTHORED_KEY
{… "entity_id": "US-001", "ac_id": "US-001-01", "line_no": 7,  "path": null}   MALFORMED_AC (header unparsable, id valid)
{… "entity_id": "US-001", "ac_id": "US-001-01", "line_no": 8,  "path": null}   AUTHORING_WARNING (line of the dropped criterion)
{… "entity_id": "US-001", "ac_id": "US-001-02", "line_no": 11, "path": null}   MISINDENTED_LINE (line inside a criterion)
{… "entity_id": "US-001", "ac_id": null,        "line_no": 4,  "path": null}   MALFORMED_STATUS
```

A banner with no title line (`# =====` / `# status: active` / `# =====`):

```text
BEFORE {"code": "MISSING_ENTITY_ID", "message": "Feature-header banner carries no 'LIVING DOC — ...' title line.", "context": "title='' line_no=1"}
AFTER  {"code": "MISSING_ENTITY_ID", "message": "Feature-header banner carries no 'LIVING DOC — ...' title line.", "context": "title='' line_no=1", "entity_id": null, "ac_id": null, "line_no": 1, "path": null}
```

**Output changes on existing headers** (decided by the owner, 2026-10-07):

1. Every warning in every artifact gains the keys `entity_id`, `ac_id`, `line_no` and `path`. An unknown one is
   written as `null`, like `context` and every other unknown value in an artifact, not left out. *Kept `null`.*
2. `ac_id` on a header `MALFORMED_AC` is read even from a header too malformed to parse (`AC:` up to a space or
   `(`), when what it reads is a valid id: `AC:US-001-01 v1.0.0 - active` and `AC:US-001-01(v1.0.0 - active` give
   `ac_id='US-001-01'`; `AC:US-1 (…)` and `AC:US-001-01-draft (…)` give `null`. *Kept tolerant.*
3. Beyond the issue's minimum list, every line inside a criterion carries `ac_id` when the criterion's id is valid,
   as the canon's header types § Indentation says ("its criterion when the criterion has a valid id"). *Canon wins.*

   ```text
   UNPARSED_AC_LINE    #     - rule: x                         ac_id='US-001-01'
   MISINDENTED_LINE    #    stray                              ac_id='US-001-01'
   AUTHORING_WARNING   #     - d   (line of a dropped AC)      ac_id='US-001-01'
   AUTHORING_WARNING   #       AC:US-001-02 (…)  (read as text) ac_id='US-001-01'
   AUTHORING_WARNING   ``` block inside ### AC:US-001-01        ac_id='US-001-01'
   AUTHORING_WARNING   #   AC:US-001-02 (…)  under a repeated acceptance_criteria:   ac_id='US-001-02'
   ```

   The repeated key's own line names no criterion: `ac_id=null`.
4. Entity-level warnings (`MISSING_STATUS`, `STATUS_AC_MISMATCH`, `FEATURE_WITHOUT_FUNCTIONALITY`, the relation
   codes) carry `entity_id` only; `MISSING_ENTITY_ID` from an issue title and `HTML_CONTENT_DROPPED` carry none.

## Out of scope

- A `keyword` field on `AcLink` and a name check in `coverage-matrix` (`D39`).
- Computing coverage for a bare tag (`toolkit`, `P35-TK6`).
- A coverage summary per Feature (`D40`).
- Forwarding the warning fields (`toolkit`, `P35-TK1a2`), rendering them (`generator-markdown`, `P35-GM3`) and
  filling `path` (`collector-gh`, `P35-AC1a`); transform warnings such as `STALE_AC_REF`; showing scenario-tag
  warnings anywhere.
- `OUTPUT_PATH` (`P35-UT12`).
