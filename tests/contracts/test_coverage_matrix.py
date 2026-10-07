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
Tests for the coverage-matrix-v1.0.0 contract (coverage_matrix.py).
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
    CoverageSummary,
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
    fields.setdefault("summary", factories.matrix_summary(fields["entities"]))
    return CoverageMatrixResult(**fields)


def test_round_trips_through_json():
    """A CoverageMatrixResult serializes to JSON and back into an equal model, schema_version intact."""
    result = _result()

    payload = json.loads(result.model_dump_json())

    assert payload["schema_version"] == CONTRACT_ID
    assert CoverageMatrixResult.model_validate(payload) == result


def test_schema_version_is_a_plain_const():
    """schema_version defaults to the fixed contract id string."""
    assert CoverageMatrixResult.model_fields["schema_version"].default == "coverage-matrix-v1.0.0"


def test_metadata_source_inputs_must_be_non_empty():
    """A CoverageMatrixResult's metadata rejects an empty source_inputs list."""
    # R7: a transform always has at least its documentation input.
    with pytest.raises(ValidationError, match="source_inputs must have at least one entry"):
        _result(metadata=factories.metadata())


def test_document_carries_only_the_view():
    """Document declares exactly one field, view."""
    assert set(Document.model_fields) == {"view"}


def test_counted_states_are_exactly_active_and_deprecated():
    """CountedState's literal values are exactly 'active' and 'deprecated'."""
    assert set(get_args(CountedState)) == {"active", "deprecated"}


def test_coverage_status_models_covered_partially_covered_and_not_covered():
    """CoverageStatus's literal values are exactly covered, partially_covered, and not_covered."""
    assert set(get_args(CoverageStatus)) == {"covered", "partially_covered", "not_covered"}


def test_ac_coverage_carries_a_per_aspect_breakdown():
    """An AcCoverage row preserves its aspects list, in order, alongside its overall status."""
    row = factories.ac_coverage(
        status="partially_covered",
        aspects=[factories.aspect_coverage(aspect="checkout", status="covered"), factories.aspect_coverage(aspect="refund", status="not_covered")],
    )

    assert row.status == "partially_covered"
    assert [a.aspect for a in row.aspects] == ["checkout", "refund"]


def test_ac_coverage_rejects_a_state_outside_the_counted_set():
    """An AcCoverage row with a state outside the counted set is rejected."""
    with pytest.raises(ValidationError):
        factories.ac_coverage(state="planned")


def test_ac_coverage_rejects_covered_status_with_a_not_covered_aspect():
    """An AcCoverage row can't be 'covered' while one of its aspects is 'not_covered'."""
    with pytest.raises(ValidationError, match="status must be 'partially_covered'"):
        factories.ac_coverage(
            status="covered",
            aspects=[factories.aspect_coverage(status="covered"), factories.aspect_coverage(status="not_covered")],
        )


def test_ac_coverage_rejects_partially_covered_status_with_no_aspects():
    """An AcCoverage row can't be 'partially_covered' with an empty aspects list."""
    with pytest.raises(ValidationError, match="cannot be 'partially_covered' when aspects is empty"):
        factories.ac_coverage(status="partially_covered", aspects=[])


def test_ac_coverage_rejects_not_covered_status_when_aspects_are_present():
    """An AcCoverage row can't be 'not_covered' while it still has covered aspects."""
    with pytest.raises(ValidationError, match="status must be 'covered'"):
        factories.ac_coverage(status="not_covered", aspects=[factories.aspect_coverage(status="covered")])


def test_ac_coverage_with_aspects_none_covered_is_not_covered():
    """`DEC-74`: an AcCoverage row whose aspects are all uncovered is 'not_covered', and 'partially_covered' is rejected."""
    aspects = [factories.aspect_coverage(aspect=name, status="not_covered") for name in ("a", "b", "c")]

    assert factories.ac_coverage(status="not_covered", aspects=aspects, scenario_ids=[]).status == "not_covered"
    with pytest.raises(ValidationError, match="status must be 'not_covered'"):
        factories.ac_coverage(status="partially_covered", aspects=aspects)


def test_ac_coverage_with_aspects_some_covered_is_partially_covered():
    """An AcCoverage row with one of three aspects covered is 'partially_covered', neither 'covered' nor 'not_covered'."""
    aspects = [
        factories.aspect_coverage(aspect="a", status="covered"),
        factories.aspect_coverage(aspect="b", status="not_covered"),
        factories.aspect_coverage(aspect="c", status="not_covered"),
    ]

    assert factories.ac_coverage(status="partially_covered", aspects=aspects).status == "partially_covered"
    for status in ("covered", "not_covered"):
        with pytest.raises(ValidationError, match="status must be 'partially_covered'"):
            factories.ac_coverage(status=status, aspects=aspects)


