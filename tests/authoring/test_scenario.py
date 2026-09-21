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

"""Scenario parsing: `@AC:<id>[/aspect:<value>]` tags link a scenario to its acceptance
criteria; the human-readable `# AC:` comment above it is never parsed as a tag."""

from living_doc_utilities.authoring.scenario import parse_scenarios
from living_doc_utilities.contracts.codes import Code

_FEATURE_BODY = """\
@US_ID:US-001
@domain_authentication
Feature: Customer Login
  As a registered customer, I can sign in with my email and password, so that I can reach my account area.

  # AC:US-001-01 (v1.0.0 - active) - valid credentials land on the account dashboard
  @AC:US-001-01
  Scenario: Customer signs in with valid credentials
    Given a registered customer is on the login screen
    When the customer submits valid credentials
    Then the account dashboard is displayed

  @AC:FUNC-001-01/aspect:minimum-length
  @Regression
  Scenario: Password shorter than the minimum length is rejected
    Given the complexity policy requires at least 12 characters
"""


def test_scenario_tags_are_parsed_and_comment_is_ignored():
    scenarios, warnings = parse_scenarios(_FEATURE_BODY, "DocumentedUserStory")

    assert warnings == []
    assert len(scenarios) == 2

    first = scenarios[0]
    assert first.title == "Customer signs in with valid credentials"
    assert [link.id for link in first.acceptance_criteria] == ["US-001-01"]
    assert first.acceptance_criteria[0].aspect is None
    # The tag is captured in `tags`; the "# AC:" comment line above it is not.
    assert "@AC:US-001-01" in first.tags
    assert not any(tag.startswith("#") for tag in first.tags)


def test_scenario_tag_with_aspect_param():
    scenarios, _warnings = parse_scenarios(_FEATURE_BODY, "DocumentedUserStory")

    second = scenarios[1]
    assert second.title == "Password shorter than the minimum length is rejected"
    assert [link.id for link in second.acceptance_criteria] == ["FUNC-001-01"]
    assert second.acceptance_criteria[0].aspect == "minimum-length"
    assert "@Regression" in second.tags


def test_malformed_ac_tag_produces_a_warning_and_no_link():
    body = "Feature: Sample\n\n  @AC:not-a-valid-id\n  Scenario: Something\n    Given a step\n"
    scenarios, warnings = parse_scenarios(body, "DocumentedUserStory")

    assert scenarios[0].acceptance_criteria == []
    assert [w.code for w in warnings] == [Code.MALFORMED_AC.name]


def test_tag_before_a_non_scenario_construct_does_not_leak_onto_a_later_scenario():
    # A tag can precede a construct other than `Scenario:`/`Scenario Outline:` - here an
    # `Examples:` table belonging to the outline above it. That tag must not survive past
    # the table and attach itself to the next, untagged, `Scenario:`.
    body = (
        "Feature: Sample\n\n"
        "  @AC:US-001-01\n"
        "  Scenario Outline: Something with <value>\n"
        "    Given a step with <value>\n\n"
        "    @DataSetTag\n"
        "    Examples:\n"
        "      | value |\n"
        "      | 1     |\n\n"
        "  Scenario: Untagged follow-up\n"
        "    Given a step\n"
    )
    scenarios, warnings = parse_scenarios(body, "DocumentedUserStory")

    assert warnings == []
    assert [link.id for link in scenarios[0].acceptance_criteria] == ["US-001-01"]
    assert scenarios[1].title == "Untagged follow-up"
    assert scenarios[1].tags == []
    assert scenarios[1].acceptance_criteria == []


def test_en_dash_comment_is_normalized_before_parsing():
    body = (
        "Feature: Sample\n\n"
        "  # AC:US-001-01 (v1.0.0 – active) - description\n"
        "  @AC:US-001-01\n"
        "  Scenario: Something\n"
        "    Given a step\n"
    )
    scenarios, warnings = parse_scenarios(body, "DocumentedUserStory")

    assert warnings == []
    assert [link.id for link in scenarios[0].acceptance_criteria] == ["US-001-01"]
