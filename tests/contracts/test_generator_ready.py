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
Tests for the generator-ready-v1.0.0 contract (docs/contracts.md, section 1).
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
        "metadata": factories.metadata(),
        "document": factories.generator_ready_document(),
        "content": Content(entities=[factories.user_story()]),
    }
    fields.update(overrides)
    return GeneratorReadyResult(**fields)


# ---------------------------------------------------------------------------
# Shape: content.entities[], a `document` block, no `meta`, no version alias.
# ---------------------------------------------------------------------------


def test_round_trips_through_json():
    result = _result()

    payload = json.loads(result.model_dump_json())

    assert payload["schema_version"] == CONTRACT_ID
    assert payload["content"]["entities"][0]["entity_id"] == "US-001"
    assert GeneratorReadyResult.model_validate(payload) == result


def test_schema_version_is_a_plain_const_with_no_1_0_alias():
    assert GeneratorReadyResult.model_fields["schema_version"].default == "generator-ready-v1.0.0"

    with pytest.raises(ValidationError):
        _result(schema_version="1.0")


def test_content_uses_entities_not_user_stories():
    assert "entities" in Content.model_fields
    assert "user_stories" not in Content.model_fields


def test_there_is_no_meta_field_on_the_result():
    assert "meta" not in GeneratorReadyResult.model_fields
    assert set(GeneratorReadyResult.model_fields) == {"schema_version", "metadata", "warnings", "document", "content"}


def test_there_is_no_retired_provenance_shape_anywhere_in_the_tree():
    # R8: no `run_context` or `audit` block - the toolkit's Meta.run_context / Meta.audit are
    # retired outright, replaced by the shared envelope's metadata.run / metadata.source_inputs.
    for model in (GeneratorReadyResult, Document, SelectionSummary, Content):
        assert "run_context" not in model.model_fields
        assert "audit" not in model.model_fields


def test_selection_summary_is_a_record_with_exactly_six_fields():
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
    document = factories.generator_ready_document(view="inner")

    assert document.view == "inner"


def test_record_root_is_content_entities():
    assert RECORD_ROOTS == {"content.entities": Entity}


# ---------------------------------------------------------------------------
# Every authored entity / acceptance-criterion field defined on doc-entities is reachable
# on generator-ready - reused directly, not redeclared (docs/contracts.md, section 1;
# this repo's issue #128 "Authored field set").
# ---------------------------------------------------------------------------


def test_content_entities_reuses_the_doc_entities_entity_model_directly():
    annotation = Content.model_fields["entities"].annotation

    # list[Entity] - unwrap to the item type.
    (item_type,) = annotation.__args__
    assert item_type is Entity


def test_every_doc_entities_field_is_reachable_on_generator_ready_content_entities():
    entity_fields = set(Entity.model_fields)

    assert entity_fields, "doc-entities Entity should declare at least one field"
    for field_name in entity_fields:
        assert field_name in Entity.model_fields  # reachable via content.entities[].<field_name>


def test_acceptance_criteria_reuses_the_shared_acceptance_criterion_model_directly():
    ac_annotation = Entity.model_fields["acceptance_criteria"].annotation
    (item_type,) = ac_annotation.__args__

    assert item_type is AcceptanceCriterion


def test_every_acceptance_criterion_field_is_reachable_on_generator_ready():
    ac_fields = set(AcceptanceCriterion.model_fields)

    assert ac_fields, "doc-entities AcceptanceCriterion should declare at least one field"
    for field_name in ac_fields:
        assert field_name in AcceptanceCriterion.model_fields  # content.entities[].acceptance_criteria[].<field_name>


# ---------------------------------------------------------------------------
# Nothing carried by today's toolkit `SelectionSummary` / `ViewSummary` models is lost in
# the move (this repo's issue #130 "Dependencies / Related"). The toolkit lives in a
# different repository, so this maps the *source* field names (read from
# living-doc-toolkit's generator_ready/v1/models.py) to their destination path here, and
# proves every destination actually resolves.
# ---------------------------------------------------------------------------

# (toolkit source model.field, destination path on GeneratorReadyResult)
TOOLKIT_FIELD_MAPPING = {
    # SelectionSummary counted entities (toolkit's "items" are user stories/entities,
    # see normalize_issues/builder.py: total_items = len(adapter_result.items)).
    "SelectionSummary.total_items": "document.selection_summary.total_entities",
    "SelectionSummary.included_items": "document.selection_summary.included_entities",
    "SelectionSummary.excluded_items": "document.selection_summary.excluded_entities",
    # ViewSummary: the applied view, plus what it additionally dropped. The new contract
    # has one excluded_* counter per kind (no separate "excluded by selection" vs.
    # "excluded by view" split) - a view-side drop is still an exclusion.
    "ViewSummary.view": "document.view",
    "ViewSummary.filtered_user_stories": "document.selection_summary.excluded_entities",
    "ViewSummary.filtered_acceptance_criteria": "document.selection_summary.excluded_acceptance_criteria",
}


def _resolve(model, path: str) -> None:
    """Walks a dotted field path through a chain of pydantic models, raising KeyError/
    AttributeError if any segment does not resolve to a real field."""
    current = model
    for segment in path.split("."):
        field_info = current.model_fields[segment]
        annotation = field_info.annotation
        origin = getattr(annotation, "__args__", None)
        if origin and type(None) in origin:
            (inner,) = [arg for arg in origin if arg is not type(None)]
            annotation = inner
        current = annotation


@pytest.mark.parametrize("source_field, destination", TOOLKIT_FIELD_MAPPING.items(), ids=list(TOOLKIT_FIELD_MAPPING))
def test_every_toolkit_selection_and_view_summary_field_maps_to_a_real_destination(source_field, destination):
    _resolve(GeneratorReadyResult, destination)


def test_the_mapping_covers_every_field_of_both_toolkit_models():
    # SelectionSummary: total_items, included_items, excluded_items.
    # ViewSummary: view, filtered_user_stories, filtered_acceptance_criteria.
    mapped_toolkit_fields = {source.split(".", 1)[1] for source in TOOLKIT_FIELD_MAPPING}
    assert mapped_toolkit_fields == {
        "total_items",
        "included_items",
        "excluded_items",
        "view",
        "filtered_user_stories",
        "filtered_acceptance_criteria",
    }


# ---------------------------------------------------------------------------
# SelectionSummary.total_entities is a guaranteed identity of the producer (the toolkit
# derives excluded_entities as total_entities - included_entities); the same identity does
# not hold for the three acceptance-criteria fields, since the producer never tallies
# criteria belonging to a dropped entity.
# ---------------------------------------------------------------------------


def test_selection_summary_enforces_total_entities_equals_included_plus_excluded():
    with pytest.raises(ValidationError, match="total_entities must equal included_entities \\+ excluded_entities"):
        factories.selection_summary(total_entities=10, included_entities=7, excluded_entities=2)


def test_selection_summary_does_not_enforce_the_same_relationship_for_acceptance_criteria():
    # Not a disjoint partition (docs/contracts.md, section 4) - must not raise.
    factories.selection_summary(
        total_acceptance_criteria=20, included_acceptance_criteria=15, excluded_acceptance_criteria=1
    )
