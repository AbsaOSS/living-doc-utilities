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
- It rewrites only structural positions: a heading value, a bullet marker, a criterion header's segments, an entity title → `authoring/normalize.py::normalize`
- It never touches fenced code, Gherkin step text, TypeScript or free prose → `tests/authoring/test_normalize_cases.py::test_normalisation_case`
- It never validates a value's meaning; the grammar does that → [Acceptance-criterion grammar](ac-grammar.md)
- It returns the text plus one `Change` per rule fired: `line`, `rule`, `before`, `after` → `authoring/normalize.py::Change`
  - A single rewritten line can produce several entries, one per rule that fired on it (for example separator, casing and version together in one AC header).
- An entity title goes through the same rules 5 and 5b on its own → `authoring/normalize.py::normalize_title`
- One helper marks the lines inside a fenced code block, for both `normalize` and the grammar → `authoring/normalize.py::compute_fence_flags`
  - Why: the two modules can never disagree about where a fence starts or ends.

Which sections hold bullet lists, per entity type → `authoring/normalize.py::TYPE_PROFILES`:

| Entity type | Bullet sections |
|---|---|
| `DocumentedUserStory` | `business_value`, `preconditions`, `not_in_scope` |
| `DocumentedFeature` | none |
| `DocumentedFunctionality` | `rationale`, `preconditions`, `not_in_scope` |

## Source formats

Five formats exist → `authoring/normalize.py::SourceFormat`. Content lines are the lines `normalize` inspects;
every other line passes through byte for byte.

| Format | Content lines | Parsed by |
|---|---|---|
| `ISSUE_BODY` | a GitHub issue body's Markdown, split on `##` headings | `issue_body.parse_issue_body` |
| `FEATURE_HEADER` | a `.feature` file's leading `# key: value` / `# key:` block between its two `# ===` banner lines | `feature_header.parse_feature_header` |
| `SCENARIO_FILE` | a `.feature` file's Gherkin body: only its `# AC:` comment lines; scenario, step and tag lines pass through | `scenario.parse_scenarios` |
| `PAGE_OBJECT` | a PageObject file's leading `/* ... */` comment: its `* key: value` lines | `page_object.parse_page_object` |
| `HTML_MARKDOWN` | the text `convert_html_to_markdown` makes from Azure DevOps HTML; the same rules as `ISSUE_BODY` | `html_to_markdown.convert_html_to_markdown`, then `issue_body.parse_issue_body` |

- `HTML_MARKDOWN` shares the Markdown handler with `ISSUE_BODY` → `authoring/normalize.py::_normalize_markdown`
  - Why: once the HTML is flattened to text, the two are structurally identical.

## Rules

Eight rules exist: 1 to 7, plus 5b, a sibling of rule 5. Each rule reshapes a token by its position in a line.
None of them knows the state vocabulary or the strict version shape; the [grammar](ac-grammar.md) owns those.

### Rule 1: bullet marker

`bullet_marker` → `authoring/normalize.py::RULE_BULLET_MARKER`:

- Rewrites: a leading `–`, `—`, `•`, `*` or `+` bullet marker to `-`, in a criterion block or a bullet section.
- Never touches: a bullet-shaped character that is not the leading marker, or a line outside a bullet section or criterion block.
  - A Gherkin `*` step and a PageObject ` * key: value` line both start with `*` and stay untouched.
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

- Rewrites: CRLF line endings to LF, and a tab or non-breaking space used as leading indentation to a space.
- Never touches: a tab or non-breaking space inside a value, past its leading indentation.
- Why: a stray `\r` breaks comparisons; a pasted tab breaks the fixed-width alignment of PageObject headers.
- Breaks if removed: a trailing `\r` corrupts equality checks and golden tests; the indentation half is only cosmetic.

### Rule 7: inline criterion description

`inline_ac_description` → `authoring/normalize.py::RULE_INLINE_AC_DESCRIPTION`:

