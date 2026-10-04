#
# Copyright 2025 ABSA Group Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""
The framing pass: one frame per input decides every boundary, by position, and both `normalize` and the
parser of the format read it - so a line's prose never ends a section and the two can never disagree.
"""

import ast
from pathlib import Path

import pytest

from living_doc_utilities.authoring import identity
from living_doc_utilities.authoring.feature_header import parse_feature_header
from living_doc_utilities.authoring.framing import (
    KEY_OUTSIDE_FRAME,
    LINE_AFTER_CLOSE,
    NO_FRAME,
    UNTERMINATED_FRAME,
    Problem,
    Role,
    sections,
)
from living_doc_utilities.authoring.issue_body import parse_issue_body
from living_doc_utilities.authoring.normalize import (
    RULE_BULLET_MARKER,
    RULE_STATE_CASING,
    SourceFormat,
    normalize,
    normalize_framed,
)
from living_doc_utilities.authoring.page_object import parse_page_object
from living_doc_utilities.authoring.scenario import parse_scenarios
from tests.authoring.golden.helpers import read_fixture

AUTHORING_DIR = Path(__file__).resolve().parents[2] / "living_doc_utilities" / "authoring"

_PAGE_OBJECT = """\
/* =============================================================================
 * LIVING DOC — FEAT-042 · Account Setup Wizard
 * =============================================================================
 * surface_type:          UI
 * purpose:               Multi-step wizard for creating a new account.
 * page-object:           AccountSetupWizardPage.ts
 * notes:
 *   • Step order is fixed; the review step cannot be skipped.
 *   • The wizard shares one URL with its step files.
 * ============================================================================= */
"""

_NOTES = ["Step order is fixed; the review step cannot be skipped.", "The wizard shares one URL with its step files."]


def _us_header(body: str) -> str:
    return (
        "# =============================================================================\n"
        "# LIVING DOC — US-001 · Sample\n"
        "# =============================================================================\n"
        f"{body}"
        "# =============================================================================\n"
        "\nFeature: Sample\n"
    )


# --- D20: an item's wrapped `AC:` line is that item's text ---------------------------------------------


def test_d20_an_ac_shaped_wrapped_line_in_a_bullet_item_is_that_items_text_and_no_criterion():
    """The exact input `debt.md` `D20` recorded: the wrapped line stays in `business_value` and no criterion,
    which nobody authored, is emitted. Before the framing pass both happened, with no warning."""
    entity, warnings = parse_issue_body(
        "## Description\n\nd\n\n## Status\n\nactive\n\n## Business Value\n\n"
        "- Parent.\n  AC:US-001-01 (v1.0.0 - active)\n  - desc here.\n",
        "US-001 · S",
        "DocumentedUserStory",
    )

    assert entity is not None
    assert entity.acceptance_criteria == []
    assert entity.business_value == ["Parent. AC:US-001-01 (v1.0.0 - active)\n  - desc here."]
    assert warnings == []


def test_d20_holds_across_a_blank_line_as_markdown_nests_a_list_item():
    """A blank line does not end an issue-body item, so its wrapped `AC:` line after one is still its text."""
    entity, warnings = parse_issue_body(
        "## Business Value\n\n- Parent.\n\n  AC:US-001-01 (v1.0.0 - active)\n  - desc here.\n",
        "US-001 · S",
        "DocumentedUserStory",
    )

    assert entity is not None
    assert entity.acceptance_criteria == []
    assert entity.business_value == ["Parent. AC:US-001-01 (v1.0.0 - active)\n  - desc here."]
    assert warnings == []


def test_d20_the_normaliser_leaves_an_items_ac_shaped_line_as_authored():
    """The normaliser reads the same frame: a wrapped line is the item's text, so rules 2-4 and 7 never touch it."""
    body = "## Business Value\n\n- Parent.\n  AC:US-001-01 (V1.0 – Active) — inline\n"

    result = normalize(body, SourceFormat.ISSUE_BODY, "DocumentedUserStory")

    assert result.lines[3] == "  AC:US-001-01 (V1.0 – Active) — inline"
    assert result.changes == []


def test_an_ac_header_at_the_items_own_level_is_still_a_criterion():
    """Only a line deeper than the item's `- ` is its text: a bare `AC:` header at the item's level still opens a
    criterion, as it always did."""
    entity, _ = parse_issue_body(
        "## Business Value\n\n- Parent.\nAC:US-001-01 (v1.0.0 - active)\n- desc\n",
        "US-001 · S",
        "DocumentedUserStory",
    )

    assert entity is not None
    assert [ac.id for ac in entity.acceptance_criteria] == ["US-001-01"]


