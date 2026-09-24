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
Tests for the generator-ready-v1.0.0 contract (generator_ready.py).
"""

import json
from typing import Any

import pytest
from pydantic import ValidationError

from living_doc_utilities.contracts.common import AcceptanceCriterion
from living_doc_utilities.contracts.doc_entities import Entity
from living_doc_utilities.contracts.generator_ready import (
    CONTRACT_ID,
    RECORD_ROOTS,
    Content,
    Document,
    GeneratorReadyResult,
    SelectionSummary,
)
from tests.contracts import factories


def _result(**overrides: Any) -> GeneratorReadyResult:
    fields: dict[str, Any] = {
        "metadata": factories.transform_metadata(),
        "document": factories.generator_ready_document(),
        "content": Content(entities=[factories.user_story()]),
    }
    fields.update(overrides)
    return GeneratorReadyResult(**fields)


# ---------------------------------------------------------------------------
# Shape: content.entities[], a `document` block, no `meta`, no version alias.
# ---------------------------------------------------------------------------


def test_round_trips_through_json():
    """A GeneratorReadyResult serializes to JSON and back into an equal model, content intact."""
    result = _result()

    payload = json.loads(result.model_dump_json())

    assert payload["schema_version"] == CONTRACT_ID
    assert payload["content"]["entities"][0]["entity_id"] == "US-001"
    assert GeneratorReadyResult.model_validate(payload) == result


def test_schema_version_is_a_plain_const_with_no_1_0_alias():
    """schema_version defaults to the full contract id and rejects a bare '1.0' alias."""
    assert GeneratorReadyResult.model_fields["schema_version"].default == "generator-ready-v1.0.0"

    with pytest.raises(ValidationError):
        _result(schema_version="1.0")


def test_content_uses_entities_not_user_stories():
    """Content is keyed by 'entities', not the retired 'user_stories' field name."""
    assert "entities" in Content.model_fields
    assert "user_stories" not in Content.model_fields


def test_there_is_no_meta_field_on_the_result():
    """GeneratorReadyResult has no 'meta' field; its field set is exactly the five documented ones."""
    assert "meta" not in GeneratorReadyResult.model_fields
    assert set(GeneratorReadyResult.model_fields) == {"schema_version", "metadata", "warnings", "document", "content"}


def test_there_is_no_retired_provenance_shape_anywhere_in_the_tree():
    """No model in the generator-ready tree carries a retired run_context or audit field."""
    # R8: the retired run_context / audit blocks are replaced by metadata.run / metadata.source_inputs.
    for model in (GeneratorReadyResult, Document, SelectionSummary, Content):
        assert "run_context" not in model.model_fields
        assert "audit" not in model.model_fields


def test_metadata_source_inputs_must_be_non_empty():
    """GeneratorReadyResult rejects metadata whose source_inputs is empty."""
    # R7: a transform always has at least its documentation input.
    with pytest.raises(ValidationError, match="source_inputs must have at least one entry"):
        _result(metadata=factories.metadata())


def test_selection_summary_is_a_record_with_exactly_six_fields():
    """SelectionSummary has exactly its six documented fields and forbids any other."""
    assert set(SelectionSummary.model_fields) == {
        "total_entities",
        "included_entities",
        "excluded_entities",
        "total_acceptance_criteria",
        "included_acceptance_criteria",
        "excluded_acceptance_criteria",
    }
    assert SelectionSummary.model_config.get("extra") == "forbid"


def test_document_view_carries_the_view_string():
    """Document.view carries through the view string it was constructed with."""
    document = factories.generator_ready_document(view="inner")

    assert document.view == "inner"


def test_record_root_is_content_entities():
    """RECORD_ROOTS maps 'content.entities' to the Entity model."""
    assert RECORD_ROOTS == {"content.entities": Entity}


# ---------------------------------------------------------------------------
# Every authored entity / AC field defined on doc-entities is reachable on generator-ready, reused not redeclared.
# ---------------------------------------------------------------------------


def test_content_entities_reuses_the_doc_entities_entity_model_directly():
    """Content.entities is typed as doc-entities' own Entity, not a redeclared look-alike model."""
    annotation = Content.model_fields["entities"].annotation

    # list[Entity] - unwrap to the item type.
    (item_type,) = annotation.__args__
    assert item_type is Entity


def test_acceptance_criteria_reuses_the_shared_acceptance_criterion_model_directly():
    """Entity.acceptance_criteria is typed as the shared AcceptanceCriterion model directly."""
    ac_annotation = Entity.model_fields["acceptance_criteria"].annotation
    (item_type,) = ac_annotation.__args__

    assert item_type is AcceptanceCriterion


# ---------------------------------------------------------------------------
# total_entities is a producer identity; the AC counts are not, as criteria of dropped entities are never tallied.
# ---------------------------------------------------------------------------


def test_selection_summary_enforces_total_entities_equals_included_plus_excluded():
    """SelectionSummary rejects a total_entities that doesn't equal included_entities + excluded_entities."""
    with pytest.raises(ValidationError, match="total_entities must equal included_entities \\+ excluded_entities"):
        factories.selection_summary(total_entities=10, included_entities=7, excluded_entities=2)


def test_selection_summary_does_not_enforce_the_same_relationship_for_acceptance_criteria():
    """SelectionSummary does not enforce the total = included + excluded identity for acceptance-criteria counts."""
    # Not a disjoint partition (`generator_ready.py::SelectionSummary`) - must not raise.
    factories.selection_summary(
        total_acceptance_criteria=20, included_acceptance_criteria=15, excluded_acceptance_criteria=1
    )
