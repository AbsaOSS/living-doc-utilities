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

"""`testing.py` (R12 check 3): `full_sample` validity and occupancy, and `shown_paths` per field-by-view row."""

import inspect
import json
from dataclasses import dataclass

import jsonschema
import pytest

from living_doc_utilities.contracts import (
    coverage_matrix,
    doc_entities,
    doc_source,
    generator_ready,
    registry,
    schema_export,
    stats,
    testing,
    ui_test_catalog,
)

CONTRACTS = [(contract_id, spec.result_model, spec.record_roots) for contract_id, spec in registry.CONTRACTS.items()]
CONTRACT_IDS = [contract_id for contract_id, _, _ in CONTRACTS]


# ---------------------------------------------------------------------------
# full_sample: schema validity, exhaustive occupancy, determinism, no `view` parameter.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("contract_id, model, _record_roots", CONTRACTS, ids=CONTRACT_IDS)
def test_full_sample_is_the_right_model_and_validates_against_the_committed_schema(contract_id, model, _record_roots):
    """full_sample returns an instance of the contract's own result model, valid against its committed schema."""
    sample = testing.full_sample(contract_id)

    assert isinstance(sample, model)
    data = json.loads(sample.model_dump_json())
    jsonschema.validate(instance=data, schema=schema_export.load_schema(contract_id))


@pytest.mark.parametrize("contract_id, _model, record_roots", CONTRACTS, ids=CONTRACT_IDS)
def test_full_sample_has_non_zero_occupancy_for_every_leaf_path(contract_id, _model, record_roots):
    """Every leaf path of the contract's schema is actually populated in full_sample, none left empty."""
    sample = testing.full_sample(contract_id)

    computed = stats.compute_stats(sample, record_roots, sample.metadata.stats.cardinality)
    expected_paths = schema_export.field_occupancy_paths(record_roots)

    zero_or_missing = [path for path in expected_paths if computed.field_occupancy.get(path, 0) == 0]
    assert zero_or_missing == [], f"{contract_id}: leaf path(s) with no occupancy in full_sample: {zero_or_missing}"


@pytest.mark.parametrize("contract_id", CONTRACT_IDS)
def test_full_sample_is_deterministic(contract_id):
    """`testing.py::full_sample` returns an equal result across repeated calls for the same contract."""
    assert testing.full_sample(contract_id) == testing.full_sample(contract_id)


def test_full_sample_rejects_an_unknown_contract_id():
    """`testing.py::full_sample` raises for a contract id that isn't registered."""
    with pytest.raises(ValueError, match="unknown contract id"):
        testing.full_sample("not-a-real-contract-v1.0.0")


def test_full_sample_takes_no_view_parameter():
    """`testing.py::full_sample`'s signature has no 'view' parameter."""
    assert "view" not in inspect.signature(testing.full_sample).parameters


# ---------------------------------------------------------------------------
# State-consistency: no record carries a field its own state makes meaningless.
# ---------------------------------------------------------------------------


def _entities_by_contract():
    doc_source_sample = testing.full_sample(doc_source.CONTRACT_ID)
    return {
        doc_entities.CONTRACT_ID: list(testing.full_sample(doc_entities.CONTRACT_ID).entities),
        doc_source.CONTRACT_ID: [
            *doc_source_sample.user_stories,
            *doc_source_sample.features,
            *doc_source_sample.functionalities,
        ],
        generator_ready.CONTRACT_ID: list(testing.full_sample(generator_ready.CONTRACT_ID).content.entities),
    }


def _every_entity_across_full_samples():
    return [entity for entities in _entities_by_contract().values() for entity in entities]


def test_no_deprecated_only_field_is_populated_on_a_non_deprecated_entity():
    """deprecated_at, deprecation_reason and superseded_by stay unset on every non-deprecated entity."""
    for entity in _every_entity_across_full_samples():
        if entity.state != "deprecated":
            assert entity.deprecated_at is None, entity.entity_id
            assert entity.deprecation_reason is None, entity.entity_id
            assert entity.superseded_by is None, entity.entity_id


