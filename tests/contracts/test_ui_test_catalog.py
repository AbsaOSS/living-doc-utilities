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
    Document,
    FeatureFileCatalog,
    LinkedScenarios,
    UiTestCatalogResult,
)
from living_doc_utilities.contracts.ui_tests import Scenario
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
    # R7: a transform always has at least its documentation input.
    with pytest.raises(ValidationError, match="source_inputs must have at least one entry"):
        _result(metadata=factories.metadata())


def test_round_trips_through_json():
    result = _result()

    payload = json.loads(result.model_dump_json())

    assert payload["schema_version"] == CONTRACT_ID
    assert payload["feature_files"][0]["feature_file"] == "checkout.feature"
    assert UiTestCatalogResult.model_validate(payload) == result


def test_document_carries_only_the_view():
    assert set(Document.model_fields) == {"view"}


def test_scenarios_are_grouped_by_feature_file_and_then_by_link_kind():
    catalog = factories.feature_file_catalog()

    assert catalog.feature_file == "checkout.feature"
    assert [g.entity_id for g in catalog.linked_to_user_story] == ["US-001"]
    assert catalog.linked_to_functionality == []
    assert catalog.unlinked == []


def test_scenario_reuses_the_ui_tests_scenario_model_directly():
    annotation = LinkedScenarios.model_fields["scenarios"].annotation
    (item_type,) = annotation.__args__

    assert item_type is Scenario


def test_unlinked_scenarios_use_the_shared_scenario_model_too():
    annotation = FeatureFileCatalog.model_fields["unlinked"].annotation
    (item_type,) = annotation.__args__

    assert item_type is Scenario


def test_record_root_is_feature_files():
    assert RECORD_ROOTS == {"feature_files": FeatureFileCatalog}
