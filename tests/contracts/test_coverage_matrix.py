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
    COUNTED_STATES,
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
        "metadata": factories.metadata(),
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


def test_document_carries_only_the_view():
    assert set(Document.model_fields) == {"view"}


def test_counted_states_are_exactly_active_and_deprecated():
    assert COUNTED_STATES == {"active", "deprecated"}
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


def test_planned_summary_models_total_backlog_and_by_target_version():
    summary = factories.planned_summary(total=5, backlog=2, by_target_version={"1.5.0": 2, "1.6.0": 1})

    assert summary.total == 5
    assert summary.backlog == 2
    assert summary.by_target_version == {"1.5.0": 2, "1.6.0": 1}


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
