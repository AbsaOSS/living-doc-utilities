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

"""Scenario parsing: `@AC:<id>[/<param>:<value>]` tags link scenarios to acceptance criteria, and each scenario keeps
its line, its steps, its rule and the backgrounds that run before it."""

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
        ("@AC:US-1-01", None),
        ("@AC:US-1-01/aspect:username-input", "username-input"),
        ("@AC:FUNC-001-03/rule:minimum-length", "minimum-length"),
        ("@AC:US-1-01/required-field:username-input", "username-input"),
        ("@AC:US-1-01/priority:high", "high"),
    ],
    ids=["bare", "aspect", "keyword", "kebab_case_keyword", "any_valid_name"],
)
def test_ac_tag_with_at_most_one_parameter_links_the_criterion(tag, aspect):
    """`DEC-76`: a bare tag links the whole criterion; one `/aspect:<v>` or `/<keyword>:<v>` gives `aspect=<v>`.
    The name is not stored or checked here, so a value the criterion does not declare is `toolkit`'s `STALE_AC_REF`."""
    scenarios, warnings = _parse_single_tag(tag)

    assert warnings == []
    assert [(link.id, link.aspect) for link in scenarios[0].acceptance_criteria] == [(tag[4:].split("/")[0], aspect)]


@pytest.mark.parametrize(
    "tag",
    [
        "@AC:US-1-01//aspect:a",
        "@AC:US-1-01/",
        "@AC:US-1-01/priority",
        "@AC:US-1-01/aspect:a/aspect:b",
        "@AC:US-1-01/aspect:a/priority:high",
        "@AC:US-1-01/priority:high/aspect:a",
        "@AC:US-1-01/owner:team-a/env:staging/aspect:a/ticket:JIRA-42",
        "@AC:US-1-01/aspect:a:b",
        "@AC:US-1-01/note:a:b",
        "@AC:US-1-01/:a",
        "@AC:US-1-01/1st:a",
        "@AC:FEAT-001-01",
    ],
    ids=[
        "empty_segment",
        "trailing_slash",
        "segment_without_colon",
        "aspect_twice",
        "aspect_then_other_param",
        "other_param_then_aspect",
        "four_params",
        "colon_in_aspect_value",
        "colon_in_keyword_value",
        "empty_name",
        "invalid_name",
        "feature_owns_no_ac",
    ],
)
def test_malformed_ac_tag_params_produce_a_warning_and_no_link(tag):
    """The format is closed (`DEC-76`): a second parameter, an empty segment, a segment without `:`, an invalid name,
    a value containing `:`, or a Feature id (a Feature owns no criteria) makes the whole tag `MALFORMED_AC`."""
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


# The testbed's func-010-total-fines-owed.feature, verbatim, so its Scenario Outline starts on line 43.
_FUNC_010 = """\
# =============================================================================
# LIVING DOC — FUNC-010 · My Loans Page - Total Fines Owed
# =============================================================================
# status:    active
# parent:    FEAT-002
# func_type: calculation
# rationale:
#   - The total is shown on its own, not on payment, so members see what they
#     owe before they come to the desk.
#
# acceptance_criteria:
#
#   AC:FUNC-010-01 (v1.0.0 - active)
#     - The total shown is the sum of the fines on every loan, to the cent.
#
#   AC:FUNC-010-02 (v1.0.0 - active)
#     - A fine that is {fine-state} is left out of the total.
#     - fine-state: paid, waived, written-off
# =============================================================================

@FUNC_ID:FUNC-010
@domain_loans
Feature: My Loans Page - Total Fines Owed
  Adds up the fines a member owes across all loans.

  # AC:FUNC-010-01 (v1.0.0 - active) - the total is the sum of every loan's fine
  @AC:FUNC-010-01
  Scenario: Total fines add up across loans
    Given the member owes 0.40 on "The Hobbit" and 1.20 on "Dune"
    When the member opens the My Loans page
    Then the total fines owed is 1.60

  # AC:FUNC-010-01 (v1.0.0 - active) - the total is the sum of every loan's fine
  @AC:FUNC-010-01
  @skip
  Scenario: Small fines add up to the cent
    Given the member owes 0.10 on "The Hobbit", 0.10 on "Dune" and 0.10 on "Emma"
    When the member opens the My Loans page
    Then the total fines owed is 0.30

  # AC:FUNC-010-02 (v1.0.0 - active) - a settled fine is left out of the total
  @AC:FUNC-010-02
  Scenario Outline: A settled fine is left out of the total
    Given the member has a fine of 0.40 on "The Hobbit" and 1.20 on "Dune"
    And the fine on "Dune" is <fine-state>
    When the member opens the My Loans page
    Then the total fines owed is 0.40

    Examples:
      | fine-state  |
      | paid        |
      | waived      |
      | written-off |
"""


def test_a_scenario_outline_keeps_its_line_and_its_steps_as_written():
    """A scenario keeps the line of its `Scenario Outline:` line and its steps as written, `Examples:` and its table
    included: blank lines drop, and the indentation the lines share is removed."""
    scenarios, warnings = parse_scenarios(_FUNC_010, "DocumentedFunctionality")

    assert warnings == []
    assert [scenario.line for scenario in scenarios] == [28, 36, 43]
    outline = scenarios[2]
    assert (outline.title, outline.rule, outline.rule_background, outline.background) == (
        "A settled fine is left out of the total",
        None,
        [],
        [],
    )
    assert outline.steps == [
        'Given the member has a fine of 0.40 on "The Hobbit" and 1.20 on "Dune"',
        'And the fine on "Dune" is <fine-state>',
        "When the member opens the My Loans page",
        "Then the total fines owed is 0.40",
        "Examples:",
        "  | fine-state  |",
        "  | paid        |",
        "  | waived      |",
        "  | written-off |",
    ]


