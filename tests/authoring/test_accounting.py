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
Line accounting: every authored line a parser does not read is reported - `AUTHORING_ERROR` when it breaks the
header format, `AUTHORING_WARNING` otherwise - and every line warning names the input line and its text.
"""

import re

import pytest

from living_doc_utilities.authoring.feature_header import parse_feature_header
from living_doc_utilities.authoring.issue_body import parse_issue_body
from living_doc_utilities.authoring.page_object import parse_page_object
from living_doc_utilities.contracts.codes import Code, CodeKind

_LINE_NO_RE = re.compile(r"line_no=(\d+)")


def _us_header(body: str) -> str:
    return f"# =====\n# LIVING DOC — US-001 · Sample\n# =====\n{body}# =====\n\nFeature: Sample\n"


def _po(body: str) -> str:
    return f"/* =====\n * LIVING DOC — FEAT-042 · Account Setup Wizard\n * =====\n{body} * ===== */\n"


def _codes_and_lines(text: str, warnings) -> list[tuple[str, str]]:
    """Each warning's code and the input line its `line_no` names."""
    lines = text.split("\n")
    return [(w.code, lines[int(_LINE_NO_RE.search(w.context).group(1)) - 1].strip()) for w in warnings]


def test_both_authoring_codes_are_warnings_so_a_parser_never_stops():
    """`AUTHORING_ERROR` names a format break, but like every parser code it is a warning: parsing goes on."""
    assert Code.AUTHORING_WARNING.kind is CodeKind.WARNING
    assert Code.AUTHORING_ERROR.kind is CodeKind.WARNING


# --- a format break: AUTHORING_ERROR ---------------------------------------------------------------------


def test_a_line_with_text_and_no_comment_marker_inside_a_feature_header_is_not_read():
    """The line breaks the format (Gherkin rejects it above `Feature:` too): its item is not read, it is reported."""
    text = _us_header("# status: active\n# business_value:\n  • Fewer support calls.\n")

    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert entity is not None and entity.business_value == []
    assert _codes_and_lines(text, warnings) == [("AUTHORING_ERROR", "• Fewer support calls.")]


def test_a_key_below_the_closing_rule_is_reported():
    """A key between the closing rule and `Feature:` is outside the header: not read, reported."""
    text = "# =====\n# LIVING DOC — US-001 · Sample\n# =====\n# status: active\n# =====\n# notes:\n#   - n\n\nFeature: S\n"

    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert entity is not None and entity.notes == []
    assert _codes_and_lines(text, warnings) == [("AUTHORING_ERROR", "# notes:")]


def test_a_comment_above_the_opening_rule_is_no_header_line_and_is_not_reported():
    """The header starts at its opening rule, so a key-shaped comment above it - Gherkin's `# language:`, which
    must sit on line 1 - is no header line: it is neither read nor reported."""
    text = "# language: en\n" + _us_header("# status: active\n")

    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert entity is not None and entity.state == "active"
    assert warnings == []


def test_a_feature_file_with_no_header_says_no_header_was_found():
    """A `.feature` file with no `# ===` rule above `Feature:` has no header: nothing is read, and the report says
    that no header was found rather than that a title line is missing."""
    text = "# status: In Review\n\n@US_ID:US-001\nFeature: Customer Login\n"

    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert entity is None
    assert [(w.code, w.message) for w in warnings] == [
        ("MISSING_ENTITY_ID", "No living-doc header found: no '# ===' rule above 'Feature:'.")
    ]


def test_a_header_with_one_rule_is_read_and_reported_as_never_closed():
    """With no closing rule the header is read to its last comment line, so its keys load; the rule is reported."""
    text = "# =====\n# LIVING DOC — US-001 · Sample\n# status: active\n\nFeature: S\n"

    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert entity is not None and entity.state == "active"
    assert _codes_and_lines(text, warnings) == [("AUTHORING_ERROR", "# =====")]


def test_header_lines_up_to_the_real_end_after_a_comment_that_closed_early_are_reported():
    """A value ending in `*/` closes the comment there, yet a later ` * ` line before any code closes it again: that
    is the header's real end, so each line up to it is reported, across a blank line too."""
    text = (
        "/* =====\n * LIVING DOC — FEAT-042 · Account Setup Wizard\n * =====\n * route: /setup */\n\n"
        " * page-object: AccountSetupWizardPage.ts\n * ===== */\n\nexport class P {}\n"
    )

    result, warnings = parse_page_object(text)

    assert result is not None and result.page_ref.route == "/setup"
    assert result.page_ref.page_object == ""
    assert _codes_and_lines(text, warnings) == [
        ("AUTHORING_ERROR", "* page-object: AccountSetupWizardPage.ts"),
        ("AUTHORING_ERROR", "* ===== */"),
    ]


