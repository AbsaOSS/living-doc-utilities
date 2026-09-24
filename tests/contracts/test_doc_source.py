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

"""The doc-source contract: its three list record roots and their reuse of doc-entities' `Entity` model."""

import pytest
from pydantic import ValidationError

from living_doc_utilities.contracts.doc_entities import Entity
from living_doc_utilities.contracts.doc_source import CONTRACT_ID, RECORD_ROOTS, DocSourceResult
from tests.contracts import factories


def test_doc_source_uses_the_three_list_record_roots():
    """DocSourceResult exposes user_stories/features/functionalities as separate lists, no items key."""
    result = DocSourceResult(
        metadata=factories.metadata(),
        user_stories=[factories.user_story()],
        features=[factories.feature()],
        functionalities=[factories.functionality()],
    )

    assert len(result.user_stories) == 1
    assert len(result.features) == 1
    assert len(result.functionalities) == 1
    assert "items" not in DocSourceResult.model_fields


def test_doc_source_lists_default_to_empty():
    """Each of the three record-root lists defaults to empty when not supplied."""
    result = DocSourceResult(metadata=factories.metadata())

    assert result.user_stories == []
    assert result.features == []
    assert result.functionalities == []


def test_doc_source_entity_is_the_same_shared_model_as_doc_entities():
    """All three doc-source record roots use the same shared `Entity` model as doc-entities."""
    assert RECORD_ROOTS == {
        "user_stories": Entity,
        "features": Entity,
        "functionalities": Entity,
    }


def test_doc_source_reuses_doc_entities_validators():
    """`DocSourceResult` enforces the same `state_origin` validator that doc-entities uses."""
    with pytest.raises(ValidationError, match="state_origin must be 'derived'"):
        DocSourceResult(metadata=factories.metadata(), features=[factories.feature(state_origin="authored")])


def test_doc_source_result_schema_version_is_the_contract_id():
    """`DocSourceResult.schema_version` equals the module's own `CONTRACT_ID`."""
    result = DocSourceResult(metadata=factories.metadata())

    assert result.schema_version == CONTRACT_ID == "doc-source-v1.0.0"


def test_doc_source_forbids_unknown_top_level_field():
    """`DocSourceResult` rejects an unrecognised top-level field."""
    with pytest.raises(ValidationError):
        DocSourceResult(metadata=factories.metadata(), items=[])
