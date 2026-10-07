# Normalisation

## Purpose

Anyone who changes how authored text is cleaned up reads this page. It defines where normalisation runs, the
five source formats, the eight rules, and the generated worked examples.

Read before: [Authoring](../authoring.md) · Next: [Acceptance-criterion grammar](ac-grammar.md)

## Contents

- [Where normalisation runs](#where-normalisation-runs)
- [Source formats](#source-formats)
- [Rules](#rules)
- [Worked examples](#worked-examples)

## Where normalisation runs

- `normalize(text, fmt, entity_type)` absorbs small formatting variance before anything parses the text → `authoring/normalize.py::normalize`
- It runs in three phases → `authoring/normalize.py::normalize_framed`:
  1. Rule 6 on each line's indent, line by line and blind to context → `authoring/normalize.py::_prepare`
  2. The framing pass: where the header starts and ends, and where each root-level section or key begins and ends → `authoring/framing.py::Frame`
  3. Every other rule, line by line, by the section the frame put the line in → `authoring/normalize.py::_rewrite_markdown`
  - Why: framing reads indents, so it needs rule 6 first; every other rule needs to know a line's section.
- A boundary is structural: the frame decides it once, from a line's position and syntax, never its prose → `authoring/framing.py::Frame`
  - Why: a prose test, blind to where its line sits, took a note for a boundary and dropped data silently.
  - A line deeper than an open bullet item's marker is that item's text: never a key, an `AC:` header or a section's end → `authoring/framing.py::BulletItemTracker`
  - A banner's title is the first line after its opening rule, whatever it reads like → `authoring/framing.py::Frame.title`
  - The parser of the format reads the same frame, so the two cannot disagree about where a section runs ([Parsers](parsers.md#common-behaviour)) → `authoring/framing.py::sections`
- The frame reports structural problems only: no frame found, a frame never closed, a key between the header's end and `Feature:`, a line inside the header without its comment marker, an `AC:` line in a criterion block that is read as text, a ` * ` line between a PageObject comment's early `*/` and the header's real end → `authoring/framing.py::Problem`
  - Why: which fields are required is checked above the parser; the parsers stay lenient.
- It rewrites a header only when the header names an entity: its title, found by position, carries an entity id → `authoring/framing.py::names_an_entity`
  - Why: an entity exists only with an id, and only then does a parser read the header; with no header there is nothing to normalise.
  - A text with no header comes back as written, with no change recorded → `tests/authoring/test_normalize.py::test_a_text_with_no_header_is_not_normalised`
  - No line outside the header is rewritten, not even its tabs: a comment above it, in the Gherkin body or in a JSDoc block → `tests/authoring/test_normalize.py::test_a_line_outside_the_header_is_never_rewritten_not_even_its_tabs`
- It rewrites only structural positions: a heading value, a bullet marker, a criterion header's segments, an entity title → `authoring/normalize.py::normalize`
- It never touches fenced code, Gherkin step text, TypeScript or free prose → `tests/authoring/test_normalize_cases.py::test_normalisation_case`
- A rewritten criterion header or bullet keeps the indent its author gave it; only rule 6 changes an indent → `tests/authoring/test_normalize.py::test_feature_header_criterion_header_keeps_its_authors_indent_when_rewritten`
  - Why: a parser reads what a line belongs to from its indent, so moving one line would move it to another parent.
- It never validates a value's meaning; the grammar does that → [Acceptance-criterion grammar](ac-grammar.md)
- It returns the text plus one `Change` per rule fired: `line`, `rule`, `before`, `after` → `authoring/normalize.py::Change`
  - A single rewritten line can produce several entries, one per rule that fired on it (for example separator, casing and version together in one AC header).
- An entity title goes through the same rules 5 and 5b on its own → `authoring/normalize.py::normalize_title`
- One helper marks the lines inside a fenced code block, for both `normalize` and the grammar → `authoring/normalize.py::compute_fence_flags`
  - Why: the two modules can never disagree about where a fence starts or ends.

Which sections hold bullet lists, per entity type → `authoring/normalize.py::TYPE_PROFILES`:

| Entity type | Bullet sections |
|---|---|
| `DocumentedUserStory` | `business_value`, `preconditions`, `not_in_scope`, `notes` |
| `DocumentedFeature` | `notes` |
| `DocumentedFunctionality` | `rationale`, `preconditions`, `not_in_scope`, `notes` |

## Source formats

Five formats exist → `authoring/normalize.py::SourceFormat`. Content lines are the lines `normalize` inspects;
every other line passes through byte for byte.

| Format | Content lines | Parsed by |
|---|---|---|
| `ISSUE_BODY` | a GitHub issue body's Markdown, split on `##` headings | `issue_body.parse_issue_body` |
| `FEATURE_HEADER` | a `.feature` file's `# key: value` / `# key:` block, from its first `# ===` rule above `Feature:` to its last, when its title names an entity | `feature_header.parse_feature_header` |
| `SCENARIO_FILE` | a `.feature` file's Gherkin body: only its `# AC:` comment lines; scenario, step and tag lines pass through | `scenario.parse_scenarios` |
| `PAGE_OBJECT` | a PageObject file's leading `/* ... */` comment: its `* key: value` lines, when its title names an entity | `page_object.parse_page_object` |
| `HTML_MARKDOWN` | the text `convert_html_to_markdown` makes from Azure DevOps HTML; the same rules as `ISSUE_BODY` | `html_to_markdown.convert_html_to_markdown`, then `issue_body.parse_issue_body` |

- `HTML_MARKDOWN` shares the Markdown frame and rules with `ISSUE_BODY` → `authoring/normalize.py::_rewrite_markdown`
  - Why: once the HTML is flattened to text, the two are structurally identical.

## Rules

Eight rules exist: 1 to 7, plus 5b, a sibling of rule 5. Each rule reshapes a token by its position in a line.
None of them knows the state vocabulary or the strict version shape; the [grammar](ac-grammar.md) owns those.

### Rule 1: bullet marker

`bullet_marker` → `authoring/normalize.py::RULE_BULLET_MARKER`:

- Rewrites: a leading `–`, `—`, `•`, `*` or `+` bullet marker to `-`, in a criterion block or a bullet section.
- Never touches: a bullet-shaped character that is not the leading marker, or a line outside a bullet section or criterion block.
  - A Gherkin `*` step and a PageObject ` * key: value` line both start with `*` and stay untouched.
  - In a PageObject header it reaches only the items of a `PO_BULLET_KEYS` key, inside the header comment's frame, so a later JSDoc block is never rewritten → `tests/authoring/test_notes.py::test_rule_one_does_not_reach_a_jsdoc_notes_block_further_down_the_file`
    - The frame ends at the first line that ends in `*/`: the canon's banner form or a bare ` */` → `tests/authoring/test_framing.py::test_the_canon_banner_and_a_bare_close_both_end_the_frame`
    - A `*/` inside a value does not end it, so rule 1 still reaches the items after that value → `tests/authoring/test_framing.py::test_a_comment_close_inside_a_value_does_not_end_the_frame`
- Why: authors, autocorrect and drafting aids emit an en-dash or a bullet dot; every extractor recognises only `-`.
- Breaks if removed: the item is glued onto the previous bullet or reported as `UNPARSED_AC_LINE`; the entry is lost.

### Rule 2: criterion header separator

`ac_header_separator` → `authoring/normalize.py::RULE_AC_HEADER_SEPARATOR`:

- Rewrites: the separator between segments in `AC:<id> (<version> - <state>[ - removal planned <version>])` to exactly `" - "`.
- Never touches: a hyphen inside a state token (`in-review`); the separator needs whitespace on at least one side.
- Why: the grammar splits the header on the literal `" - "` and has no dash tolerance of its own.
- Breaks if removed: the grammar cannot split the header and drops the whole criterion as `MALFORMED_AC`.

### Rule 3: state casing

`state_casing` → `authoring/normalize.py::RULE_STATE_CASING`:

- Rewrites: a `## Status` / `status:` value or a header's state segment to lowercase, spaces and hyphens to one `_` (`In Review` → `in_review`).
- Also folds the fixed phrase `Removal Planned` to `removal planned`.
- Never touches: any other word, including prose that mentions a state word ("the Active tab").
- Why: the vocabulary is lowercase with underscores, checked in one place; a capitalised status must not fail it.
- Breaks if removed: a header is rejected, or an unnormalised status fails `ParsedEntity` validation, is dropped, and is reported as `MALFORMED_STATUS`; status derivation then treats it as missing.

### Rule 4: version form

`version_form` → `authoring/normalize.py::RULE_VERSION_FORM`:

- Rewrites: a version token to `vX.Y.Z` with a lowercase `v` and three parts: `V1.2`, `1.2` and `v1.2` become `v1.2.0`.
- Never touches: a version with no minor part (`v1`); the grammar then reports it as `MALFORMED_AC`.
  - Why: with no minor digit there is nothing to infer a patch number from.
- Why: a stored version is checked against a strict shape ([version format](../contracts/entities-and-state.md#version-format)); authors often omit the patch.
- Breaks if removed: `v1.2` or `V1.2.0` fails the grammar's exact version check, and the criterion is dropped.

### Rule 5: entity name dash

`entity_name_dash` → `authoring/normalize.py::RULE_ENTITY_NAME_DASH`:

- Rewrites: the dash between the two halves of a compound name to `" - "` (`Login Page–Validate Password Strength`).
- In a `.feature` or PageObject banner it reaches only the line the frame placed as the title, and only when that line reads `LIVING DOC` → `authoring/normalize.py::_emit_title`
- An en-dash or em-dash always; a plain hyphen only with whitespace on at least one side.
- Never touches: a hyphen inside a word, such as `Password-reset` or `Sign-in`.
- Why: renderers and comparisons expect one separator; autocorrect turns a typed `-` into a dash.
- Breaks if removed: nothing fails, but two names that differ only by dash no longer compare equal.

### Rule 5b: title id separator

`title_id_separator` → `authoring/normalize.py::RULE_TITLE_ID_SEPARATOR`:

- Rewrites: the character right after an entity id in a title to `" · "`: `US-001 - Customer Login` → `US-001 · Customer Login`.
- Never touches: anything before the id, such as a `LIVING DOC — ` prefix or a historical `GH-` prefix.
- Why: issue titles and both comment banners (`LIVING DOC — <id> · <title>`) converge on one separator here.
- Breaks if removed: the id is still found, but each surface renders its title separator differently.

### Rule 6: whitespace

`whitespace` → `authoring/normalize.py::RULE_WHITESPACE`:

- Rewrites: CRLF line endings to LF, in every format.
- Rewrites: a leading byte-order mark away, in every format — it belongs to the encoding, and left in place it would keep the first line from matching the opening rule → `tests/authoring/test_framing.py::test_a_leading_byte_order_mark_does_not_move_the_frames_start`
- Runs first, on every line that has text, before the frame is decided; a whitespace-only line stays as written → `authoring/normalize.py::_prepare`
- Rewrites: each tab or non-breaking space in a line's leading indentation to one space, in a PageObject header and a `.feature` header → `authoring/normalize.py::_fix_indentation_whitespace`
  - The indent is counted after the comment marker and at most one space (`# `, ` * `).
  - A tab right after the marker becomes the marker's own space: `#<tab>x` reads as `# x`, at indent 0, for every reader → `authoring/normalize.py::_prepared`
  - One character becomes one space, so tab-indented lines keep their levels relative to each other.
- Rewrites: in an issue body, each non-breaking space in a line's leading indentation to one space, and each tab to the next multiple of 4 columns → `authoring/normalize.py::_prepare`
  - Why 4: GitHub renders a tab to that stop, so the parser sees the levels the reader sees, even where tabs and spaces mix (`    - B` then `\t- C` are siblings).
  - A tab moves to the next stop, it does not add 4: two spaces and a tab are 4 columns, not 6.
  - A header keeps one space per tab: nothing renders it, and its indent starts after the comment marker, not at a tab stop.
- Records each rewritten line as a `whitespace` change → `tests/authoring/test_normalize.py::test_feature_header_rule_6_is_recorded_per_line_with_its_before_and_after`
- Never touches: a tab or non-breaking space inside a value, past its leading indentation, or any line of a fenced code block.
- Why: a stray `\r` breaks comparisons, and a parser decides what a line belongs to by its indent in spaces ([Parsers, common behaviour](parsers.md#common-behaviour)).
- Breaks if removed: a trailing `\r` corrupts equality checks and golden tests; a tab-indented line has no defined level, so an item or a sub-list can attach to the wrong parent.

### Rule 7: inline criterion description

`inline_ac_description` → `authoring/normalize.py::RULE_INLINE_AC_DESCRIPTION`:

- Rewrites: a description written on the header line (`AC:US-001-01 (v1.0.0 - active) — the description`) onto its own `- ` bullet.
- Applies to the issue-body and feature-header formats, whose grammar expects the description as a bullet.
- In a `.feature` header the new bullet sits two spaces deeper than its header, wherever the header is → `tests/authoring/test_normalize.py::test_feature_header_split_description_sits_one_level_below_its_header`
- Never touches: a scenario-file `# AC:` comment's inline description; only its separator is canonicalised.
- Why: the grammar reads the description only as the block's first bullet; inline text would be lost.
- Breaks if removed: the block has no description bullet, so the criterion is dropped with a `MALFORMED_AC` warning; the header still parses.

## Worked examples

- Generated from `living_doc_utilities/authoring/normalisation_cases.yaml` by `make docs` → `authoring/docs_export.py::regenerate`
- The same file is the test data: `tests/authoring/test_normalize_cases.py` runs every row → `tests/authoring/test_normalize_cases.py::test_normalisation_case`
- Do not hand-edit the table; CI fails the build when it drifts → `.github/workflows/test.yml::docs-regeneration-check`

<!-- over limit: generated, one row per test case in normalisation_cases.yaml -->
<!-- BEGIN GENERATED: normalisation-examples -->
| ID | Rule | Format | Entity type | Before | After | Note |
|---|---|---|---|---|---|---|
| rule1_bullet_marker_en_dash_business_value | bullet_marker | issue_body | DocumentedUserStory | `## Business Value`<br><br>`– Registered customers can reach their account area.` | `## Business Value`<br><br>`- Registered customers can reach their account area.` | An en-dash bullet in a bullet section (the glossary/agentic-toolkit form) is silently corrected, not dropped - the defect this package replaces. |
| rule1_bullet_marker_star_rationale_feature_header | bullet_marker | feature_header | DocumentedFunctionality | `# =====`<br>`# LIVING DOC — FUNC-001 · Validate Password Strength`<br>`# =====`<br>`# rationale:`<br>`#   * Password strength is checked client-side for immediate feedback.`<br>`# =====` | `# =====`<br>`# LIVING DOC — FUNC-001 · Validate Password Strength`<br>`# =====`<br>`# rationale:`<br>`#   - Password strength is checked client-side for immediate feedback.`<br>`# =====` | A "*" bullet inside a bullet section becomes "-"; the "#" comment prefix stays. |
| rule1_bullet_marker_plus_not_in_scope_feature_header | bullet_marker | feature_header | DocumentedUserStory | `# =====`<br>`# LIVING DOC — US-001 · Customer Login`<br>`# =====`<br>`# not_in_scope:`<br>`#   + Social-identity (OAuth) sign-in.`<br>`# =====` | `# =====`<br>`# LIVING DOC — US-001 · Customer Login`<br>`# =====`<br>`# not_in_scope:`<br>`#   - Social-identity (OAuth) sign-in.`<br>`# =====` | A "+" bullet is also corrected, matching rule 1's marker set. |
| rule1_bullet_marker_bullet_dot_ac_block | bullet_marker | issue_body | DocumentedFunctionality | `### AC:FUNC-001-01 (v1.0.0 - active)`<br><br>`• Returns valid=false when the candidate password fails a complexity rule.` | `### AC:FUNC-001-01 (v1.0.0 - active)`<br><br>`- Returns valid=false when the candidate password fails a complexity rule.` | A "•" bullet inside an AC block is corrected, independent of TYPE_PROFILES. |
| rule1_bullet_marker_bullet_dot_notes_page_object | bullet_marker | page_object | DocumentedFeature | `/* =============================================================================`<br>` * LIVING DOC — FEAT-001 · Login Page`<br>` * =====`<br>` * page-object:           LoginPage.ts`<br>` * notes:`<br>` *   • The sign-in form markup comes from the shared identity template.`<br>` *   - The screen is called "Sign in" to customers.`<br>` * ============================================================================= */` | `/* =============================================================================`<br>` * LIVING DOC — FEAT-001 · Login Page`<br>` * =====`<br>` * page-object:           LoginPage.ts`<br>` * notes:`<br>` *   - The sign-in form markup comes from the shared identity template.`<br>` *   - The screen is called "Sign in" to customers.`<br>` * ============================================================================= */` | A PageObject header's "notes:" list is its one bullet section, so rule 1 corrects its markers there too. Mixing markers is the case that would otherwise merge the two notes into one entry with no warning: the "•" item has no marker the reader knows, so it joins the open item. |
| never_touched_page_object_jsdoc_after_the_header | none | page_object | DocumentedFeature | `/* =============================================================================`<br>` * page-object:           LoginPage.ts`<br>` * ============================================================================= */`<br><br>`export class LoginPage {`<br>`  /**`<br>`   * notes:`<br>`   *   • Not a living-doc note; a JSDoc line of its own.`<br>`   */`<br>`  async goto(): Promise<void> {}`<br>`}` | `/* =============================================================================`<br>` * page-object:           LoginPage.ts`<br>` * ============================================================================= */`<br><br>`export class LoginPage {`<br>`  /**`<br>`   * notes:`<br>`   *   • Not a living-doc note; a JSDoc line of its own.`<br>`   */`<br>`  async goto(): Promise<void> {}`<br>`}` | The header comment's "*/" closes rule 1 for the rest of the file, so a later JSDoc block with a "notes:" line of its own keeps its markers: normalisation never rewrites TypeScript. |
| rule2_ac_header_separator_en_dash_issue_body | ac_header_separator | issue_body | DocumentedUserStory | `### AC:US-001-01 (v1.0.0 – active)`<br><br>`- A customer who submits valid credentials lands on the account dashboard.` | `### AC:US-001-01 (v1.0.0 - active)`<br><br>`- A customer who submits valid credentials lands on the account dashboard.` | An en-dash separator inside an AC header's parentheses becomes " - ". |
| rule2_ac_header_separator_em_dash_feature_header | ac_header_separator | feature_header | DocumentedFunctionality | `# =====`<br>`# LIVING DOC — FUNC-001 · Validate Password Strength`<br>`# =====`<br>`# acceptance_criteria:`<br>`#   AC:FUNC-001-01 (v1.0.0 — active)`<br>`#     - Returns valid=false when the candidate password fails a complexity rule.`<br>`# =====` | `# =====`<br>`# LIVING DOC — FUNC-001 · Validate Password Strength`<br>`# =====`<br>`# acceptance_criteria:`<br>`#   AC:FUNC-001-01 (v1.0.0 - active)`<br>`#     - Returns valid=false when the candidate password fails a complexity rule.`<br>`# =====` | An em-dash separator is corrected the same way as an en-dash. |
| rule3_state_casing_status_heading_issue_body | state_casing | issue_body | DocumentedUserStory | `## Status`<br><br>`ACTIVE` | `## Status`<br><br>`active` | A "## Status" value's case is normalised even with no dash/hyphen to collapse. |
| rule3_state_casing_status_key_feature_header | state_casing | feature_header | DocumentedFunctionality | `# =====`<br>`# LIVING DOC — FUNC-001 · Validate Password Strength`<br>`# =====`<br>`# status:          In Review`<br>`# =====` | `# =====`<br>`# LIVING DOC — FUNC-001 · Validate Password Strength`<br>`# =====`<br>`# status:          in_review`<br>`# =====` | "In Review" collapses to "in_review" in a "# status:" value. |
| rule3_state_casing_ac_header_issue_body | state_casing | issue_body | DocumentedUserStory | `### AC:US-001-01 (v1.0.0 - ACTIVE)`<br><br>`- desc` | `### AC:US-001-01 (v1.0.0 - active)`<br><br>`- desc` | The AC header's own state token is lowercased the same way. |
| rule3_state_casing_ac_header_feature_header_keeps_indent | state_casing | feature_header | DocumentedUserStory | `# =====`<br>`# LIVING DOC — US-001 · Customer Login`<br>`# =====`<br>`# acceptance_criteria:`<br>`# AC:US-001-01 (v1.0.0 - Active)`<br>`# - Valid credentials land on the dashboard.`<br>`# =====` | `# =====`<br>`# LIVING DOC — US-001 · Customer Login`<br>`# =====`<br>`# acceptance_criteria:`<br>`# AC:US-001-01 (v1.0.0 - active)`<br>`# - Valid credentials land on the dashboard.`<br>`# =====` | A rewritten header keeps its author's indent, so its bullets stay where they belong. |
| rule3_state_casing_removal_planned_keyword | state_casing | issue_body | DocumentedUserStory | `### AC:US-001-04 (v1.0.0 - deprecated - Removal Planned v2.0.0)`<br><br>`- desc` | `### AC:US-001-04 (v1.0.0 - deprecated - removal planned v2.0.0)`<br><br>`- desc` | "Removal Planned" is lowercased to the fixed keyword phrase "removal planned". |
| rule4_version_form_short_issue_body | version_form | issue_body | DocumentedUserStory | `### AC:US-001-03 (v1.1 - planned)`<br><br>`- A customer who forgot the password can request a reset link.` | `### AC:US-001-03 (v1.1.0 - planned)`<br><br>`- A customer who forgot the password can request a reset link.` | vX.Y becomes vX.Y.0. |
| rule4_version_form_bare_numeric_feature_header | version_form | feature_header | DocumentedFunctionality | `# =====`<br>`# LIVING DOC — FUNC-001 · Validate Password Strength`<br>`# =====`<br>`# acceptance_criteria:`<br>`#   AC:FUNC-001-02 (1.0.0 - active)`<br>`#     - Returns valid=true when the candidate password satisfies every rule.`<br>`# =====` | `# =====`<br>`# LIVING DOC — FUNC-001 · Validate Password Strength`<br>`# =====`<br>`# acceptance_criteria:`<br>`#   AC:FUNC-001-02 (v1.0.0 - active)`<br>`#     - Returns valid=true when the candidate password satisfies every rule.`<br>`# =====` | A bare "1.0.0" gains the canonical leading "v". |
| rule4_version_form_capital_v_issue_body | version_form | issue_body | DocumentedUserStory | `### AC:US-001-01 (V1.0.0 - active)`<br><br>`- desc` | `### AC:US-001-01 (v1.0.0 - active)`<br><br>`- desc` | "V1.0.0" is lowercased to "v1.0.0". |
| rule4_version_form_v1_left_as_is | none | issue_body | DocumentedUserStory | `### AC:US-001-01 (v1 - active)`<br><br>`- desc` | `### AC:US-001-01 (v1 - active)`<br><br>`- desc` | "v1" alone has no digit to infer a patch version from - normalize leaves it unchanged (a malformed-acceptance-criterion error for ac_grammar, not normalize). |
| rule5_entity_name_dash_functionality_title | entity_name_dash | feature_header | DocumentedFunctionality | `# =============================================================================`<br>`# LIVING DOC — FUNC-001 · Login Page–Validate Password Strength`<br>`# =============================================================================`<br>`# status:    active` | `# =============================================================================`<br>`# LIVING DOC — FUNC-001 · Login Page - Validate Password Strength`<br>`# =============================================================================`<br>`# status:    active` | An en-dash between the two halves of a Functionality name becomes " - ". |
| rule5b_title_id_separator_hyphen_feature_header | title_id_separator | feature_header | DocumentedUserStory | `# =============================================================================`<br>`# LIVING DOC — US-001 - Customer Login`<br>`# =============================================================================`<br>`# status:    active` | `# =============================================================================`<br>`# LIVING DOC — US-001 · Customer Login`<br>`# =============================================================================`<br>`# status:    active` | The character right after the entity id becomes " · ", even a plain hyphen. |
| rule5b_title_id_separator_colon_page_object | title_id_separator | page_object | DocumentedFeature | `/* =============================================================================`<br>` * LIVING DOC — FEAT-001: Login Page`<br>` * =============================================================================`<br>` * surface_type:          UI`<br>` * ============================================================================= */` | `/* =============================================================================`<br>` * LIVING DOC — FEAT-001 · Login Page`<br>` * =============================================================================`<br>` * surface_type:          UI`<br>` * ============================================================================= */` | A colon right after the entity id in a PageObject banner also becomes " · ". |
| rule6_whitespace_crlf_issue_body | whitespace | issue_body | DocumentedUserStory | `## Status\r`<br>`\r`<br>`active\r` | `## Status`<br><br>`active` | CRLF line endings become LF. |
| rule6_whitespace_tab_indentation_page_object | whitespace | page_object | DocumentedFeature | `/* =============================================================================`<br>` * LIVING DOC — FEAT-001 · Login Page`<br>` * =====`<br>` *	surface_type:          UI`<br>` * ============================================================================= */` | `/* =============================================================================`<br>` * LIVING DOC — FEAT-001 · Login Page`<br>` * =====`<br>` * surface_type:          UI`<br>` * ============================================================================= */` | A tab used to indent a field's value becomes a plain space; the value itself is untouched. |
| rule6_whitespace_tab_indentation_feature_header | whitespace | feature_header | DocumentedUserStory | `# =====`<br>`# LIVING DOC — US-001 · Customer Login`<br>`# =====`<br>`# business_value:`<br>`#	- Fewer support calls.`<br>`#		A wrapped line.`<br>`# =====` | `# =====`<br>`# LIVING DOC — US-001 · Customer Login`<br>`# =====`<br>`# business_value:`<br>`# - Fewer support calls.`<br>`#  A wrapped line.`<br>`# =====` | Each tab or no-break space in a header line's indent becomes one space, so the relative levels stay. |
| rule6_whitespace_nbsp_indentation_feature_header | whitespace | feature_header | DocumentedUserStory | `# =====`<br>`# LIVING DOC — US-001 · Customer Login`<br>`# =====`<br>`# business_value:`<br>`#   - Fewer support calls.`<br>`# =====` | `# =====`<br>`# LIVING DOC — US-001 · Customer Login`<br>`# =====`<br>`# business_value:`<br>`#   - Fewer support calls.`<br>`# =====` | A no-break space in a header line's indent becomes one space. |
| rule6_whitespace_tab_indentation_issue_body | whitespace | issue_body | DocumentedUserStory | `## Business Value`<br><br>`- Login works on every supported browser.`<br>`    - Chrome and Firefox.`<br>`	- Safari.` | `## Business Value`<br><br>`- Login works on every supported browser.`<br>`    - Chrome and Firefox.`<br>`    - Safari.` | An issue-body tab moves to GitHub's next tab stop of 4, so a tab-indented item is the sibling a reader sees. |
| rule6_whitespace_tab_after_spaces_issue_body | whitespace | issue_body | DocumentedUserStory | `## Business Value`<br><br>`- Login works on every supported browser.`<br>`  	- Safari.` | `## Business Value`<br><br>`- Login works on every supported browser.`<br>`    - Safari.` | A tab moves to the next stop, it does not add 4 - two spaces and a tab are 4 columns, not 6. |
| rule6_whitespace_nbsp_indentation_issue_body | whitespace | issue_body | DocumentedUserStory | `## Business Value`<br><br>`- Login works on every supported browser.`<br>`  - Safari.` | `## Business Value`<br><br>`- Login works on every supported browser.`<br>`  - Safari.` | A no-break space in an issue-body indent becomes one space. |
| rule7_inline_ac_description_issue_body_split | inline_ac_description | issue_body | DocumentedUserStory | `### AC:US-001-01 (v1.0.0 - active) — customer places an order with a saved payment method` | `### AC:US-001-01 (v1.0.0 - active)`<br>`- customer places an order with a saved payment method` | An inline description on the header line moves onto its own bullet. |
| rule7_inline_ac_description_feature_header_split | inline_ac_description | feature_header | DocumentedFunctionality | `# =====`<br>`# LIVING DOC — FUNC-001 · Validate Password Strength`<br>`# =====`<br>`# acceptance_criteria:`<br>`#   AC:FUNC-001-01 (v1.0.0 - active) - rejects a weak password`<br>`# =====` | `# =====`<br>`# LIVING DOC — FUNC-001 · Validate Password Strength`<br>`# =====`<br>`# acceptance_criteria:`<br>`#   AC:FUNC-001-01 (v1.0.0 - active)`<br>`#     - rejects a weak password`<br>`# =====` | Same split for a feature-header AC block, keeping the "#" comment prefix. |
| rule7_inline_ac_description_scenario_file_inline | inline_ac_description | scenario_file | DocumentedUserStory | `# AC:US-001-01 (v1.0.0 - active) — valid credentials land on the account dashboard`<br>`@AC:US-001-01`<br>`Scenario: Customer signs in with valid credentials` | `# AC:US-001-01 (v1.0.0 - active) - valid credentials land on the account dashboard`<br>`@AC:US-001-01`<br>`Scenario: Customer signs in with valid credentials` | A "# AC:" comment keeps its description inline - only the separator before it is canonicalised, no line is inserted. |
| rule2_rule3_rule4_scenario_file_combined | ac_header_separator | scenario_file | DocumentedFunctionality | `# AC:FUNC-001-01 (v1.0 – ACTIVE) - rejects a weak password \| aspect: minimum length`<br>`@AC:FUNC-001-01/aspect:minimum-length` | `# AC:FUNC-001-01 (v1.0.0 - active) - rejects a weak password \| aspect: minimum length`<br>`@AC:FUNC-001-01/aspect:minimum-length` | Rules 2, 3 and 4 all fire on one scenario-file "# AC:" line; the "\| aspect: ..." suffix is free text and stays untouched. |
| html_markdown_ac_header_defect_corrected | ac_header_separator | html_markdown | DocumentedUserStory | `### AC:US-001-01 (v1.0.0 – active)`<br><br>`- A customer who submits valid credentials lands on the account dashboard.` | `### AC:US-001-01 (v1.0.0 - active)`<br><br>`- A customer who submits valid credentials lands on the account dashboard.` | html_markdown (Azure DevOps HTML converted to markdown) uses the same rules. |
| agentic_toolkit_descope_fixture | bullet_marker | issue_body | DocumentedUserStory | `AC:US-042-03 (v1.2.0 – descoped)`<br>`   – Promo codes can be stacked and applied in defined priority order.`<br>`   – descoped_at: 2026-05-15`<br>`   – descoped_reason: Promo stacking rule deferred — too complex for current sprint`<br>`   – future_release: sprint-52` | `AC:US-042-03 (v1.2.0 - descoped)`<br>`   - Promo codes can be stacked and applied in defined priority order.`<br>`   - descoped_at: 2026-05-15`<br>`   - descoped_reason: Promo stacking rule deferred — too complex for current sprint`<br>`   - future_release: sprint-52` | tests/fixtures/agentic_toolkit_descope.md's AC block (agentic-toolkit@c479c80, skills/living-doc-update/SKILL.md's descope example), bare "AC:" line and all - a header with no markdown "###" wrapper is still recognised. The prose em-dash inside "deferred — too complex" is untouched: it is not a structural position. |
| never_touched_page_object_metadata | none | page_object | DocumentedFeature | `/* =============================================================================`<br>` * LIVING DOC — FEAT-001 · Login Page`<br>` * =============================================================================`<br>` * surface_type:          UI`<br>` * route:                 /login`<br>` * owners:                Identity Team`<br>` * stub-reason:           Login template carries no test-id attributes yet;`<br>` *                        surface documented from the interface spec - discovered 2026-09-08.`<br>` * purpose:               The screen where a registered customer enters an email and password to sign in.`<br>` * user_stories:          US-001`<br>` * functionalities:       FUNC-001`<br>` * external_dependencies: auth-api`<br>` * page-object:           LoginPage.ts`<br>` * ============================================================================= */` | `/* =============================================================================`<br>` * LIVING DOC — FEAT-001 · Login Page`<br>` * =============================================================================`<br>` * surface_type:          UI`<br>` * route:                 /login`<br>` * owners:                Identity Team`<br>` * stub-reason:           Login template carries no test-id attributes yet;`<br>` *                        surface documented from the interface spec - discovered 2026-09-08.`<br>` * purpose:               The screen where a registered customer enters an email and password to sign in.`<br>` * user_stories:          US-001`<br>` * functionalities:       FUNC-001`<br>` * external_dependencies: auth-api`<br>` * page-object:           LoginPage.ts`<br>` * ============================================================================= */` | A naive bullet-character rule over raw text would corrupt every " * key: value" line here (each starts with "*"); normalize leaves every field, and the already- canonical title line, byte-for-byte unchanged. |
| never_touched_gherkin_star_steps | none | scenario_file | DocumentedUserStory | `Scenario: Customer signs in with valid credentials`<br>`  * a registered customer is on the login screen`<br>`  * the customer submits valid credentials`<br>`  * the account dashboard is displayed` | `Scenario: Customer signs in with valid credentials`<br>`  * a registered customer is on the login screen`<br>`  * the customer submits valid credentials`<br>`  * the account dashboard is displayed` | Gherkin's "*" step keyword is never touched - only "# AC:" comment lines are content in a scenario file. |
| never_touched_fenced_code_block_issue_body | none | issue_body | DocumentedFunctionality | `## Description`<br><br>`Example payload:`<br><br>```json<br>`{"status": "active", "items": ["a", "b"]}`<br>``` | `## Description`<br><br>`Example payload:`<br><br>```json<br>`{"status": "active", "items": ["a", "b"]}`<br>``` | A fenced code block is never touched, even though it contains the word "active". |
| never_touched_tab_in_fenced_code_block_issue_body | none | issue_body | DocumentedUserStory | `## Description`<br><br>```<br>`	indented_with_a_tab()`<br>``` | `## Description`<br><br>```<br>`	indented_with_a_tab()`<br>``` | Rule 6 never touches a fenced code block; its tabs are the code's own. |
| never_touched_tilde_fenced_code_block_issue_body | none | issue_body | DocumentedFunctionality | `## Description`<br><br>`Example AC header shown as a worked example:`<br><br>`~~~`<br>`AC:US-999-01 (v9.9.9 - active)`<br>`~~~` | `## Description`<br><br>`Example AC header shown as a worked example:`<br><br>`~~~`<br>`AC:US-999-01 (v9.9.9 - active)`<br>`~~~` | A "~~~"-fenced code block is never touched either - not only the backtick form. |
| never_touched_prose_en_dash_issue_body | none | issue_body | DocumentedUserStory | `## Description`<br><br>`As a registered customer – who values speed – I can sign in with my email and`<br>`password, so that I can reach my account area.` | `## Description`<br><br>`As a registered customer – who values speed – I can sign in with my email and`<br>`password, so that I can reach my account area.` | Free prose keeps its en-dashes; only structural positions are rewritten. |
| never_touched_scalar_field_feature_header | none | feature_header | DocumentedFunctionality | `# source:    https://github.com/example/repo/issues/42`<br>`# parent:    FEAT-001`<br>`# func_type: field_validation` | `# source:    https://github.com/example/repo/issues/42`<br>`# parent:    FEAT-001`<br>`# func_type: field_validation` | Scalar keys other than "status" are never rewritten (no state lives in them). |
| never_touched_ac_keyword_name_capitalised | none | feature_header | DocumentedUserStory | `# acceptance_criteria:`<br>`#   AC:US-001-01 (v1.0.0 - active)`<br>`#     - Shows an error under the {field} input.`<br>`#     - Field: username, password` | `# acceptance_criteria:`<br>`#   AC:US-001-01 (v1.0.0 - active)`<br>`#     - Shows an error under the {field} input.`<br>`#     - Field: username, password` | A keyword's name keeps its authored case: normalize rewrites no name. The AC grammar folds "Field" to "field", the slug of "{field}", so the bullet is the AC's keyword. |
| never_touched_ac_keyword_name_with_a_space | none | feature_header | DocumentedUserStory | `# acceptance_criteria:`<br>`#   AC:US-001-01 (v1.0.0 - active)`<br>`#     - A {user-role} lands on their own dashboard.`<br>`#     - user role: customer, guest` | `# acceptance_criteria:`<br>`#   AC:US-001-01 (v1.0.0 - active)`<br>`#     - A {user-role} lands on their own dashboard.`<br>`#     - user role: customer, guest` | A space in a keyword's name is left as written; the AC grammar folds "user role" and "{user-role}" to the one slug "user_role" (case, "-", "_" and space equal). |
| never_touched_ac_keyword_name_with_a_hyphen | none | feature_header | DocumentedUserStory | `# acceptance_criteria:`<br>`#   AC:US-001-01 (v1.0.0 - active)`<br>`#     - A {User Role} lands on their own dashboard.`<br>`#     - user-role: customer, guest` | `# acceptance_criteria:`<br>`#   AC:US-001-01 (v1.0.0 - active)`<br>`#     - A {User Role} lands on their own dashboard.`<br>`#     - user-role: customer, guest` | The canon's kebab-case name: "user-role" and "{User Role}" fold to the same slug "user_role" as the space form, so all three spellings name one keyword. |
<!-- END GENERATED: normalisation-examples -->
