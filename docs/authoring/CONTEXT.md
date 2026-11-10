# docs/authoring

Parent: ../CONTEXT.md

## Purpose

The code maps of the four authoring pages: for each fact a page states, where the code realises it.

## Code map

### Normalisation

What realises each fact of [normalisation.md](normalisation.md):

- `normalize(text, fmt, entity_type)` absorbs small formatting variance before anything parses the text → `authoring/normalize.py::normalize`
- It runs in three phases → `authoring/normalize.py::normalize_framed`
- Rule 6 on each line's indent, line by line and blind to context → `authoring/normalize.py::_prepare`
- The framing pass: where the header starts and ends, and where each root-level section or key begins and ends → `authoring/framing.py::Frame`
- Every other rule, line by line, by the section the frame put the line in → `authoring/normalize.py::_rewrite_markdown`
- A boundary is structural: the frame decides it once, from a line's position and syntax, never its prose → `authoring/framing.py::Frame`
- A line deeper than an open bullet item's marker is that item's text: never a key, an `AC:` header or a section's end → `authoring/framing.py::BulletItemTracker`
- A banner's title is the first line after its opening rule, whatever it reads like → `authoring/framing.py::Frame.title`
- The parser of the format reads the same frame, so the two cannot disagree about where a section runs → `authoring/framing.py::sections`
- The frame reports structural problems only → `authoring/framing.py::Problem`
- It rewrites a header only when the header names an entity: its title, found by position, carries an entity id → `authoring/framing.py::names_an_entity`
- Rule 6 still removes a leading byte-order mark and CRLF line endings from every text, header or not, each recorded as `whitespace` → `tests/authoring/test_normalize.py::test_rule_6_removes_a_byte_order_mark_and_crlf_endings_even_where_no_header_is_normalised`
- Apart from that, a `FEATURE_HEADER` or `PAGE_OBJECT` text with no header, or with a header that names no entity, comes back as written → `tests/authoring/test_normalize.py::test_a_text_with_no_header_is_not_normalised`, `tests/authoring/test_normalize.py::test_a_header_whose_title_names_no_entity_is_not_normalised`
- Apart from that, in a `FEATURE_HEADER` or `PAGE_OBJECT` text no line outside the header is rewritten, not even its tabs: a comment above it, in the Gherkin body or in a JSDoc block → `tests/authoring/test_normalize.py::test_a_line_outside_the_header_is_never_rewritten_not_even_its_tabs`
- It rewrites only structural positions: a heading value, a bullet marker, a criterion header's segments, an entity title → `authoring/normalize.py::normalize`
- It never touches fenced code, Gherkin step text, TypeScript or free prose → `tests/authoring/test_normalize_cases.py::test_normalisation_case`
- A rewritten criterion header or bullet keeps the indent its author gave it; only rule 6 changes an indent → `tests/authoring/test_normalize.py::test_feature_header_criterion_header_keeps_its_authors_indent_when_rewritten`
- It returns the text plus one `Change` per rule fired: `line`, `rule`, `before`, `after` → `authoring/normalize.py::Change`
- An entity title goes through the same rules 5 and 5b on its own → `authoring/normalize.py::normalize_title`
- One helper marks the lines inside a fenced code block, for both `normalize` and the grammar → `authoring/normalize.py::compute_fence_flags`
- Which sections hold bullet lists, per entity type → `authoring/normalize.py::TYPE_PROFILES`
- Five formats exist → `authoring/normalize.py::SourceFormat`
- `HTML_MARKDOWN` shares the Markdown frame and rules with `ISSUE_BODY` → `authoring/normalize.py::_rewrite_markdown`
- Rule `bullet_marker` → `authoring/normalize.py::RULE_BULLET_MARKER`
- Rule `bullet_marker`: In a PageObject header it reaches only the items of a `PO_BULLET_KEYS` key, inside the header comment's frame, so a later JSDoc block is never rewritten → `tests/authoring/test_notes.py::test_rule_one_does_not_reach_a_jsdoc_notes_block_further_down_the_file`
- Rule `bullet_marker`: The frame ends at the first line that ends in `*/`: the canon's banner form or a bare ` */` → `tests/authoring/test_framing.py::test_the_canon_banner_and_a_bare_close_both_end_the_frame`
- Rule `bullet_marker`: A `*/` inside a value does not end it, so rule 1 still reaches the items after that value → `tests/authoring/test_framing.py::test_a_comment_close_inside_a_value_does_not_end_the_frame`
- Rule `ac_header_separator` → `authoring/normalize.py::RULE_AC_HEADER_SEPARATOR`
- Rule `state_casing` → `authoring/normalize.py::RULE_STATE_CASING`
- Rule `version_form` → `authoring/normalize.py::RULE_VERSION_FORM`
- Rule `entity_name_dash` → `authoring/normalize.py::RULE_ENTITY_NAME_DASH`
- Rule `entity_name_dash`: In a `.feature` or PageObject banner it reaches only the line the frame placed as the title, and only when that line reads `LIVING DOC` → `authoring/normalize.py::_emit_title`
- Rule `title_id_separator` → `authoring/normalize.py::RULE_TITLE_ID_SEPARATOR`
- Rule `whitespace` → `authoring/normalize.py::RULE_WHITESPACE`
- Rule `whitespace`: Rewrites: a leading byte-order mark away, in every format → `tests/authoring/test_framing.py::test_a_leading_byte_order_mark_does_not_move_the_frames_start`
- Rule `whitespace`: Runs first, on every line that has text, before the frame is decided; a whitespace-only line stays as written → `authoring/normalize.py::_prepare`
- Rule `whitespace`: Rewrites: each tab or non-breaking space in a line's leading indentation to one space, in a PageObject header and a `.feature` header → `authoring/normalize.py::_fix_indentation_whitespace`
- Rule `whitespace`: A tab right after the marker becomes the marker's own space: `#<tab>x` reads as `# x`, at indent 0, for every reader → `authoring/normalize.py::_prepared`
- Rule `whitespace`: Rewrites: in an issue body, each non-breaking space in a line's leading indentation to one space, and each tab to the next multiple of 4 columns → `authoring/normalize.py::_prepare`
- Rule `whitespace`: Records each rewritten line as a `whitespace` change → `tests/authoring/test_normalize.py::test_feature_header_rule_6_is_recorded_per_line_with_its_before_and_after`
- Rule `inline_ac_description` → `authoring/normalize.py::RULE_INLINE_AC_DESCRIPTION`
- Rule `inline_ac_description`: In a `.feature` header the new bullet sits two spaces deeper than its header, wherever the header is → `tests/authoring/test_normalize.py::test_feature_header_split_description_sits_one_level_below_its_header`
- Generated from `living_doc_utilities/authoring/normalisation_cases.yaml` by `make docs` → `authoring/docs_export.py::regenerate`
- The same file is the test data: `tests/authoring/test_normalize_cases.py` runs every row → `tests/authoring/test_normalize_cases.py::test_normalisation_case`
- Do not hand-edit the table; CI fails the build when it drifts → `.github/workflows/test.yml::docs-regeneration-check`