# --- the title is found by position --------------------------------------------------------------------


def test_a_quoted_banner_title_in_a_note_is_never_the_title_even_when_the_banner_has_none():
    """With no title after the opening rule, a note quoting the whole title form does not stand in for one: the
    header has no title, and no other entity's id is taken from the note."""
    text = _PAGE_OBJECT.replace(" * LIVING DOC — FEAT-042 · Account Setup Wizard\n", "").replace(
        " *   • Step order is fixed; the review step cannot be skipped.\n",
        " *   - See the LIVING DOC — FEAT-002 · Breached Password Check banner.\n",
    )

    result, warnings = parse_page_object(text)

    assert result is None
    assert [w.code for w in warnings] == ["MISSING_ENTITY_ID"]


def test_a_feature_header_title_is_the_line_after_the_opening_rule_not_any_line_reading_like_one():
    """A `.feature` header with no title line is reported, whatever a business-value item quotes."""
    text = (
        "# =============================================================================\n"
        "# =============================================================================\n"
        "# business_value:\n"
        "#   - LIVING DOC — US-009 · Quoted\n"
        "# =============================================================================\n"
        "\nFeature: Sample\n"
    )

    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert entity is None
    assert [w.code for w in warnings] == ["MISSING_ENTITY_ID"]


def test_the_title_is_the_frames_and_both_readers_take_it_from_there():
    """`normalize` rewrites the line the frame placed as the title, and the parser reads its id from that line."""
    text = _PAGE_OBJECT.replace("FEAT-042 · Account", "FEAT-042: Account")

    normalized, frame = normalize_framed(text, SourceFormat.PAGE_OBJECT, "DocumentedFeature")
    result, _ = parse_page_object(text)

    assert frame.title is not None
    assert frame.title.rendered == " * LIVING DOC — FEAT-042 · Account Setup Wizard"
    assert normalized.lines[1] == frame.title.rendered
    assert result is not None and result.entity is not None
    assert result.entity.title == "FEAT-042 · Account Setup Wizard"


def test_a_base_level_line_quoting_the_title_after_the_title_is_no_title_and_fits_no_level():
    """No line's prose ends a key or makes a title: a later `LIVING DOC — …` line at the key's own level is no
    continuation of its value either, so it is reported and not read."""
    text = _PAGE_OBJECT.replace(
        " * page-object:           AccountSetupWizardPage.ts\n",
        " * page-object:           AccountSetupWizardPage.ts\n * LIVING DOC — FEAT-002 · Quoted\n",
    )

    result, warnings = parse_page_object(text)

    assert result is not None and result.entity is not None
    assert result.entity.entity_id == "FEAT-042"
    assert result.page_ref.page_object == "AccountSetupWizardPage.ts"
    assert [(w.code, w.context) for w in warnings] == [
        ("AUTHORING_WARNING", "entity_id='FEAT-042' line_no=7 line='* LIVING DOC — FEAT-002 · Quoted'")
    ]


def test_the_identity_module_no_longer_offers_a_title_predicate():
    """`is_living_doc_title` decided a boundary by reading a line's prose; with the title placed by position it
    has no caller, and is gone with the guard that protected it."""
    assert not hasattr(identity, "is_living_doc_title")


# --- the header comment's close is recognised once ------------------------------------------------------


def test_a_comment_close_inside_a_value_does_not_end_the_frame():
    """A `*/` within a value is not the close: rule 1 still reaches the notes after it, and the parser reads them."""
    text = _PAGE_OBJECT.replace("a new account.", "a new account (see /* legacy */ wizard).")

    normalized = normalize(text, SourceFormat.PAGE_OBJECT, "DocumentedFeature")
    result, warnings = parse_page_object(text)

    assert [c.rule for c in normalized.changes] == [RULE_BULLET_MARKER, RULE_BULLET_MARKER]
    assert result is not None and result.entity is not None
    assert result.entity.notes == _NOTES
    assert warnings == []


