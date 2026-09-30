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

"""`.feature`-header parsing: recognised keys land on their fields, unrecognised keys warn."""

import pytest

from living_doc_utilities.authoring.feature_header import parse_feature_header
from living_doc_utilities.contracts.codes import Code

_US_HEADER = """\
# =============================================================================
# LIVING DOC — US-001 · Sample Story
# =============================================================================
# source:          https://github.com/absaoss/sample/issues/1
# status:          active
# deprecated_at:      2026-01-01
# deprecation_reason: Reason text.
# superseded_by:      US-002
# business_value:
#   - Value one.
#
# acceptance_criteria:
#
#   AC:US-001-01 (v1.0.0 - active)
#     - desc
# =============================================================================

@US_ID:US-001
Feature: Sample Story
  As a user, I can do something, so that outcome.
"""

_HEADER_WITH_UNKNOWN_KEY = """\
# =============================================================================
# LIVING DOC — US-002 · Another Story
# =============================================================================
# status:          active
# business_value:
#   - Value one.
# totally_unknown_key: some value
#
# acceptance_criteria:
#
#   AC:US-002-01 (v1.0.0 - active)
#     - desc
# =============================================================================

@US_ID:US-002
Feature: Another Story
"""

_FUNCTIONALITY_HEADER = """\
# =============================================================================
# LIVING DOC — FUNC-001 · Sample Functionality
# =============================================================================
# status:          active
# parent:           US-001
# func_type:        backend
# rationale:
#   - Centralizes validation so every caller gets the same rules.
# =============================================================================

@FUNC_ID:FUNC-001
Feature: Sample Functionality
"""


def test_recognised_keys_land_on_their_fields():
    """Every recognised `.feature`-header key is assigned to its matching entity field, with no warnings."""
    entity, warnings = parse_feature_header(_US_HEADER, "DocumentedUserStory")

    assert warnings == []
    assert entity.entity_id == "US-001"
    assert entity.title == "US-001 · Sample Story"
    assert entity.source == "https://github.com/absaoss/sample/issues/1"
    assert entity.state == "active"
    assert entity.deprecated_at == "2026-01-01"
    assert entity.deprecation_reason == "Reason text."
    assert entity.superseded_by == "US-002"
    assert entity.business_value == ["Value one."]
    assert [ac.id for ac in entity.acceptance_criteria] == ["US-001-01"]


def test_unrecognised_key_produces_ignored_authored_key():
    """An unrecognised `.feature`-header key produces an `IGNORED_AUTHORED_KEY` warning naming that key."""
    entity, warnings = parse_feature_header(_HEADER_WITH_UNKNOWN_KEY, "DocumentedUserStory")

    assert entity is not None
    assert [w.code for w in warnings] == [Code.IGNORED_AUTHORED_KEY.name]
    assert "totally_unknown_key" in warnings[0].message


def test_missing_title_line_produces_missing_entity_id():
    """A `.feature` header with no parseable title line yields no entity and a `MISSING_ENTITY_ID` warning."""
    text = "# =============================================================================\n# not a title\n"
    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert entity is None
    assert [w.code for w in warnings] == ["MISSING_ENTITY_ID"]


def test_title_without_an_entity_id_produces_missing_entity_id_naming_the_title():
    """A `LIVING DOC` title with no entity id yields no entity and a `MISSING_ENTITY_ID` warning naming the title."""
    text = (
        "# =============================================================================\n"
        "# LIVING DOC — Just a title with no id\n"
        "# =============================================================================\n"
    )
    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert entity is None
    assert [w.code for w in warnings] == ["MISSING_ENTITY_ID"]
    assert "Just a title with no id" in warnings[0].context