### Acceptance-criterion grammar

What realises each fact of [ac-grammar.md](ac-grammar.md):

- `parse_acceptance_criteria(text, entity_id)` reads every criterion in already-normalised text → `authoring/ac_grammar.py::parse_acceptance_criteria`
- `<id>` is the entity id, a hyphen and a sequence number, e.g. `US-001-01` → `contracts/common.py::AC_ID_PATTERN`
- Only a User Story or a Functionality owns criteria, so `<id>` starts `US-` or `FUNC-`; `FEAT-001-01` is rejected → `tests/contracts/test_common.py::test_acceptance_criterion_id_rejects_a_prefix_that_owns_no_criteria`
- Other modules check an id with one helper, never their own pattern → `authoring/ac_grammar.py::is_valid_ac_id`
- A version is required unless the state is `planned` → `contracts/common.py::AcceptanceCriterion._check_version_required_unless_planned`
- `removal planned` is required on `deprecated` and allowed nowhere else → `contracts/common.py::AcceptanceCriterion._check_removal_planned_only_when_deprecated`
- A header may follow a comment leader: `###` in an issue body, `#` in a `.feature` file, `*` in a PageObject → `authoring/ac_grammar.py::parse_acceptance_criteria`
- `entity_id` only names a warning's entity; that an id belongs to its entity is checked on the model → `contracts/common.py::check_ac_ids_owned`
- In a parser the frame bounds it, so the grammar finds no boundary itself → `authoring/ac_grammar.py::parse_frame_criteria`
- In a parser it ends where the frame ends it → `authoring/framing.py::criterion_blocks`
- Over bare text, `parse_acceptance_criteria` finds the blocks itself → `authoring/ac_grammar.py::parse_acceptance_criteria`
- An `AC:` line deeper than the open bullet item's `- ` is that item's wrapped text and ends nothing → `tests/authoring/test_ac_grammar.py::test_a_line_wrapped_deeper_than_a_criterion_item_is_never_an_ac_header`
- A criterion with nothing under its header is dropped with `MALFORMED_AC`, "has no description line"; the other criteria are read → `tests/authoring/test_ac_grammar.py::test_a_criterion_with_nothing_under_its_header_is_reported_and_the_rest_is_read`
- Each line keeps its indent: only the comment leader (`#`, `###`, `*`) and one following space are removed → `authoring/ac_grammar.py::parse_acceptance_criteria`
- Lines inside a fenced code block are skipped → `authoring/normalize.py::compute_fence_flags`
- Each block line fills one field of the criterion → `contracts/common.py::AcceptanceCriterion`
- The block's content level is the indent of its first bullet → `authoring/ac_grammar.py::_ExtensionReader`
- A line fits no level when it is shallower than the content level, or sits between a sub-list's key and its items → `tests/authoring/test_ac_grammar.py::test_a_bullet_between_a_sub_key_and_its_items_is_misindented_and_dropped`
- The first item of a sub-list decides how far the list reaches → `authoring/ac_grammar.py::_SubList`
- A nested sub-list ends at the first line at or above its key's indent, read as a criterion line, with no warning → `tests/authoring/test_ac_grammar.py::test_a_bullet_back_at_criterion_level_closes_an_indented_sub_list`
- A flat sub-list takes every later bullet of the block, in line order → `tests/authoring/test_ac_grammar.py::test_flat_sub_list_keeps_every_later_bullet_in_line_order`
- A line deeper than an item's `- ` is that item's text: a sub-key or `<key>:` there is not read as a key → `authoring/ac_grammar.py::_ExtensionReader`
- A nested precondition stays in its parent's entry: `["An account exists.\n  - It is not locked."]` → `tests/authoring/test_ac_grammar.py::test_a_nested_precondition_item_is_kept_in_its_parents_string`
- An unknown bare key is reported with exactly the lines deeper than it → `tests/authoring/test_ac_grammar.py::test_unknown_sub_key_is_reported_with_exactly_the_lines_deeper_than_it`
- A bare `<key>:` with no deeper line right under it is a wrapped line, not a key → `tests/authoring/test_ac_grammar.py::test_a_bare_key_with_nothing_deeper_under_it_is_wrapped_text`
- Why: without an indent the two cannot be told apart, so the line is read as it always was → `tests/authoring/test_ac_grammar.py::test_a_flat_unknown_key_is_read_as_wrapped_text_and_its_bullets_as_criterion_lines`
- A keyword is the other spelling of `Aspect:`: its values fill `aspect`, and `placeholder_values` keeps its one name → `tests/authoring/test_ac_grammar.py::test_a_keyword_named_in_the_description_fills_aspect_and_keeps_its_name`
- A `- <name>: <values>` bullet is a keyword only when the description names `{<name>}` → `authoring/ac_grammar.py::_ExtensionReader._read_keyword`
- Otherwise it is `UNPARSED_AC_LINE` and fills nothing → `tests/authoring/test_ac_grammar.py::test_a_bullet_whose_name_the_description_does_not_name_is_unparsed`
- Names are compared folded: lowercase, with `-`, `_` and space equal; `- user role:` matches `{user-role}`, stored as `user_role` → `authoring/ac_grammar.py::_slug_placeholder_name`
- The folded name must match `^[A-Za-z_][A-Za-z0-9_]*$` → `contracts/common.py::PLACEHOLDER_NAME_PATTERN`
- Normalisation never rewrites a name, as its `never_touched_ac_keyword_name_*` rows show → `tests/authoring/test_ac_grammar.py::test_each_keyword_name_form_normalisation_leaves_folds_to_one_slug`
- `aspect` is reserved: a keyword named `aspect`, in any case, is `UNPARSED_AC_LINE` → `tests/authoring/test_ac_grammar.py::test_a_keyword_named_aspect_is_reserved_and_unparsed`
- `Rationale:` is never a keyword, even with `{rationale}` in the description → `authoring/ac_grammar.py::_ExtensionReader._read_criterion_field`
- `Aspect:` plus a keyword, two keywords, or `Aspect:` twice is `MALFORMED_AC`, and the criterion is dropped; no declaration wins → `authoring/ac_grammar.py::_Extensions.declares_two_variants`
- A scenario links one value with `@AC:<id>/aspect:<value>` or `@AC:<id>/<name>:<value>` → `authoring/scenario.py::_parse_ac_tag`
- A criterion is skipped with a `MALFORMED_AC` warning → `authoring/ac_grammar.py::_build_ac`
- In a parser, each line of a dropped criterion's block is reported too, one `AUTHORING_WARNING` per line, unless another warning already names it → `tests/authoring/test_accounting.py::test_every_line_of_a_dropped_criterion_is_reported_and_the_next_criterion_is_read`
- `AC:<id> (v<x.y.z> - descoped)` is converted to a version-less `planned` criterion, with a `LEGACY_AC_STATE` warning → `authoring/ac_grammar.py::_build_ac`
- Any other `descoped` shape is `MALFORMED_AC` → `authoring/ac_grammar.py::_build_ac`
- In a converted block, `descoped_reason:` becomes `rationale` → `authoring/ac_grammar.py::_parse_extensions`
- `descoped_at:` and `future_release:` lines are dropped; the model has no field for them → `authoring/ac_grammar.py::_parse_extensions`
- `canonical_header()` renders `AC:<id> (v<x.y.z> - <state>)`, adding ` - removal planned v<x.y.z>` on `deprecated` → `contracts/common.py::AcceptanceCriterion.canonical_header`
- A version-less criterion renders as `AC:<id> (planned)` → `contracts/common.py::AcceptanceCriterion.canonical_header`