def test_at_least_one_deprecated_entity_actually_carries_its_deprecation_fields():
    """full_sample actually includes a deprecated entity, and it has its deprecation fields populated."""
    # Guards the check above from passing vacuously when full_sample has no deprecated entity.
    deprecated = [entity for entity in _every_entity_across_full_samples() if entity.state == "deprecated"]

    assert deprecated
    assert all(entity.deprecated_at is not None for entity in deprecated)
    assert all(entity.deprecation_reason is not None for entity in deprecated)


def test_no_acceptance_criterion_outside_planned_is_version_less():
    """Every acceptance criterion not in the 'planned' state carries a version."""
    for entity in _every_entity_across_full_samples():
        for ac in entity.acceptance_criteria:
            if ac.state != "planned":
                assert ac.version is not None, ac.id


def test_full_sample_includes_a_targeted_and_a_backlog_planned_acceptance_criterion():
    """Each entity-carrying full_sample includes both a version-targeted and a version-less (backlog) planned AC."""
    for contract_id, entities in _entities_by_contract().items():
        planned = [ac for entity in entities for ac in entity.acceptance_criteria if ac.state == "planned"]

        assert any(ac.version is not None for ac in planned), f"{contract_id}: expected a targeted planned AC"
        assert any(ac.version is None for ac in planned), f"{contract_id}: expected a backlog planned AC"


# ---------------------------------------------------------------------------
# shown_paths: every row of testing.py's field-by-view table, for both views.
# ---------------------------------------------------------------------------

_CID = generator_ready.CONTRACT_ID
_INNER = "inner"
_RELEASE = "release"


@dataclass(frozen=True)
class ShownPathCase:
    """One row of the field-by-view rendering table (`testing.py::shown_paths`), for one view."""

    row: str
    view: str
    shown: tuple[str, ...] = ()
    hidden: tuple[str, ...] = ()


SHOWN_PATH_CASES = [
    ShownPathCase("entity_state", _INNER, shown=("content.entities[].state",)),
    ShownPathCase("entity_state", _RELEASE, shown=("content.entities[].state",)),
    ShownPathCase("feature_stub_reason", _INNER, shown=("content.entities[].stub_reason",)),
    ShownPathCase("feature_stub_reason", _RELEASE, hidden=("content.entities[].stub_reason",)),
    ShownPathCase(
        "entity_not_in_scope_and_preconditions",
        _INNER,
        shown=("content.entities[].not_in_scope[]", "content.entities[].preconditions[]"),
    ),
    ShownPathCase(
        "entity_not_in_scope_and_preconditions",
        _RELEASE,
        shown=("content.entities[].not_in_scope[]", "content.entities[].preconditions[]"),
    ),
    ShownPathCase(
        "ac_not_in_scope_and_preconditions",
        _INNER,
        shown=(
            "content.entities[].acceptance_criteria[].not_in_scope[]",
            "content.entities[].acceptance_criteria[].preconditions[]",
        ),
    ),
    ShownPathCase(
        "ac_not_in_scope_and_preconditions",
        _RELEASE,
        shown=(
            "content.entities[].acceptance_criteria[].not_in_scope[]",
            "content.entities[].acceptance_criteria[].preconditions[]",
        ),
    ),
    ShownPathCase(
        "deprecation_date_and_reason",
        _INNER,
        shown=("content.entities[].deprecated_at", "content.entities[].deprecation_reason"),
    ),
    ShownPathCase(
        "deprecation_date_and_reason",
        _RELEASE,
        hidden=("content.entities[].deprecated_at", "content.entities[].deprecation_reason"),
    ),
    ShownPathCase("ac_removal_planned", _INNER, shown=("content.entities[].acceptance_criteria[].removal_planned",)),
    ShownPathCase(
        "ac_removal_planned", _RELEASE, shown=("content.entities[].acceptance_criteria[].removal_planned",)
    ),
    ShownPathCase(
        "ac_header_state_and_version",
        _INNER,
        shown=(
            "content.entities[].acceptance_criteria[].state",
            "content.entities[].acceptance_criteria[].version",
        ),
    ),
    ShownPathCase(
        "ac_header_state_and_version",
        _RELEASE,
        shown=(
            "content.entities[].acceptance_criteria[].state",
            "content.entities[].acceptance_criteria[].version",
        ),
    ),
    # Planned labels render from state + version, so these rows repeat the header row; release drops them as records.
    ShownPathCase(
        "ac_planned_with_target_version",
        _INNER,
        shown=(
            "content.entities[].acceptance_criteria[].state",
            "content.entities[].acceptance_criteria[].version",
        ),
    ),
    ShownPathCase(
        "ac_planned_without_version",
        _INNER,
        shown=(
            "content.entities[].acceptance_criteria[].state",
            "content.entities[].acceptance_criteria[].version",
        ),
    ),
    ShownPathCase("ac_aspect", _INNER, shown=("content.entities[].acceptance_criteria[].aspect[]",)),
    ShownPathCase("ac_aspect", _RELEASE, shown=("content.entities[].acceptance_criteria[].aspect[]",)),
    ShownPathCase(
        "ac_and_functionality_rationale",
        _INNER,
        shown=(
            "content.entities[].acceptance_criteria[].rationale",
            "content.entities[].acceptance_criteria[].placeholder_values",
            "content.entities[].rationale",
        ),
    ),
    ShownPathCase(
        "ac_and_functionality_rationale",
        _RELEASE,
        shown=(
            "content.entities[].acceptance_criteria[].rationale",
            "content.entities[].acceptance_criteria[].placeholder_values",
            "content.entities[].rationale",
        ),
    ),
    ShownPathCase(
        "source_ref_area_and_iteration_path",
        _INNER,
        shown=("content.entities[].source_ref.area_path", "content.entities[].source_ref.iteration_path"),
    ),
    ShownPathCase(
        "source_ref_area_and_iteration_path",
        _RELEASE,
        hidden=("content.entities[].source_ref.area_path", "content.entities[].source_ref.iteration_path"),
    ),
    ShownPathCase(
        "source_ref_native_type_and_tracker_state",
        _INNER,
        hidden=("content.entities[].source_ref.native_type", "content.entities[].source_ref.tracker_state"),
    ),
    ShownPathCase(
        "source_ref_native_type_and_tracker_state",
        _RELEASE,
        hidden=("content.entities[].source_ref.native_type", "content.entities[].source_ref.tracker_state"),
    ),
]