def test_a_comment_closed_by_a_value_with_no_later_close_ends_the_header_there():
    """With no later ` * ` line closing the comment again, the header ends where the comment did: what follows is
    no header line, and nothing is reported. Such a file is no valid TypeScript, and TypeScript reports it."""
    text = (
        "/* =====\n * LIVING DOC — FEAT-042 · Account Setup Wizard\n * =====\n * route: /setup */\n"
        " * page-object: AccountSetupWizardPage.ts\n\nexport class P {}\n"
    )

    result, warnings = parse_page_object(text)

    assert result is not None and result.page_ref.route == "/setup"
    assert result.page_ref.page_object == ""
    assert warnings == []


def test_an_unclosed_page_object_comment_is_reported_as_read_nowhere():
    """A PageObject comment with no `*/` is no valid TypeScript, and nothing in it is read: the report says so,
    not that it was read up to its last comment line as an unclosed `.feature` header is."""
    text = "/* =====\n * LIVING DOC — FEAT-042 · Account Setup Wizard\n * route: /setup\n\nexport class P {}\n"

    result, warnings = parse_page_object(text)

    assert result is None
    assert [(w.code, w.message) for w in warnings if w.code == Code.AUTHORING_ERROR.name] == [
        ("AUTHORING_ERROR", "The header comment is never closed with '*/': nothing in it is read.")
    ]


@pytest.mark.parametrize(
    "key_line, field, value",
    [
        ("# status: active\n#   - Second.\n", "state", "active"),
        ("# status: active\n#\n#   - Second.\n", "state", "active"),
    ],
    ids=["under_the_key", "after_a_blank_line"],
)
def test_a_single_value_key_reports_a_further_line_and_keeps_its_value(key_line, field, value):
    """`status:` takes one value: a deeper line under it is an error and is not read, so the state stays valid."""
    text = _us_header(key_line)

    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert getattr(entity, field) == value
    assert _codes_and_lines(text, warnings) == [("AUTHORING_ERROR", "#   - Second.")]


def test_a_page_object_line_without_its_star_is_reported():
    """A line inside the header comment without ` * ` is not read, and reported like a `.feature` line without `#`."""
    text = _po(" * purpose: Wizard\n   continues here\n * page-object: W.ts\n")

    result, warnings = parse_page_object(text)

    assert result is not None and result.page_ref.purpose == "Wizard"
    assert _codes_and_lines(text, warnings) == [("AUTHORING_ERROR", "continues here")]


# --- an unread line: AUTHORING_WARNING -------------------------------------------------------------------


def test_prose_before_the_first_key_is_reported():
    """A `.feature` header has no place for prose before its first key."""
    text = _us_header("# Some prose line.\n# status: active\n")

    _, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert _codes_and_lines(text, warnings) == [("AUTHORING_WARNING", "# Some prose line.")]


def test_a_cross_reference_headers_opening_prose_is_canon_and_not_reported():
    """The canon lets a cross-reference header open with prose before its first key."""
    text = _po(" * This file implements Step 1 (Profile).\n *\n * parent-feat: FEAT-042\n * route: /setup/profile\n")

    _, warnings = parse_page_object(text)

    assert warnings == []


def test_a_key_written_twice_reads_the_first_value_and_reports_the_later_one():
    """Only the first occurrence of a key is read (owner, 2026-10-04); the later one is reported, not used."""
    text = _us_header("# status: active\n# status: deprecated\n")

    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert entity is not None and entity.state == "active"
    assert _codes_and_lines(text, warnings) == [("AUTHORING_WARNING", "# status: deprecated")]


def test_every_line_of_a_repeated_bullet_key_is_reported():
    """A repeated key's items are its value too: each is reported on its own line, so none is lost unnamed."""
    text = _po(" * notes:\n *   - First note.\n * notes:\n *   - Second note.\n *     wrapped.\n")

    result, warnings = parse_page_object(text)

    assert result is not None and result.entity is not None
    assert result.entity.notes == ["First note."]
    assert _codes_and_lines(text, warnings) == [
        ("AUTHORING_WARNING", "* notes:"),
        ("AUTHORING_WARNING", "*   - Second note."),
        ("AUTHORING_WARNING", "*     wrapped."),
    ]