### Parsers

What realises each fact of [parsers.md](parsers.md):

- Each parser returns `(parsed, warnings)` and never raises on malformed input; every information-losing skip is a coded warning → `tests/authoring/test_warning_coverage.py::test_information_losing_skip_produces_a_coded_warning_and_no_log_record`
- Every authored line no field reads is reported, one warning per line → `authoring/accounting.py::unplaced_lines`
- A line that breaks its header's format is `AUTHORING_ERROR` → `tests/authoring/test_accounting.py::test_a_line_with_text_and_no_comment_marker_inside_a_feature_header_is_not_read`
- A line a structural problem already names is reported once, by that problem, not again by the unread-line sweep → `tests/authoring/test_framing.py::test_a_line_a_structural_problem_names_is_reported_once`
- Any other unread line no more specific code covers is `AUTHORING_WARNING` → `tests/authoring/test_accounting.py::test_a_key_written_twice_reads_the_first_value_and_reports_the_later_one`
- Both are warnings: parsing goes on, and a format check decides what fails it → `tests/authoring/test_accounting.py::test_both_authoring_codes_are_warnings_so_a_parser_never_stops`
- An HTML comment, and the prose a cross-reference header may open with, are not content and are not reported → `tests/authoring/test_accounting.py::test_issue_body_text_before_the_first_heading_is_reported_but_an_html_comment_is_not`
- A warning about a line sets its 1-based `line_no`, and its context keeps the line or its text (`line=`) → `tests/authoring/test_accounting.py::test_every_line_warning_of_a_broken_header_names_its_input_line`
- A warning sets every location field its parser knows: `entity_id`, `ac_id` when the criterion's id is valid, `line_no` → `tests/authoring/test_warning_location.py::test_a_warning_carries_the_location_its_parser_knows`
- Every line inside a criterion names that criterion when its id is valid → `authoring/ac_grammar.py::criterion_ids`
- No authoring module uses `logging` → `tests/authoring/test_warning_coverage.py::test_no_authoring_module_uses_the_logging_module`
- `None` with `MISSING_ENTITY_ID` means the title or banner had no id → `authoring/identity.py::derive_entity_id`
- A parsed entity has every entity field except `source_ref`, `tags` and `timestamps`; the collector fills those → `authoring/issue_body.py::ParsedEntity`
- `state` and `state_origin` stay empty until status derivation runs → `authoring/issue_body.py::ParsedEntity`
- An authored value that fails its field's validation is dropped with a warning (`MALFORMED_STATUS` for a status) → `authoring/issue_body.py::_build_parsed_entity`
- Every parser reads its sections from the frame built in normalisation's three phases: rule 6, then the frame, then the other rules → `authoring/framing.py::sections`
- Every parser reads a line's indent before deciding what the line belongs to; one line model serves them all → `authoring/framing.py::indented`
- In a bullet-list field, a line deeper than an open item's `- ` is that item's text → `authoring/framing.py::BulletItemTracker`
- A blank line ends nothing, with or without its comment marker: not an item, not a key's section, as in a Markdown list → `tests/authoring/test_framing.py::test_a_blank_comment_line_in_a_feature_header_ends_nothing_either`
- An item's wrapped `AC:` line yields no criterion → `tests/authoring/test_framing.py::test_d20_an_ac_shaped_wrapped_line_in_a_bullet_item_is_that_items_text_and_no_criterion`
- A PageObject header's one bullet-list key is `notes:`, declared where the frame reads it → `authoring/normalize.py::PO_BULLET_KEYS`
- In a header a key sits at the key level, the indent of its first key; a line shaped `key:` any deeper is content, never a key → `tests/authoring/test_feature_header.py::test_a_key_shaped_line_deeper_than_the_key_level_is_content_not_a_key`
- A scalar key's value continues on a line deeper than the key, as the canon wraps `purpose:` → `authoring/accounting.py::scalar_lines`
- A key whose value is one token takes no further line: a deeper line under it is `AUTHORING_ERROR` and is not read, so the value stays valid → `tests/authoring/test_accounting.py::test_a_single_value_key_reports_a_further_line_and_keeps_its_value`
- A text value and an id list may wrap; a part after a blank line is read with `AUTHORING_WARNING` → `tests/authoring/test_accounting.py::test_a_text_value_wraps_silently_and_continues_after_a_blank_line_with_a_warning`
- A bullet-list field holds one string per top-level item. Its first `- ` sets the item level; each line is read by its indent → `authoring/issue_body.py::_read_bullets`
- Example: `- Parent.` then `  - Child.` gives the one entry `"Parent.\n  - Child."`, in an issue body and a `.feature` header alike → `tests/authoring/test_feature_header.py::test_a_nested_business_value_item_is_kept_in_its_parents_string_as_extracted`
- An id-list field never nests; it is read as comma-separated text → `authoring/issue_body.py::split_id_list`
- The same rule reads a criterion's `preconditions` and `not_in_scope` items → `authoring/normalize.py::ItemText`
- Text before a bullet-list field's first `- ` bullet is dropped with `UNPARSED_BULLET_LINE` → `authoring/issue_body.py::unparsed_bullet_warning`
- Both bullet-field warnings are built in one place → `authoring/issue_body.py::bullet_field_warnings`
- A header key's own-line text counts as before the first bullet → `authoring/feature_header.py::_read_keys`
- The `UNPARSED_BULLET_LINE` context names the contract field, not the authored key or heading → `authoring/issue_body.py::unparsed_bullet_warning`
- An id list is comma-separated; blank or `none` means empty → `authoring/issue_body.py::split_id_list`
- Every entity type carries an optional `notes` bullet list, the canon's one place for human context → `contracts/doc_entities.py::EntityContent`
- Nothing ever reads a note's text → `tests/authoring/test_notes.py::test_a_field_shaped_note_changes_no_derived_state_and_raises_no_warning`
- It does not decide how its own file is read either → `tests/authoring/test_notes.py::test_a_note_whose_wrapped_line_reads_as_parent_feat_does_not_make_a_cross_reference_header`, `tests/authoring/test_notes.py::test_a_note_that_mentions_living_doc_is_still_a_note`
- The title is found by position, not by its prose, so an item may quote the whole `LIVING DOC — <id> · <title>` form → `authoring/framing.py::Frame.title`, `tests/authoring/test_notes.py::test_a_note_quoting_a_whole_banner_title_is_still_a_note`
- `notes` is entity-level, plus a cross-reference page's own; a `notes:` inside a criterion block fills no field and is reported → `tests/authoring/test_notes.py::test_an_ac_level_notes_key_in_an_issue_body_is_reported_and_reads_as_no_field`
- `deprecation_reason` stays its own typed field and does not move into a note → `contracts/doc_entities.py::EntityContent`
- `parse_issue_body(text, title, entity_type)` reads a GitHub issue body → `authoring/issue_body.py::parse_issue_body`
- Each `##` heading maps by slug (lowercase, spaces and underscores as `_`) to a field → `authoring/issue_body.py::_SECTIONS_BY_TYPE`
- A heading with no mapping is `UNKNOWN_SECTION`, not a failure → `authoring/issue_body.py::parse_issue_body`
- An `### AC:` heading opens a criterion wherever it appears, except as a bullet item's text → `authoring/framing.py::criterion_blocks`
- Under a criterion item, a deeper line is that item's text, an `AC:` line too, which is reported → `tests/authoring/test_framing.py::test_an_ac_line_on_a_criterion_items_text_in_an_issue_body_is_reported`
- Only a `##` heading outside a fenced code block opens a section; a `###` heading is content of the section it sits in → `authoring/framing.py::frame_issue_body`
- A heading may be indented by up to three spaces, as CommonMark reads it → `tests/authoring/test_framing.py::test_a_heading_indented_up_to_three_spaces_ends_a_criterion_as_commonmark_reads_it`
- An item nested one space deeper than its parent is reported: the parser nests it, GitHub shows a sibling → `tests/authoring/test_accounting.py::test_an_item_nested_one_space_deeper_is_reported_as_github_renders_it_a_sibling`
- `parse_feature_header(text, entity_type)` reads a User Story's or Functionality's `.feature` header → `authoring/feature_header.py::parse_feature_header`
- The header runs from the first `# ===` rule to the last; it holds `# key: value` lines, and `# key:` lines with an indented bullet list → `authoring/framing.py::frame_feature_header`
- Nothing outside it is read: not a line above the first rule or below the last → `authoring/framing.py::frame_feature_header`
- A key below the last rule, above `Feature:`, is `AUTHORING_ERROR` → `tests/authoring/test_accounting.py::test_a_key_below_the_closing_rule_is_reported`
- A comment above the first rule is no header line and is not reported: Gherkin's `# language:` sits on line 1 → `tests/authoring/test_accounting.py::test_a_comment_above_the_opening_rule_is_no_header_line_and_is_not_reported`
- A header with only one rule never closes → `tests/authoring/test_framing.py::test_a_feature_header_with_one_rule_is_read_to_its_last_comment_line_and_reported`
- The title is the first line after the opening rule: `LIVING DOC — <id> · <title>` → `authoring/framing.py::Frame.title`
- A header with no title there is `MISSING_ENTITY_ID`, whatever a later line reads like → `tests/authoring/test_framing.py::test_a_feature_header_title_is_the_line_after_the_opening_rule_not_any_line_reading_like_one`
- A file with no rule above `Feature:` has no header at all: `MISSING_ENTITY_ID` says that no header was found → `tests/authoring/test_accounting.py::test_a_feature_file_with_no_header_says_no_header_was_found`
- The rule search stops at the file's `Feature:` line → `authoring/framing.py::frame_feature_header`
- Every criterion sits in `acceptance_criteria:`'s section, as the canon writes it → `tests/authoring/test_framing.py::test_an_ac_header_outside_the_criteria_key_is_no_criterion_and_the_keys_after_it_are_read`
- A criterion block runs from its `AC:` header to the next `AC:` header, a key at the key level, or a `# ===` rule → `tests/authoring/test_framing.py::test_a_key_at_the_key_level_ends_a_criterion_block_and_is_read`
- A rule inside the header is an optional end of a block; the last rule ends the header → `tests/authoring/test_framing.py::test_a_rule_inside_the_header_ends_a_criterion_block_and_the_last_rule_ends_the_header`
- The first `AC:` line sets the criterion level; an `AC:` line at another indent, or on an item's text, is no header and is reported → `tests/authoring/test_framing.py::test_an_ac_line_off_the_criterion_level_is_text_and_reported`
- A blank line ends nothing, with `#` or without it → `tests/authoring/test_framing.py::test_a_blank_line_without_a_comment_marker_in_a_feature_header_closes_nothing`
- A line with text and no `#` inside the header is not read and is `AUTHORING_ERROR`; Gherkin rejects such a line above `Feature:` too → `tests/authoring/test_accounting.py::test_a_line_with_text_and_no_comment_marker_inside_a_feature_header_is_not_read`
- An unknown key is `IGNORED_AUTHORED_KEY` → `authoring/feature_header.py::parse_feature_header`
- `acceptance_criteria:` is structural → `tests/authoring/test_accounting.py::test_an_acceptance_criteria_keys_own_line_text_is_reported`
- Written bare, as the canon writes it, nothing is unread and nothing is reported → `tests/authoring/test_accounting.py::test_an_acceptance_criteria_key_written_bare_is_not_reported`
- The keys each entity type's header reads → `authoring/feature_header.py::_KEYS_BY_TYPE`
- `parse_page_object(text)` reads a PageObject file's leading `/* ... */` comment → `authoring/page_object.py::parse_page_object`
- The comment ends at its first line that ends in `*/`; a `*/` inside a value does not end it → `authoring/framing.py::frame_page_object`
- A key written on that last line is still read, without the comment's `*/` → `tests/authoring/test_framing.py::test_a_key_on_the_closing_line_is_still_read_without_the_close`
- With no line ending in `*/` the comment never closes, and nothing in it is read → `tests/authoring/test_framing.py::test_an_unclosed_page_object_comment_leaves_its_lines_as_written`
- It is reported as `AUTHORING_ERROR`, saying that nothing in it is read → `tests/authoring/test_accounting.py::test_an_unclosed_page_object_comment_is_reported_as_read_nowhere`
- A value ending in `*/` closes the comment early when a later ` * ` line, before any code, closes it again → `tests/authoring/test_accounting.py::test_header_lines_up_to_the_real_end_after_a_comment_that_closed_early_are_reported`
- With no later close, the header ends where the comment did, and nothing after it is reported → `tests/authoring/test_accounting.py::test_a_comment_closed_by_a_value_with_no_later_close_ends_the_header_there`
- A `===` rule ends the open key; a blank ` *` line ends nothing → `tests/authoring/test_accounting.py::test_a_blank_star_line_in_a_notes_list_ends_nothing`
- A line inside the comment without ` * ` is not read and is `AUTHORING_ERROR`, as a `.feature` line without `#` is → `tests/authoring/test_accounting.py::test_a_page_object_line_without_its_star_is_reported`
- The frame runs from the `/*` line through the `*/` line, so both delimiter lines are header lines too → `tests/authoring/test_accounting.py::test_text_beside_the_closing_delimiter_is_reported`, `tests/authoring/test_accounting.py::test_text_beside_the_opening_delimiter_is_reported`
- Only what sits beside a delimiter counts as its text → `tests/authoring/test_accounting.py::test_a_delimiter_carries_no_authored_text_of_its_own`
- The full-header and cross-reference key sets → `authoring/page_object.py::_FULL_HEADER_KEYS`, `authoring/page_object.py::_CROSS_REFERENCE_KEYS`
- A cross-reference result names `parent_feat`; the collector appends its page to that Feature's `pages` → `authoring/page_object.py::PageObjectResult`
- `status:` and `deprecated_at:` are recognised only to be dropped as `IGNORED_AUTHORED_KEY`, in a full or a cross-reference header → `authoring/page_object.py::IGNORED_AUTHORED_KEYS`
- A full-header-only key on a cross-reference header is an unknown key, `IGNORED_AUTHORED_KEY` → `tests/authoring/test_page_object.py::test_full_header_only_key_on_a_cross_reference_header_is_an_unrecognised_key`
- `notes` is allowed on both → `tests/authoring/test_notes.py::test_a_note_on_a_cross_reference_page_object_header_stays_with_its_page`
- `notes` is the header's one bullet key; every other key's value is a scalar or an id list, joined from its lines → `authoring/page_object.py::_joined`
- `wizard-steps` is split on ` · ` → `authoring/page_object.py::parse_page_object`
- `parse_scenarios(text, entity_type)` reads a `.feature` file's Gherkin body → `authoring/scenario.py::parse_scenarios`
- Each `Scenario:` or `Scenario Outline:` takes the `@AC:<id>[/<param>:<value>]` tags right before it → `authoring/scenario.py::_tags_to_ac_links`
- The tag format is closed: at most one `/<param>:<value>` follows the id → `authoring/scenario.py::_parse_ac_tag`
- A bare `@AC:<id>` links the whole criterion, every declared value: the link's `aspect` is `None` → `contracts/ui_tests.py::AcLink`
- Any other line between a tag block and the next scenario (`Rule:`, a step, `Examples:`) drops the pending tags → `authoring/scenario.py::parse_scenarios`
- A `Feature:` or `Background:` line also drops pending tags → `authoring/scenario.py::parse_scenarios`
- When an `@AC:` tag is `MALFORMED_AC` and skipped → `tests/authoring/test_scenario.py::test_malformed_ac_tag_params_produce_a_warning_and_no_link`
- The collector fills each scenario's `scenario_id` and `source_ref` → `authoring/scenario.py::ParsedScenario`
- An entity id is `US-<nnn>`, `FEAT-<nnn>` or `FUNC-<nnn>`, the canon's three prefixes → `tests/authoring/test_identity.py::test_each_canon_prefix_is_an_entity_id`
- `derive_entity_id(title)` takes the first such run as a whole word, so another tracker key before it is passed over (`BUG-7 fix for US-001` gives `US-001`) → `tests/authoring/test_identity.py::test_other_tracker_keys_are_not_entity_ids`
- A run glued to other letters, digits or `_` (`XUS-001`, `US-001abc`, `GH_US-001`) is not an id → `tests/authoring/test_identity.py::test_an_id_run_glued_to_other_word_characters_is_not_an_entity_id`
- A historical prefix is skipped: in `GH-US-001`, the match is `US-001` → `tests/authoring/test_identity.py::test_valid_title_prefixes_extract_us_001`
- No such run returns `(None, [MISSING_ENTITY_ID])`, even when the title names another key such as `JIRA-12` → `authoring/identity.py::derive_entity_id`
- Normalisation rules 5 and 5b find the id with the same pattern, so the ` · ` separator lands after the real id → `authoring/normalize.py::normalize_title`
- The same function serves an issue title, a `.feature` banner and a PageObject banner → `authoring/identity.py::derive_entity_id`
- One helper reads the title text from the banner's title line, in both banner formats → `authoring/identity.py::extract_living_doc_title`
- `derive_statuses(entities)` settles every entity's `state` and `state_origin` once, after a run's entities are parsed → `authoring/status.py::derive_statuses`
- A User Story or Functionality keeps its authored state, with `state_origin` `authored` → `authoring/status.py::_derive_us_or_func`
- With no authored state, it is derived from its own criteria by the majority rule, with `MISSING_STATUS`; the origin stays `authored` → `authoring/status.py::_derive_us_or_func`
- An authored state that contradicts its own criteria gets `STATUS_AC_MISMATCH`; the authored value wins → `authoring/status.py::_is_mismatch`
- A Feature is always derived, from its Functionalities alone → `authoring/status.py::_derive_feature`
- A linked User Story never stands in for a Functionality → `tests/authoring/test_status.py::test_feature_with_only_linked_user_stories_is_a_feature_without_functionality`
- Non-Features are settled first, so a Feature reads settled states whatever the input order → `authoring/status.py::derive_statuses`
- The majority rule → `authoring/status.py::_majority_state`
- An authored state contradicts its criteria → `authoring/status.py::_is_mismatch`
- `check_relations(entities)` runs once per collector run, over the whole collected set → `authoring/relations.py::check_relations`
- A target outside the set is `UNRESOLVED_RELATION` → `authoring/relations.py::check_relations`
- A target of another type is `RELATION_TYPE_MISMATCH`; context names the entity, field, target, actual and expected type → `authoring/relations.py::_type_mismatch`
- A Feature's functionality whose `parent` names another Feature is `RELATION_MISMATCH` → `authoring/relations.py::check_relations`
- A Functionality missing from its parent's non-empty `functionalities` list is `RELATION_MISMATCH` → `authoring/relations.py::check_relations`
- A `feature_dependencies` target that is a Feature with no `API` surface is `RELATION_TYPE_MISMATCH` → `authoring/relations.py::_feature_dependency_warning`
- A Feature naming itself in `feature_dependencies` is `RELATION_MISMATCH` → `authoring/relations.py::_feature_dependency_warning`
- A Feature's `feature_dependencies` is exactly what is authored on it → `tests/authoring/test_relations.py::test_a_feature_keeps_exactly_its_authored_feature_dependencies`
- In a source-code run, a `UI` Feature's `feature_dependencies` target is `UNRESOLVED_RELATION`, and that is expected → `tests/authoring/golden/test_golden_source_code_chain.py::test_a_ui_feature_dependency_is_unresolved_in_a_source_code_run_and_nothing_else`
- `tests/fixtures/golden/` holds `AbsaOSS/living-doc`'s `docs/examples/` documents verbatim, plus hand-written expected entities → `tests/authoring/golden/test_golden_entities.py::test_golden_entities_match_hand_written_json`
- Each fixture's header names the canon commit it was copied from; a refresh re-pins every fixture together → `tests/fixtures/golden/gh-issues/us-001-customer-login.md::commit`
- The corpus is expected to raise exactly two warnings, both `FEATURE_WITHOUT_FUNCTIONALITY` → `tests/authoring/golden/test_golden_entities.py::test_golden_run_produces_exactly_the_expected_corpus_warnings`
- In the source-code chain FEAT-003's `feature_dependencies` target is also `UNRESOLVED_RELATION`, expected until an API Feature has a source-code form → `tests/authoring/golden/test_golden_source_code_chain.py::test_a_ui_feature_dependency_is_unresolved_in_a_source_code_run_and_nothing_else`

