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
Tests for the ui-test-catalog-v1.0.0 contract.
"""

import json
from typing import Any

import pytest
from pydantic import ValidationError

from living_doc_utilities.contracts.ui_test_catalog import (
    CONTRACT_ID,
    RECORD_ROOTS,
    CatalogAcLink,
    CatalogScenario,
    Document,
    FeatureFileCatalog,
    LinkedScenarios,
    UiTestCatalogResult,
)
from living_doc_utilities.contracts.ui_tests import AcLink, ScenarioCore
from tests.contracts import factories


def _result(**overrides: Any) -> UiTestCatalogResult:
    fields: dict[str, Any] = {
        "metadata": factories.transform_metadata(),
        "document": factories.ui_test_catalog_document(),
        "feature_files": [factories.feature_file_catalog()],
    }
    fields.update(overrides)
    return UiTestCatalogResult(**fields)


def test_metadata_source_inputs_must_be_non_empty():
    """An empty `source_inputs` list is rejected; a transform always has at least its documentation input."""
    with pytest.raises(ValidationError, match="source_inputs must have at least one entry"):
        _result(metadata=factories.metadata())


def test_round_trips_through_json():
    """A UiTestCatalogResult serializes to JSON and back into an equal model, feature_files intact."""
    result = _result()

    payload = json.loads(result.model_dump_json())

    assert payload["schema_version"] == CONTRACT_ID
    assert payload["feature_files"][0]["feature_file"] == "checkout.feature"
    assert UiTestCatalogResult.model_validate(payload) == result


def test_document_carries_only_the_view():
    """`Document` has exactly one field, `view`."""
    assert set(Document.model_fields) == {"view"}


def test_scenarios_are_grouped_by_feature_file_and_then_by_link_kind():
    """A FeatureFileCatalog groups its scenarios by link kind (user story, functionality, unlinked)."""
    catalog = factories.feature_file_catalog()

    assert catalog.feature_file == "checkout.feature"
    assert [g.entity_id for g in catalog.linked_to_user_story] == ["US-001"]
    assert catalog.linked_to_functionality == []
    assert catalog.unlinked == []


def test_scenario_builds_on_the_ui_tests_scenario_core():
    """`LinkedScenarios.scenarios` is typed as `CatalogScenario`, built on `ui_tests`' shared `ScenarioCore`, not a
    copy of its fields."""
    annotation = LinkedScenarios.model_fields["scenarios"].annotation
    (item_type,) = annotation.__args__

    assert item_type is CatalogScenario
    assert issubclass(CatalogScenario, ScenarioCore)
    assert issubclass(CatalogAcLink, AcLink)


def test_unlinked_scenarios_use_the_catalog_scenario_too():
    """`FeatureFileCatalog.unlinked` is typed as `CatalogScenario` too, built on `ui_tests`' shared `ScenarioCore`."""
    annotation = FeatureFileCatalog.model_fields["unlinked"].annotation
    (item_type,) = annotation.__args__

    assert item_type is CatalogScenario


def test_a_feature_files_background_sits_on_the_file_once():
    """A feature file's `Background:` lines sit on its `FeatureFileCatalog`, never on its scenarios; a scenario keeps
    its rule's background."""
    catalog = factories.feature_file_catalog(background=["Given a member in good standing is signed in"])

    assert catalog.background == ["Given a member in good standing is signed in"]
    assert "background" not in CatalogScenario.model_fields
    assert {"line", "rule", "rule_background", "steps"} <= set(CatalogScenario.model_fields)
    with pytest.raises(ValidationError):
        factories.catalog_scenario(background=["Given a step"])


@pytest.mark.parametrize("state", ["active", "deprecated", "planned", "in_review", None])
def test_each_link_carries_its_criterion_s_state_or_none(state):
    """A catalog link carries its criterion's state, or none for a criterion no document holds."""
    link = factories.catalog_ac_link(state=state)

    assert link.state == state


def test_a_link_state_outside_the_lifecycle_is_rejected():
    """A catalog link's state is one of the four lifecycle states."""
    with pytest.raises(ValidationError):
        factories.catalog_ac_link(state="done")


def test_a_catalog_written_before_the_new_fields_still_validates():
    """The contract id stays `ui-test-catalog-v1.0.0`, so a feature file and a link without the new fields validate."""
    feature_file = FeatureFileCatalog.model_validate(
        {"feature_file": "checkout.feature", "unlinked": [factories.catalog_scenario().model_dump(exclude={"line"})]}
    )

    assert feature_file.background == []
    assert CatalogAcLink.model_validate({"id": "US-001-01"}).state is None


def test_record_root_is_feature_files():
    """The contract's only record root is `feature_files`, mapped to `FeatureFileCatalog`."""
    assert RECORD_ROOTS == {"feature_files": FeatureFileCatalog}
