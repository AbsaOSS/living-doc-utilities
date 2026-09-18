# Authoring

This file holds the normative rules for `living_doc_utilities.authoring` — version 1. Every
collector that mines a GitHub issue, a `.feature` file, a PageObject header, or Azure DevOps
rich-text HTML writes and reads text against the rules below.

Contents:

- [1. Where normalisation runs](#1-where-normalisation-runs)
- [2. Normalisation rules](#2-normalisation-rules)
- [3. Normalisation, the acceptance-criterion grammar, and warnings](#3-normalisation-the-acceptance-criterion-grammar-and-warnings)
- [4. Parser layouts](#4-parser-layouts)
- [5. Entity identity](#5-entity-identity)
- [6. Status derivation](#6-status-derivation)
- [7. URL policy](#7-url-policy)
- [8. HTML-to-Markdown conversion](#8-html-to-markdown-conversion)

## 1. Where normalisation runs

`normalize(text, fmt, entity_type)` (`living_doc_utilities/authoring/normalize.py`) is the one
place every authoring surface's small, mechanical formatting variance is absorbed before anything
else parses it. It never validates a value's *meaning* (that is `ac_grammar.py`'s job alone — see
section 3) and never touches fenced code, Gherkin step text, TypeScript, or free prose — only
content in a *structural* position: a heading value, a bullet marker, an acceptance-criterion
header's own segments, an entity title.

Five source formats exist (`SourceFormat`):

| Format | Extracted content lines | Parsed by |
|---|---|---|
| `ISSUE_BODY` | A GitHub issue body's Markdown text, split on `##` section headings | `issue_body.parse_issue_body` |
| `FEATURE_HEADER` | A `.feature` file's leading `# key: value` / `# key:` comment block, between its two `# ===...===` banner lines | `feature_header.parse_feature_header` |
| `SCENARIO_FILE` | A `.feature` file's Gherkin body — only its `# AC:...` documentation-comment lines are content; every scenario, step and tag line passes through untouched | `scenario.parse_scenarios` |
| `PAGE_OBJECT` | A PageObject file's leading `/* ... */` header comment's `* key: value` lines | `page_object.parse_page_object` |
| `HTML_MARKDOWN` | The Markdown-like text `html_to_markdown.convert_html_to_markdown` produces from an Azure DevOps rich-text HTML fragment — normalised with exactly the same rules as `ISSUE_BODY` (both share `normalize.py`'s internal Markdown handler), since the two are structurally identical once the HTML has been flattened to text | `html_to_markdown.convert_html_to_markdown`, then this module, then `issue_body.parse_issue_body` |

"Extracted content lines" means: the lines `normalize` actually inspects for a structural
rewrite, as opposed to lines it passes through byte-for-byte because they lie outside any
recognised structural position (free prose, a fenced code block, a Gherkin step).
`compute_fence_flags` is the one helper shared by `normalize.py` and `ac_grammar.py` that marks
which lines lie inside a fenced code block, so the two modules can never disagree about where a
fence starts or ends.

## 2. Normalisation rules

Eight rules exist (numbered 1–7, plus 5b — a sibling of rule 5 rather than a later addition).
Every rule reshapes a token by its position in a line; none of them enumerate or validate the
acceptance-criterion state vocabulary or the strict version shape — that is section 3's job alone.

### Rule 1 — `bullet_marker`

**Rewrites:** A bullet-list item's leading marker — en-dash `–`, em-dash `—`, bullet-dot `•`,
`*`, or `+` (each with its following single space) — to a plain `-`. Applies inside an
acceptance-criterion block's own bullets (any format), and — per entity type's bullet-section
profile — a bullet section such as `## Business Value` / `## Not In Scope` / `## Preconditions`
(issue body) or `rationale:` / `preconditions:` / `not_in_scope:` (feature header).

**Why:** Authors — and tools that help draft these documents, such as a word processor's
autocorrect or an LLM-assisted drafting aid — commonly emit an en-dash or a bullet-dot instead of
a hyphen. Every downstream bullet-extraction routine only recognises a literal `-`.

**Never touches:** A bullet-shaped character that is not a line's own leading marker (e.g. `*`
used for emphasis or multiplication inside prose), or a bullet-shaped line outside a
bullet-eligible section or acceptance-criterion block — a Gherkin `*`-style step and a
PageObject's ` * key: value` metadata line both start with `*` for unrelated reasons and are left
untouched.

**What breaks if removed:** An authored bullet using any marker other than `-` silently fails to
parse as a list item — it is glued onto the previous bullet as continuation text (or reported as
`UNPARSED_AC_LINE`), silently losing a business-value entry, a precondition, or an
acceptance-criterion description rather than merely mis-rendering it.

### Rule 2 — `ac_header_separator`

**Rewrites:** The separator between the segments inside an acceptance-criterion header's
parentheses — `AC:<id> (<version> - <state>[ - removal planned <version>])` — to exactly `" - "`
(space, hyphen, space), whatever dash character and spacing an author used.

**Why:** The acceptance-criterion grammar splits a header's inner content on the literal string
`" - "` — it does no dash-tolerant parsing of its own, by design (section 3).

**Never touches:** A hyphen that is part of a state token itself (e.g. the hyphen in `in-review`
before rule 3 folds it into `in_review`) — the separator is only recognised where whitespace sits
on at least one side, so a hyphen tight against surrounding letters is left for rule 3.

**What breaks if removed:** The acceptance-criterion grammar cannot split the header's segments at
all, falls into its "shape could not be mapped" branch, and drops the whole acceptance criterion
with a `MALFORMED_AC` warning — even though the header was correct except for its author's choice
of dash character.

### Rule 3 — `state_casing`

**Rewrites:** A state token — a `## Status` / `status:` scalar value, or the state segment inside
an acceptance-criterion header — to lowercase with internal whitespace or hyphens collapsed to a
single underscore (`In Review` → `in_review`). Also folds the fixed two-word phrase
`Removal Planned` to `removal planned`.

**Why:** The state vocabulary (`planned`, `in_review`, `active`, `deprecated`) is defined and
validated in exactly one place as lowercase, underscore-separated tokens; an author capitalising a
status for readability (a heading value, a table cell) must not silently fail that check.

**Never touches:** Any other word in an entity's prose — including free text that happens to
contain a state word, e.g. a rationale sentence mentioning "the Active tab".

**What breaks if removed:** `## Status\n\nActive` (or `# status: In Review`) does not match the
state vocabulary's exact lowercase, underscore-separated tokens, so the value is either rejected
outright (an acceptance-criterion header) or silently kept as an unrecognised authored string that
status derivation (section 6) cannot reason about.

### Rule 4 — `version_form`

**Rewrites:** A version token to the canonical `vX.Y.Z` — lowercase leading `v`, exactly three
dot-separated numeric parts. `V1.2`, `1.2` and `v1.2` all become `v1.2.0`.

**Why:** A stored acceptance-criterion version is validated against a strict `X.Y.Z` shape (no
leading `v` once stored — see the "Version format" rule in `docs/contracts.md`), but an author
routinely omits the patch number or capitalises the `v`; this rule is the one place that tolerance
is absorbed before validation runs.

**Never touches:** A bare version with no minor part at all (e.g. `v1`) — there is no digit to
infer a patch number from, so it is left as-is; the acceptance-criterion grammar then reports it
as `MALFORMED_AC` rather than this rule guessing a shape.

**What breaks if removed:** `v1.2` (missing patch) or `V1.2.0` (uppercase `v`) fails the
acceptance-criterion grammar's exact-match version check, and the whole acceptance criterion is
dropped as malformed even though its version was unambiguous to a human reader.

### Rule 5 — `entity_name_dash`

**Rewrites:** The dash between the two halves of a compound Feature/Functionality name in a title
(`Login Page–Validate Password Strength` → `Login Page - Validate Password Strength`) —
unconditionally for an en-dash or em-dash, and for a plain hyphen only when whitespace sits on at
least one side (so a hyphenated word inside the name, e.g. `Password-reset`, is left alone).

**Why:** Every renderer and comparison downstream expects a single canonical separator between a
compound entity name's two halves; a word processor's autocorrect commonly turns a typed `-` into
an en-dash or em-dash.

**Never touches:** A hyphen inside a single word (no surrounding whitespace) anywhere in the
title, e.g. `Password-reset`, `Sign-in`.

**What breaks if removed:** Nothing fails outright — the title is still readable — but two
entities whose names differ only by dash character are no longer trivially comparable, and any
tooling that renders or diffs entity names surfaces an inconsistency the author never intended.

### Rule 5b — `title_id_separator`

**Rewrites:** The character immediately after an entity id in a title — a hyphen, colon, or other
punctuation — to the canonical `" · "` (space, middle dot, space): `US-001 - Customer Login` →
`US-001 · Customer Login`.

**Why:** Entity-id extraction (section 5) finds the id itself with a separator-agnostic search,
but every downstream renderer and both comment-banner conventions
(`LIVING DOC — <id> · <title>`) expect one canonical separator, so the GitHub-issue-title path and
the two comment-banner paths all converge on it here.

**Never touches:** Anything before the entity id (e.g. a `LIVING DOC — ` prefix, or a historical
`GH-` prefix ahead of the real id) — only the character immediately following the id is rewritten.

**What breaks if removed:** Nothing breaks structurally — the id is still found — but every
authoring surface renders its title separator differently depending on which punctuation a given
author or tool happened to type, defeating the point of one canonical entity-title format shared
across GitHub issues, `.feature` banners and PageObject banners.

### Rule 6 — `whitespace`

**Rewrites:** CRLF line endings to LF, and a tab or non-breaking space used as leading
indentation to a plain space.

**Why:** A `\r` embedded mid-line would otherwise survive into a stored field or a rendered
document as an invisible, comparison-breaking character; a tab or non-breaking space in a
PageObject header's indentation (often copy-pasted from a rich-text editor) breaks the
fixed-width alignment convention those headers use for readability, even though it never changes
what the line means.

**Never touches:** A tab or non-breaking space that appears inside a value itself, past its
leading indentation.

**What breaks if removed:** A CRLF line ending survives as a literal trailing `\r`, corrupting
equality comparisons (golden-fixture tests, generator diffing) and rendering as a stray character
in some viewers; a tab-indented PageObject field misaligns visually but still parses correctly —
this half of the rule is a readability fix, not a parsing necessity.

### Rule 7 — `inline_ac_description`

**Rewrites:** A short description written inline on an acceptance-criterion header's own line
(`AC:US-001-01 (v1.0.0 - active) — the description`) — moved onto its own following
`- <description>` bullet line, for the issue-body and feature-header formats (the two formats
whose extension grammar expects the description as a separate bulleted line). A scenario-file
`# AC:` comment is the one exception: it keeps the description inline on the header's own line,
since that format's convention is a documentation comment, not a section with its own bullets —
only the separator before the description is canonicalised there.

**Why:** The acceptance-criterion grammar only recognises a block's `description` as the block's
first bullet line — an inline description after the header's closing parenthesis would otherwise
be silently absorbed into the header match and discarded, for issue-body/feature-header input.

**Never touches:** A scenario-file `# AC:` comment's own inline description (see above).

**What breaks if removed:** An issue-body or feature-header acceptance criterion's inline
description is silently dropped — it never reaches the grammar's `description` field, and the
acceptance criterion is stored with no description at all, with no warning raised (the header
itself still parses successfully; only the trailing text disappears).

### Worked examples

Generated from `living_doc_utilities/authoring/normalisation_cases.yaml` — the same file
`tests/authoring/test_normalize_cases.py` runs every row of — by `make docs`. Do not hand-edit the
table below; a CI check fails the build if it drifts from that file.

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
| rule4_version_form_bare_numeric_feature_header | version_form | feature_header | DocumentedFunctionality | `#   AC:FUNC-001-02 (1.0.0 - active)`<br>`#     - Returns valid=true when the candidate password satisfies every rule.` | `#   AC:FUNC-001-02 (v1.0.0 - active)`<br>`#     - Returns valid=true when the candidate password satisfies every rule.` | A bare "1.2.0" gains the canonical leading "v". |
| rule4_version_form_capital_v_issue_body | version_form | issue_body | DocumentedUserStory | `### AC:US-001-01 (V1.0.0 - active)`<br><br>`- desc` | `### AC:US-001-01 (v1.0.0 - active)`<br><br>`- desc` | "V1.2.0" is lowercased to "v1.2.0". |
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
| agentic_toolkit_descope_fixture | bullet_marker | issue_body | DocumentedUserStory | `AC:US-042-03 (v1.2.0 – descoped)`<br>`   – Promo codes can be stacked and applied in defined priority order.`<br>`   – descoped_at: 2026-05-15`<br>`   – descoped_reason: Promo stacking rule deferred — too complex for current sprint`<br>`   – future_release: sprint-52` | `AC:US-042-03 (v1.2.0 - descoped)`<br>`   - Promo codes can be stacked and applied in defined priority order.`<br>`   - descoped_at: 2026-05-15`<br>`   - descoped_reason: Promo stacking rule deferred — too complex for current sprint`<br>`   - future_release: sprint-52` | tests/fixtures/agentic_toolkit_descope.md's AC block (agentic-toolkit@c479c80, skills/living-doc-update/SKILL.md lines 156-160), bare "AC:" line and all - a header with no markdown "###" wrapper is still recognised. The prose em-dash inside "deferred — too complex" is untouched: it is not a structural position. |
| never_touched_page_object_metadata | none | page_object | DocumentedFeature | `/* =============================================================================`<br>` * LIVING DOC — FEAT-001 · Login Page`<br>` * =============================================================================`<br>` * surface_type:          UI`<br>` * route:                 /login`<br>` * owners:                Identity Team`<br>` * stub-reason:           Login template carries no test-id attributes yet;`<br>` *                        surface documented from the interface spec - discovered 2026-09-08.`<br>` * purpose:               The screen where a registered customer enters an email and password to sign in.`<br>` * user_stories:          US-001`<br>` * functionalities:       FUNC-001`<br>` * external_dependencies: auth-api`<br>` * page-object:           LoginPage.ts`<br>` * ============================================================================= */` | `/* =============================================================================`<br>` * LIVING DOC — FEAT-001 · Login Page`<br>` * =============================================================================`<br>` * surface_type:          UI`<br>` * route:                 /login`<br>` * owners:                Identity Team`<br>` * stub-reason:           Login template carries no test-id attributes yet;`<br>` *                        surface documented from the interface spec - discovered 2026-09-08.`<br>` * purpose:               The screen where a registered customer enters an email and password to sign in.`<br>` * user_stories:          US-001`<br>` * functionalities:       FUNC-001`<br>` * external_dependencies: auth-api`<br>` * page-object:           LoginPage.ts`<br>` * ============================================================================= */` | A naive bullet-character rule over raw text would corrupt every " * key: value" line here (each starts with "*"); normalize leaves every field, and the already- canonical title line, byte-for-byte unchanged. |
| never_touched_gherkin_star_steps | none | scenario_file | DocumentedUserStory | `Scenario: Customer signs in with valid credentials`<br>`  * a registered customer is on the login screen`<br>`  * the customer submits valid credentials`<br>`  * the account dashboard is displayed` | `Scenario: Customer signs in with valid credentials`<br>`  * a registered customer is on the login screen`<br>`  * the customer submits valid credentials`<br>`  * the account dashboard is displayed` | Gherkin's "*" step keyword is never touched - only "# AC:" comment lines are content in a scenario file. |
| never_touched_fenced_code_block_issue_body | none | issue_body | DocumentedFunctionality | `## Description`<br><br>`Example payload:`<br><br>```json<br>`{"status": "active", "items": ["a", "b"]}`<br>``` | `## Description`<br><br>`Example payload:`<br><br>```json<br>`{"status": "active", "items": ["a", "b"]}`<br>``` | A fenced code block is never touched, even though it contains the word "active". |
| never_touched_tilde_fenced_code_block_issue_body | none | issue_body | DocumentedFunctionality | `## Description`<br><br>`Example AC header shown as a worked example:`<br><br>`~~~`<br>`AC:US-999-01 (v9.9.9 - active)`<br>`~~~` | `## Description`<br><br>`Example AC header shown as a worked example:`<br><br>`~~~`<br>`AC:US-999-01 (v9.9.9 - active)`<br>`~~~` | A "~~~"-fenced code block is never touched either - not only the backtick form. |
| never_touched_prose_en_dash_issue_body | none | issue_body | DocumentedUserStory | `## Description`<br><br>`As a registered customer – who values speed – I can sign in with my email and`<br>`password, so that I can reach my account area.` | `## Description`<br><br>`As a registered customer – who values speed – I can sign in with my email and`<br>`password, so that I can reach my account area.` | Free prose keeps its en-dashes; only structural positions are rewritten. |
| never_touched_scalar_field_feature_header | none | feature_header | DocumentedFunctionality | `# source:    https://github.com/example/repo/issues/42`<br>`# parent:    FEAT-001`<br>`# func_type: field_validation` | `# source:    https://github.com/example/repo/issues/42`<br>`# parent:    FEAT-001`<br>`# func_type: field_validation` | Scalar keys other than "status" are never rewritten (no state lives in them). |
<!-- END GENERATED: normalisation-examples -->

## 3. Normalisation, the acceptance-criterion grammar, and warnings

`normalize` and `ac_grammar.py` are two strictly separated layers, on purpose: `normalize`
reshapes a token by its *position* in a line — it never knows what a *valid* acceptance-criterion
state or version looks like. `ac_grammar.py` is the one module that owns that vocabulary and
validates it; it parses only the canonical form `normalize` produces, with no dash, case or
version-form tolerance of its own. A package-shape test enforces this split statically: no module
other than `ac_grammar.py` may define a regex that enumerates the acceptance-criterion state
vocabulary or validates the strict version shape.

Every parser in this package calls `normalize` first and its own section/acceptance-criterion
extraction second — never the reverse — so a mis-cased or mis-dashed but otherwise well-formed
acceptance-criterion header is silently corrected rather than rejected. A header whose *shape*
cannot be mapped at all even after normalisation (no id, an unrecognised state, a missing version
on a non-`planned` state, `removal planned` on a non-`deprecated` state, and so on) is dropped
with a `MALFORMED_AC` warning; a legacy `descoped` state converts to a version-less `planned`
acceptance criterion with a `LEGACY_AC_STATE` warning instead of being rejected outright.

No parser in this package ever raises on malformed input, and none of them use the `logging`
module — every information-losing skip becomes a coded warning
(`living_doc_utilities.contracts.envelope.ContractWarning`: `code`, `message`, `context`) instead,
so a caller always has a structured way to see what was lost. `docs/contracts.md`'s "Errors and
warnings" section is the single normative source for every warning code's meaning; this document
only explains *why* normalisation and the acceptance-criterion grammar produce the ones they do.

## 4. Parser layouts

Each parser accepts exactly one physical layout — the canonical shape established in
`AbsaOSS/living-doc`'s `docs/guides/living-doc-glossary.md` and
`docs/guides/living-doc-header-types.md` — after `normalize` has run. Every parser returns
`(parsed_or_none, warnings)` and never raises; `None` (with a `MISSING_ENTITY_ID` warning) means
the title/banner carried no id this package could recognise — nothing else about the input is
inspected in that case.

### `issue_body.parse_issue_body`

A GitHub issue body: a sequence of `##`-level Markdown headings, each mapped by slug (lowercase,
spaces/underscores collapsed to `_`) onto a field of the entity type it is called with. A heading
with no mapping produces `UNKNOWN_SECTION`, not a parse failure. `## Acceptance Criteria`'s own
content is not read section-by-section — the whole normalised text is handed to the
acceptance-criterion grammar instead, so an `### AC:...` sub-heading is recognised wherever it
appears, not only directly under that one heading.

### `feature_header.parse_feature_header`

A `.feature` file's header comment block: two `# ===...===` banner lines bracket a
`# key: value` / `# key:` (with an indented bulleted sub-list) comment block, with the file's
`LIVING DOC — <id> · <title>` title as the first content line. The banner search is bounded to
before the file's `Feature:` declaration, so a banner-shaped comment inside the Gherkin scenario
body below it (e.g. a worked `# AC:` example) is never mistaken for the header's own closing
banner.

### `page_object.parse_page_object`

A PageObject file's leading `/* ... */` block comment: `* key: value` lines, with the same
`LIVING DOC — <id> · <title>` title convention. Two shapes exist — a **full header** (describes
the whole Feature plus its own page) and a **cross-reference header** (`parent-feat:` present;
describes only its own page, scoped to an already-described Feature elsewhere) — distinguished
solely by whether `parent-feat:` is present, each with its own known-key set.

### `scenario.parse_scenarios`

A `.feature` file's Gherkin body: every `Scenario:`/`Scenario Outline:` block, together with the
`@AC:<id>[/aspect:<value>]` Cucumber tag(s) immediately preceding it. A human-readable `# AC:`
comment above a scenario is documentation only — never parsed as a tag; only the machine-readable
`@AC:` tag links a scenario to an acceptance criterion. Any other construct between a tag block
and the next `Scenario:`/`Scenario Outline:` line (a `Rule:`, a step, an `Examples:` table)
invalidates that pending tag block — it links only the very next scenario line, never one further
down.

## 5. Entity identity

`identity.derive_entity_id(title)` extracts an entity's id (`US-001`, `FEAT-001`, `FUNC-001`,
...) from a title by searching for the *last* run matching an uppercase-letters-hyphen-digits
shape — "last", not "first", so a historical prefix ahead of the real id (e.g. `GH-US-001`) is
skipped naturally: `GH-` is not itself id-shaped (letters directly followed by a hyphen then a
digit fails to match starting at `GH`, since what follows `GH-` is `US`, not a digit), so the
search lands on `US-001`.

A title with no id-shaped substring produces `(None, [MISSING_ENTITY_ID])` — the caller (a
collector) is responsible for adding location context to that warning and for counting the skip
toward `metadata.stats.cardinality.entities_skipped` (`docs/contracts.md`, "Entity identity").
Nothing else about the document is inspected once this fails.

The same function backs every authoring surface that carries a title: a GitHub issue's own title,
a `.feature` file's `LIVING DOC — <id> · <title>` banner line, and a PageObject's banner line —
one shared helper recognises both comment-banner formats' title line, so neither parser re-derives
that pattern for itself.

## 6. Status derivation

`status.derive_statuses(entities)` settles every entity's final `state`/`state_origin` in one
pass, after every entity in a run has been parsed. (`docs/contracts.md`'s "State and
`state_origin`" is the normative definition of the vocabulary itself; this section explains the
derivation algorithm that fills it in.)

- A **User Story** or **Functionality**'s state is authored by a human. When present, it is kept
  (`state_origin = "authored"`) and checked for self-consistency against its own acceptance
  criteria's states (`STATUS_AC_MISMATCH` — e.g. an authored `planned` entity with an `active`
  acceptance criterion). When absent, it is derived from its own acceptance criteria's states
  instead (`MISSING_STATUS` warning), using the shared majority rule below.
- A **Feature**'s state is *never* authored — a written Feature status is dropped as
  `IGNORED_AUTHORED_KEY` (`docs/contracts.md`). It is derived, in order: `deprecated` if the
  Feature itself carries a `deprecated_at`; else the majority state of its linked Functionalities;
  else, if it has none, the majority state of its linked User Stories; else — a Feature with no
  linked Functionality and no linked User Story in this run — `active`, with an `ORPHAN_FEATURE`
  warning.

The shared majority rule, used both for a User Story/Functionality deriving from its own
acceptance criteria and a Feature deriving from its linked entities' already-settled states:
`active` wins if any input is `active`; else `in_review` wins if any input is `in_review`; else
`deprecated` if every input is `deprecated` (uniform retirement is itself a signal); else
`planned` (nothing stronger to go on, including an empty input set). Non-Feature entities are
always resolved first, so a Feature's derivation can safely read their already-settled `state`
regardless of input order.

## 7. URL policy

`url_policy.py` is the one place that decides which links survive into rendered documentation — a
single, small policy shared by every consumer that needs it, rather than each hand-rolling its own
href/image allow-listing.

- **`ALLOWED_SCHEMES = {"http", "https", "mailto"}`** — the only schemes a kept link may use.
- **`safe_href(href) -> str | None`** returns `href` unchanged when it is an absolute link using
  one of those schemes; `None` for a relative link (no scheme at all), a protocol-relative link
  (`//host/...` — it has no scheme of its own to vet, since it inherits whatever scheme the
  embedding page loaded over), or a link using any other scheme (`javascript:`, `data:`, `file:`,
  ...).
- **`sanitize_html_fragment(html) -> str`** sanitises an HTML fragment with
  [`nh3`](https://pypi.org/project/nh3/) (an `ammonia`-based HTML sanitizer): every `<img>` tag is
  stripped entirely, every `href` attribute is passed through `safe_href` (an attribute a
  rejecting call drops, keeping the surrounding element's own text), and nh3's own default
  allow-list handles everything else a general sanitiser must — `<script>`/`<style>` tags and
  their content, event-handler attributes such as `onclick`, and any tag outside its conservative
  default formatting-tag set.

`nh3` is a native (Rust) dependency, shipped behind this package's optional `html` extra
(`pip install living-doc-utilities[html]`) rather than as a core dependency, since most consumers
of this library never touch HTML at all. Both functions that need it — `sanitize_html_fragment`
here, and `html_to_markdown.py`'s conversion pipeline — import it lazily, inside the function that
uses it, so importing either module (or calling `safe_href`, which has no such dependency) never
requires the extra; only actually sanitising HTML does.

`sanitize_html_fragment` has no consumer inside `living_doc_utilities` beyond
`html_to_markdown.py` and its own tests today — it exists so a future PDF-generator text filter
can reuse the exact same vetted href/image policy instead of writing its own.

## 8. HTML-to-Markdown conversion

`html_to_markdown.convert_html_to_markdown(html) -> (text, warnings)` turns an Azure DevOps
rich-text HTML fragment into the Markdown-like text every other parser in this package
understands. Its output is meant to be run through
`normalize(text, SourceFormat.HTML_MARKDOWN, entity_type)` and then `issue_body.parse_issue_body`
(or whichever parser fits the entity) — exactly like any other source format; this module only
turns markup into text, it never derives an entity id or a field itself.

Supported constructs: headings (`<h1>`–`<h6>`), paragraphs (`<p>`), line grouping
(`<div>`/`<br>`), lists (`<ul>`/`<ol>`/`<li>` — both list types render as this package's plain
`"- "` bullet form, since its bullet grammar has no ordered-list concept of its own), tables
(`<table>`/`<tr>`/`<td>`/`<th>`, rendered as a GitHub-Flavored-Markdown table), links
(`<a href="...">`), and inline code (`<code>`).

Sanitising is delegated to `url_policy.sanitize_html_fragment` rather than reimplemented here — a
`<script>`/`<style>` tag and its content, an event-handler attribute, and an `<img>` tag are all
dropped that way; a link keeps its `href` only when `url_policy.safe_href` allows it, otherwise
only its visible text survives. Any remaining tag this converter simply has no Markdown form for
(nh3's default allow-list covers plenty of formatting tags this module doesn't specifically
render, e.g. `<strong>`) is unwrapped the same way — its text kept, its markup dropped.

Every dropped construct, of whichever kind, is folded into exactly **one** `HTML_CONTENT_DROPPED`
warning per call — never one warning per drop — carrying a per-kind count in its `context` (e.g.
`script_tag=1, style_tag=1, event_handler_attribute=1, img_tag=1, unsafe_href=1`), so a caller
processing many documents does not get flooded with one warning row per stripped tag.
`docs/contracts.md`'s warnings table (`HTML_CONTENT_DROPPED`) is the normative definition of the
code itself.

Handling the specific quirks of a *real* Azure DevOps rich-text editor's HTML output is out of
scope for this converter's current version — that is a later Azure-DevOps-collector task's job,
once real editor samples are available. This converter covers the well-formed-HTML case.