def test_criteria_under_a_repeated_acceptance_criteria_key_are_not_read_and_are_reported():
    """In a `.feature` header the criteria under a key belong to it, so a repeated `acceptance_criteria:` takes its
    criteria along: they are reported line by line, and only the first key's criteria are read."""
    text = _us_header(
        "# acceptance_criteria:\n#   AC:US-001-01 (v1.0.0 - active)\n#     - First.\n"
        "# acceptance_criteria:\n#   AC:US-001-02 (v1.0.0 - active)\n#     - Second.\n"
    )

    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert entity is not None and [ac.id for ac in entity.acceptance_criteria] == ["US-001-01"]
    assert _codes_and_lines(text, warnings) == [
        ("AUTHORING_WARNING", "# acceptance_criteria:"),
        ("AUTHORING_WARNING", "#   AC:US-001-02 (v1.0.0 - active)"),
        ("AUTHORING_WARNING", "#     - Second."),
    ]


def test_every_line_of_a_dropped_criterion_is_reported_and_the_next_criterion_is_read():
    """A criterion the grammar drops - here an unknown state - takes its block's lines with it: each is reported on
    its own line, beside the criterion's `MALFORMED_AC`, and the next criterion is read."""
    text = _us_header(
        "# acceptance_criteria:\n#   AC:US-001-01 (v1.0.0 - bogus)\n#     - First.\n#       wrapped.\n"
        "#   AC:US-001-02 (v1.0.0 - active)\n#     - Second.\n"
    )

    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert entity is not None and [ac.id for ac in entity.acceptance_criteria] == ["US-001-02"]
    assert _codes_and_lines(text, warnings) == [
        ("MALFORMED_AC", "#   AC:US-001-01 (v1.0.0 - bogus)"),
        ("AUTHORING_WARNING", "#     - First."),
        ("AUTHORING_WARNING", "#       wrapped."),
    ]


def test_a_dropped_criterions_line_already_reported_is_not_reported_twice():
    """A block line the grammar named already keeps its one warning; a dropped criterion adds none for it."""
    text = _us_header("# acceptance_criteria:\n#   AC:US-001-01 (v1.0.0 - active)\n#     prose with no bullet\n")

    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert entity is not None and entity.acceptance_criteria == []
    assert [w.code for w in warnings] == [Code.UNPARSED_AC_LINE.name, Code.MALFORMED_AC.name]


def test_every_line_of_a_dropped_issue_body_criterion_is_reported():
    """The issue body's criteria are bounded by the same frame: a dropped one's lines are reported too."""
    body = "## Acceptance Criteria\n\n### AC:US-001-01 (v1.0.0 - bogus)\n\n- First.\n"

    entity, warnings = parse_issue_body(body, "US-001 · S", "DocumentedUserStory")

    assert entity is not None and entity.acceptance_criteria == []
    assert _codes_and_lines(body, warnings) == [
        ("MALFORMED_AC", "### AC:US-001-01 (v1.0.0 - bogus)"),
        ("AUTHORING_WARNING", "- First."),
    ]


def test_a_line_at_the_keys_own_level_under_a_scalar_key_is_reported():
    """A scalar value continues only on a deeper line: one at the key's level fits no level and is not read."""
    text = _po(" * page-object: AccountSetupWizardPage.ts\n * LIVING DOC — FEAT-002 · Quoted\n")

    result, warnings = parse_page_object(text)

    assert result is not None and result.page_ref.page_object == "AccountSetupWizardPage.ts"
    assert _codes_and_lines(text, warnings) == [("AUTHORING_WARNING", "* LIVING DOC — FEAT-002 · Quoted")]


def test_a_text_value_wraps_silently_and_continues_after_a_blank_line_with_a_warning():
    """`purpose:` is text: its canonical wrap is read silently; a part after a blank line is read and reported."""
    wrapped = _po(" * purpose: Multi-step wizard for creating\n *          a new account.\n")
    after_blank = _po(" * purpose: Multi-step wizard for creating\n *\n *          a new account.\n")

    wrapped_result, wrapped_warnings = parse_page_object(wrapped)
    blank_result, blank_warnings = parse_page_object(after_blank)

    assert wrapped_warnings == []
    assert wrapped_result is not None and blank_result is not None
    assert wrapped_result.page_ref.purpose == blank_result.page_ref.purpose == "Multi-step wizard for creating a new account."
    assert _codes_and_lines(after_blank, blank_warnings) == [("AUTHORING_WARNING", "*          a new account.")]


