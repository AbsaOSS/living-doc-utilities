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

from living_doc_utilities.contracts import schema_export
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


def test_metadata_source_inputs_must_be_non_empty():
    # R7: a transform always has at least its documentation input.
    with pytest.raises(ValidationError, match="source_inputs must have at least one entry"):
        _result(metadata=factories.metadata())


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


def test_acceptance_criteria_reuses_the_shared_acceptance_criterion_model_directly():
    ac_annotation = Entity.model_fields["acceptance_criteria"].annotation
    (item_type,) = ac_annotation.__args__

    assert item_type is AcceptanceCriterion


# ---------------------------------------------------------------------------
# Nothing carried by today's toolkit's generator-ready models is lost in the move (this
# repo's issue #130 "Dependencies / Related": "nothing existing should be lost in the move -
# track it with a field-by-field mapping test"). The toolkit lives in a different repository
# (living-doc-toolkit, packages/datasets_generator_ready/.../generator_ready/v1/models.py),
# so this maps each of its *source* field names to a destination path here and proves every
# destination actually resolves. A container field (Meta.selection_summary, Meta.view,
# UserStory.timestamps, UserStory.sections) is not itself an entry: its own fields are proven
# reachable by the nested model's entries below instead, the same way this table never lists
# "GeneratorReadyV1.meta" or "GeneratorReadyV1.content".
# ---------------------------------------------------------------------------

# (toolkit source model.field, destination path on GeneratorReadyResult; "[]" crosses a list,
# matching docs/contracts.md's own field-path notation)
TOOLKIT_FIELD_MAPPING = {
    # Meta (docs/contracts.md, "The metadata envelope").
    "Meta.document_title": "document.title",
    "Meta.document_version": "document.version",
    "Meta.generated_at": "metadata.generated_at",
    # A flat list of source identifiers; superseded by R7's richer, structured per-input
    # provenance record (producer, run, source, stats - not just a name).
    "Meta.source_set": "metadata.source_inputs",
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
    # UserStory -> content.entities[] (doc-entities Entity, reused directly - not redeclared).
    "UserStory.title": "content.entities[].title",
    "UserStory.state": "content.entities[].state",
    "UserStory.tags": "content.entities[].tags",
    "UserStory.url": "content.entities[].source_ref.url",
    "Timestamps.created": "content.entities[].timestamps.created_at",
    "Timestamps.updated": "content.entities[].timestamps.updated_at",
    # Sections -> content.entities[] (a User Story's authored body).
    "Sections.description": "content.entities[].narrative",
    "Sections.business_value": "content.entities[].business_value",
    "Sections.preconditions": "content.entities[].preconditions",
    # AcceptanceCriterion -> content.entities[].acceptance_criteria[] (common.AcceptanceCriterion,
    # reused directly).
    "AcceptanceCriterion.id": "content.entities[].acceptance_criteria[].id",
    "AcceptanceCriterion.state": "content.entities[].acceptance_criteria[].state",
    "AcceptanceCriterion.version": "content.entities[].acceptance_criteria[].version",
    "AcceptanceCriterion.description": "content.entities[].acceptance_criteria[].description",
}

# Legacy fields with no destination today, each with why - mirrors R11's lineage-table
# convention (every input leaf either maps or is dropped with a reason, never silently
# forgotten). This is an accounting device for the test below, not a contract rule.
TOOLKIT_FIELDS_NOT_CARRIED = {
    # R8: retired outright, no alias window, no per-entry fallback.
    "Meta.run_context": "retired outright (R8) - replaced by metadata.run",
    "Meta.audit": "retired outright (R8) - replaced by metadata.source_inputs / metadata.stats",
    # entity_id is parsed from the title (MISSING_ENTITY_ID) - it is not a rename of this
    # field (docs/contracts.md, "Entity identity").
    "UserStory.id": "superseded by entity_id, which is parsed from the title, not carried from this field",
    # Retired, not lost: none of these three is in the canonical authored field set
    # (test_authored_field_set.py, copied from AbsaOSS/living-doc's canon, issue #128) that
    # Entity's shape was built and tested against - they are toolkit-internal fields the canon
    # never carried forward, not fields this contract forgot to place.
    "Sections.user_guide": "retired - not in the canonical authored field set (test_authored_field_set.py)",
    "Sections.connections": "retired - not in the canonical authored field set (test_authored_field_set.py)",
    "Sections.last_edited": "retired - not in the canonical authored field set (test_authored_field_set.py) "
    "(free-text attribution, not an ISO timestamp - not the same as Timestamps.updated)",
}


def _resolve(model, path: str) -> None:
    """Walks a dotted field path through a chain of pydantic models, raising KeyError if any
    segment does not resolve to a real field. A segment suffixed "[]" crosses that field's
    list boundary onto its item type - schema_export.unwrap_field_type does the same
    Optional/list peeling schema_export's own leaf-path walk and stats.compute_stats rely on."""
    current = model
    for raw_segment in path.split("."):
        segment = raw_segment[:-2] if raw_segment.endswith("[]") else raw_segment
        field_info = current.model_fields[segment]
        current, _is_array = schema_export.unwrap_field_type(field_info.annotation)


@pytest.mark.parametrize("source_field, destination", TOOLKIT_FIELD_MAPPING.items(), ids=list(TOOLKIT_FIELD_MAPPING))
def test_every_toolkit_field_maps_to_a_real_destination(source_field, destination):
    _resolve(GeneratorReadyResult, destination)


def test_the_mapping_and_drop_list_together_account_for_every_field_of_every_toolkit_model():
    accounted: dict[str, set[str]] = {}
    for source in list(TOOLKIT_FIELD_MAPPING) + list(TOOLKIT_FIELDS_NOT_CARRIED):
        model_name, field_name = source.split(".", 1)
        accounted.setdefault(model_name, set()).add(field_name)

    # Meta's own leaves only - selection_summary/view are containers, proven by
    # SelectionSummary's/ViewSummary's own entries instead.
    assert accounted["Meta"] == {"document_title", "document_version", "generated_at", "source_set", "run_context", "audit"}
    assert accounted["SelectionSummary"] == {"total_items", "included_items", "excluded_items"}
    assert accounted["ViewSummary"] == {"view", "filtered_user_stories", "filtered_acceptance_criteria"}
    # UserStory's own leaves only - timestamps/sections are containers, proven by
    # Timestamps's/Sections's own entries instead.
    assert accounted["UserStory"] == {"title", "state", "tags", "url", "id"}
    assert accounted["Timestamps"] == {"created", "updated"}
    assert accounted["Sections"] == {
        "description",
        "business_value",
        "preconditions",
        "user_guide",
        "connections",
        "last_edited",
    }
    assert accounted["AcceptanceCriterion"] == {"id", "state", "version", "description"}


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