@pytest.mark.parametrize(
    "close",
    [" * ============================================================================= */\n", " */\n", " *   */\n"],
    ids=["canon_banner", "bare", "indented_bare"],
)
def test_the_canon_banner_and_a_bare_close_both_end_the_frame(close):
    """Whichever form closes the comment, the frame ends on it, so a JSDoc `notes:` below is outside for both readers."""
    text = _PAGE_OBJECT.replace(" * ============================================================================= */\n", close) + (
        "\nexport class AccountSetupWizardPage {\n  /**\n   * notes:\n   *   • A JSDoc line.\n   */\n}\n"
    )

    normalized, frame = normalize_framed(text, SourceFormat.PAGE_OBJECT, "DocumentedFeature")
    result, warnings = parse_page_object(text)

    in_frame = [framed for framed in frame.lines if framed.role is not Role.OUTSIDE]
    assert in_frame[-1].raw == close.rstrip("\n")
    assert in_frame[-1].role is Role.RULE
    assert "   *   • A JSDoc line." in normalized.lines
    assert result is not None and result.entity is not None
    assert result.entity.notes == _NOTES
    assert warnings == []


def test_a_key_on_the_closing_line_is_still_read_without_the_close():
    """The close ends the frame after its own line: a key written on it is a header key, as it always was, and its
    value does not take the comment's `*/`."""
    text = _PAGE_OBJECT.replace(
        " * ============================================================================= */\n", " * route: /setup */\n"
    )

    result, _ = parse_page_object(text)

    assert result is not None
    assert result.page_ref.route == "/setup"


# --- one frame: the normaliser and the parser agree by construction -------------------------------------


def test_only_a_level_two_heading_ends_an_issue_body_section_for_the_normaliser_too():
    """A `###` heading inside `## Business Value` is that section's content for the parser, so rule 1 still reaches
    the items under it."""
    body = "## Business Value\n\n### Detail\n\n• Fewer support calls.\n"

    normalized = normalize(body, SourceFormat.ISSUE_BODY, "DocumentedUserStory")
    entity, _ = parse_issue_body(body, "US-001 · S", "DocumentedUserStory")

    assert normalized.lines[4] == "- Fewer support calls."
    assert entity is not None
    assert entity.business_value == ["Fewer support calls."]


def test_a_key_shaped_line_in_a_criterion_block_is_not_a_key_for_the_normaliser_either():
    """A `.feature` criterion block runs to the next rule: its `status:` line is no key, so it keeps its case."""
    text = _us_header("# acceptance_criteria:\n#   AC:US-001-01 (v1.0.0 - active)\n#     - desc\n#   status: Deprecated\n")

    normalized = normalize(text, SourceFormat.FEATURE_HEADER, "DocumentedUserStory")
    entity, _ = parse_feature_header(text, "DocumentedUserStory")

    assert "#   status: Deprecated" in normalized.lines
    assert RULE_STATE_CASING not in {c.rule for c in normalized.changes}
    assert entity is not None and entity.state is None


def test_a_bullet_key_with_text_on_its_own_line_still_opens_its_list_for_rule_one():
    """`preconditions: text` opens that key's section for the parser, so the normaliser corrects its items' markers."""
    text = _us_header("# status: active\n# preconditions: The customer is signed in.\n#   + The account is active.\n")

    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert entity is not None
    assert entity.preconditions == ["The account is active."]
    assert [w.code for w in warnings] == ["UNPARSED_BULLET_LINE"]


def test_a_tab_right_after_the_comment_marker_is_read_at_the_indent_of_its_rewritten_line():
    """Rule 6 makes `#<tab>- a` read `# - a`, at indent 0: the frame reads that indent, as every re-reader of the
    normalised text does, so the next line's level relative to it is the same for all of them."""
    text = _us_header("# status: active\n# business_value:\n#\t- one\n#  - two\n")

    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert warnings == []
    assert entity is not None
    assert entity.business_value == ["one\n - two"]


def test_a_blank_line_without_a_comment_marker_in_a_feature_header_closes_nothing():
    """A blank line without `#` is no header line: the list goes on after it, as a Markdown list does, for both
    readers."""
    text = _us_header("# status: active\n# business_value:\n#   - First.\n\n#   • Second.\n")

    normalized = normalize(text, SourceFormat.FEATURE_HEADER, "DocumentedUserStory")
    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert "#   - Second." in normalized.lines
    assert warnings == []
    assert entity is not None
    assert entity.business_value == ["First.", "Second."]


def test_a_blank_comment_line_in_a_feature_header_ends_nothing_either():
    """`#` alone is layout like a blank line: the list goes on after it, so its second item is read."""
    text = _us_header("# status: active\n# business_value:\n#   - First.\n#\n#   - Second.\n")

    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert warnings == []
    assert entity is not None
    assert entity.business_value == ["First.", "Second."]