def test_banner_shaped_comment_in_scenario_body_is_not_absorbed_into_header():
    """A banner-shaped comment inside the scenario body is never absorbed into the header block or double-parsed."""
    text = (
        "# =============================================================================\n"
        "# LIVING DOC — US-004 · Divider Story\n"
        "# =============================================================================\n"
        "# status:          active\n"
        "#\n"
        "# acceptance_criteria:\n"
        "#\n"
        "#   AC:US-004-01 (v1.0.0 - active)\n"
        "#     - desc\n"
        "# =============================================================================\n"
        "\n@US_ID:US-004\nFeature: Divider Story\n"
        "\n# =============================================================================\n"
        "# AC:US-004-01 (v1.0.0 - active)\n"
        "#   - duplicate, must not be parsed as a header field\n"
        "# =============================================================================\n"
        "  Scenario: Something\n"
        "    Given a step\n"
    )
    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert warnings == []
    assert entity.entity_id == "US-004"
    assert [ac.id for ac in entity.acceptance_criteria] == ["US-004-01"]
    assert len(entity.acceptance_criteria) == 1


def test_en_dash_input_is_normalized_before_ac_grammar_runs():
    """An en dash in an acceptance-criterion header is normalized before parsing, so state and version still parse."""
    text = (
        "# =============================================================================\n"
        "# LIVING DOC — US-003 · Dash Story\n"
        "# =============================================================================\n"
        "# status:          active\n"
        "#\n"
        "# acceptance_criteria:\n"
        "#\n"
        "#   AC:US-003-01 (v1.0.0 – active)\n"
        "#     - desc\n"
        "# =============================================================================\n"
        "\n@US_ID:US-003\nFeature: Dash Story\n"
    )
    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert warnings == []
    assert entity.entity_id == "US-003"
    assert entity.acceptance_criteria[0].state == "active"
    assert entity.acceptance_criteria[0].version == "1.0.0"


def test_functionality_rationale_key_lands_on_its_field():
    """A Functionality header's `rationale:` bullet joins into the `rationale` field, alongside `parent`/`func_type`."""
    entity, warnings = parse_feature_header(_FUNCTIONALITY_HEADER, "DocumentedFunctionality")

    assert warnings == []
    assert entity.entity_id == "FUNC-001"
    assert entity.parent == "US-001"
    assert entity.func_type == "backend"
    assert entity.rationale == "Centralizes validation so every caller gets the same rules."


def test_status_not_one_of_the_four_lifecycle_states_is_a_warning_not_a_crash():
    """An authored `status:` value outside the four lifecycle states warns and leaves state unset, not a crash."""
    text = (
        "# =============================================================================\n"
        "# LIVING DOC — US-005 · Bad Status Story\n"
        "# =============================================================================\n"
        "# status:          shipped\n"
        "# =============================================================================\n"
        "\n@US_ID:US-005\nFeature: Bad Status Story\n"
    )
    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert entity is not None
    assert entity.state is None
    assert [w.code for w in warnings] == [Code.MALFORMED_STATUS.name]
    assert "shipped" in warnings[0].message


@pytest.mark.parametrize(
    "entity_id, entity_type, extra_key",
    [
        ("FUNC-001", "DocumentedFunctionality", "# parent:       FEAT-001\n"),
        ("US-001", "DocumentedUserStory", ""),
    ],
)
def test_feature_dependencies_key_on_a_non_feature_is_an_unrecognised_key(entity_id, entity_type, extra_key):
    """`feature_dependencies:` is a Feature field only: on a `.feature` header it is the generic unrecognised key."""
    text = (
        "# =============================================================================\n"
        f"# LIVING DOC — {entity_id} · Sample\n"
        "# =============================================================================\n"
        "# status:       active\n"
        f"{extra_key}"
        "# feature_dependencies: FEAT-002\n"
        "# =============================================================================\n"
        "\nFeature: Sample\n"
    )
    entity, warnings = parse_feature_header(text, entity_type)

    assert entity is not None
    assert entity.feature_dependencies == []
    assert [(w.code, w.message) for w in warnings] == [
        (Code.IGNORED_AUTHORED_KEY.name, "'feature_dependencies:' is not a field this contract carries.")
    ]


def _us_header(keys: str) -> str:
    return (
        "# =============================================================================\n"
        "# LIVING DOC — US-001 · Sample\n"
        "# =============================================================================\n"
        "# status:       active\n"
        f"{keys}"
        "# =============================================================================\n"
        "\nFeature: Sample\n"
    )


