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
