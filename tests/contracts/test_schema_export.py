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
import json
import re
from pathlib import Path
from typing import Union

import jsonschema
import pytest
from pydantic import ValidationError

from living_doc_utilities.contracts import (
    coverage_matrix,
    doc_entities,
    doc_source,
    generator_ready,
    schema_export,
    ui_test_catalog,
    ui_tests,
)
from living_doc_utilities.contracts.envelope import AUDIT_FIELD_PATH_PATTERN
from tests.contracts import factories

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMAS_DIR = REPO_ROOT / "living_doc_utilities" / "contracts" / "schemas"

CONTRACTS = [
    (doc_entities.CONTRACT_ID, doc_entities.DocEntitiesResult, doc_entities.RECORD_ROOTS),
    (doc_source.CONTRACT_ID, doc_source.DocSourceResult, doc_source.RECORD_ROOTS),
    (ui_tests.CONTRACT_ID, ui_tests.UITestsResult, ui_tests.RECORD_ROOTS),
    (generator_ready.CONTRACT_ID, generator_ready.GeneratorReadyResult, generator_ready.RECORD_ROOTS),
    (coverage_matrix.CONTRACT_ID, coverage_matrix.CoverageMatrixResult, coverage_matrix.RECORD_ROOTS),
    (ui_test_catalog.CONTRACT_ID, ui_test_catalog.UiTestCatalogResult, ui_test_catalog.RECORD_ROOTS),
]
CONTRACT_IDS = [contract_id for contract_id, _, _ in CONTRACTS]


def _committed_schema(contract_id: str) -> dict:
    return json.loads((SCHEMAS_DIR / f"{contract_id}-schema.json").read_text(encoding="utf-8"))


def _doc_entities_instance_dict(**metadata_overrides) -> dict:
    result = doc_entities.DocEntitiesResult(
        metadata=factories.metadata(**metadata_overrides), entities=[factories.user_story()]
    )
    return json.loads(result.model_dump_json())


def _instance_dict_with_entities(entities) -> dict:
    result = doc_entities.DocEntitiesResult(metadata=factories.metadata(), entities=entities)
    return json.loads(result.model_dump_json())


def _coverage_matrix_instance_dict() -> dict:
    result = coverage_matrix.CoverageMatrixResult(
        metadata=factories.transform_metadata(),
        document=factories.coverage_matrix_document(),
        entities=[factories.entity_coverage()],
        planned_summary=factories.planned_summary(),
    )
    return json.loads(result.model_dump_json())


# ---------------------------------------------------------------------------
# Regeneration: byte-for-byte and in step with the committed files.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("contract_id, model, record_roots", CONTRACTS, ids=CONTRACT_IDS)
def test_committed_schema_is_up_to_date(contract_id, model, record_roots):
    regenerated = schema_export.generate_schema(contract_id, model, record_roots)

    assert regenerated == _committed_schema(contract_id)


def test_write_schemas_is_byte_for_byte_deterministic(tmp_path):
    first_pass = {path.name: path.read_bytes() for path in schema_export.write_schemas(tmp_path)}
    second_pass = {path.name: path.read_bytes() for path in schema_export.write_schemas(tmp_path)}

    assert first_pass == second_pass
    assert len(first_pass) == 6


def test_write_schemas_writes_lf_line_endings_only(tmp_path):
    # Text mode would write CRLF on Windows.
    for path in schema_export.write_schemas(tmp_path):
        content = path.read_bytes()

        assert b"\r" not in content
        assert content.endswith(b"}\n")


def test_regeneration_overwrites_a_tampered_schema_file(tmp_path):
    target = tmp_path / f"{doc_entities.CONTRACT_ID}-schema.json"
    target.write_text('{"$schema": "tampered"}\n', encoding="utf-8")
    tampered_bytes = target.read_bytes()

    schema_export.write_schemas(tmp_path)

    assert target.read_bytes() != tampered_bytes
    assert json.loads(target.read_text(encoding="utf-8"))["$schema"] == schema_export.SCHEMA_DIALECT


