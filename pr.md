## Overview

One framing pass now decides, once per input and by position, where a source's header starts and ends and where each root-level section or key begins and ends. `normalize` rewrites by that frame, and the parser of the same format reads the same frame. Before this, each format derived its boundaries twice: once in a `normalize.py` walker and once in its parser. The two agreed only by hand. Four defects in two rounds came from that split: a predicate read a line's prose without knowing the line's structural context.

The three phases (`normalize.py::normalize_framed`):

1. **Rule 6 on each line's indent**, line by line and blind to context (`normalize.py::_prepare`), so every later decision reads an indent in spaces.
2. **The frame** (`authoring/framing.py`, new): one `frame_*` function per format places every line. It records the line's role (rule, title, heading, key, text…), the root-level section it is in, whether it is an open bullet item's text, and whether it belongs to a criterion block. It also reports structural problems only: `no_frame`, `unterminated_frame`, `key_outside_frame`.
3. **Every other rule and the typed parse**, by section. The normaliser's phase-3 rewriters read roles and sections instead of keeping their own flags. `parse_issue_body`, `parse_feature_header`, `parse_page_object` and `parse_scenarios` read `framing.sections()`, `Frame.title` and `framing.criteria_text()` instead of re-deriving anything.

What this removes:

- The seven line-walking state machines become four framers plus four phase-3 rewriters with no boundary state. `header_closed`, `seen_title` and `current_section` are gone everywhere (`tests/authoring/test_framing.py::test_no_module_keeps_a_boundary_flag_of_its_own`).
- The banner title is the first line after the opening rule (`framing.py::_title`), never a line matching `LIVING DOC — …`. `identity.py::is_living_doc_title` and the `#176` guard in `normalize.py::po_section_break` are deleted with it.
- The header comment's close is recognised once, at the first line ending in `*/` (`framing.py::_COMMENT_CLOSE_RE`). The unanchored `"*/" in raw` check and `page_object.py::_COMMENT_CLOSE_RE` are gone.
- `D20`: in an issue body's bullet field, a line deeper than the open item's `- ` is that item's text, across a blank line too. The grammar reads it blanked, which is the rule the `.feature` path already followed.

`BulletItemTracker` and `DEC-45`(b)'s nested-item form (`ItemText`) are unchanged. They moved to, or are read through, the frame.

### Lines removed from the two header parsers

The header parsers no longer build a regex over all known keys, or any regex. Both read the frame's key sections and look each key up in their own map: `_KEYS_BY_TYPE` and `_FULL_HEADER_KEYS` / `_CROSS_REFERENCE_KEYS`. Line numbers are against `master` at `216d866`.

- `feature_header.py`:
  - lines 107–165, `_parse_keys`, including its key regex at 108–110;
  - lines 84–92, `_extract_header_block`;
  - lines 80–81, `_strip_comment_prefix`;
  - lines 50–52, `_BANNER_RE`, `_AC_HEADER_LOOKALIKE_RE` and `_GENERIC_KEY_RE`;
  - line 206, the item-text blanking.
- `page_object.py`:
  - lines 139–179, `_parse_keys`, including its key regex at 143–147;
  - line 211, the second `_ANY_HEADER_KEYS` probe pass, and line 90, `_ANY_HEADER_KEYS` itself;
  - lines 110–128, `_header_comment_lines` and `_content_lines`;
  - lines 49–51, `_GENERIC_KEY_RE`, `_COMMENT_OPEN_RE` and `_COMMENT_CLOSE_RE`.
- `normalize.py`:
  - the four walkers: `_normalize_markdown` (412–466), `_normalize_feature_header` (487–570), `_normalize_scenario_file` (576–595) and `_normalize_page_object` (630–693);
  - `po_section_break` (612–627), `_emit_title_if_present` (364–372) and `_in_bullet_context` (302–306);
  - `_FH_KEY_LIST_RE` / `_FH_KEY_SCALAR_RE` (469–470) and `_PO_COMMENT_CLOSE_CONTENT_RE` (606).
- `issue_body.py`: lines 149–164, `_split_h2_sections`.
- `identity.py`: lines 48–54, `is_living_doc_title`.

### Intended output changes