def test_a_line_without_the_star_marker_inside_the_header_comment_closes_nothing_and_is_reported():
    """A comment line without ` * ` is no header line: it is not read but reported, and the next `•` is its own
    note for both readers."""
    text = _PAGE_OBJECT.replace(
        " *   • The wizard shares", "   wrapped without star\n *   • The wizard shares"
    )

    normalized = normalize(text, SourceFormat.PAGE_OBJECT, "DocumentedFeature")
    result, warnings = parse_page_object(text)

    assert " *   - The wizard shares one URL with its step files." in normalized.lines
    assert [(w.code, w.context) for w in warnings] == [
        ("AUTHORING_ERROR", "entity_id='FEAT-042' line_no=9 line='wrapped without star'")
    ]
    assert result is not None and result.entity is not None
    assert result.entity.notes == _NOTES


def test_an_unclosed_page_object_comment_leaves_its_lines_as_written():
    """With no `*/` the comment never ends, so no parser reads it and the normaliser rewrites none of its lines."""
    text = "/* ===\n * LIVING DOC — FEAT-001 · Login\n * notes:\n *   • a\n"

    normalized, frame = normalize_framed(text, SourceFormat.PAGE_OBJECT, "DocumentedFeature")

    assert " *   • a" in normalized.lines
    assert frame.problems[0].kind == UNTERMINATED_FRAME


def test_a_feature_header_with_one_rule_is_read_to_its_last_comment_line_and_reported():
    """A `.feature` header that never closes is still read, up to its last comment line before a tag or `Feature:`,
    so its entity and state load; the missing closing rule is reported."""
    text = "# =====\n# LIVING DOC — US-001 · Sample\n# status: Active\n\n@US_ID:US-001\nFeature: Sample\n"

    normalized, frame = normalize_framed(text, SourceFormat.FEATURE_HEADER, "DocumentedUserStory")
    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert "# status: active" in normalized.lines
    assert [problem.kind for problem in frame.problems] == [UNTERMINATED_FRAME]
    assert entity is not None and entity.state == "active"
    assert [(w.code, w.context) for w in warnings] == [
        ("AUTHORING_ERROR", "entity_id='US-001' line_no=1 line='# ====='")
    ]


def test_a_notes_items_wrapped_line_on_a_cross_reference_header_is_that_notes_text():
    """A cross-reference header's `notes:` items are items: a wrapped line reading `route:` is that note's text and
    never replaces the header's real route."""
    text = (
        "/* ===\n * LIVING DOC — FEAT-042 · W [cross-reference]\n * ===\n * parent-feat: FEAT-042\n"
        " * route: /a\n * notes:\n *   - a note that wraps\n *     route: /b\n * === */\n"
    )

    result, warnings = parse_page_object(text)

    assert result is not None
    assert result.page_ref.route == "/a"
    assert result.page_ref.notes == ["a note that wraps route: /b"]
    assert warnings == []


# --- criterion blocks: the frame alone bounds them -------------------------------------------------------


def test_a_key_at_the_key_level_ends_a_criterion_block_and_is_read():
    """`notes:` and `status:` belong to the entity: after the criteria, at the key level, both are read."""
    text = _us_header(
        "# acceptance_criteria:\n#   AC:US-001-01 (v1.0.0 - active)\n#     - desc\n"
        "# status: deprecated\n# notes:\n#   - A note after the criteria.\n"
    )

    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert warnings == []
    assert entity is not None
    assert [(ac.id, ac.description) for ac in entity.acceptance_criteria] == [("US-001-01", "desc")]
    assert entity.state == "deprecated"
    assert entity.notes == ["A note after the criteria."]


def test_a_rule_inside_the_header_ends_a_criterion_block_and_the_last_rule_ends_the_header():
    """A `# ===` rule is an optional end of a block; the last one ends the header."""
    text = _us_header(
        "# acceptance_criteria:\n#   AC:US-001-01 (v1.0.0 - active)\n#     - desc\n# =====\n# status: active\n"
    )

    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert warnings == []
    assert entity is not None and entity.state == "active"


def test_an_ac_line_off_the_criterion_level_is_text_and_reported():
    """The first `AC:` line sets the criterion level; one at another indent is no header, and it is reported."""
    text = _us_header(
        "# acceptance_criteria:\n#   AC:US-001-01 (v1.0.0 - active)\n#     - desc\n"
        "#    AC:US-001-02 (v1.0.0 - active)\n"
    )

    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert entity is not None and [ac.id for ac in entity.acceptance_criteria] == ["US-001-01"]
    assert [w.code for w in warnings][:1] == ["AUTHORING_WARNING"]
    assert "line_no=7 line='#    AC:US-001-02 (v1.0.0 - active)'" in warnings[0].context