_RULES_AND_BACKGROUNDS = """\
Feature: Loans
  Background:
    Given a member in good standing is signed in
    # a comment in a background drops too

  Scenario: Before any rule
    Given a step

  Rule: Fines are capped
    Background:
      Given the fine cap is 5.00
      And the member owes 7.00

    Scenario: Under the first rule
      Given a step

  Rule: Overdue loans block borrowing

    Scenario: Under the second rule
      Given a step
"""


def test_every_scenario_carries_its_files_background_and_its_rules_own():
    """Each scenario carries its file's `Background:` lines, the name of the `Rule:` it sits under, or none, and that
    rule's own `Background:` lines; a rule without one has none, whatever the rule before it had."""
    scenarios, warnings = parse_scenarios(_RULES_AND_BACKGROUNDS, "DocumentedUserStory")

    assert warnings == []
    assert [scenario.background for scenario in scenarios] == [["Given a member in good standing is signed in"]] * 3
    assert [(scenario.rule, scenario.rule_background) for scenario in scenarios] == [
        (None, []),
        ("Fines are capped", ["Given the fine cap is 5.00", "And the member owes 7.00"]),
        ("Overdue loans block borrowing", []),
    ]
    assert [scenario.steps for scenario in scenarios] == [["Given a step"]] * 3


_STEP_ARGUMENTS = '''\
Feature: Step arguments
  Scenario: A step with a DocString and a DataTable
    # a comment between steps drops
    Given the request body
      """json
      {
        "member": "M-1"

        # a line inside a DocString is content
      }
      """
    And the loans
      | title      | due        |
      | The Hobbit | 2026-12-01 |
    When the member opens the page
'''


def test_a_docstring_and_a_datatable_come_through_unchanged():
    """A DocString keeps every line, blank and `#` lines included, and a DataTable keeps its rows; only the indentation
    the scenario's lines share is removed."""
    scenarios, warnings = parse_scenarios(_STEP_ARGUMENTS, "DocumentedUserStory")

    assert warnings == []
    assert scenarios[0].steps == [
        "Given the request body",
        '  """json',
        "  {",
        '    "member": "M-1"',
        "",
        "    # a line inside a DocString is content",
        "  }",
        '  """',
        "And the loans",
        "  | title      | due        |",
        "  | The Hobbit | 2026-12-01 |",
        "When the member opens the page",
    ]


def test_a_docstring_line_reading_like_a_tag_or_a_scenario_is_content():
    """A `@AC:` tag or a `Scenario:` line inside a DocString neither links a scenario nor opens one."""
    body = (
        "Feature: F\n"
        "  Scenario: Writes a feature file\n"
        "    Given the file\n"
        "      ```\n"
        "      @AC:US-001-01\n"
        "      Scenario: inside the DocString\n"
        "      ```\n\n"
        "  Scenario: The next one\n"
        "    Given a step\n"
    )
    scenarios, warnings = parse_scenarios(body, "DocumentedUserStory")

    assert warnings == []
    assert [(scenario.title, scenario.tags) for scenario in scenarios] == [
        ("Writes a feature file", []),
        ("The next one", []),
    ]
    assert scenarios[0].steps == ["Given the file", "  ```", "  @AC:US-001-01", "  Scenario: inside the DocString", "  ```"]


_TWO_EXAMPLES = """\
Feature: Outline
  @AC:US-001-01
  Scenario Outline: A fine of <amount>
    Given a fine of <amount>

    @paid
    Examples: Paid
      | amount |
      | 0.40   |

    Examples: Waived
      | amount |
      | 1.20   |

  @AC:US-001-02
  Scenario: The next one
    Given a step
"""


def test_an_examples_tag_line_stays_out_of_the_tags_and_the_steps():
    """A tag line above an `Examples:` block is no scenario's tag and no step; the next scenario's tags are its own."""
    scenarios, warnings = parse_scenarios(_TWO_EXAMPLES, "DocumentedUserStory")

    assert warnings == []
    assert [scenario.tags for scenario in scenarios] == [["@AC:US-001-01"], ["@AC:US-001-02"]]
    assert scenarios[0].steps == [
        "Given a fine of <amount>",
        "Examples: Paid",
        "  | amount |",
        "  | 0.40   |",
        "Examples: Waived",
        "  | amount |",
        "  | 1.20   |",
    ]
    assert scenarios[1].steps == ["Given a step"]


def test_a_step_line_in_any_gherkin_language_is_kept_as_written():
    """The steps are lines, not parsed keywords: a step in another Gherkin language, or a `*` step, is kept as written."""
    body = "Feature: F\n  Scenario: S\n    Angenommen eine Gebühr von 0.40\n    * die Summe ist 0.40\n    Beispiele:\n"

    scenarios, _ = parse_scenarios(body, "DocumentedUserStory")

    assert scenarios[0].steps == ["Angenommen eine Gebühr von 0.40", "* die Summe ist 0.40", "Beispiele:"]