Old and new code were compared on every input the test suite passes to `normalize` and the parsers (234), on the golden corpus, and on 60,000 seeded mutations of both (two seeds). On the recorded test inputs and the golden corpus nothing differs. Every difference on the mutated inputs falls into one of the groups below. No other output moves.

**The two this issue names:**

1. **`D20`.** In an issue body, an `AC:`-shaped line that is a bullet item's text yields no criterion and no `MALFORMED_AC`. Item text means deeper than the item's `- `, across a blank line too. `normalize` no longer rewrites that line as a criterion header, so it stays the item's text as authored. Some of these inputs used to raise `ValueError` (see `D22` below) and now parse.
2. **The `*/` close (PageObject).** The header comment ends at its first line ending in `*/`.
   - A `*/` inside a value no longer stops rule 1 for the lines after it. Before, a later `• note` was dropped with `UNPARSED_BULLET_LINE`.
   - An indented bare `*   */` ends the comment too. Before, it was appended to the open key's value, for example `owners: Team */`.

**Required by acceptance criterion 2 (title by position):**

3. **A `LIVING DOC — …` line anywhere but right after the opening rule is no longer the title.** That covers a note quoting the form, a line above the rules or after the last rule, and a file with no rule.
   - The parser returns `MISSING_ENTITY_ID` where it used to take that line's id. Example: a PageObject banner with no title line, whose note quoted `LIVING DOC — FEAT-002 · …`, used to become entity `FEAT-002`.
   - The normaliser no longer applies rules 5/5b to that line.
   - In a PageObject header, such a line after the title no longer ends the open key; it is that key's text.

**Beyond the two the issue names, for owner review.** These are inputs on which the old normaliser and the old parser disagreed about a boundary. One frame has to pick one reading. Groups 4–11 take the parser's, because the parser's reading is the contract; group 12 takes the normaliser's, because the parser's reading there was the defect. Where the parser's own output still moves, it is because the normaliser now rewrites what the parser reads. All of these inputs are non-canonical.

4. **Issue body: only a `##` heading opens a section.** The normaliser used to switch rules 1 and 3 at a heading of any level. A `### Sub` inside `## Business Value` no longer stops rule 1. A `### Status` no longer lowercases the lines under it.
5. **`.feature` header: a criterion block runs to the next `# ===` rule.** A `key:` line inside the block is not a key, so `normalize` no longer rewrites it as one. For example, `status: Deprecated` there keeps its case, and `UNPARSED_AC_LINE` quotes it as written. Rule 1 keeps reaching the block's later bullets.
6. **`.feature` header: a bullet key with text on its own line** (`preconditions: …`) opens its list, as the parser always read it. `normalize` now applies rule 1 to its items and reads their wrapped lines as item text.
7. **A tab right after the comment marker.** `#<tab>x` is read at the indent its rewritten line `# x` has. That is the indent the parser and the criterion grammar always read. `normalize`'s own item-text decisions now use it too.
8. **`.feature` header: a blank line without `#` inside the frame** now closes the open key for `normalize`, as it always did for the parser.
9. **PageObject: a line without ` * ` inside the header comment** is not a header line and closes nothing, for either reader. A `• note` after such a line is now its own note; before, it was joined to the previous note.
10. **Missing or unterminated frame.** This covers a `.feature` header with exactly one `# ===` rule, and a PageObject file with no `/*` or no closing `*/`. `normalize` no longer rewrites lines that no parser reads; only a `.feature` title is still rewritten. A `.feature` text with no rule at all is still normalised whole, so bare fragments keep working.
11. **Rule 6 runs first, on every line that has text.** It now also reaches a header's title line, a `# ===` rule and an issue-body `## Status` value. A whitespace-only line stays as written in every format; before, a PageObject ` *<tab>` line was rewritten.

12. **PageObject cross-reference header: a `notes:` list's items are item text there too.** `notes:` is unknown on a cross-reference header and is still reported with `IGNORED_AUTHORED_KEY`. Its wrapped lines are now that note's text whatever the header shape, as the normaliser always read them. Before, the parser read a wrapped note line `route: /b` as the `route` key and overwrote the real one.

The tests pin 1–3, 4–7 and the frame structure in `tests/authoring/test_framing.py`. No existing test was changed.

### Found, not fixed