def test_an_id_list_may_wrap():
    """A long id list continues on a deeper line, as text does."""
    text = _po(" * functionalities: FUNC-005,\n *                  FUNC-006\n")

    result, warnings = parse_page_object(text)

    assert warnings == []
    assert result is not None and result.entity is not None
    assert result.entity.functionalities == ["FUNC-005", "FUNC-006"]


def test_a_blank_star_line_in_a_notes_list_ends_nothing():
    """` *` alone is layout: the list goes on after it."""
    text = _po(" * notes:\n *   - First note.\n *\n *   - Second note.\n")

    result, warnings = parse_page_object(text)

    assert warnings == []
    assert result is not None and result.entity is not None
    assert result.entity.notes == ["First note.", "Second note."]


# --- issue bodies ----------------------------------------------------------------------------------------


def test_issue_body_text_before_the_first_heading_is_reported_but_an_html_comment_is_not():
    """An HTML comment renders as nothing (the canon's provenance note); any other text there is reported."""
    body = "<!-- provenance -->\nSome intro text.\n\n## Status\n\nactive\n"

    _, warnings = parse_issue_body(body, "US-001 · S", "DocumentedUserStory")

    assert _codes_and_lines(body, warnings) == [("AUTHORING_WARNING", "Some intro text.")]


def test_a_heading_written_twice_reads_the_first_section_and_reports_every_line_of_the_later_one():
    """Only the first `## Notes` is read; the later heading and each of its lines are reported."""
    body = "## Status\n\nactive\n\n## Notes\n\n- First note.\n\n## Notes\n\n- Second note.\n"

    entity, warnings = parse_issue_body(body, "US-001 · S", "DocumentedUserStory")

    assert entity is not None and entity.notes == ["First note."]
    assert _codes_and_lines(body, warnings) == [
        ("AUTHORING_WARNING", "## Notes"),
        ("AUTHORING_WARNING", "- Second note."),
    ]


def test_prose_in_the_criteria_section_outside_every_criterion_is_reported():
    """`## Acceptance Criteria` holds criteria; a line before the first one belongs to none."""
    body = "## Acceptance Criteria\n\nThese cover login.\n\n### AC:US-001-01 (v1.0.0 - active)\n\n- d\n"

    entity, warnings = parse_issue_body(body, "US-001 · S", "DocumentedUserStory")

    assert entity is not None and [ac.id for ac in entity.acceptance_criteria] == ["US-001-01"]
    assert _codes_and_lines(body, warnings) == [("AUTHORING_WARNING", "These cover login.")]


def test_a_code_block_inside_a_criterion_is_reported_line_by_line():
    """No criterion field holds code: each line of the block is reported."""
    body = "## Acceptance Criteria\n\n### AC:US-001-01 (v1.0.0 - active)\n\n- d\n\n```\nPOST /login\n```\n"

    _, warnings = parse_issue_body(body, "US-001 · S", "DocumentedUserStory")

    assert _codes_and_lines(body, warnings) == [
        ("AUTHORING_WARNING", "```"),
        ("AUTHORING_WARNING", "POST /login"),
        ("AUTHORING_WARNING", "```"),
    ]


def test_an_item_nested_one_space_deeper_is_reported_as_github_renders_it_a_sibling():
    """`D19`: the parser nests it by indent, GitHub shows a sibling; the author is told to decide."""
    body = "## Business Value\n\n- A.\n - B.\n"

    entity, warnings = parse_issue_body(body, "US-001 · S", "DocumentedUserStory")

    assert entity is not None and entity.business_value == ["A.\n - B."]
    assert _codes_and_lines(body, warnings) == [("AUTHORING_WARNING", "- B.")]


# --- every line warning names its line ---------------------------------------------------------------------


def test_every_line_warning_of_a_broken_header_names_its_input_line():
    """Each warning about a line carries `line_no` and the line itself; the caller adds the file."""
    text = _us_header(
        "# status: Bogus\n"
        "# unknown_key: x\n"
        "# preconditions: prose\n"
        "#   - p\n"
        "# acceptance_criteria:\n"
        "#   AC:US-001-01 (v1.0.0 - active)\n"
        "#     - d\n"
        "#    odd line\n"
    )

    _, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert sorted(_codes_and_lines(text, warnings)) == sorted(
        [
            ("IGNORED_AUTHORED_KEY", "# unknown_key: x"),
            ("UNPARSED_BULLET_LINE", "# preconditions: prose"),
            ("MISINDENTED_LINE", "#    odd line"),
            ("MALFORMED_STATUS", "# status: Bogus"),
        ]
    )
