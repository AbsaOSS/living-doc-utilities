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

"""`.feature`-header parsing: recognised keys land on their fields, an unrecognised key
produces `IGNORED_AUTHORED_KEY`, and `normalize` runs before `ac_grammar`."""

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


def test_recognised_keys_land_on_their_fields():
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
    entity, warnings = parse_feature_header(_HEADER_WITH_UNKNOWN_KEY, "DocumentedUserStory")

    assert entity is not None
    assert [w.code for w in warnings] == [Code.IGNORED_AUTHORED_KEY.name]
    assert "totally_unknown_key" in warnings[0].message


def test_missing_title_line_produces_missing_entity_id():
    text = "# =============================================================================\n# not a title\n"
    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert entity is None
    assert [w.code for w in warnings] == ["MISSING_ENTITY_ID"]


def test_banner_shaped_comment_in_scenario_body_is_not_absorbed_into_header():
    # A "# ===...===" comment pair in the Gherkin body (a human habit, e.g. separating
    # scenario groups with a divider that itself brackets a documentation-only "# AC:"
    # line) must never be mistaken for the header's own block: the header ends at the
    # "Feature:" declaration, full stop. Before the fix, the *last* banner-shaped line
    # anywhere in the file closed the header block, so this divider's own "AC:US-004-01"
    # line was re-parsed as a second (duplicate) acceptance criterion.
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