def test_text_on_a_bullet_keys_own_line_is_dropped_with_unparsed_bullet_line():
    """`# preconditions: <text>` has no bullet to join the text onto: it warns, and the bullets below are kept."""
    text = _us_header("# preconditions: The customer is signed in.\n#   - account is active\n#   - MFA is enrolled\n")
    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert entity.preconditions == ["account is active", "MFA is enrolled"]
    assert [(w.code, w.context) for w in warnings] == [
        (Code.UNPARSED_BULLET_LINE.name, "entity_id='US-001' field='preconditions'")
    ]
    assert "'The customer is signed in.'" in warnings[0].message


def test_prose_before_the_first_business_value_bullet_warns_once():
    """A `business_value:` with a prose line before its bullets warns once for that line."""
    text = _us_header("# business_value:\n#   Why this matters:\n#   - fewer support calls\n")
    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert entity.business_value == ["fewer support calls"]
    assert [w.code for w in warnings] == [Code.UNPARSED_BULLET_LINE.name]
    assert "'Why this matters:'" in warnings[0].message


def test_a_bullet_with_a_continuation_line_raises_no_unparsed_bullet_line():
    """A bullet followed by an unmarked line is joined onto that bullet, not dropped."""
    text = _us_header("# business_value:\n#   - fewer support\n#     calls\n")
    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert warnings == []
    assert entity.business_value == ["fewer support calls"]


def test_prose_on_a_rationale_keys_own_line_is_dropped_with_unparsed_bullet_line():
    """`# rationale: <text>` with no `- ` bullet keeps nothing: `rationale` is `None` and the text is reported."""
    text = (
        "# =============================================================================\n"
        "# LIVING DOC — FUNC-001 · Sample\n"
        "# =============================================================================\n"
        "# status:       active\n"
        "# rationale:    Keeps the audit trail intact.\n"
        "# =============================================================================\n"
        "\nFeature: Sample\n"
    )
    entity, warnings = parse_feature_header(text, "DocumentedFunctionality")

    assert entity.rationale is None
    assert [(w.code, w.context) for w in warnings] == [
        (Code.UNPARSED_BULLET_LINE.name, "entity_id='FUNC-001' field='rationale'")
    ]
    assert "'Keeps the audit trail intact.'" in warnings[0].message


# --- indentation: a line's level decides what it belongs to (DEC-44) ---------------------------


def test_a_wrapped_bullet_line_reading_like_a_key_is_that_items_text():
    """A `business_value` item's wrapped line `status: deprecated ...`, deeper than its `- `, opens no `status` key."""
    text = _us_header(
        "# business_value:\n"
        "#   - Migrated accounts keep working; they carry\n"
        "#     status: deprecated until the owner re-verifies them.\n"
    )
    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert warnings == []
    assert entity.state == "active"
    assert entity.business_value == [
        "Migrated accounts keep working; they carry status: deprecated until the owner re-verifies them."
    ]


def test_an_indented_key_after_the_bullet_item_has_closed_is_still_a_key():
    """A key indented to the item's own `- ` column is not deeper than it, so the item closes and the key is read."""
    text = (
        "# =============================================================================\n"
        "# LIVING DOC — US-001 · Sample\n"
        "# =============================================================================\n"
        "# business_value:\n"
        "#   - Fewer support calls.\n"
        "#   status: deprecated\n"
        "# =============================================================================\n"
        "\nFeature: Sample\n"
    )
    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert warnings == []
    assert entity.state == "deprecated"
    assert entity.business_value == ["Fewer support calls."]


def test_a_wrapped_bullet_line_reading_like_an_ac_header_is_not_a_criterion():
    """A `business_value` item's wrapped `AC:<id> (...)` line is item text; the grammar never sees a criterion there."""
    text = _us_header("# business_value:\n#   - Mirrors the rule of\n#     AC:US-001-09 (v1.0.0 - active)\n")
    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert warnings == []
    assert entity.acceptance_criteria == []
    assert entity.business_value == ["Mirrors the rule of AC:US-001-09 (v1.0.0 - active)"]