def test_ac_coverage_accepts_covered_status_when_every_aspect_is_covered():
    """An AcCoverage row is 'covered' when every one of its aspects is covered."""
    row = factories.ac_coverage(status="covered", aspects=[factories.aspect_coverage(status="covered")])

    assert row.status == "covered"


def test_ac_coverage_rejects_a_malformed_ac_id():
    """An AcCoverage row rejects an ac_id that doesn't match the canonical AC id pattern."""
    # AC_ID_PATTERN also applies here; the belongs-to-entity prefix check alone misses a malformed suffix.
    with pytest.raises(ValidationError):
        factories.ac_coverage(ac_id="US-001-anything")


def test_aspect_coverage_rejects_covered_status_with_no_linked_scenarios():
    """An AspectCoverage can't be 'covered' with no linked scenario_ids."""
    with pytest.raises(ValidationError, match="status must be 'not_covered'"):
        factories.aspect_coverage(status="covered", scenario_ids=[])


def test_aspect_coverage_rejects_not_covered_status_with_linked_scenarios():
    """An AspectCoverage can't be 'not_covered' while it still has linked scenario_ids."""
    with pytest.raises(ValidationError, match="status must be 'covered'"):
        factories.aspect_coverage(status="not_covered", scenario_ids=["SCN-001"])


def test_ac_coverage_without_aspects_rejects_covered_status_with_no_linked_scenarios():
    """An AcCoverage row with no aspects can't be 'covered' with no linked scenario_ids."""
    with pytest.raises(ValidationError, match="status must be 'not_covered'"):
        factories.ac_coverage(status="covered", aspects=[], scenario_ids=[])


def test_ac_coverage_without_aspects_rejects_not_covered_status_with_linked_scenarios():
    """An AcCoverage row with no aspects can't be 'not_covered' while scenario_ids are linked."""
    with pytest.raises(ValidationError, match="status must be 'covered'"):
        factories.ac_coverage(status="not_covered", aspects=[], scenario_ids=["SCN-001"])


def test_planned_summary_models_total_backlog_and_by_target_version():
    """A valid PlannedSummary preserves its total, backlog and per-target-version counts as given."""
    summary = factories.planned_summary(total=5, backlog=2, by_target_version={"1.5.0": 2, "1.6.0": 1})

    assert summary.total == 5
    assert summary.backlog == 2
    assert summary.by_target_version == {"1.5.0": 2, "1.6.0": 1}


def test_planned_summary_rejects_a_total_that_does_not_equal_backlog_plus_targeted():
    """A PlannedSummary rejects a total that doesn't equal backlog plus the targeted counts."""
    with pytest.raises(ValidationError, match="must equal backlog"):
        factories.planned_summary(total=1, backlog=1, by_target_version={"1.5.0": 2})


def test_by_target_version_keys_must_be_a_version_string():
    """PlannedSummary's by_target_version rejects a key that isn't a valid version string."""
    with pytest.raises(ValidationError):
        factories.planned_summary(by_target_version={"v1.5": 1})


def test_by_target_version_values_must_be_nonnegative():
    """PlannedSummary's by_target_version rejects a negative count value."""
    with pytest.raises(ValidationError):
        factories.planned_summary(by_target_version={"1.5.0": -1})


def test_entity_coverage_state_is_the_full_lifecycle_state_not_just_counted_states():
    """An EntityCoverage's own state can be any lifecycle value, independent of its ACs' counted states."""
    # Counting is decided per AC, never by the parent entity's state: an in_review story can own an active AC.
    row = factories.entity_coverage(state="in_review", acceptance_criteria=[factories.ac_coverage()])

    assert row.state == "in_review"
    assert row.acceptance_criteria[0].state == "active"


def test_acceptance_criterion_id_must_belong_to_its_entity():
    """An EntityCoverage rejects an AcCoverage row whose ac_id doesn't belong to that entity."""
    with pytest.raises(ValidationError, match="does not belong to entity"):
        _result(entities=[factories.entity_coverage(entity_id="US-001", acceptance_criteria=[factories.ac_coverage(parent_id="US-002")])])


# --- CoverageSummary (`DEC-74`) ------------------------------------------------------------------------------


def _rows(*statuses: str) -> list:
    """One row per status: 'covered' and 'not_covered' without aspects, 'partially_covered' as 1 of 3 aspects."""
    rows = []
    for seq, status in enumerate(statuses, start=1):
        if status == "partially_covered":
            aspects = [factories.aspect_coverage(aspect="a", status="covered")] + [
                factories.aspect_coverage(aspect=name, status="not_covered") for name in ("b", "c")
            ]
            rows.append(factories.ac_coverage(seq=seq, status=status, aspects=aspects))
        else:
            scenario_ids = ["SCN-001"] if status == "covered" else []
            rows.append(factories.ac_coverage(seq=seq, status=status, scenario_ids=scenario_ids))
    return rows


