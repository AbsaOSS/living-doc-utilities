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
Where a warning belongs (`DEC-77`): each authoring warning sets the `entity_id`, `ac_id` and `line_no` its parser
knows, and `context` keeps its free text. `path` is never set here: a collector fills it.
"""

from dataclasses import dataclass
from typing import Callable, Optional

import pytest

from living_doc_utilities.authoring.feature_header import parse_feature_header
from living_doc_utilities.authoring.html_to_markdown import convert_html_to_markdown
from living_doc_utilities.authoring.issue_body import parse_issue_body
from living_doc_utilities.authoring.page_object import parse_page_object
from living_doc_utilities.authoring.relations import check_relations
from living_doc_utilities.authoring.scenario import parse_scenarios
from living_doc_utilities.authoring.status import derive_statuses
from living_doc_utilities.contracts.envelope import ContractWarning


def _us_header(body: str) -> str:
    """A User Story `.feature` header: the title is on line 2, so `body` starts on line 4."""
    return f"# =====\n# LIVING DOC — US-001 · Sample\n# =====\n{body}# =====\n\nFeature: Sample\n"


def _criterion(header: str, *lines: str) -> str:
    """`# status:` on line 4, `# acceptance_criteria:` on 5, the criterion's header on 6 and `lines` from 7."""
    return _us_header("# status: active\n# acceptance_criteria:\n" + "".join(f"#{line}\n" for line in (header, *lines)))


def _code_block_warnings(ac_id: str) -> list[ContractWarning]:
    """An issue body whose criterion `ac_id` holds a code block, on lines 15 to 17."""
    body = (
        "## Description\n\nd\n\n## Status\n\nactive\n\n## Acceptance Criteria\n\n"
        f"### AC:{ac_id} (v1.0.0 - active)\n\n- Shows the result.\n\n```\nx = 1\n```\n"
    )
    return parse_issue_body(body, "US-001 · S", "DocumentedUserStory")[1]


def _header_warnings(text: str) -> list[ContractWarning]:
    return parse_feature_header(text, "DocumentedUserStory")[1]


def _tag_warnings(tag: str) -> list[ContractWarning]:
    """The tag is on line 3."""
    return parse_scenarios(f"Feature: S\n\n  {tag}\n  Scenario: Sc\n    Given a step\n", "DocumentedUserStory")[1]


def _parsed_us(status: str = "active"):
    entity, _ = parse_issue_body(f"## Description\n\nd\n\n## Status\n\n{status}\n", "US-001 · S", "DocumentedUserStory")
    return entity


@dataclass(frozen=True)
class LocationCase:
    """One warning a parser reports, and the location fields it must carry."""

    name: str
    produce: Callable[[], list[ContractWarning]]
    code: str
    entity_id: Optional[str]
    ac_id: Optional[str]
    line_no: Optional[int]