def test_load_schema_matches_the_committed_file():
    for contract_id in CONTRACT_IDS:
        assert schema_export.load_schema(contract_id) == _committed_schema(contract_id)


# ---------------------------------------------------------------------------
# R1/R2/R3/R4: header keys.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("contract_id", CONTRACT_IDS)
def test_schema_first_key_is_the_2020_12_dialect(contract_id):
    schema = _committed_schema(contract_id)

    assert next(iter(schema)) == "$schema"
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"


@pytest.mark.parametrize("contract_id", CONTRACT_IDS)
def test_schema_id_is_under_living_doc_utilities(contract_id):
    schema = _committed_schema(contract_id)

    assert schema["$id"] == f"https://absaoss.github.io/living-doc-utilities/schemas/{contract_id}-schema.json"


@pytest.mark.parametrize("contract_id", CONTRACT_IDS)
def test_schema_version_is_a_top_level_const(contract_id):
    schema = _committed_schema(contract_id)

    assert schema["properties"]["schema_version"]["const"] == contract_id
    assert "enum" not in schema["properties"]["schema_version"]


def test_no_schema_version_dollar_key_anywhere_in_the_package():
    offenders = [
        str(path)
        for path in (REPO_ROOT / "living_doc_utilities").rglob("*")
        if path.is_file() and path.suffix in {".py", ".json"} and "$schema_version" in path.read_text(encoding="utf-8")
    ]

    assert offenders == []


# ---------------------------------------------------------------------------
# R9: every object is a record (additionalProperties: false) or a typed map
# (additionalProperties + propertyNames) - never a third kind.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("contract_id", CONTRACT_IDS)
def test_committed_schema_has_no_untyped_map_or_bare_pattern_properties(contract_id):
    assert schema_export.find_schema_violations(_committed_schema(contract_id)) == []


def test_find_schema_violations_catches_a_bare_pattern_properties_map():
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {"bad": {"type": "object", "patternProperties": {"^[a-z]+$": {"type": "integer"}}}},
    }

    violations = schema_export.find_schema_violations(schema)

    assert len(violations) == 1
    assert "bad" in violations[0]


def test_find_schema_violations_catches_an_untyped_map():
    schema = {"type": "object", "additionalProperties": True}

    assert schema_export.find_schema_violations(schema) == ["$: map without typed additionalProperties + propertyNames"]


def test_find_schema_violations_catches_a_record_without_additional_properties_false():
    schema = {"type": "object", "properties": {"x": {"type": "string"}}}

    assert schema_export.find_schema_violations(schema) == ["$: record object without additionalProperties: false"]


# ---------------------------------------------------------------------------
# R9's enum-versus-pattern split for field_occupancy.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("contract_id, _model, record_roots", CONTRACTS, ids=CONTRACT_IDS)
def test_every_own_leaf_path_matches_the_audit_pattern(contract_id, _model, record_roots):
    paths = schema_export.field_occupancy_paths(record_roots)

    assert paths, f"{contract_id}: expected at least one leaf path"
    for path in paths:
        assert re.fullmatch(AUDIT_FIELD_PATH_PATTERN, path), f"{contract_id}: '{path}' does not match the audit pattern"


def test_mistyped_path_in_own_field_occupancy_fails_schema_validation():
    data = _doc_entities_instance_dict()
    data["metadata"]["stats"]["field_occupancy"] = {"entities[].not_a_real_field": 1}

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=data, schema=_committed_schema(doc_entities.CONTRACT_ID))


def test_valid_own_field_occupancy_path_passes_schema_validation():
    data = _doc_entities_instance_dict()
    data["metadata"]["stats"]["field_occupancy"] = {"entities[].not_in_scope[]": 3}

    jsonschema.validate(instance=data, schema=_committed_schema(doc_entities.CONTRACT_ID))