- Rewrites: a description written on the header line (`AC:US-001-01 (v1.0.0 - active) — the description`) onto its own `- ` bullet.
- Applies to the issue-body and feature-header formats, whose grammar expects the description as a bullet.
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
| rule1_bullet_marker_star_rationale_feature_header | bullet_marker | feature_header | DocumentedFunctionality | `# rationale:`<br>`#   * Password strength is checked client-side for immediate feedback.` | `# rationale:`<br>`#   - Password strength is checked client-side for immediate feedback.` | A "*" bullet inside a bullet section becomes "-"; the "#" comment prefix stays. |
| rule1_bullet_marker_plus_not_in_scope_feature_header | bullet_marker | feature_header | DocumentedUserStory | `# not_in_scope:`<br>`#   + Social-identity (OAuth) sign-in.` | `# not_in_scope:`<br>`#   - Social-identity (OAuth) sign-in.` | A "+" bullet is also corrected, matching rule 1's marker set. |
| rule1_bullet_marker_bullet_dot_ac_block | bullet_marker | issue_body | DocumentedFunctionality | `### AC:FUNC-001-01 (v1.0.0 - active)`<br><br>`• Returns valid=false when the candidate password fails a complexity rule.` | `### AC:FUNC-001-01 (v1.0.0 - active)`<br><br>`- Returns valid=false when the candidate password fails a complexity rule.` | A "•" bullet inside an AC block is corrected, independent of TYPE_PROFILES. |
| rule2_ac_header_separator_en_dash_issue_body | ac_header_separator | issue_body | DocumentedUserStory | `### AC:US-001-01 (v1.0.0 – active)`<br><br>`- A customer who submits valid credentials lands on the account dashboard.` | `### AC:US-001-01 (v1.0.0 - active)`<br><br>`- A customer who submits valid credentials lands on the account dashboard.` | An en-dash separator inside an AC header's parentheses becomes " - ". |
| rule2_ac_header_separator_em_dash_feature_header | ac_header_separator | feature_header | DocumentedFunctionality | `#   AC:FUNC-001-01 (v1.0.0 — active)`<br>`#     - Returns valid=false when the candidate password fails a complexity rule.` | `#   AC:FUNC-001-01 (v1.0.0 - active)`<br>`#     - Returns valid=false when the candidate password fails a complexity rule.` | An em-dash separator is corrected the same way as an en-dash. |
| rule3_state_casing_status_heading_issue_body | state_casing | issue_body | DocumentedUserStory | `## Status`<br><br>`ACTIVE` | `## Status`<br><br>`active` | A "## Status" value's case is normalised even with no dash/hyphen to collapse. |
| rule3_state_casing_status_key_feature_header | state_casing | feature_header | DocumentedFunctionality | `# status:          In Review` | `# status:          in_review` | "In Review" collapses to "in_review" in a "# status:" value. |
| rule3_state_casing_ac_header_issue_body | state_casing | issue_body | DocumentedUserStory | `### AC:US-001-01 (v1.0.0 - ACTIVE)`<br><br>`- desc` | `### AC:US-001-01 (v1.0.0 - active)`<br><br>`- desc` | The AC header's own state token is lowercased the same way. |
| rule3_state_casing_removal_planned_keyword | state_casing | issue_body | DocumentedUserStory | `### AC:US-001-04 (v1.0.0 - deprecated - Removal Planned v2.0.0)`<br><br>`- desc` | `### AC:US-001-04 (v1.0.0 - deprecated - removal planned v2.0.0)`<br><br>`- desc` | "Removal Planned" is lowercased to the fixed keyword phrase "removal planned". |
| rule4_version_form_short_issue_body | version_form | issue_body | DocumentedUserStory | `### AC:US-001-03 (v1.1 - planned)`<br><br>`- A customer who forgot the password can request a reset link.` | `### AC:US-001-03 (v1.1.0 - planned)`<br><br>`- A customer who forgot the password can request a reset link.` | vX.Y becomes vX.Y.0. |
| rule4_version_form_bare_numeric_feature_header | version_form | feature_header | DocumentedFunctionality | `#   AC:FUNC-001-02 (1.0.0 - active)`<br>`#     - Returns valid=true when the candidate password satisfies every rule.` | `#   AC:FUNC-001-02 (v1.0.0 - active)`<br>`#     - Returns valid=true when the candidate password satisfies every rule.` | A bare "1.0.0" gains the canonical leading "v". |
| rule4_version_form_capital_v_issue_body | version_form | issue_body | DocumentedUserStory | `### AC:US-001-01 (V1.0.0 - active)`<br><br>`- desc` | `### AC:US-001-01 (v1.0.0 - active)`<br><br>`- desc` | "V1.0.0" is lowercased to "v1.0.0". |
| rule4_version_form_v1_left_as_is | none | issue_body | DocumentedUserStory | `### AC:US-001-01 (v1 - active)`<br><br>`- desc` | `### AC:US-001-01 (v1 - active)`<br><br>`- desc` | "v1" alone has no digit to infer a patch version from - normalize leaves it unchanged (a malformed-acceptance-criterion error for ac_grammar, not normalize). |
| rule5_entity_name_dash_functionality_title | entity_name_dash | feature_header | DocumentedFunctionality | `# =============================================================================`<br>`# LIVING DOC — FUNC-001 · Login Page–Validate Password Strength`<br>`# =============================================================================`<br>`# status:    active` | `# =============================================================================`<br>`# LIVING DOC — FUNC-001 · Login Page - Validate Password Strength`<br>`# =============================================================================`<br>`# status:    active` | An en-dash between the two halves of a Functionality name becomes " - ". |
| rule5b_title_id_separator_hyphen_feature_header | title_id_separator | feature_header | DocumentedUserStory | `# =============================================================================`<br>`# LIVING DOC — US-001 - Customer Login`<br>`# =============================================================================`<br>`# status:    active` | `# =============================================================================`<br>`# LIVING DOC — US-001 · Customer Login`<br>`# =============================================================================`<br>`# status:    active` | The character right after the entity id becomes " · ", even a plain hyphen. |
| rule5b_title_id_separator_colon_page_object | title_id_separator | page_object | DocumentedFeature | `/* =============================================================================`<br>` * LIVING DOC — FEAT-001: Login Page`<br>` * =============================================================================`<br>` * surface_type:          UI`<br>` * ============================================================================= */` | `/* =============================================================================`<br>` * LIVING DOC — FEAT-001 · Login Page`<br>` * =============================================================================`<br>` * surface_type:          UI`<br>` * ============================================================================= */` | A colon right after the entity id in a PageObject banner also becomes " · ". |
| rule6_whitespace_crlf_issue_body | whitespace | issue_body | DocumentedUserStory | `## Status\r`<br>`\r`<br>`active\r` | `## Status`<br><br>`active` | CRLF line endings become LF. |
| rule6_whitespace_tab_indentation_page_object | whitespace | page_object | DocumentedFeature | `/* =============================================================================`<br>` *	surface_type:          UI`<br>` * ============================================================================= */` | `/* =============================================================================`<br>` * surface_type:          UI`<br>` * ============================================================================= */` | A tab used to indent a field's value becomes a plain space; the value itself is untouched. |
| rule7_inline_ac_description_issue_body_split | inline_ac_description | issue_body | DocumentedUserStory | `### AC:US-001-01 (v1.0.0 - active) — customer places an order with a saved payment method` | `### AC:US-001-01 (v1.0.0 - active)`<br>`- customer places an order with a saved payment method` | An inline description on the header line moves onto its own bullet. |
| rule7_inline_ac_description_feature_header_split | inline_ac_description | feature_header | DocumentedFunctionality | `#   AC:FUNC-001-01 (v1.0.0 - active) - rejects a weak password` | `#   AC:FUNC-001-01 (v1.0.0 - active)`<br>`#     - rejects a weak password` | Same split for a feature-header AC block, keeping the "#" comment prefix. |
| rule7_inline_ac_description_scenario_file_inline | inline_ac_description | scenario_file | DocumentedUserStory | `# AC:US-001-01 (v1.0.0 - active) — valid credentials land on the account dashboard`<br>`@AC:US-001-01`<br>`Scenario: Customer signs in with valid credentials` | `# AC:US-001-01 (v1.0.0 - active) - valid credentials land on the account dashboard`<br>`@AC:US-001-01`<br>`Scenario: Customer signs in with valid credentials` | A "# AC:" comment keeps its description inline - only the separator before it is canonicalised, no line is inserted. |
| rule2_rule3_rule4_scenario_file_combined | ac_header_separator | scenario_file | DocumentedFunctionality | `# AC:FUNC-001-01 (v1.0 – ACTIVE) - rejects a weak password \| aspect: minimum length`<br>`@AC:FUNC-001-01/aspect:minimum-length` | `# AC:FUNC-001-01 (v1.0.0 - active) - rejects a weak password \| aspect: minimum length`<br>`@AC:FUNC-001-01/aspect:minimum-length` | Rules 2, 3 and 4 all fire on one scenario-file "# AC:" line; the "\| aspect: ..." suffix is free text and stays untouched. |
| html_markdown_ac_header_defect_corrected | ac_header_separator | html_markdown | DocumentedUserStory | `### AC:US-001-01 (v1.0.0 – active)`<br><br>`- A customer who submits valid credentials lands on the account dashboard.` | `### AC:US-001-01 (v1.0.0 - active)`<br><br>`- A customer who submits valid credentials lands on the account dashboard.` | html_markdown (Azure DevOps HTML converted to markdown) uses the same rules. |
| agentic_toolkit_descope_fixture | bullet_marker | issue_body | DocumentedUserStory | `AC:US-042-03 (v1.2.0 – descoped)`<br>`   – Promo codes can be stacked and applied in defined priority order.`<br>`   – descoped_at: 2026-05-15`<br>`   – descoped_reason: Promo stacking rule deferred — too complex for current sprint`<br>`   – future_release: sprint-52` | `AC:US-042-03 (v1.2.0 - descoped)`<br>`   - Promo codes can be stacked and applied in defined priority order.`<br>`   - descoped_at: 2026-05-15`<br>`   - descoped_reason: Promo stacking rule deferred — too complex for current sprint`<br>`   - future_release: sprint-52` | tests/fixtures/agentic_toolkit_descope.md's AC block (agentic-toolkit@c479c80, skills/living-doc-update/SKILL.md's descope example), bare "AC:" line and all - a header with no markdown "###" wrapper is still recognised. The prose em-dash inside "deferred — too complex" is untouched: it is not a structural position. |
| never_touched_page_object_metadata | none | page_object | DocumentedFeature | `/* =============================================================================`<br>` * LIVING DOC — FEAT-001 · Login Page`<br>` * =============================================================================`<br>` * surface_type:          UI`<br>` * route:                 /login`<br>` * owners:                Identity Team`<br>` * stub-reason:           Login template carries no test-id attributes yet;`<br>` *                        surface documented from the interface spec - discovered 2026-09-08.`<br>` * purpose:               The screen where a registered customer enters an email and password to sign in.`<br>` * user_stories:          US-001`<br>` * functionalities:       FUNC-001`<br>` * external_dependencies: auth-api`<br>` * page-object:           LoginPage.ts`<br>` * ============================================================================= */` | `/* =============================================================================`<br>` * LIVING DOC — FEAT-001 · Login Page`<br>` * =============================================================================`<br>` * surface_type:          UI`<br>` * route:                 /login`<br>` * owners:                Identity Team`<br>` * stub-reason:           Login template carries no test-id attributes yet;`<br>` *                        surface documented from the interface spec - discovered 2026-09-08.`<br>` * purpose:               The screen where a registered customer enters an email and password to sign in.`<br>` * user_stories:          US-001`<br>` * functionalities:       FUNC-001`<br>` * external_dependencies: auth-api`<br>` * page-object:           LoginPage.ts`<br>` * ============================================================================= */` | A naive bullet-character rule over raw text would corrupt every " * key: value" line here (each starts with "*"); normalize leaves every field, and the already- canonical title line, byte-for-byte unchanged. |
| never_touched_gherkin_star_steps | none | scenario_file | DocumentedUserStory | `Scenario: Customer signs in with valid credentials`<br>`  * a registered customer is on the login screen`<br>`  * the customer submits valid credentials`<br>`  * the account dashboard is displayed` | `Scenario: Customer signs in with valid credentials`<br>`  * a registered customer is on the login screen`<br>`  * the customer submits valid credentials`<br>`  * the account dashboard is displayed` | Gherkin's "*" step keyword is never touched - only "# AC:" comment lines are content in a scenario file. |
| never_touched_fenced_code_block_issue_body | none | issue_body | DocumentedFunctionality | `## Description`<br><br>`Example payload:`<br><br>```json<br>`{"status": "active", "items": ["a", "b"]}`<br>``` | `## Description`<br><br>`Example payload:`<br><br>```json<br>`{"status": "active", "items": ["a", "b"]}`<br>``` | A fenced code block is never touched, even though it contains the word "active". |
| never_touched_tilde_fenced_code_block_issue_body | none | issue_body | DocumentedFunctionality | `## Description`<br><br>`Example AC header shown as a worked example:`<br><br>`~~~`<br>`AC:US-999-01 (v9.9.9 - active)`<br>`~~~` | `## Description`<br><br>`Example AC header shown as a worked example:`<br><br>`~~~`<br>`AC:US-999-01 (v9.9.9 - active)`<br>`~~~` | A "~~~"-fenced code block is never touched either - not only the backtick form. |
| never_touched_prose_en_dash_issue_body | none | issue_body | DocumentedUserStory | `## Description`<br><br>`As a registered customer – who values speed – I can sign in with my email and`<br>`password, so that I can reach my account area.` | `## Description`<br><br>`As a registered customer – who values speed – I can sign in with my email and`<br>`password, so that I can reach my account area.` | Free prose keeps its en-dashes; only structural positions are rewritten. |
| never_touched_scalar_field_feature_header | none | feature_header | DocumentedFunctionality | `# source:    https://github.com/example/repo/issues/42`<br>`# parent:    FEAT-001`<br>`# func_type: field_validation` | `# source:    https://github.com/example/repo/issues/42`<br>`# parent:    FEAT-001`<br>`# func_type: field_validation` | Scalar keys other than "status" are never rewritten (no state lives in them). |
<!-- END GENERATED: normalisation-examples -->