def test_an_ac_line_on_a_criterion_items_text_in_an_issue_body_is_reported():
    """An `AC:` line deeper than a criterion item's `- ` continues that item, so it is no header; it is reported."""
    body = "## Acceptance Criteria\n\n### AC:US-001-01 (v1.0.0 - active)\n\n- d1\n  AC:US-001-02 (v1.0.0 - active)\n"

    entity, warnings = parse_issue_body(body, "US-001 · S", "DocumentedUserStory")

    assert entity is not None
    assert [(ac.id, ac.description) for ac in entity.acceptance_criteria] == [
        ("US-001-01", "d1 AC:US-001-02 (v1.0.0 - active)")
    ]
    assert [(w.code, w.context) for w in warnings] == [
        ("AUTHORING_WARNING", "entity_id='US-001' line_no=6 line='AC:US-001-02 (v1.0.0 - active)'")
    ]


def test_a_rule_line_inside_an_issue_body_criterion_is_its_text_not_its_end():
    """Only the frame ends a criterion: a `=====` line in an issue-body criterion is no boundary, so the lines after
    it are still read (the rule line itself wraps onto the description, as any unmarked line does)."""
    body = (
        "## Acceptance Criteria\n\n### AC:US-001-01 (v1.0.0 - active)\n\n- Valid credentials land on the dashboard.\n"
        "=====\n- Aspect: usability\n"
    )

    entity, warnings = parse_issue_body(body, "US-001 · S", "DocumentedUserStory")

    assert warnings == []
    assert entity is not None
    assert entity.acceptance_criteria[0].aspect == ["usability"]
    assert entity.acceptance_criteria[0].description == "Valid credentials land on the dashboard. ====="


def test_a_heading_indented_up_to_three_spaces_ends_a_criterion_as_commonmark_reads_it():
    """CommonMark allows a heading three spaces in: the frame ends the criterion there, so nothing after it is lost."""
    body = (
        "## Acceptance Criteria\n\n### AC:US-001-01 (v1.0.0 - active)\n\n- d\nmore text\n"
        "  ## Notes\n- A note.\n"
    )

    entity, warnings = parse_issue_body(body, "US-001 · S", "DocumentedUserStory")

    assert warnings == []
    assert entity is not None
    assert entity.acceptance_criteria[0].description == "d more text"
    assert entity.notes == ["A note."]


def test_a_heading_deeper_than_a_criterion_items_marker_is_that_items_text():
    """Under an open item, an indented heading is the item's content, as CommonMark nests it; the next `- ` stays in
    the criterion and, naming no field, is reported."""
    body = (
        "## Acceptance Criteria\n\n### AC:US-001-01 (v1.0.0 - active)\n\n- After login the dashboard shows the\n"
        "  ## Notes\n- A note.\n"
    )

    entity, warnings = parse_issue_body(body, "US-001 · S", "DocumentedUserStory")

    assert entity is not None and entity.notes == []
    assert entity.acceptance_criteria[0].description == "After login the dashboard shows the ## Notes"
    assert [w.code for w in warnings] == ["UNPARSED_AC_LINE"]
    assert "line_no=7 line='- A note.'" in warnings[0].context


# --- what the frame holds --------------------------------------------------------------------------------


def test_issue_body_sections_are_the_level_two_headings_in_order():
    """`sections` gives each `##` section's name and lines; a `###` heading and a fenced `##` line are content."""
    body = "intro\n\n## Description\n\nd\n\n### Detail\n\n```\n## not a heading\n```\n\n## Notes\n\n- n\n"

    _, frame = normalize_framed(body, SourceFormat.ISSUE_BODY, "DocumentedUserStory")
    found = sections(frame)

    assert [section.name for section in found] == ["description", "notes"]
    assert "## not a heading" in [framed.rendered for framed in found[0].lines]
    assert [framed.role for framed in found[0].lines if framed.rendered.startswith("#")] == [
        Role.SUBHEADING,
        Role.CODE,
    ]


def test_a_key_line_on_an_open_items_text_opens_no_section():
    """A wrapped line reading `status:` is the item's text: the frame opens no `status` section for it."""
    text = _us_header("# business_value:\n#   - Old accounts carry\n#     status: deprecated until verified.\n")

    _, frame = normalize_framed(text, SourceFormat.FEATURE_HEADER, "DocumentedUserStory")

    assert [section.name for section in sections(frame)] == ["business_value"]
    assert [framed.item_text for framed in sections(frame)[0].lines] == [False, True]