def test_another_contracts_path_inside_source_inputs_audit_field_occupancy_passes():
    data = _doc_entities_instance_dict(source_inputs=[factories.source_input_entry(schema_version="doc-source-v1.0.0")])
    # doc-source's own path, carried as an audit copy inside a doc-entities file's source_inputs[].
    data["metadata"]["source_inputs"][0]["stats"]["field_occupancy"] = {"user_stories[].business_value": 4}

    jsonschema.validate(instance=data, schema=_committed_schema(doc_entities.CONTRACT_ID))


@pytest.mark.parametrize(
    "malformed_path", ["Entities[].title", "entities[].Title", "123abc", "entities[].not_in-scope"]
)
def test_malformed_path_inside_source_inputs_audit_field_occupancy_fails(malformed_path):
    data = _doc_entities_instance_dict(source_inputs=[factories.source_input_entry()])
    data["metadata"]["source_inputs"][0]["stats"]["field_occupancy"] = {malformed_path: 1}

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=data, schema=_committed_schema(doc_entities.CONTRACT_ID))


# ---------------------------------------------------------------------------
# Cross-field model_validator rules, mirrored into the schema as allOf if/then/else
# (_inject_cross_field_constraints): each invalid payload must be rejected by both
# Pydantic and a plain jsonschema validator, not just by Pydantic.
#
# Key-*omission* parity for these same rules (dropping a field entirely, rather than setting
# it to an explicit invalid value) is tested once, generically, in test_omission_parity.py -
# not per rule here.
# ---------------------------------------------------------------------------


def test_deprecated_ac_without_removal_planned_is_rejected_by_pydantic_and_jsonschema():
    with pytest.raises(ValidationError, match="removal_planned is required"):
        factories.acceptance_criterion(state="deprecated", removal_planned=None)

    entity = factories.user_story(acceptance_criteria=[factories.acceptance_criterion(state="active", version="1.0.0")])
    data = _instance_dict_with_entities([entity])
    data["entities"][0]["acceptance_criteria"][0]["state"] = "deprecated"

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=data, schema=_committed_schema(doc_entities.CONTRACT_ID))


def test_non_planned_ac_without_version_is_rejected_by_pydantic_and_jsonschema():
    with pytest.raises(ValidationError, match="version is required"):
        factories.acceptance_criterion(state="active", version=None)

    entity = factories.user_story(acceptance_criteria=[factories.acceptance_criterion(state="planned", version=None)])
    data = _instance_dict_with_entities([entity])
    data["entities"][0]["acceptance_criteria"][0]["state"] = "active"

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=data, schema=_committed_schema(doc_entities.CONTRACT_ID))


def test_feature_with_authored_state_origin_is_rejected_by_pydantic_and_jsonschema():
    with pytest.raises(ValidationError, match="state_origin must be 'derived'"):
        factories.feature(state_origin="authored")

    data = _instance_dict_with_entities([factories.feature()])
    data["entities"][0]["state_origin"] = "authored"

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=data, schema=_committed_schema(doc_entities.CONTRACT_ID))


def test_user_story_with_derived_state_origin_is_rejected_by_pydantic_and_jsonschema():
    with pytest.raises(ValidationError, match="state_origin must be 'authored'"):
        factories.user_story(state_origin="derived")

    data = _instance_dict_with_entities([factories.user_story()])
    data["entities"][0]["state_origin"] = "derived"

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=data, schema=_committed_schema(doc_entities.CONTRACT_ID))


def test_stub_reason_on_a_non_feature_is_rejected_by_pydantic_and_jsonschema():
    with pytest.raises(ValidationError, match="stub_reason is only valid on a Feature"):
        factories.user_story(stub_reason="surface not yet instrumented")

    data = _instance_dict_with_entities([factories.user_story()])
    data["entities"][0]["stub_reason"] = "surface not yet instrumented"

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=data, schema=_committed_schema(doc_entities.CONTRACT_ID))