LOCATION_CASES = [
    # A criterion header: the entity, the criterion when its id is valid, and the header's line.
    LocationCase(
        "header_unmappable_valid_id",
        lambda: _header_warnings(_criterion("   AC:US-001-01 (v1.0.0 - active - soon)", "     - Desc.")),
        "MALFORMED_AC",
        "US-001",
        "US-001-01",
        6,
    ),
    LocationCase(
        "header_without_parentheses_valid_id",
        lambda: _header_warnings(_criterion("   AC:US-001-01 v1.0.0 - active", "     - Desc.")),
        "MALFORMED_AC",
        "US-001",
        "US-001-01",
        6,
    ),
    LocationCase(
        "header_two_declarations",
        lambda: _header_warnings(
            _criterion(
                "   AC:US-001-01 (v1.0.0 - active)", "     - Shows {rule}.", "     - Aspect: a, b", "     - rule: x"
            )
        ),
        "MALFORMED_AC",
        "US-001",
        "US-001-01",
        6,
    ),
    LocationCase(
        "header_invalid_id",
        lambda: _header_warnings(_criterion("   AC:US-1 (v1.0.0 - active)", "     - Desc.")),
        "MALFORMED_AC",
        "US-001",
        None,
        6,
    ),
    # A line: the entity and the line, and the criterion it is in when that criterion's id is valid.
    LocationCase(
        "dropped_criterion_line",
        lambda: _header_warnings(_criterion("   AC:US-001-01 (v1.0.0 - active - soon)", "     - Desc.")),
        "AUTHORING_WARNING",
        "US-001",
        "US-001-01",
        7,
    ),
    LocationCase(
        "unparsed_ac_line",
        lambda: _header_warnings(_criterion("   AC:US-001-01 (v1.0.0 - active)", "     - Desc.", "     - rule: x")),
        "UNPARSED_AC_LINE",
        "US-001",
        "US-001-01",
        8,
    ),
    LocationCase(
        "misindented_criterion_line",
        lambda: _header_warnings(_criterion("   AC:US-001-01 (v1.0.0 - active)", "     - Desc.", "    stray")),
        "MISINDENTED_LINE",
        "US-001",
        "US-001-01",
        8,
    ),
    LocationCase(
        "criterion_header_read_as_text",
        lambda: _header_warnings(
            _criterion("   AC:US-001-01 (v1.0.0 - active)", "     - Desc.", "       AC:US-001-02 (v1.0.0 - active)")
        ),
        "AUTHORING_WARNING",
        "US-001",
        "US-001-01",
        8,
    ),
    LocationCase(
        "code_block_in_criterion",
        lambda: _code_block_warnings("US-001-01"),
        "AUTHORING_WARNING",
        "US-001",
        "US-001-01",
        15,
    ),
    LocationCase(
        "code_block_in_criterion_with_invalid_id",
        lambda: _code_block_warnings("US-1"),
        "AUTHORING_WARNING",
        "US-001",
        None,
        15,
    ),
    LocationCase(
        "misindented_bullet_field_line",
        lambda: _header_warnings(_us_header("# status: active\n# preconditions:\n#   - one\n#  - two\n")),
        "MISINDENTED_LINE",
        "US-001",
        None,
        7,
    ),
    LocationCase(
        "ignored_authored_key",
        lambda: _header_warnings(_us_header("# status: active\n# owner: x\n")),
        "IGNORED_AUTHORED_KEY",
        "US-001",
        None,
        5,
    ),
    LocationCase(
        "authoring_warning",
        lambda: _header_warnings(_us_header("# Some prose.\n# status: active\n")),
        "AUTHORING_WARNING",
        "US-001",
        None,
        4,
    ),
    LocationCase(
        "authoring_error",
        lambda: _header_warnings(_us_header("# status: active\n#   more\n")),
        "AUTHORING_ERROR",
        "US-001",
        None,
        5,
    ),
    LocationCase(
        "issue_body_unknown_section",
        lambda: parse_issue_body("## Description\n\nd\n\n## Nonsense\n\nv\n", "US-001 · S", "DocumentedUserStory")[1],
        "UNKNOWN_SECTION",
        "US-001",
        None,
        5,
    ),
    LocationCase(
        "issue_body_malformed_status",
        lambda: parse_issue_body(
            "## Description\n\nd\n\n## Status\n\nshipping\n", "US-001 · S", "DocumentedUserStory"
        )[1],
        "MALFORMED_STATUS",
        "US-001",
        None,
        5,
    ),
    # No entity was emitted: the line only.
    LocationCase(
        "missing_title_line",
        lambda: _header_warnings("# =====\n# status: active\n# =====\n\nFeature: S\n"),
        "MISSING_ENTITY_ID",
        None,
        None,
        1,
    ),
    LocationCase(
        "title_without_id",
        lambda: _header_warnings("# =====\n# LIVING DOC — Sample\n# =====\n# status: active\n# =====\n\nFeature: S\n"),
        "MISSING_ENTITY_ID",
        None,
        None,
        2,
    ),
    LocationCase(
        "page_object_missing_title",
        lambda: parse_page_object("/* no title */\n")[1],
        "MISSING_ENTITY_ID",
        None,
        None,
        1,
    ),
    # A scenario tag: the criterion when the tag's id is valid, and the tag's line; a scenario names no entity.
    LocationCase(
        "tag_second_parameter",
        lambda: _tag_warnings("@AC:US-001-01/aspect:a/priority:high"),
        "MALFORMED_AC",
        None,
        "US-001-01",
        3,
    ),
    LocationCase("tag_invalid_id", lambda: _tag_warnings("@AC:not-valid"), "MALFORMED_AC", None, None, 3),
    # Knows the entity only.
    LocationCase(
        "missing_status",
        lambda: derive_statuses([_parsed_us().model_copy(update={"state": None})])[1],
        "MISSING_STATUS",
        "US-001",
        None,
        None,
    ),
    LocationCase(
        "unresolved_relation",
        lambda: check_relations([_parsed_us().model_copy(update={"superseded_by": "US-404"})]),
        "UNRESOLVED_RELATION",
        "US-001",
        None,
        None,
    ),
    # Knows nothing: an issue title, or an HTML fragment.
    LocationCase(
        "issue_title_without_id",
        lambda: parse_issue_body("## Description\n\nd\n", "No id", "DocumentedUserStory")[1],
        "MISSING_ENTITY_ID",
        None,
        None,
        None,
    ),
    LocationCase(
        "html_content_dropped",
        lambda: convert_html_to_markdown("<script>x</script><p>kept</p>")[1],
        "HTML_CONTENT_DROPPED",
        None,
        None,
        None,
    ),
]


@pytest.mark.parametrize("case", LOCATION_CASES, ids=[case.name for case in LOCATION_CASES])
def test_a_warning_carries_the_location_its_parser_knows(case: LocationCase):
    """The first warning with the case's code carries exactly the entity, criterion and line the parser knows."""
    warning = next(warning for warning in case.produce() if warning.code == case.code)

    assert (warning.entity_id, warning.ac_id, warning.line_no) == (case.entity_id, case.ac_id, case.line_no)
    assert warning.path is None


def test_a_line_of_a_criterion_under_a_repeated_key_names_that_criterion():
    """A key written twice is not read, and each of its lines is reported; one inside a criterion names it."""
    text = _us_header(
        "# status: active\n# acceptance_criteria:\n#   AC:US-001-01 (v1.0.0 - active)\n#     - First.\n"
        "# acceptance_criteria:\n#   AC:US-001-02 (v1.0.0 - active)\n#     - Second.\n"
    )

    warnings = _header_warnings(text)

    assert [(w.code, w.ac_id, w.line_no) for w in warnings] == [
        ("AUTHORING_WARNING", None, 8),
        ("AUTHORING_WARNING", "US-001-02", 9),
        ("AUTHORING_WARNING", "US-001-02", 10),
    ]


@pytest.mark.parametrize("case", LOCATION_CASES, ids=[case.name for case in LOCATION_CASES])
def test_a_warning_keeps_its_context_text(case: LocationCase):
    """`context` keeps its free text: it still names the line a structured `line_no` names."""
    warning = next(warning for warning in case.produce() if warning.code == case.code)

    assert warning.context
    if warning.line_no is not None:
        assert f"line_no={warning.line_no}" in warning.context
