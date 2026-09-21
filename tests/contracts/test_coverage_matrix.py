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
Tests for the coverage-matrix-v1.0.0 contract (docs/contracts.md, section 4, "Coverage").
"""

import json
from typing import Any, get_args

import pytest
from pydantic import ValidationError

from living_doc_utilities.contracts import schema_export
from living_doc_utilities.contracts.coverage_matrix import (
    CONTRACT_ID,
    RECORD_ROOTS,
    CountedState,
    CoverageMatrixResult,
    CoverageStatus,
    Document,
    EntityCoverage,
)
from tests.contracts import factories


def _result(**overrides: Any) -> CoverageMatrixResult:
    fields: dict[str, Any] = {
        "metadata": factories.transform_metadata(),
        "document": factories.coverage_matrix_document(),
        "entities": [factories.entity_coverage()],
        "planned_summary": factories.planned_summary(),
    }
    fields.update(overrides)
    return CoverageMatrixResult(**fields)


def test_round_trips_through_json():
    result = _result()

    payload = json.loads(result.model_dump_json())

    assert payload["schema_version"] == CONTRACT_ID
    assert CoverageMatrixResult.model_validate(payload) == result


def test_schema_version_is_a_plain_const():
    assert CoverageMatrixResult.model_fields["schema_version"].default == "coverage-matrix-v1.0.0"


def test_metadata_source_inputs_must_be_non_empty():
    # R7: a transform always has at least its documentation input.
    with pytest.raises(ValidationError, match="source_inputs must have at least one entry"):
        _result(metadata=factories.metadata())


def test_document_carries_only_the_view():
    assert set(Document.model_fields) == {"view"}


def test_counted_states_are_exactly_active_and_deprecated():
    assert set(get_args(CountedState)) == {"active", "deprecated"}


def test_coverage_status_models_covered_partially_covered_and_not_covered():
    assert set(get_args(CoverageStatus)) == {"covered", "partially_covered", "not_covered"}


def test_ac_coverage_carries_a_per_aspect_breakdown():
    row = factories.ac_coverage(
        status="partially_covered",
        aspects=[factories.aspect_coverage(aspect="checkout", status="covered"), factories.aspect_coverage(aspect="refund", status="not_covered")],
    )

    assert row.status == "partially_covered"
    assert [a.aspect for a in row.aspects] == ["checkout", "refund"]


def test_ac_coverage_rejects_a_state_outside_the_counted_set():
    with pytest.raises(ValidationError):
        factories.ac_coverage(state="planned")


def test_ac_coverage_rejects_covered_status_with_a_not_covered_aspect():
    with pytest.raises(ValidationError, match="status must be 'partially_covered'"):
        factories.ac_coverage(
            status="covered",
            aspects=[factories.aspect_coverage(status="covered"), factories.aspect_coverage(status="not_covered")],
        )


def test_ac_coverage_rejects_partially_covered_status_with_no_aspects():
    with pytest.raises(ValidationError, match="cannot be 'partially_covered' when aspects is empty"):
        factories.ac_coverage(status="partially_covered", aspects=[])


def test_ac_coverage_rejects_not_covered_status_when_aspects_are_present():
    with pytest.raises(ValidationError, match="status must be 'covered'"):
        factories.ac_coverage(status="not_covered", aspects=[factories.aspect_coverage(status="covered")])


def test_ac_coverage_accepts_covered_status_when_every_aspect_is_covered():
    row = factories.ac_coverage(status="covered", aspects=[factories.aspect_coverage(status="covered")])

    assert row.status == "covered"


def test_ac_coverage_rejects_a_malformed_ac_id():
    # AC_ID_PATTERN, same as common.AcceptanceCriterion.id and ui_tests.AcLink.id - the
    # belongs-to-entity prefix check alone does not catch a malformed suffix.
    with pytest.raises(ValidationError):
        factories.ac_coverage(ac_id="US-001-anything")


def test_aspect_coverage_rejects_covered_status_with_no_linked_scenarios():
    with pytest.raises(ValidationError, match="status must be 'not_covered'"):
        factories.aspect_coverage(status="covered", scenario_ids=[])


def test_aspect_coverage_rejects_not_covered_status_with_linked_scenarios():
    with pytest.raises(ValidationError, match="status must be 'covered'"):
        factories.aspect_coverage(status="not_covered", scenario_ids=["SCN-001"])


def test_ac_coverage_without_aspects_rejects_covered_status_with_no_linked_scenarios():
    with pytest.raises(ValidationError, match="status must be 'not_covered'"):
        factories.ac_coverage(status="covered", aspects=[], scenario_ids=[])


def test_ac_coverage_without_aspects_rejects_not_covered_status_with_linked_scenarios():
    with pytest.raises(ValidationError, match="status must be 'covered'"):
        factories.ac_coverage(status="not_covered", aspects=[], scenario_ids=["SCN-001"])


def test_planned_summary_models_total_backlog_and_by_target_version():
    summary = factories.planned_summary(total=5, backlog=2, by_target_version={"1.5.0": 2, "1.6.0": 1})

    assert summary.total == 5
    assert summary.backlog == 2
    assert summary.by_target_version == {"1.5.0": 2, "1.6.0": 1}


def test_planned_summary_rejects_a_total_that_does_not_equal_backlog_plus_targeted():
    with pytest.raises(ValidationError, match="must equal backlog"):
        factories.planned_summary(total=1, backlog=1, by_target_version={"1.5.0": 2})


def test_by_target_version_keys_must_be_a_version_string():
    with pytest.raises(ValidationError):
        factories.planned_summary(by_target_version={"v1.5": 1})


def test_by_target_version_values_must_be_nonnegative():
    with pytest.raises(ValidationError):
        factories.planned_summary(by_target_version={"1.5.0": -1})


def test_entity_coverage_state_is_the_full_lifecycle_state_not_just_counted_states():
    # A User Story can still be `in_review` overall while one of its acceptance criteria is
    # already `active` and must be counted (docs/contracts.md, "Coverage": counting is
    # decided per AC, in both views, never by the parent entity's state).
    row = factories.entity_coverage(state="in_review", acceptance_criteria=[factories.ac_coverage()])

    assert row.state == "in_review"
    assert row.acceptance_criteria[0].state == "active"


def test_acceptance_criterion_id_must_belong_to_its_entity():
    with pytest.raises(ValidationError, match="does not belong to entity"):
        _result(entities=[factories.entity_coverage(entity_id="US-001", acceptance_criteria=[factories.ac_coverage(parent_id="US-002")])])


def test_record_root_is_entities():
    assert RECORD_ROOTS == {"entities": EntityCoverage}


# ---------------------------------------------------------------------------
# Nothing carried by today's toolkit's coverage-matrix model is lost in the move (this
# repo's issue #130 "Dependencies / Related": "nothing existing should be lost in the move -
# track it with a field-by-field mapping test"). The toolkit lives in a different repository
# (living-doc-toolkit, packages/services/coverage_matrix/.../model/coverage_item.py), so this
# maps each of its *source* field names to a destination path here and proves every mapped
# destination actually resolves. A container field (CoverageMatrix.summary/user_stories/...,
# UserStoryCoverage.summary/acceptance_criteria, Coverage.tests) is not itself an entry: its
# own fields get their own entries below instead, keyed by the nested model's class name -
# the same convention test_generator_ready.py uses.
# ---------------------------------------------------------------------------

# (toolkit source model.field, destination path on CoverageMatrixResult; "[]" crosses a list)
TOOLKIT_FIELD_MAPPING = {
    "CoverageMatrix.generated_at": "metadata.generated_at",
    "UserStoryCoverage.title": "entities[].title",
    "UserStoryCoverage.state": "entities[].state",
    "FunctionalityCoverage.title": "entities[].title",
    "FunctionalityCoverage.state": "entities[].state",
    "TestRef.id": "entities[].acceptance_criteria[].scenario_ids",
    "Coverage.status": "entities[].acceptance_criteria[].status",
    "AcCoverage.id": "entities[].acceptance_criteria[].ac_id",
    "AcCoverage.state": "entities[].acceptance_criteria[].state",
}

# Legacy fields with no destination today, each with why - mirrors R11's lineage-table
# convention (every input leaf either maps or is dropped with a reason, never silently
# forgotten). This is an accounting device for the test below, not a contract rule.
_DERIVED_NOT_STORED = "derivable from entities[].acceptance_criteria[], not stored"
_SUPERSEDED_ID = "superseded by entity_id (parsed elsewhere from the title), not derived from either legacy id field"
_JOIN_GENERATOR_READY = "available via generator-ready's content.entities[] by joining entity_id, not duplicated here"
_JOIN_UI_TEST_CATALOG = "available via ui-test-catalog by joining scenario_ids against Scenario, not duplicated here by design"
_MOVED_TO_FEATURE_ENTRY = (
    "Features carry no acceptance criteria and are out of coverage-matrix's scope; "
    "carried instead by generator-ready's content.entities[] (type=DocumentedFeature)"
)
_MOVED_TO_UNLINKED = "unlinked scenarios are a different contract - ui-test-catalog's feature_files[].unlinked"
_MOVED_TO_WARNINGS = "flattened into the free-text warnings[] of a STALE_AC_REF warning, not a structured field"
_NO_AC_TEXT_DESTINATION = (
    "not present on the new AcCoverage row; available via generator-ready's "
    "content.entities[].acceptance_criteria[] by joining ac_id, not duplicated here - same "
    "join-not-duplicate design as _JOIN_GENERATOR_READY/_JOIN_UI_TEST_CATALOG above"
)

TOOLKIT_FIELDS_NOT_CARRIED = {
    # TopSummary: the aggregate rollup is not stored; a consumer recomputes it from entities[].
    "TopSummary.total_user_stories": _DERIVED_NOT_STORED,
    "TopSummary.total_functionalities": _DERIVED_NOT_STORED,
    "TopSummary.total_features": "not derivable from coverage-matrix (Features carry no ACs and are absent from "
    "entities[]); available from generator-ready's content.entities[] instead",
    "TopSummary.total_acs": _DERIVED_NOT_STORED,
    "TopSummary.active_acs": _DERIVED_NOT_STORED,
    "TopSummary.covered_acs": _DERIVED_NOT_STORED,
    "TopSummary.coverage_pct": _DERIVED_NOT_STORED,
    # Summary: the same per-entity rollup, same reasoning.
    "Summary.total_acs": _DERIVED_NOT_STORED,
    "Summary.active_acs": _DERIVED_NOT_STORED,
    "Summary.covered_acs": _DERIVED_NOT_STORED,
    "Summary.coverage_pct": _DERIVED_NOT_STORED,
    # UserStoryCoverage / FunctionalityCoverage identity and Functionality-only fields.
    "UserStoryCoverage.id": _SUPERSEDED_ID,
    "UserStoryCoverage.full_id": _SUPERSEDED_ID,
    "FunctionalityCoverage.id": _SUPERSEDED_ID,
    "FunctionalityCoverage.full_id": _SUPERSEDED_ID,
    "FunctionalityCoverage.parent": _JOIN_GENERATOR_READY,
    "FunctionalityCoverage.func_type": _JOIN_GENERATOR_READY,
    # TestRef: only the id is carried (as a scenario_ids entry); the rest is joined, not duplicated.
    "TestRef.scenario_name": _JOIN_UI_TEST_CATALOG,
    "TestRef.tags": _JOIN_UI_TEST_CATALOG,
    "TestRef.source": _JOIN_UI_TEST_CATALOG,
    # Coverage.test_count is a count of Coverage.tests, so it is not stored separately either.
    "Coverage.test_count": "derivable as len(scenario_ids) per acceptance criterion, not stored",
    # AcCoverage (legacy): version/description are not on the new row - a genuine open question.
    "AcCoverage.version": _NO_AC_TEXT_DESTINATION,
    "AcCoverage.description": _NO_AC_TEXT_DESTINATION,
    # FeatureEntry: the whole model moved to generator-ready - Features have no coverage.
    "FeatureEntry.id": _MOVED_TO_FEATURE_ENTRY,
    "FeatureEntry.full_id": _MOVED_TO_FEATURE_ENTRY,
    "FeatureEntry.title": _MOVED_TO_FEATURE_ENTRY,
    "FeatureEntry.state": _MOVED_TO_FEATURE_ENTRY,
    "FeatureEntry.surface_type": _MOVED_TO_FEATURE_ENTRY,
    "FeatureEntry.route": _MOVED_TO_FEATURE_ENTRY,
    "FeatureEntry.owners": _MOVED_TO_FEATURE_ENTRY,
    "FeatureEntry.purpose": _MOVED_TO_FEATURE_ENTRY,
    "FeatureEntry.user_stories": _MOVED_TO_FEATURE_ENTRY,
    "FeatureEntry.functionalities": _MOVED_TO_FEATURE_ENTRY,
    "FeatureEntry.external_dependencies": _MOVED_TO_FEATURE_ENTRY,
    "FeatureEntry.page_object": _MOVED_TO_FEATURE_ENTRY,
    # UnlinkedTest: moved to ui-test-catalog outright.
    "UnlinkedTest.id": _MOVED_TO_UNLINKED,
    "UnlinkedTest.scenario_name": _MOVED_TO_UNLINKED,
    "UnlinkedTest.us_id": _MOVED_TO_UNLINKED,
    "UnlinkedTest.func_id": _MOVED_TO_UNLINKED,
    "UnlinkedTest.ac_ids": _MOVED_TO_UNLINKED,
    "UnlinkedTest.source": _MOVED_TO_UNLINKED,
    # StaleAcRef: flattened into a warning instead of a structured record.
    "StaleAcRef.scenario_id": _MOVED_TO_WARNINGS,
    "StaleAcRef.scenario_name": _MOVED_TO_WARNINGS,
    "StaleAcRef.us_id": _MOVED_TO_WARNINGS,
    "StaleAcRef.func_id": _MOVED_TO_WARNINGS,
    "StaleAcRef.stale_ac_id": _MOVED_TO_WARNINGS,
    "StaleAcRef.source": _MOVED_TO_WARNINGS,
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
    _resolve(CoverageMatrixResult, destination)


def test_the_mapping_and_drop_list_together_account_for_every_field_of_every_toolkit_model():
    accounted: dict[str, set[str]] = {}
    for source in list(TOOLKIT_FIELD_MAPPING) + list(TOOLKIT_FIELDS_NOT_CARRIED):
        model_name, field_name = source.split(".", 1)
        accounted.setdefault(model_name, set()).add(field_name)

    assert accounted["CoverageMatrix"] == {"generated_at"}
    assert accounted["TopSummary"] == {
        "total_user_stories",
        "total_functionalities",
        "total_features",
        "total_acs",
        "active_acs",
        "covered_acs",
        "coverage_pct",
    }
    assert accounted["Summary"] == {"total_acs", "active_acs", "covered_acs", "coverage_pct"}
    assert accounted["UserStoryCoverage"] == {"id", "full_id", "title", "state"}
    assert accounted["FunctionalityCoverage"] == {"id", "full_id", "title", "state", "parent", "func_type"}
    assert accounted["TestRef"] == {"id", "scenario_name", "tags", "source"}
    assert accounted["Coverage"] == {"status", "test_count"}
    assert accounted["AcCoverage"] == {"id", "state", "version", "description"}
    assert accounted["FeatureEntry"] == {
        "id",
        "full_id",
        "title",
        "state",
        "surface_type",
        "route",
        "owners",
        "purpose",
        "user_stories",
        "functionalities",
        "external_dependencies",
        "page_object",
    }
    assert accounted["UnlinkedTest"] == {"id", "scenario_name", "us_id", "func_id", "ac_ids", "source"}
    assert accounted["StaleAcRef"] == {"scenario_id", "scenario_name", "us_id", "func_id", "stale_ac_id", "source"}