def test_pages_without_exactly_one_primary_is_rejected_by_pydantic_and_jsonschema():
    with pytest.raises(ValidationError, match="exactly one primary PageRef"):
        factories.feature(pages=[factories.page_ref(is_primary=False)])

    data = _instance_dict_with_entities([factories.feature()])
    data["entities"][0]["pages"][0]["is_primary"] = False

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=data, schema=_committed_schema(doc_entities.CONTRACT_ID))


def test_ac_coverage_covered_status_with_a_not_covered_aspect_is_rejected_by_pydantic_and_jsonschema():
    with pytest.raises(ValidationError, match="status must be 'partially_covered'"):
        factories.ac_coverage(status="covered", aspects=[factories.aspect_coverage(status="not_covered")])

    data = _coverage_matrix_instance_dict()
    data["entities"][0]["acceptance_criteria"][0]["status"] = "covered"
    data["entities"][0]["acceptance_criteria"][0]["aspects"] = [
        {"aspect": "checkout", "status": "not_covered", "scenario_ids": []}
    ]

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=data, schema=_committed_schema(coverage_matrix.CONTRACT_ID))


def test_ac_coverage_partially_covered_status_with_no_aspects_is_rejected_by_pydantic_and_jsonschema():
    with pytest.raises(ValidationError, match="cannot be 'partially_covered'"):
        factories.ac_coverage(status="partially_covered", aspects=[])

    data = _coverage_matrix_instance_dict()
    data["entities"][0]["acceptance_criteria"][0]["status"] = "partially_covered"
    data["entities"][0]["acceptance_criteria"][0]["aspects"] = []

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=data, schema=_committed_schema(coverage_matrix.CONTRACT_ID))


def test_ac_coverage_with_a_malformed_ac_id_is_rejected_by_pydantic_and_jsonschema():
    with pytest.raises(ValidationError):
        factories.ac_coverage(ac_id="US-001-anything")

    data = _coverage_matrix_instance_dict()
    data["entities"][0]["acceptance_criteria"][0]["ac_id"] = "US-001-anything"

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=data, schema=_committed_schema(coverage_matrix.CONTRACT_ID))


def test_aspect_coverage_covered_status_with_no_scenario_ids_is_rejected_by_pydantic_and_jsonschema():
    with pytest.raises(ValidationError, match="status must be 'not_covered'"):
        factories.aspect_coverage(status="covered", scenario_ids=[])

    data = _coverage_matrix_instance_dict()
    data["entities"][0]["acceptance_criteria"][0]["status"] = "covered"
    data["entities"][0]["acceptance_criteria"][0]["aspects"] = [
        {"aspect": "checkout", "status": "covered", "scenario_ids": []}
    ]

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=data, schema=_committed_schema(coverage_matrix.CONTRACT_ID))


def test_ac_coverage_without_aspects_covered_status_with_no_scenario_ids_is_rejected_by_pydantic_and_jsonschema():
    with pytest.raises(ValidationError, match="status must be 'not_covered'"):
        factories.ac_coverage(status="covered", aspects=[], scenario_ids=[])

    data = _coverage_matrix_instance_dict()
    data["entities"][0]["acceptance_criteria"][0]["status"] = "covered"
    data["entities"][0]["acceptance_criteria"][0]["aspects"] = []
    data["entities"][0]["acceptance_criteria"][0]["scenario_ids"] = []

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=data, schema=_committed_schema(coverage_matrix.CONTRACT_ID))


def test_ac_coverage_without_aspects_covered_status_with_scenario_ids_key_omitted_is_rejected_by_jsonschema_too():
    data = _coverage_matrix_instance_dict()
    data["entities"][0]["acceptance_criteria"][0]["status"] = "covered"
    data["entities"][0]["acceptance_criteria"][0]["aspects"] = []
    del data["entities"][0]["acceptance_criteria"][0]["scenario_ids"]

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=data, schema=_committed_schema(coverage_matrix.CONTRACT_ID))


