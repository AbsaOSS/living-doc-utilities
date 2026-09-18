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
Structural tests for `normalize` that are not about one rule's text transform: the
`TYPE_PROFILES`-only branching guarantee, `Change` naming every fired rule, and
`normalize_title`'s own edge cases (it has no `SourceFormat`, so it is not covered by
normalisation_cases.yaml rows).
"""

import inspect

from living_doc_utilities.authoring import normalize as normalize_module
from living_doc_utilities.authoring.normalize import (
    TYPE_PROFILES,
    NormalizedSource,
    SourceFormat,
    compute_fence_flags,
    normalize,
    normalize_title,
)
from tests.authoring.test_normalize_cases import CASES


def _case(case_id: str) -> dict:
    return next(c for c in CASES if c["id"] == case_id)


def test_module_never_branches_on_entity_type():
    source = inspect.getsource(normalize_module)
    assert "entity_type ==" not in source
    assert "entity_type !=" not in source


def test_type_profiles_is_the_only_place_with_bullet_section_data():
    assert TYPE_PROFILES["DocumentedFeature"].bullet_sections == frozenset()
    assert "business_value" in TYPE_PROFILES["DocumentedUserStory"].bullet_sections
    assert "rationale" in TYPE_PROFILES["DocumentedFunctionality"].bullet_sections
    assert "rationale" not in TYPE_PROFILES["DocumentedUserStory"].bullet_sections


def test_normalized_source_text_joins_lines():
    case = _case("rule3_state_casing_status_heading_issue_body")
    result = normalize(case["input"], SourceFormat(case["format"]), case["entity_type"])

    assert isinstance(result, NormalizedSource)
    assert result.text == "\n".join(result.lines)


def test_changes_name_every_rule_that_fired_on_one_line():
    # Reuses normalisation_cases.yaml's own multi-rule case rather than a new literal,
    # per the "cases file is normalize's only test data" rule; this test asserts a
    # property that case's own harness does not check - every fired rule is named,
    # each sharing the same before/after text.
    case = _case("rule2_rule3_rule4_scenario_file_combined")
    result = normalize(case["input"], SourceFormat(case["format"]), case["entity_type"])

    header_changes = [c for c in result.changes if c.line == 1]
    fired_rules = {c.rule for c in header_changes}

    assert fired_rules == {
        normalize_module.RULE_AC_HEADER_SEPARATOR,
        normalize_module.RULE_STATE_CASING,
        normalize_module.RULE_VERSION_FORM,
        normalize_module.RULE_INLINE_AC_DESCRIPTION,
    }
    expected_before = case["input"].splitlines()[0]
    expected_after = case["expected"].splitlines()[0]
    for change in header_changes:
        assert change.before == expected_before
        assert change.after == expected_after


def test_normalize_title_leaves_text_with_no_entity_id_untouched():
    title, changes = normalize_title("Just some free text")

    assert title == "Just some free text"
    assert changes == []


def test_normalize_title_leaves_already_canonical_title_untouched():
    title, changes = normalize_title("US-001 · Customer Login")

    assert title == "US-001 · Customer Login"
    assert changes == []


def test_normalize_title_fixes_separator_and_later_dash_together():
    title, changes = normalize_title("FUNC-001-Login Page–Validate Password Strength")

    assert title == "FUNC-001 · Login Page - Validate Password Strength"
    fired = {c.rule for c in changes}
    assert fired == {normalize_module.RULE_TITLE_ID_SEPARATOR, normalize_module.RULE_ENTITY_NAME_DASH}


def test_normalize_title_preserves_text_before_the_id():
    title, _ = normalize_title("LIVING DOC — US-001 - Customer Login")

    assert title.startswith("LIVING DOC — US-001")


def test_fence_flags_backtick_info_string_with_a_backtick_does_not_open_a_fence():
    # CommonMark: a backtick fence's info string may not itself contain a backtick
    # (a tilde fence has no such restriction) - so this is not a fence at all, and the
    # "AC:" line below it is live content, not a quoted example.
    lines = ["```lang`with`backtick", "AC:US-001-01 (v1.0.0 - active)", "```"]

    assert compute_fence_flags(lines) == [False, False, True]


def test_fence_flags_tab_indented_marker_does_not_open_a_fence():
    # CommonMark: a fence marker may be indented by at most three spaces; a tab
    # advances to the next 4-space tab stop, so it disqualifies the marker.
    lines = ["\t```", "AC:US-001-01 (v1.0.0 - active)", "```"]

    assert compute_fence_flags(lines) == [False, False, True]


def test_fence_flags_over_indented_closer_does_not_close_the_fence():
    # CommonMark: a closing fence may be indented by at most three spaces; four or
    # more leaves the block open, so the line after it is still inside the fence.
    lines = ["```", "AC:US-001-01 (v1.0.0 - active) example inside the fence", "    ```", "still inside"]

    assert compute_fence_flags(lines) == [True, True, True, True]