- **`D22` (new row in `debt.md`).** A criterion header with nothing under it makes `parse_issue_body` and `parse_feature_header` raise `ValueError` from `ac_grammar.py::_parse_extensions`. This happens on `master` too. The fix would move output beyond this task's list, so it is parked.
- **`D19`'s claim does not fully hold.** The row says acting on `D19` becomes "a one-site change" after this task. In fact, issue-body nesting is now read in two places: which lines are an item's text (`framing.py::frame_issue_body`) and how they join (`issue_body.py::_read_bullets`). No normaliser carries it any more.

## Release Notes

- Every authoring parser and `normalize` now read one frame per input. Where a header, section or key begins and ends is decided once, by a line's position, never by its text.
- An `AC:`-shaped line wrapped inside an issue-body bullet item stays that item's text and no longer creates an acceptance criterion nobody wrote.
- A PageObject header comment ends at its first line ending in `*/`. A `*/` inside a value no longer cuts the header short.
- A banner's title is the line after its opening rule. A note quoting `LIVING DOC — <id> · <title>` can no longer supply the entity id.
- New `authoring.framing` module (`Frame`, `FramedLine`, `Role`, `sections()`) and `normalize.normalize_framed()`. The frame's `problems` list reports structural problems: no frame, an unterminated frame, a key outside the frame.

## Framework

Stays inside the frame: F5 Utilities only (`DEC-43`, `DEC-46`); no row bent and no exception added.

## Out of scope, confirmed

- No required-key validation: the frame reports structural problems only, and the parsers stay lenient (`D18`, `D21`).
- No change to what indentation means: `DEC-44` and `DEC-45` stand, and `BulletItemTracker` and `ItemText` are unchanged.
- `D19` is left open.
- No contract field, no schema change and no new warning code.
- The version stays `0.5.0` (`DEC-41`); no tag is cut here.

## Acceptance criteria

- [x] One framing pass produces the frame and every root-level section boundary for all four formats, and the normaliser and the parser of each format both read it:
  - framers in `framing.py` (`frame_issue_body`, `frame_feature_header`, `frame_page_object`, `frame_scenario_file`);
  - `normalize.py::normalize_framed`, which builds the frame and rewrites by it;
  - the parsers read it via `normalize_framed` (`issue_body.py`, `feature_header.py`, `page_object.py`, `scenario.py`);
  - no boundary flag survives anywhere: `test_framing.py::test_no_module_keeps_a_boundary_flag_of_its_own`.
- [x] The banner title is identified by position:
  - `framing.py::_title` and `Frame.title`;
  - a quoting note is still an item: `test_notes.py::test_a_note_quoting_a_whole_banner_title_is_still_a_note`, unchanged;
  - `is_living_doc_title` and `po_section_break` are deleted: `test_framing.py::test_the_identity_module_no_longer_offers_a_title_predicate`.
- [x] `D20` closes:
  - tested over its exact recorded input in `test_framing.py::test_d20_an_ac_shaped_wrapped_line_in_a_bullet_item_is_that_items_text_and_no_criterion`;
  - `debt.md`: the row is deleted and a *Closed 2026-10-01* note added.
- [x] The header-comment close is recognised once, at `framing.py::_COMMENT_CLOSE_RE`:
  - `test_framing.py::test_a_comment_close_inside_a_value_does_not_end_the_frame`;
  - `test_framing.py::test_the_canon_banner_and_a_bare_close_both_end_the_frame` (canon banner, bare, indented bare).
- [x] Neither header parser builds a key regex: `test_framing.py::test_neither_header_parser_compiles_a_regex_of_its_own`. The removed lines are listed above.
- [x] Behaviour held:
  - all 938 existing tests pass unchanged, including golden fixtures at `b28820e`, plus 32 new ones (970);
  - intended output changes are listed above, and no others were found.
- [x] Out of scope confirmed above.
- [x] `docs/authoring/normalisation.md` § Where normalisation runs describes the three phases and the structural boundary. `docs/authoring/parsers.md` § Common behaviour names them and links there. Both replace the `po_section_break` and raw-`*/` guard notes. `docs/api.md` lists `authoring.framing`.
- [x] `make qa` is green, and the `## Framework` section is present.

## Related

Closes #183

🤖 Generated with [Claude Code](https://claude.com/claude-code)
