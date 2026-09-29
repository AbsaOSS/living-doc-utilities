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

"""Scenario parsing: `@AC:<id>[/<param>:<value>...]` tags link scenarios to acceptance criteria."""

import pytest

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
    """A `@AC:<id>` scenario tag links the scenario to that criterion; the `# AC:` comment above it is not a tag."""
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
    """A `@AC:<id>/aspect:<value>` tag links the scenario to that criterion and records the aspect value."""
    scenarios, _warnings = parse_scenarios(_FEATURE_BODY, "DocumentedUserStory")

    second = scenarios[1]
    assert second.title == "Password shorter than the minimum length is rejected"
    assert [link.id for link in second.acceptance_criteria] == ["FUNC-001-01"]
    assert second.acceptance_criteria[0].aspect == "minimum-length"
    assert "@Regression" in second.tags


def test_malformed_ac_tag_produces_a_warning_and_no_link():
    """A `@AC:` tag with an unparseable id produces a `MALFORMED_AC` warning and links the scenario to nothing."""
    body = "Feature: Sample\n\n  @AC:not-a-valid-id\n  Scenario: Something\n    Given a step\n"
    scenarios, warnings = parse_scenarios(body, "DocumentedUserStory")

    assert scenarios[0].acceptance_criteria == []
    assert [w.code for w in warnings] == [Code.MALFORMED_AC.name]


def _parse_single_tag(tag: str):
    return parse_scenarios(f"Feature: x\n  {tag}\n  Scenario: s\n", "DocumentedUserStory")


@pytest.mark.parametrize(
    ("tag", "aspect"),
    [
        ("@AC:US-1-01/aspect:username-input", "username-input"),
        ("@AC:US-1-01/aspect:a/priority:high", "a"),
        ("@AC:US-1-01/priority:high", None),
        ("@AC:US-1-01/priority:high/aspect:a", "a"),
        ("@AC:US-1-01/owner:team-a/env:staging/aspect:a/ticket:JIRA-42", "a"),
        ("@AC:US-1-01/note:a:b", None),
    ],
    ids=[
        "aspect",
        "aspect_then_other_param",
        "unknown_param_only",
        "other_param_then_aspect",
        "several_unknown_params",
        "unknown_param_value_with_colon",
    ],
)
def test_ac_tag_param_segments_link_the_criterion(tag, aspect):
    """Any `/<param>:<value>` segments are accepted; `aspect` stops at the next `/`, other parameters are not stored."""
    scenarios, warnings = _parse_single_tag(tag)

    assert warnings == []
    assert [(link.id, link.aspect) for link in scenarios[0].acceptance_criteria] == [("US-1-01", aspect)]


@pytest.mark.parametrize(
    "tag",
    [
        "@AC:US-1-01//aspect:a",
        "@AC:US-1-01/priority",
        "@AC:US-1-01/aspect:a/aspect:b",
        "@AC:US-1-01/aspect:a:b",
        "@AC:FEAT-001-01",
    ],
    ids=["empty_segment", "segment_without_colon", "aspect_twice", "colon_in_aspect_value", "feature_owns_no_ac"],
)
def test_malformed_ac_tag_params_produce_a_warning_and_no_link(tag):
    """An empty segment, a segment without `:`, a repeated `aspect`, an `aspect` value containing `:`, or a Feature
    id (a Feature owns no criteria) makes the whole tag `MALFORMED_AC`."""
    scenarios, warnings = _parse_single_tag(tag)

    assert scenarios[0].acceptance_criteria == []
    assert [w.code for w in warnings] == [Code.MALFORMED_AC.name]


def test_tag_before_a_non_scenario_construct_does_not_leak_onto_a_later_scenario():
    """A tag preceding a non-scenario construct like `Examples:` never carries over onto a later, untagged scenario."""
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
    """An en dash inside an ignored `# AC:` comment does not disrupt parsing of the `@AC:` tag on the next line."""
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