def test_a_scenario_files_sections_are_its_gherkin_keyword_lines():
    """`Feature:`, `Background:` and `Scenario:` open sections; the parser links tags to the scenario that follows."""
    text = "@tag\nFeature: F\n\nBackground:\n  Given x\n\n@AC:US-001-01\nScenario: S\n  When y\n"

    _, frame = normalize_framed(text, SourceFormat.SCENARIO_FILE, "DocumentedUserStory")
    scenarios, _ = parse_scenarios(text, "DocumentedUserStory")

    assert [framed.section for framed in frame.lines if framed.role is Role.HEADING] == [
        "Feature",
        "Background",
        "Scenario",
    ]
    assert [(s.title, s.tags) for s in scenarios] == [("S", ["@AC:US-001-01"])]


# --- structural problems -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text, fmt, expected",
    [
        ("# status: active\n", SourceFormat.FEATURE_HEADER, [Problem(NO_FRAME, 1)]),
        ("\n# ===\n# LIVING DOC — US-1 · S\n", SourceFormat.FEATURE_HEADER, [Problem(UNTERMINATED_FRAME, 2)]),
        ("export class P {}\n", SourceFormat.PAGE_OBJECT, [Problem(NO_FRAME, 1)]),
        ("// x\n/* ===\n * LIVING DOC — FEAT-1 · S\n", SourceFormat.PAGE_OBJECT, [Problem(UNTERMINATED_FRAME, 2)]),
        (
            "# ===\n# LIVING DOC — US-1 · S\n# ===\n# status: active\n\nFeature: S\n",
            SourceFormat.FEATURE_HEADER,
            [Problem(KEY_OUTSIDE_FRAME, 4)],
        ),
        (
            "/* ===\n * LIVING DOC — FEAT-1 · S\n * route: /s */\n * owners: T\n * === */\n\nexport class P {}\n",
            SourceFormat.PAGE_OBJECT,
            [Problem(LINE_AFTER_CLOSE, 4), Problem(LINE_AFTER_CLOSE, 5)],
        ),
    ],
    ids=["fh_no_frame", "fh_unterminated", "po_no_frame", "po_unterminated", "fh_key_outside", "po_line_after_close"],
)
def test_the_frame_reports_structural_problems_only(text, fmt, expected):
    """No frame, an unterminated frame, a key outside the frame and a line after an early close are reported -
    never a missing required key."""
    _, frame = normalize_framed(text, fmt, "DocumentedUserStory" if fmt is SourceFormat.FEATURE_HEADER else "DocumentedFeature")

    assert frame.problems == expected


@pytest.mark.parametrize(
    "parts, fmt, entity_type",
    [
        (("gherkin", "liv_doc_us", "us-001-customer-login.feature"), SourceFormat.FEATURE_HEADER, "DocumentedUserStory"),
        (("pageobject", "LoginPage.ts"), SourceFormat.PAGE_OBJECT, "DocumentedFeature"),
        (("gh-issues", "us-001-customer-login.md"), SourceFormat.ISSUE_BODY, "DocumentedUserStory"),
    ],
    ids=["feature_header", "page_object", "issue_body"],
)
def test_the_canon_examples_frame_without_a_problem(parts, fmt, entity_type):
    """The golden corpus is well framed: its title, if it has one, is found and no structural problem is reported."""
    _, frame = normalize_framed(read_fixture(*parts), fmt, entity_type)

    assert frame.problems == []
    assert (frame.title is not None) == (fmt is not SourceFormat.ISSUE_BODY)


# --- the boundary decisions live in one place ----------------------------------------------------------


def _names_in(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} | {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    }


def test_no_module_keeps_a_boundary_flag_of_its_own():
    """`header_closed`, `seen_title` and `current_section` were each walker's own boundary state; none survives."""
    offenders = {
        path.name: names
        for path in sorted(AUTHORING_DIR.glob("*.py"))
        if (names := _names_in(path) & {"header_closed", "seen_title", "current_section"})
    }

    assert offenders == {}


@pytest.mark.parametrize("module", ["feature_header.py", "page_object.py"])
def test_neither_header_parser_compiles_a_regex_of_its_own(module):
    """Both read the frame's key sections and look each key up in their key map; neither builds a key regex."""
    tree = ast.parse((AUTHORING_DIR / module).read_text(encoding="utf-8"))
    compiles = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "compile"
    ]

    assert compiles == []
