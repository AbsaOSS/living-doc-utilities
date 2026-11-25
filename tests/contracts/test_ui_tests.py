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

"""The ui-tests contract: the scenarios array and `Scenario`'s per-tag `AcLink` pairing of an AC with its aspect."""

import pytest
from pydantic import ValidationError

from living_doc_utilities.contracts.ui_tests import CONTRACT_ID, RECORD_ROOTS, AcLink, Scenario, UITestsResult
from tests.contracts import factories


def test_ui_tests_result_uses_scenarios_array_key():
    """UITestsResult exposes its list under 'scenarios', not the retired 'items' field name."""
    result = UITestsResult(metadata=factories.metadata(), scenarios=[factories.scenario()])

    assert len(result.scenarios) == 1
    assert "items" not in UITestsResult.model_fields


def test_ui_tests_result_schema_version_is_the_contract_id():
    """UITestsResult.schema_version defaults to the ui-tests-v1.0.0 contract id."""
    result = UITestsResult(metadata=factories.metadata())

    assert result.schema_version == CONTRACT_ID == "ui-tests-v1.0.0"


def test_record_roots_declares_scenarios():
    """RECORD_ROOTS maps 'scenarios' to the Scenario model."""
    assert RECORD_ROOTS == {"scenarios": Scenario}


def test_scenario_pairs_each_acceptance_criterion_with_its_own_aspect():
    """A Scenario keeps each AcLink's id paired with its own aspect, in tag order, not flattened."""
    # Two @AC: tags with distinct aspects: the shape the flat acceptance_criteria[]/aspects[] pair could not express.
    result = factories.scenario(
        acceptance_criteria=[
            factories.ac_link(id="FUNC-001-01", aspect="minimum-length"),
            factories.ac_link(id="FUNC-001-01", aspect="character-classes"),
        ]
    )

    assert [(link.id, link.aspect) for link in result.acceptance_criteria] == [
        ("FUNC-001-01", "minimum-length"),
        ("FUNC-001-01", "character-classes"),
    ]


def test_scenario_ac_link_aspect_defaults_to_none():
    """AcLink.aspect defaults to None when not given."""
    link = factories.ac_link()

    assert link.aspect is None


def test_scenario_ac_link_id_rejects_non_canonical_form():
    """AcLink.id rejects a value that isn't a canonical acceptance-criterion id."""
    with pytest.raises(ValidationError):
        factories.ac_link(id="not-canonical")


def test_ac_link_forbids_unknown_field():
    """AcLink rejects construction with a field it doesn't declare."""
    with pytest.raises(ValidationError):
        AcLink(id="US-001-01", aspect=None, not_a_real_field="nope")


def test_scenario_forbids_unknown_field():
    """Scenario rejects construction with a field it doesn't declare."""
    with pytest.raises(ValidationError):
        factories.scenario(not_a_real_field="nope")


def test_a_scenario_carries_its_line_steps_rule_and_backgrounds():
    """A Scenario keeps its line, its steps, its rule with the rule's background, and its file's background."""
    scenario = factories.scenario(
        line=43,
        rule="Fines are capped",
        rule_background=["Given the fine cap is 5.00"],
        background=["Given a member in good standing is signed in"],
        steps=["Given a step", "Examples:", "  | amount |"],
    )

    assert scenario.model_dump(include={"line", "rule", "rule_background", "background", "steps"}) == {
        "line": 43,
        "rule": "Fines are capped",
        "rule_background": ["Given the fine cap is 5.00"],
        "background": ["Given a member in good standing is signed in"],
        "steps": ["Given a step", "Examples:", "  | amount |"],
    }


def test_a_scenario_written_before_the_new_fields_still_validates():
    """The contract id stays `ui-tests-v1.0.0`, so a scenario without the new fields still validates, with no line,
    no rule and empty step and background lists."""
    payload = {
        "scenario_id": "SCN-001",
        "title": "A scenario",
        "source_ref": factories.github_source_ref().model_dump(),
    }

    scenario = Scenario.model_validate(payload)

    assert (scenario.line, scenario.rule, scenario.rule_background, scenario.background, scenario.steps) == (
        None,
        None,
        [],
        [],
        [],
    )


def test_a_scenario_line_is_one_based():
    """A Scenario's line counts from 1."""
    with pytest.raises(ValidationError):
        factories.scenario(line=0)


def test_a_ui_tests_link_carries_no_criterion_state():
    """A collector does not know a criterion's state, so a ui-tests link has no `state`; the catalog's link has it."""
    with pytest.raises(ValidationError):
        AcLink(id="US-001-01", state="active")


def test_scenario_source_ref_accepts_github_and_azure_devops():
    """A Scenario's source_ref accepts both a GitHub-shaped and an Azure DevOps-shaped SourceRef."""
    github_scenario = factories.scenario(source_ref=factories.github_source_ref())
    azure_scenario = factories.scenario(source_ref=factories.azure_devops_source_ref())

    assert github_scenario.source_ref.system == "GitHub"
    assert azure_scenario.source_ref.system == "AzureDevOps"