def test_a_tab_indented_header_is_read_at_its_normalised_indent():
    """Rule 6 turns a tab indent into spaces before the parser reads levels: the criterion and its sub-list parse."""
    text = _us_header(
        "# acceptance_criteria:\n"
        "#\tAC:US-001-01 (v1.0.0 - active)\n"
        "#\t\t- desc\n"
        "#\t\tpreconditions:\n"
        "#\t\t\t- An account exists.\n"
        "#\t\t- Aspect: security\n"
    )
    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert warnings == []
    assert entity.acceptance_criteria[0].preconditions == ["An account exists."]
    assert entity.acceptance_criteria[0].aspect == ["security"]


def test_a_nested_business_value_item_is_kept_in_its_parents_string_as_extracted():
    """The same nested list as in an issue body gives the same value: the child on its own line, under its parent."""
    text = _us_header(
        "# business_value:\n"
        "#   - Registered customers can reach their account area.\n"
        "#     - Returning users convert without friction.\n"
        "#   - Support calls about lost sessions drop.\n"
    )
    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert warnings == []
    assert entity.business_value == [
        "Registered customers can reach their account area.\n  - Returning users convert without friction.",
        "Support calls about lost sessions drop.",
    ]


def test_a_nested_item_returning_between_two_levels_is_misindented_with_its_wrapped_line():
    """Back from a child at 6 to indent 4, with the item at 2, fits no level: that line and its wrap are dropped."""
    text = _us_header(
        "# business_value:\n"
        "#   - Registered customers can reach their account area.\n"
        "#       - Returning users convert without friction.\n"
        "#     - Support calls about lost\n"
        "#       sessions drop.\n"
        "#   - Fewer password resets.\n"
    )
    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert entity.business_value == [
        "Registered customers can reach their account area.\n    - Returning users convert without friction.",
        "Fewer password resets.",
    ]
    assert [w.code for w in warnings] == [Code.MISINDENTED_LINE.name] * 2
    assert [w.context.split(" line=")[1] for w in warnings] == ["'- Support calls about lost'", "'sessions drop.'"]


def test_a_flush_header_keeps_every_criterion_when_a_rule_rewrites_its_headers():
    """Headers and bullets at the same indent stay there when rule 3 lowercases `Active`: both criteria parse."""
    text = _us_header(
        "# acceptance_criteria:\n"
        "# AC:US-001-01 (v1.0.0 - Active)\n"
        "# - Valid credentials land on the dashboard.\n"
        "# - Aspect: security\n"
        "# AC:US-001-02 (v1.0.0 - Active)\n"
        "# - Three wrong passwords lock the account.\n"
    )
    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert warnings == []
    assert [(ac.id, ac.state, ac.description) for ac in entity.acceptance_criteria] == [
        ("US-001-01", "active", "Valid credentials land on the dashboard."),
        ("US-001-02", "active", "Three wrong passwords lock the account."),
    ]
    assert entity.acceptance_criteria[0].aspect == ["security"]


def test_a_header_deeper_than_the_previous_criterions_items_is_their_text_with_a_warning():
    """Items shallower than their own header break the canon: the next header, deeper than them, is their text.

    Nothing is lost silently: the swallowed criterion's own bullet is reported."""
    text = _us_header(
        "# acceptance_criteria:\n"
        "#  AC:US-001-01 (v1.0.0 - active)\n"
        "# - Valid credentials land on the dashboard.\n"
        "#  AC:US-001-02 (v1.0.0 - active)\n"
        "# - Three wrong passwords lock the account.\n"
    )
    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert [ac.id for ac in entity.acceptance_criteria] == ["US-001-01"]
    assert [(w.code, w.context.split(" line=")[1]) for w in warnings] == [
        (Code.UNPARSED_AC_LINE.name, "'- Three wrong passwords lock the account.'")
    ]


def test_a_blank_line_closes_a_bullet_item_so_a_deeper_key_is_read():
    """A blank comment line ends the open item: a `status:` below it, even one deeper than the `- `, is a key."""
    text = (
        "# =============================================================================\n"
        "# LIVING DOC — US-001 · Sample\n"
        "# =============================================================================\n"
        "# business_value:\n"
        "#   - Fewer support calls.\n"
        "#\n"
        "#     status: deprecated\n"
        "# =============================================================================\n"
        "\nFeature: Sample\n"
    )
    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert warnings == []
    assert entity.business_value == ["Fewer support calls."]
    assert entity.state == "deprecated"
