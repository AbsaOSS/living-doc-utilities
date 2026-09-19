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
Tests for contracts.testing (docs/contracts.md, R12 check 3 and section 4): full_sample's
schema validity, exhaustive leaf-path occupancy, determinism and state-consistency, and
shown_paths against every row of the field-by-view table.
"""

import inspect
import json

import jsonschema
import pytest

from living_doc_utilities.contracts import (
    coverage_matrix,
    doc_entities,
    doc_source,
    generator_ready,
    schema_export,
    stats,
    testing,
    ui_test_catalog,
    ui_tests,
)

CONTRACTS = [
    (doc_entities.CONTRACT_ID, doc_entities.DocEntitiesResult, doc_entities.RECORD_ROOTS),
    (doc_source.CONTRACT_ID, doc_source.DocSourceResult, doc_source.RECORD_ROOTS),
    (ui_tests.CONTRACT_ID, ui_tests.UITestsResult, ui_tests.RECORD_ROOTS),
    (generator_ready.CONTRACT_ID, generator_ready.GeneratorReadyResult, generator_ready.RECORD_ROOTS),
    (coverage_matrix.CONTRACT_ID, coverage_matrix.CoverageMatrixResult, coverage_matrix.RECORD_ROOTS),
    (ui_test_catalog.CONTRACT_ID, ui_test_catalog.UiTestCatalogResult, ui_test_catalog.RECORD_ROOTS),
]
CONTRACT_IDS = [contract_id for contract_id, _, _ in CONTRACTS]


# ---------------------------------------------------------------------------
# full_sample: schema validity, exhaustive occupancy, determinism, no `view` parameter.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("contract_id, model, _record_roots", CONTRACTS, ids=CONTRACT_IDS)
def test_full_sample_is_the_right_model_and_validates_against_the_committed_schema(contract_id, model, _record_roots):
    sample = testing.full_sample(contract_id)

    assert isinstance(sample, model)
    data = json.loads(sample.model_dump_json())
    jsonschema.validate(instance=data, schema=schema_export.load_schema(contract_id))


@pytest.mark.parametrize("contract_id, _model, record_roots", CONTRACTS, ids=CONTRACT_IDS)
def test_full_sample_has_non_zero_occupancy_for_every_leaf_path(contract_id, _model, record_roots):
    sample = testing.full_sample(contract_id)

    computed = stats.compute_stats(sample, record_roots, sample.metadata.stats.cardinality)
    expected_paths = schema_export.field_occupancy_paths(record_roots)

    zero_or_missing = [path for path in expected_paths if computed.field_occupancy.get(path, 0) == 0]
    assert zero_or_missing == [], f"{contract_id}: leaf path(s) with no occupancy in full_sample: {zero_or_missing}"


@pytest.mark.parametrize("contract_id", CONTRACT_IDS)
def test_full_sample_is_deterministic(contract_id):
    assert testing.full_sample(contract_id) == testing.full_sample(contract_id)


def test_full_sample_rejects_an_unknown_contract_id():
    with pytest.raises(ValueError, match="unknown contract id"):
        testing.full_sample("not-a-real-contract-v1.0.0")


def test_full_sample_takes_no_view_parameter():
    assert "view" not in inspect.signature(testing.full_sample).parameters


# ---------------------------------------------------------------------------
# State-consistency: no record carries a field its own state makes meaningless.
# ---------------------------------------------------------------------------


def _every_entity_across_full_samples():
    entities = list(testing.full_sample(doc_entities.CONTRACT_ID).entities)

    doc_source_sample = testing.full_sample(doc_source.CONTRACT_ID)
    entities += doc_source_sample.user_stories
    entities += doc_source_sample.features
    entities += doc_source_sample.functionalities

    entities += testing.full_sample(generator_ready.CONTRACT_ID).content.entities
    return entities


def test_no_deprecated_only_field_is_populated_on_a_non_deprecated_entity():
    for entity in _every_entity_across_full_samples():
        if entity.state != "deprecated":
            assert entity.deprecated_at is None, entity.entity_id
            assert entity.deprecation_reason is None, entity.entity_id
            assert entity.superseded_by is None, entity.entity_id


def test_at_least_one_deprecated_entity_actually_carries_its_deprecation_fields():
    # The check above would pass vacuously if full_sample never included a deprecated entity
    # at all - this asserts the deprecated case is actually present.
    deprecated = [entity for entity in _every_entity_across_full_samples() if entity.state == "deprecated"]

    assert deprecated
    assert all(entity.deprecated_at is not None for entity in deprecated)
    assert all(entity.deprecation_reason is not None for entity in deprecated)


def test_no_acceptance_criterion_outside_planned_is_version_less():
    for entity in _every_entity_across_full_samples():
        for ac in entity.acceptance_criteria:
            if ac.state != "planned":
                assert ac.version is not None, ac.id


def test_full_sample_includes_a_targeted_and_a_backlog_planned_acceptance_criterion():
    planned = [
        ac
        for entity in _every_entity_across_full_samples()
        for ac in entity.acceptance_criteria
        if ac.state == "planned"
    ]

    assert any(ac.version is not None for ac in planned), "expected a targeted planned AC"
    assert any(ac.version is None for ac in planned), "expected a backlog planned AC"


# ---------------------------------------------------------------------------
# shown_paths: every row of docs/contracts.md section 4, for both views.
# ---------------------------------------------------------------------------

_CID = generator_ready.CONTRACT_ID
_INNER = "inner"
_RELEASE = "release"


def test_shown_paths_shows_derived_feature_state_in_both_views():
    assert "content.entities[].state" in testing.shown_paths(_CID, _INNER)
    assert "content.entities[].state" in testing.shown_paths(_CID, _RELEASE)


def test_shown_paths_shows_feature_stub_reason_in_inner_only():
    assert "content.entities[].stub_reason" in testing.shown_paths(_CID, _INNER)
    assert "content.entities[].stub_reason" not in testing.shown_paths(_CID, _RELEASE)


def test_shown_paths_shows_entity_not_in_scope_and_preconditions_in_both_views():
    for view in (_INNER, _RELEASE):
        shown = testing.shown_paths(_CID, view)
        assert "content.entities[].not_in_scope[]" in shown
        assert "content.entities[].preconditions[]" in shown


def test_shown_paths_shows_ac_level_not_in_scope_and_preconditions_in_both_views():
    for view in (_INNER, _RELEASE):
        shown = testing.shown_paths(_CID, view)
        assert "content.entities[].acceptance_criteria[].not_in_scope[]" in shown
        assert "content.entities[].acceptance_criteria[].preconditions[]" in shown


def test_shown_paths_shows_deprecation_date_and_reason_in_inner_only():
    for path in ("content.entities[].deprecated_at", "content.entities[].deprecation_reason"):
        assert path in testing.shown_paths(_CID, _INNER)
        assert path not in testing.shown_paths(_CID, _RELEASE)


def test_shown_paths_shows_removal_planned_in_both_views():
    for view in (_INNER, _RELEASE):
        assert "content.entities[].acceptance_criteria[].removal_planned" in testing.shown_paths(_CID, view)


def test_shown_paths_shows_ac_header_and_deprecated_badge_state_and_version_in_both_views():
    for view in (_INNER, _RELEASE):
        shown = testing.shown_paths(_CID, view)
        assert "content.entities[].acceptance_criteria[].state" in shown
        assert "content.entities[].acceptance_criteria[].version" in shown


def test_shown_paths_shows_a_planned_ac_only_as_a_record_the_release_filter_drops():
    # "planned vX.Y.Z" / "backlog" are inner-only because release drops planned ACs as records (a
    # transform's job), not because a path is hidden; the label is rendered from state + version.
    planned = [ac for entity in testing.full_sample(_CID).content.entities for ac in entity.acceptance_criteria]
    assert any(ac.state == "planned" and ac.version is not None for ac in planned)
    assert any(ac.state == "planned" and ac.version is None for ac in planned)
    assert "content.entities[].acceptance_criteria[].version" in testing.shown_paths(_CID, _INNER)


def test_shown_paths_shows_ac_aspect_in_both_views():
    for view in (_INNER, _RELEASE):
        assert "content.entities[].acceptance_criteria[].aspect[]" in testing.shown_paths(_CID, view)


def test_shown_paths_shows_ac_rationale_placeholder_values_and_functionality_rationale_in_both_views():
    for view in (_INNER, _RELEASE):
        shown = testing.shown_paths(_CID, view)
        assert "content.entities[].acceptance_criteria[].rationale" in shown
        assert "content.entities[].acceptance_criteria[].placeholder_values" in shown
        assert "content.entities[].rationale" in shown


def test_shown_paths_shows_source_ref_area_path_and_iteration_path_in_inner_only():
    for path in ("content.entities[].source_ref.area_path", "content.entities[].source_ref.iteration_path"):
        assert path in testing.shown_paths(_CID, _INNER)
        assert path not in testing.shown_paths(_CID, _RELEASE)


def test_shown_paths_hides_source_ref_native_type_and_tracker_state_in_both_views():
    for view in (_INNER, _RELEASE):
        shown = testing.shown_paths(_CID, view)
        assert "content.entities[].source_ref.native_type" not in shown
        assert "content.entities[].source_ref.tracker_state" not in shown


def test_shown_paths_rejects_an_unsupported_contract():
    with pytest.raises(ValueError, match="only supports"):
        testing.shown_paths(doc_entities.CONTRACT_ID, _INNER)


def test_shown_paths_coverage_matrix_shows_aspect_breakdown_in_both_views_and_planned_summary_in_inner_only():
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
    for view in (_INNER, _RELEASE):
        assert testing.shown_paths(ui_test_catalog.CONTRACT_ID, view) == set()


def test_shown_paths_rejects_an_unknown_view():
    with pytest.raises(ValueError, match="view"):
        testing.shown_paths(_CID, "somewhere-else")
