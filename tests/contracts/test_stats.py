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
Tests for stats.compute_stats (docs/contracts.md, R11): metadata.stats.cardinality and
.field_occupancy, computed fresh from a contract result's own record roots.
"""

from living_doc_utilities.contracts import stats
from living_doc_utilities.contracts.coverage_matrix import RECORD_ROOTS as COVERAGE_MATRIX_ROOTS
from living_doc_utilities.contracts.coverage_matrix import CoverageMatrixResult
from living_doc_utilities.contracts.doc_entities import RECORD_ROOTS as DOC_ENTITIES_ROOTS
from living_doc_utilities.contracts.doc_entities import DocEntitiesResult
from living_doc_utilities.contracts.doc_source import RECORD_ROOTS as DOC_SOURCE_ROOTS
from living_doc_utilities.contracts.doc_source import DocSourceResult
from living_doc_utilities.contracts.envelope import Cardinality, ContractWarning
from living_doc_utilities.contracts.generator_ready import RECORD_ROOTS as GENERATOR_READY_ROOTS
from living_doc_utilities.contracts.generator_ready import Content, GeneratorReadyResult
from living_doc_utilities.contracts.ui_test_catalog import RECORD_ROOTS as UI_TEST_CATALOG_ROOTS
from living_doc_utilities.contracts.ui_test_catalog import UiTestCatalogResult
from living_doc_utilities.contracts.ui_tests import RECORD_ROOTS as UI_TESTS_ROOTS
from living_doc_utilities.contracts.ui_tests import UITestsResult
from tests.contracts import factories

_ALL_CARDINALITY_KEYS = {
    "entities",
    "entities_by_type",
    "acceptance_criteria",
    "scenarios",
    "warnings_by_code",
    "sources_configured",
    "sources_failed",
    "unresolved_refs",
    "entities_skipped",
}


# ---------------------------------------------------------------------------
# _is_empty rules: None, "", [], {} are empty; a present value, and 0/False, are not.
# ---------------------------------------------------------------------------


def test_empty_value_variants_are_not_counted_in_field_occupancy():
    story = factories.user_story(
        entity_id="US-001",
        narrative="",  # empty string
        not_in_scope=[],  # empty list
        acceptance_criteria=[
            factories.acceptance_criterion(parent_id="US-001", placeholder_values={})  # empty dict
        ],
    )
    result = DocEntitiesResult(metadata=factories.metadata(), entities=[story])

    computed = stats.compute_stats(result, DOC_ENTITIES_ROOTS, Cardinality())

    assert computed.field_occupancy["entities[].narrative"] == 0
    assert computed.field_occupancy["entities[].not_in_scope[]"] == 0
    assert computed.field_occupancy["entities[].acceptance_criteria[].placeholder_values"] == 0


def test_non_empty_value_variants_are_counted_in_field_occupancy():
    story = factories.user_story(
        entity_id="US-001",
        narrative="As a user...",
        not_in_scope=["out of scope item"],
        acceptance_criteria=[
            factories.acceptance_criterion(parent_id="US-001", placeholder_values={"user_role": ["admin"]})
        ],
    )
    result = DocEntitiesResult(metadata=factories.metadata(), entities=[story])

    computed = stats.compute_stats(result, DOC_ENTITIES_ROOTS, Cardinality())

    assert computed.field_occupancy["entities[].narrative"] == 1
    assert computed.field_occupancy["entities[].not_in_scope[]"] == 1
    assert computed.field_occupancy["entities[].acceptance_criteria[].placeholder_values"] == 1


def test_boolean_false_is_not_miscounted_as_empty():
    # PageRef.is_primary is a bool defaulting to False - _is_empty must not treat a false-y,
    # present value the same as an actually-absent one.
    primary = factories.page_ref(is_primary=True)
    secondary = factories.page_ref(is_primary=False, route="/other", page_object="Other.ts")
    feature = factories.feature(entity_id="FEAT-001", pages=[primary, secondary])
    result = DocEntitiesResult(metadata=factories.metadata(), entities=[feature])

    computed = stats.compute_stats(result, DOC_ENTITIES_ROOTS, Cardinality())

    # Both pages carry an explicit is_primary value (True and False alike), so both count.
    assert computed.field_occupancy["entities[].pages[].is_primary"] == 2


# ---------------------------------------------------------------------------
# entity-level not_in_scope vs AC-level not_in_scope: distinct, independently counted keys.
# ---------------------------------------------------------------------------


def test_entity_level_and_ac_level_not_in_scope_are_distinct_keys():
    story = factories.user_story(
        entity_id="US-001",
        not_in_scope=["entity-level exclusion"],
        acceptance_criteria=[
            factories.acceptance_criterion(parent_id="US-001", seq=1, not_in_scope=["ac-level exclusion"]),
            factories.acceptance_criterion(parent_id="US-001", seq=2, not_in_scope=[]),
        ],
    )
    result = DocEntitiesResult(metadata=factories.metadata(), entities=[story])

    computed = stats.compute_stats(result, DOC_ENTITIES_ROOTS, Cardinality())

    assert "entities[].not_in_scope[]" in computed.field_occupancy
    assert "entities[].acceptance_criteria[].not_in_scope[]" in computed.field_occupancy
    assert computed.field_occupancy["entities[].not_in_scope[]"] == 1
    # Only one of the two ACs carries a non-empty not_in_scope.
    assert computed.field_occupancy["entities[].acceptance_criteria[].not_in_scope[]"] == 1


# ---------------------------------------------------------------------------
# Every contract's record roots produce paths with the correct prefix.
# ---------------------------------------------------------------------------


def test_doc_entities_field_occupancy_uses_the_entities_prefix():
    result = DocEntitiesResult(metadata=factories.metadata(), entities=[factories.user_story()])

    computed = stats.compute_stats(result, DOC_ENTITIES_ROOTS, Cardinality())

    assert all(path.startswith("entities[].") for path in computed.field_occupancy)


def test_doc_source_field_occupancy_uses_the_three_named_prefixes():
    result = DocSourceResult(
        metadata=factories.metadata(),
        user_stories=[factories.user_story()],
        features=[factories.feature()],
        functionalities=[factories.functionality()],
    )

    computed = stats.compute_stats(result, DOC_SOURCE_ROOTS, Cardinality())

    prefixes = {path.split("[]")[0] for path in computed.field_occupancy}
    assert prefixes == {"user_stories", "features", "functionalities"}


def test_generator_ready_field_occupancy_uses_the_content_entities_prefix():
    result = GeneratorReadyResult(
        metadata=factories.transform_metadata(),
        document=factories.generator_ready_document(),
        content=Content(entities=[factories.user_story()]),
    )

    computed = stats.compute_stats(result, GENERATOR_READY_ROOTS, Cardinality())

    assert all(path.startswith("content.entities[].") for path in computed.field_occupancy)


def test_ui_tests_field_occupancy_uses_the_scenarios_prefix():
    result = UITestsResult(metadata=factories.metadata(), scenarios=[factories.scenario()])

    computed = stats.compute_stats(result, UI_TESTS_ROOTS, Cardinality())

    assert all(path.startswith("scenarios[].") for path in computed.field_occupancy)


def test_coverage_matrix_field_occupancy_uses_the_entities_prefix():
    result = CoverageMatrixResult(
        metadata=factories.transform_metadata(),
        document=factories.coverage_matrix_document(),
        entities=[factories.entity_coverage()],
        planned_summary=factories.planned_summary(),
    )

    computed = stats.compute_stats(result, COVERAGE_MATRIX_ROOTS, Cardinality())

    assert all(path.startswith("entities[].") for path in computed.field_occupancy)


def test_ui_test_catalog_field_occupancy_uses_the_feature_files_prefix():
    result = UiTestCatalogResult(
        metadata=factories.transform_metadata(),
        document=factories.ui_test_catalog_document(),
        feature_files=[factories.feature_file_catalog()],
    )

    computed = stats.compute_stats(result, UI_TEST_CATALOG_ROOTS, Cardinality())

    assert all(path.startswith("feature_files[].") for path in computed.field_occupancy)


# ---------------------------------------------------------------------------
# Every Cardinality key is always present, even at zero/empty.
# ---------------------------------------------------------------------------


def test_every_cardinality_key_is_always_present_even_when_not_applicable():
    # ui-tests' record root is Scenario, which has neither entity_id nor type, so the
    # entity-shaped counters stay at their zero/empty default rather than being omitted.
    result = UITestsResult(metadata=factories.metadata(), scenarios=[factories.scenario()])

    computed = stats.compute_stats(result, UI_TESTS_ROOTS, Cardinality())
    dumped = computed.model_dump()["cardinality"]

    assert set(dumped.keys()) == _ALL_CARDINALITY_KEYS
    assert dumped["entities"] == 0
    assert dumped["entities_by_type"] == {}
    assert dumped["scenarios"] == 1


# ---------------------------------------------------------------------------
# cardinality.entities / entities_by_type, .acceptance_criteria, .scenarios tallies.
# ---------------------------------------------------------------------------


def test_cardinality_entities_and_entities_by_type_are_tallied_for_doc_entities():
    result = DocEntitiesResult(
        metadata=factories.metadata(), entities=[factories.user_story(), factories.feature(), factories.functionality()]
    )

    computed = stats.compute_stats(result, DOC_ENTITIES_ROOTS, Cardinality())

    assert computed.cardinality.entities == 3
    assert computed.cardinality.entities_by_type == {
        "DocumentedUserStory": 1,
        "DocumentedFeature": 1,
        "DocumentedFunctionality": 1,
    }


def test_cardinality_entities_and_entities_by_type_are_tallied_for_coverage_matrix_entity_coverage():
    result = CoverageMatrixResult(
        metadata=factories.transform_metadata(),
        document=factories.coverage_matrix_document(),
        entities=[factories.entity_coverage(entity_id="US-001"), factories.entity_coverage(entity_id="US-002")],
        planned_summary=factories.planned_summary(),
    )

    computed = stats.compute_stats(result, COVERAGE_MATRIX_ROOTS, Cardinality())

    assert computed.cardinality.entities == 2
    assert computed.cardinality.entities_by_type == {"DocumentedUserStory": 2}


def test_cardinality_acceptance_criteria_tallies_acceptance_criterion_lists():
    story = factories.user_story(
        entity_id="US-001",
        acceptance_criteria=[
            factories.acceptance_criterion(parent_id="US-001", seq=1),
            factories.acceptance_criterion(parent_id="US-001", seq=2),
        ],
    )
    result = DocEntitiesResult(metadata=factories.metadata(), entities=[story])

    computed = stats.compute_stats(result, DOC_ENTITIES_ROOTS, Cardinality())

    assert computed.cardinality.acceptance_criteria == 2


def test_cardinality_acceptance_criteria_tallies_ac_coverage_lists():
    entity = factories.entity_coverage(
        entity_id="US-001",
        acceptance_criteria=[
            factories.ac_coverage(parent_id="US-001", seq=1),
            factories.ac_coverage(parent_id="US-001", seq=2),
        ],
    )
    result = CoverageMatrixResult(
        metadata=factories.transform_metadata(),
        document=factories.coverage_matrix_document(),
        entities=[entity],
        planned_summary=factories.planned_summary(),
    )

    computed = stats.compute_stats(result, COVERAGE_MATRIX_ROOTS, Cardinality())

    assert computed.cardinality.acceptance_criteria == 2


def test_cardinality_scenarios_tallies_top_level_scenarios_for_ui_tests():
    result = UITestsResult(metadata=factories.metadata(), scenarios=[factories.scenario("SCN-001"), factories.scenario("SCN-002")])

    computed = stats.compute_stats(result, UI_TESTS_ROOTS, Cardinality())

    assert computed.cardinality.scenarios == 2


def test_cardinality_scenarios_tallies_deeply_nested_scenarios_for_ui_test_catalog():
    feature_file = factories.feature_file_catalog(
        linked_to_user_story=[
            factories.linked_scenarios(entity_id="US-001", scenarios=[factories.scenario("SCN-001"), factories.scenario("SCN-002")])
        ],
        linked_to_functionality=[
            factories.linked_scenarios(entity_id="FUNC-001", scenarios=[factories.scenario("SCN-003")])
        ],
        unlinked=[factories.scenario("SCN-004")],
    )
    result = UiTestCatalogResult(
        metadata=factories.transform_metadata(), document=factories.ui_test_catalog_document(), feature_files=[feature_file]
    )

    computed = stats.compute_stats(result, UI_TEST_CATALOG_ROOTS, Cardinality())

    assert computed.cardinality.scenarios == 4


# ---------------------------------------------------------------------------
# cardinality.warnings_by_code
# ---------------------------------------------------------------------------


def test_cardinality_warnings_by_code_counts_each_code_from_the_warnings_array():
    result = DocEntitiesResult(
        metadata=factories.metadata(),
        entities=[factories.user_story()],
        warnings=[
            ContractWarning(code="MISSING_STATUS", message="m1"),
            ContractWarning(code="MISSING_STATUS", message="m2"),
            ContractWarning(code="ORPHAN_FEATURE", message="m3"),
        ],
    )

    computed = stats.compute_stats(result, DOC_ENTITIES_ROOTS, Cardinality())

    assert computed.cardinality.warnings_by_code == {"MISSING_STATUS": 2, "ORPHAN_FEATURE": 1}


# ---------------------------------------------------------------------------
# The four passthrough fields are copied verbatim from `reported`, never recomputed.
# ---------------------------------------------------------------------------


def test_passthrough_cardinality_fields_come_from_reported_unchanged():
    result = DocEntitiesResult(metadata=factories.metadata(), entities=[factories.user_story()])
    reported = Cardinality(sources_configured=7, sources_failed=3, unresolved_refs=5, entities_skipped=9)

    computed = stats.compute_stats(result, DOC_ENTITIES_ROOTS, reported)

    assert computed.cardinality.sources_configured == 7
    assert computed.cardinality.sources_failed == 3
    assert computed.cardinality.unresolved_refs == 5
    assert computed.cardinality.entities_skipped == 9


def test_passthrough_cardinality_fields_default_to_zero_when_reported_is_default():
    result = DocEntitiesResult(metadata=factories.metadata(), entities=[factories.user_story()])

    computed = stats.compute_stats(result, DOC_ENTITIES_ROOTS, Cardinality())

    assert computed.cardinality.sources_configured == 0
    assert computed.cardinality.sources_failed == 0
    assert computed.cardinality.unresolved_refs == 0
    assert computed.cardinality.entities_skipped == 0