@pytest.mark.parametrize("case", SHOWN_PATH_CASES, ids=[f"{c.row}[{c.view}]" for c in SHOWN_PATH_CASES])
def test_shown_paths_matches_the_rendering_table_row(case: ShownPathCase):
    """shown_paths shows/hides exactly the paths this table row says, per view."""
    shown = testing.shown_paths(_CID, case.view)

    for path in case.shown:
        assert path in shown, f"{case.row} ({case.view}): expected {path!r} shown"
    for path in case.hidden:
        assert path not in shown, f"{case.row} ({case.view}): expected {path!r} hidden"


def test_shown_paths_rejects_an_unsupported_contract():
    """`testing.py::shown_paths` raises for a contract id, such as doc-entities, that it doesn't support."""
    with pytest.raises(ValueError, match="only supports"):
        testing.shown_paths(doc_entities.CONTRACT_ID, _INNER)


def test_shown_paths_coverage_matrix_shows_aspect_breakdown_in_both_views_and_planned_summary_in_inner_only():
    """Coverage-matrix's aspect breakdown is shown in both views; planned_summary only in inner."""
    both = {
        "entities[].acceptance_criteria[].status",
        "entities[].acceptance_criteria[].aspects[].aspect",
        "entities[].acceptance_criteria[].aspects[].status",
    }
    planned_summary = {"planned_summary.total", "planned_summary.backlog", "planned_summary.by_target_version"}
    inner = testing.shown_paths(coverage_matrix.CONTRACT_ID, _INNER)
    release = testing.shown_paths(coverage_matrix.CONTRACT_ID, _RELEASE)

    assert both <= inner and both <= release
    assert planned_summary <= inner
    assert not planned_summary & release


def test_shown_paths_ui_test_catalog_has_no_view_dependent_rows():
    """ui-test-catalog's shown_paths returns an empty set for every view; it has no view-dependent rows."""
    for view in (_INNER, _RELEASE):
        assert testing.shown_paths(ui_test_catalog.CONTRACT_ID, view) == set()


def test_shown_paths_rejects_an_unknown_view():
    """`testing.py::shown_paths` raises for a view name that isn't 'inner' or 'release'."""
    with pytest.raises(ValueError, match="view"):
        testing.shown_paths(_CID, "somewhere-else")
