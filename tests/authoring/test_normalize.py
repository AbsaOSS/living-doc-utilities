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

"""Structural `normalize` tests: `TYPE_PROFILES`-only branching, `Change` naming every fired rule, `normalize_title`."""

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
    """The `normalize` module's source contains no `entity_type ==` or `entity_type !=` branch."""
    source = inspect.getsource(normalize_module)
    assert "entity_type ==" not in source
    assert "entity_type !=" not in source


def test_type_profiles_lists_the_bullet_sections_per_entity_type():
    """`TYPE_PROFILES`: a Feature has only `notes`, a User Story `business_value`, a Functionality `rationale`."""
    assert TYPE_PROFILES["DocumentedFeature"] == frozenset({"notes"})
    assert "business_value" in TYPE_PROFILES["DocumentedUserStory"]
    assert "rationale" in TYPE_PROFILES["DocumentedFunctionality"]
    assert "rationale" not in TYPE_PROFILES["DocumentedUserStory"]
    # `notes` is the one bullet section every entity type carries.
    for entity_type in TYPE_PROFILES:
        assert "notes" in TYPE_PROFILES[entity_type]


def test_normalized_source_text_joins_lines():
    """`NormalizedSource.text` is always exactly its `lines` rejoined with newlines, never drifting from them."""
    case = _case("rule3_state_casing_status_heading_issue_body")
    result = normalize(case["input"], SourceFormat(case["format"]), case["entity_type"])

    assert isinstance(result, NormalizedSource)
    assert result.text == "\n".join(result.lines)


def test_changes_name_every_rule_that_fired_on_one_line():
    """When multiple rules fire on one line, every one is named in `changes`, sharing that line's before/after."""
    # Reuses the multi-rule case from normalisation_cases.yaml; asserts what its harness skips: every rule is named.
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
    """A title with no entity id passes through `normalize_title` unchanged, with no changes recorded."""
    title, changes = normalize_title("Just some free text")

    assert title == "Just some free text"
    assert changes == []


def test_normalize_title_leaves_already_canonical_title_untouched():
    """A title already in canonical form passes through `normalize_title` unchanged, with no changes recorded."""
    title, changes = normalize_title("US-001 · Customer Login")

    assert title == "US-001 · Customer Login"
    assert changes == []


def test_normalize_title_fixes_separator_and_later_dash_together():
    """A title with both a non-canonical id separator and an en dash further on gets both fixed in one pass."""
    title, changes = normalize_title("FUNC-001-Login Page–Validate Password Strength")

    assert title == "FUNC-001 · Login Page - Validate Password Strength"
    fired = {c.rule for c in changes}
    assert fired == {normalize_module.RULE_TITLE_ID_SEPARATOR, normalize_module.RULE_ENTITY_NAME_DASH}


def test_normalize_title_preserves_text_before_the_id():
    """`normalize_title` keeps any free text preceding the entity id intact."""
    title, _ = normalize_title("LIVING DOC — US-001 - Customer Login")

    assert title.startswith("LIVING DOC — US-001")


def test_normalize_title_places_the_separator_after_the_real_id_not_a_tracker_key():
    """A tracker key before the entity id is left alone; the canonical separator lands after the real id."""
    title, _ = normalize_title("BUG-7 fix for US-001 - Customer Login")

    assert title == "BUG-7 fix for US-001 · Customer Login"


def test_fence_flags_backtick_info_string_with_a_backtick_does_not_open_a_fence():
    """A backtick fence whose info string itself contains a backtick is not a fence, so content below it stays live."""
    lines = ["```lang`with`backtick", "AC:US-001-01 (v1.0.0 - active)", "```"]

    assert compute_fence_flags(lines) == [False, False, True]


def test_fence_flags_tab_indented_marker_does_not_open_a_fence():
    """A tab-indented fence marker does not open a fence, since a tab expands past the three-space indent limit."""
    lines = ["\t```", "AC:US-001-01 (v1.0.0 - active)", "```"]

    assert compute_fence_flags(lines) == [False, False, True]


def test_fence_flags_over_indented_closer_does_not_close_the_fence():
    """A closing fence marker indented four or more spaces fails to close the fence, so the line after stays inside."""
    lines = ["```", "AC:US-001-01 (v1.0.0 - active) example inside the fence", "    ```", "still inside"]

    assert compute_fence_flags(lines) == [True, True, True, True]


def test_feature_header_rule_6_is_recorded_per_line_with_its_before_and_after():
    """A tab-indented `.feature` header line is rewritten and recorded as a `whitespace` change on that line."""
    result = normalize("# business_value:\n#\t- one\n", SourceFormat.FEATURE_HEADER, "DocumentedUserStory")

    assert result.lines == ["# business_value:", "# - one", ""]
    assert [(c.line, c.rule, c.before, c.after) for c in result.changes] == [
        (2, normalize_module.RULE_WHITESPACE, "#\t- one", "# - one")
    ]


def test_feature_header_wrapped_bullet_line_is_never_rewritten_as_a_key_or_an_ac_header():
    """A line deeper than an open item's `- ` is item text: its `status:` and `AC:` look-alikes keep their case."""
    text = (
        "# business_value:\n"
        "#   - Old accounts carry\n"
        "#     status: Deprecated\n"
        "#     AC:US-001-09 (V1.0 - Active)\n"
        "#   status: Active\n"
    )
    result = normalize(text, SourceFormat.FEATURE_HEADER, "DocumentedUserStory")

    assert result.lines[2:4] == ["#     status: Deprecated", "#     AC:US-001-09 (V1.0 - Active)"]
    assert result.lines[4] == "#   status: active"
    assert [c.line for c in result.changes] == [5]


def test_feature_header_criterion_header_keeps_its_authors_indent_when_rewritten():
    """Rule 3 fixes a header's state casing where the author put it: flush stays flush, the canon's indent 2 stays 2."""
    text = "# AC:US-001-01 (v1.0.0 - Active)\n# - d1\n#\n#   AC:US-001-02 (v1.0.0 - Active)\n#     - d2\n"
    result = normalize(text, SourceFormat.FEATURE_HEADER, "DocumentedUserStory")

    assert result.lines[:5] == [
        "# AC:US-001-01 (v1.0.0 - active)",
        "# - d1",
        "#",
        "#   AC:US-001-02 (v1.0.0 - active)",
        "#     - d2",
    ]
    assert [(c.line, c.rule) for c in result.changes] == [
        (1, normalize_module.RULE_STATE_CASING),
        (4, normalize_module.RULE_STATE_CASING),
    ]


def test_feature_header_split_description_sits_one_level_below_its_header():
    """Rule 7 puts an inline description on a bullet two spaces deeper than its header, wherever the header is."""
    result = normalize("# AC:US-001-01 (v1.0.0 - active) - desc\n", SourceFormat.FEATURE_HEADER, "DocumentedUserStory")

    assert result.lines[:2] == ["# AC:US-001-01 (v1.0.0 - active)", "#   - desc"]


def test_issue_body_rule_6_is_recorded_on_the_line_alongside_the_bullet_marker_rule():
    """A tab-indented `•` bullet gets both rules on one line: its indent to GitHub's tab stop, its marker to `-`."""
    result = normalize("## Business Value\n\n- A.\n\t• B.\n", SourceFormat.ISSUE_BODY, "DocumentedUserStory")

    assert result.lines[3] == "    - B."
    assert [(c.line, c.rule, c.before, c.after) for c in result.changes] == [
        (4, normalize_module.RULE_BULLET_MARKER, "\t• B.", "    - B."),
        (4, normalize_module.RULE_WHITESPACE, "\t• B.", "    - B."),
    ]
