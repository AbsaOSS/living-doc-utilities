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

"""US-001's and FUNC-001's `.feature` headers match their issue-body golden entities plus one optional extension."""

from living_doc_utilities.authoring.feature_header import parse_feature_header
from living_doc_utilities.authoring.scenario import parse_scenarios
from tests.authoring.golden.helpers import load_expected, read_fixture

_FUNC_001_RULES = ["minimum-length", "character-classes", "no-username"]


def _ac_core(ac):
    return (ac.id, ac.state, ac.version, ac.description, ac.removal_planned)


def test_us_001_feature_header_matches_its_issue_body_golden_entity():
    """A user story's `.feature`-header form matches its issue-body golden entity, plus its own AC preconditions."""
    text = read_fixture("gherkin", "liv_doc_us", "us-001-customer-login.feature")
    entity, warnings = parse_feature_header(text, "DocumentedUserStory")
    expected = load_expected("us-001-customer-login.json")

    assert warnings == []
    assert entity is not None
    assert entity.entity_id == expected["entity_id"]
    assert entity.title == expected["title"]
    assert entity.state == expected["state"]
    assert entity.business_value == expected["business_value"]
    assert [_ac_core(ac) for ac in entity.acceptance_criteria] == [
        (ac["id"], ac["state"], ac["version"], ac["description"], ac["removal_planned"])
        for ac in expected["acceptance_criteria"]
    ]

    # The AC's nested `preconditions:` sub-list must not leak into the entity-level field of the same name.
    assert entity.preconditions == []

    # The one extension this corpus assigns only to the .feature-header form.
    by_id = {ac.id: ac for ac in entity.acceptance_criteria}
    assert by_id["US-001-01"].preconditions == ["A registered customer account exists and is not locked."]
    for ac_id in ("US-001-02", "US-001-03", "US-001-04"):
        assert by_id[ac_id].preconditions == []


def test_func_001_feature_header_matches_its_issue_body_golden_entity():
    """A functionality's `.feature`-header form matches its issue-body golden entity, plus its own AC aspects."""
    text = read_fixture("gherkin", "liv_doc_func", "func-001-validate-password-strength.feature")
    entity, warnings = parse_feature_header(text, "DocumentedFunctionality")
    expected = load_expected("func-001-validate-password-strength.json")

    assert warnings == []
    assert entity is not None
    assert entity.entity_id == expected["entity_id"]
    assert entity.title == expected["title"]
    assert entity.state == expected["state"]
    assert entity.parent == expected["parent"]
    assert entity.func_type == expected["func_type"]
    assert [_ac_core(ac) for ac in entity.acceptance_criteria] == [
        (ac["id"], ac["state"], ac["version"], ac["description"], ac["removal_planned"])
        for ac in expected["acceptance_criteria"]
    ]

    # The one extension this corpus assigns only to the .feature-header form, in both its spellings.
    by_id = {ac.id: ac for ac in entity.acceptance_criteria}
    assert by_id["FUNC-001-01"].aspect == _FUNC_001_RULES
    assert by_id["FUNC-001-01"].placeholder_values == {}
    assert by_id["FUNC-001-02"].aspect == []
    # The named keyword `- rule:` is the other spelling of `Aspect:`: the same values, its name kept.
    assert by_id["FUNC-001-03"].aspect == _FUNC_001_RULES
    assert by_id["FUNC-001-03"].placeholder_values == {"rule": _FUNC_001_RULES}


def test_func_001_scenarios_link_one_value_of_each_variant_spelling():
    """`@AC:FUNC-001-01/aspect:<v>` and `@AC:FUNC-001-03/rule:<v>` both link one declared value; no tag is malformed."""
    text = read_fixture("gherkin", "liv_doc_func", "func-001-validate-password-strength.feature")
    scenarios, warnings = parse_scenarios(text, "DocumentedFunctionality")

    assert warnings == []
    assert [(link.id, link.aspect) for scenario in scenarios for link in scenario.acceptance_criteria] == [
        ("FUNC-001-01", "minimum-length"),
        ("FUNC-001-01", "character-classes"),
        ("FUNC-001-01", "no-username"),
        ("FUNC-001-03", "minimum-length"),
    ]