def test_summary_counts_each_status_and_weighs_a_partial_row_by_its_covered_aspects():
    """1 + 0 + 1/3 over three rows is 44.4: a partially_covered row weighs its covered/declared aspects."""
    summary = CoverageSummary.from_rows(_rows("covered", "not_covered", "partially_covered"))

    assert summary == CoverageSummary(
        counted_acs=3, covered_acs=1, partially_covered_acs=1, not_covered_acs=1, coverage_pct=44.4
    )


def test_summary_of_no_counted_row_has_no_percentage():
    """With no counted row the counts are 0 and coverage_pct is None, never 0 or 100."""
    assert CoverageSummary.from_rows([]) == CoverageSummary(
        counted_acs=0, covered_acs=0, partially_covered_acs=0, not_covered_acs=0, coverage_pct=None
    )


def test_summary_rounds_half_up_once_from_the_exact_fraction():
    """1 of 16 rows covered is exactly 6.25%, which rounds half up to 6.3 (a float `round` gives 6.2)."""
    summary = CoverageSummary.from_rows(_rows("covered", *["not_covered"] * 15))

    assert summary.coverage_pct == 6.3


def test_summary_counts_a_deprecated_row():
    """A deprecated row is counted like an active one."""
    summary = CoverageSummary.from_rows([factories.ac_coverage(state="deprecated", status="covered")])

    assert (summary.counted_acs, summary.covered_acs, summary.coverage_pct) == (1, 1, 100.0)


@pytest.mark.parametrize("owner", ["entity", "root"])
def test_summary_is_required_on_every_entity_and_on_the_matrix(owner):
    """An EntityCoverage and a CoverageMatrixResult without `summary` are rejected."""
    entity = factories.entity_coverage()
    if owner == "entity":
        data = entity.model_dump()
        del data["summary"]
        with pytest.raises(ValidationError, match="summary"):
            EntityCoverage.model_validate(data)
    else:
        data = _result(entities=[entity]).model_dump()
        del data["summary"]
        with pytest.raises(ValidationError, match="summary"):
            CoverageMatrixResult.model_validate(data)


@pytest.mark.parametrize(
    "field, value",
    [
        ("counted_acs", 4),
        ("covered_acs", 2),
        ("partially_covered_acs", 0),
        ("not_covered_acs", 0),
        ("coverage_pct", 44.5),
        ("coverage_pct", None),
    ],
)
def test_an_entity_summary_that_disagrees_with_its_rows_is_rejected(field, value):
    """Every summary field is recomputed from the entity's rows: a count or coverage_pct off by one step fails."""
    rows = _rows("covered", "not_covered", "partially_covered")
    summary = CoverageSummary.from_rows(rows).model_copy(update={field: value})

    with pytest.raises(ValidationError, match="summary of entity 'US-001' must equal"):
        factories.entity_coverage(acceptance_criteria=rows, summary=summary)


def test_the_matrix_summary_weighs_every_row_not_the_entity_percentages():
    """An entity with 1 covered row and one with 10 uncovered rows is 1/11 = 9.1%, not the 50.0 mean of 100 and 0."""
    small = factories.entity_coverage(entity_id="US-001", acceptance_criteria=_rows("covered"))
    large = factories.entity_coverage(
        entity_id="US-002",
        acceptance_criteria=[
            factories.ac_coverage(parent_id="US-002", seq=seq, status="not_covered", scenario_ids=[])
            for seq in range(1, 11)
        ],
    )
    result = _result(entities=[small, large])

    assert (small.summary.coverage_pct, large.summary.coverage_pct) == (100.0, 0.0)
    assert result.summary.coverage_pct == 9.1
    with pytest.raises(ValidationError, match="summary of the matrix must equal"):
        _result(entities=[small, large], summary=result.summary.model_copy(update={"coverage_pct": 50.0}))


@pytest.mark.parametrize("value", [-0.1, 100.1])
def test_coverage_pct_is_bounded_to_a_percentage(value):
    """coverage_pct outside 0-100 is rejected by its own field bounds."""
    with pytest.raises(ValidationError):
        CoverageSummary(counted_acs=1, covered_acs=1, partially_covered_acs=0, not_covered_acs=0, coverage_pct=value)


def test_record_root_is_entities():
    """RECORD_ROOTS maps the 'entities' array key to EntityCoverage."""
    assert RECORD_ROOTS == {"entities": EntityCoverage}