@pytest.mark.parametrize(
    "contract_id, _model, record_roots",
    [c for c in CONTRACTS if c[0] in {generator_ready.CONTRACT_ID, coverage_matrix.CONTRACT_ID, ui_test_catalog.CONTRACT_ID}],
    ids=[generator_ready.CONTRACT_ID, coverage_matrix.CONTRACT_ID, ui_test_catalog.CONTRACT_ID],
)
def test_transform_output_source_inputs_minitems_is_mirrored_into_the_schema(contract_id, _model, record_roots):
    schema = _committed_schema(contract_id)
    metadata_def = schema["$defs"]["Metadata"]

    assert metadata_def["properties"]["source_inputs"]["minItems"] == 1


def test_generator_ready_with_empty_source_inputs_is_rejected_by_pydantic_and_jsonschema():
    with pytest.raises(ValidationError, match="source_inputs must have at least one entry"):
        generator_ready.GeneratorReadyResult(
            metadata=factories.metadata(),
            document=factories.generator_ready_document(),
            content=generator_ready.Content(entities=[factories.user_story()]),
        )

    result = generator_ready.GeneratorReadyResult(
        metadata=factories.transform_metadata(),
        document=factories.generator_ready_document(),
        content=generator_ready.Content(entities=[factories.user_story()]),
    )
    data = json.loads(result.model_dump_json())
    data["metadata"]["source_inputs"] = []

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=data, schema=_committed_schema(generator_ready.CONTRACT_ID))


def test_collector_output_with_empty_source_inputs_still_passes_jsonschema():
    # The minItems constraint above is gated to the three transform contracts only - a
    # collector output's Metadata legitimately carries an empty source_inputs (R7).
    data = _doc_entities_instance_dict()
    assert data["metadata"]["source_inputs"] == []

    jsonschema.validate(instance=data, schema=_committed_schema(doc_entities.CONTRACT_ID))


# ---------------------------------------------------------------------------
# Cross-cutting envelope facts.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("contract_id, _model, record_roots", CONTRACTS, ids=CONTRACT_IDS)
def test_every_contract_declares_its_own_non_empty_record_roots(contract_id, _model, record_roots):
    assert isinstance(record_roots, dict)
    assert record_roots, f"{contract_id}: RECORD_ROOTS must not be empty"


def test_metadata_is_one_shared_model_across_all_six_contracts():
    assert (
        doc_entities.Metadata
        is doc_source.Metadata
        is ui_tests.Metadata
        is generator_ready.Metadata
        is coverage_matrix.Metadata
        is ui_test_catalog.Metadata
    )


# ---------------------------------------------------------------------------
# Internal helpers: the annotation walker and the defensive guards around a
# contract module losing its expected shape.
# ---------------------------------------------------------------------------


def test_unwrap_treats_a_multi_member_union_as_an_opaque_leaf():
    item_type, is_array = schema_export._unwrap(Union[int, str])

    assert (item_type, is_array) == (Union[int, str], False)


def test_inject_own_field_occupancy_enum_requires_a_stats_definition():
    with pytest.raises(ValueError, match="expected a 'Stats' definition"):
        schema_export._inject_own_field_occupancy_enum({"$defs": {}}, [])


def test_inject_own_field_occupancy_enum_requires_a_field_occupancy_property():
    schema = {"$defs": {"Stats": {"properties": {}}}}

    with pytest.raises(ValueError, match="expected a 'field_occupancy' property"):
        schema_export._inject_own_field_occupancy_enum(schema, [])


def test_inject_cross_field_constraints_requires_a_source_inputs_property_on_transform_contracts():
    schema = {"$defs": {"Metadata": {"properties": {}}}}

    with pytest.raises(ValueError, match="expected a 'source_inputs' property"):
        schema_export._inject_cross_field_constraints(schema, generator_ready.CONTRACT_ID)


def test_main_regenerates_the_committed_schemas_in_place():
    schema_export.main()

    for contract_id in CONTRACT_IDS:
        assert schema_export.load_schema(contract_id) == _committed_schema(contract_id)