### URLs and HTML

What realises each fact of [urls-and-html.md](urls-and-html.md):

- One small policy decides which links survive into rendered documentation → `authoring/url_policy.py::safe_href`
- Allowed schemes: `http`, `https`, `mailto` → `authoring/url_policy.py::ALLOWED_SCHEMES`
- `safe_href(href)` returns `href` unchanged when it is absolute and uses an allowed scheme; `http` and `https` also need a host → `authoring/url_policy.py::safe_href`
- `sanitize_html_fragment(html)` cleans a fragment with `nh3`, an `ammonia`-based sanitiser → `authoring/url_policy.py::sanitize_html_fragment`
- It strips every `<img>` tag → `authoring/url_policy.py::sanitized_tag_allowlist`
- It passes every `href` through `safe_href`; a rejected `href` is dropped and the element's text kept → `authoring/url_policy.py::sanitize_html_fragment`
- nh3's default allow-list handles the rest: `<script>` and `<style>` with their content, event-handler attributes, tags outside its set → `authoring/url_policy.py::sanitized_tag_allowlist`
- `nh3` needs the `html` extra and is imported inside the two functions that use it → `tests/authoring/test_isolation.py::test_nh3_is_imported_only_inside_a_function_that_needs_it`
- Its only consumer today is `html_to_markdown`; a future PDF-generator text filter can reuse the same policy → `authoring/url_policy.py::sanitize_html_fragment`
- `convert_html_to_markdown(html)` returns `(text, warnings)` → `authoring/html_to_markdown.py::convert_html_to_markdown`
- Supported tags → `authoring/html_to_markdown.py::_SUPPORTED_TAGS`
- Sanitising is delegated to `sanitize_html_fragment`, not reimplemented → `authoring/html_to_markdown.py::convert_html_to_markdown`
- Any other tag that survives sanitising, such as `<strong>`, is unwrapped: text kept, markup dropped → `authoring/html_to_markdown.py::_TreeBuilder`
- Every drop in one call folds into one `HTML_CONTENT_DROPPED` warning with per-kind counts in its context → `authoring/html_to_markdown.py::_build_warnings`
- Drop kinds counted in the warning context, e.g. `img_tag=1, script_tag=1` → `authoring/html_to_markdown.py::_DropCountingParser`
