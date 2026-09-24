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
Tests for compat.py (docs/contracts.md, R5): the shared three-step compatibility check, and
the SCHEMA_VALIDATION_FAILED message builder it shares with io.write_artifact.
"""

import json

import pytest
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError

from living_doc_utilities.contracts import compat, schema_export
from living_doc_utilities.contracts.codes import Code, ContractError
from living_doc_utilities.contracts.doc_entities import CONTRACT_ID, DocEntitiesResult
from living_doc_utilities.contracts.validation import validate
from tests.contracts import factories


def _valid_payload(**metadata_overrides) -> dict:
    result = DocEntitiesResult(metadata=factories.metadata(**metadata_overrides), entities=[factories.user_story()])
    return json.loads(result.model_dump_json())


# ---------------------------------------------------------------------------
# installed_utilities_version
# ---------------------------------------------------------------------------


def test_installed_utilities_version_delegates_to_importlib_metadata(mocker):
    spy = mocker.patch("living_doc_utilities.contracts.compat._installed_version", return_value="9.9.9")

    assert compat.installed_utilities_version() == "9.9.9"
    spy.assert_called_once_with("living-doc-utilities")


# ---------------------------------------------------------------------------
# check_input step 1: schema_version presence/shape.
# ---------------------------------------------------------------------------


def test_check_input_missing_schema_version_raises_invalid_contract_id():
    with pytest.raises(ContractError) as excinfo:
        compat.check_input({}, "doc-entities")

    assert excinfo.value.code == Code.INVALID_CONTRACT_ID


def test_check_input_non_string_schema_version_raises_invalid_contract_id():
    with pytest.raises(ContractError) as excinfo:
        compat.check_input({"schema_version": 123}, "doc-entities")

    assert excinfo.value.code == Code.INVALID_CONTRACT_ID


@pytest.mark.parametrize(
    "schema_version",
    [
        "doc-entities-1.0.0",
        "DocEntities-v1.0.0",
        "doc_entities-v1.0.0",
        "doc-entities-v1.0",
        "doc-entities-vX.Y.Z",
        "a--x-v1.0.0",
        "Doc-v1.0.0",
    ],
)
def test_check_input_malformed_schema_version_raises_invalid_contract_id(schema_version):
    with pytest.raises(ContractError) as excinfo:
        compat.check_input({"schema_version": schema_version}, "doc-entities")

    assert excinfo.value.code == Code.INVALID_CONTRACT_ID


def test_check_input_non_dict_payload_raises_invalid_contract_id():
    with pytest.raises(ContractError) as excinfo:
        compat.check_input(["not", "a", "dict"], "doc-entities")

    assert excinfo.value.code == Code.INVALID_CONTRACT_ID


# ---------------------------------------------------------------------------
# check_input step 2: contract name membership.
# ---------------------------------------------------------------------------


def test_check_input_contract_name_not_in_expected_single_string_raises_contract_mismatch():
    with pytest.raises(ContractError) as excinfo:
        compat.check_input({"schema_version": "doc-entities-v1.0.0"}, "doc-source")

    assert excinfo.value.code == Code.CONTRACT_MISMATCH
    assert "'doc-source'" in excinfo.value.message
    assert "'doc-entities'" in excinfo.value.message


def test_check_input_contract_name_not_in_a_two_name_expected_set_names_both():
    with pytest.raises(ContractError) as excinfo:
        compat.check_input({"schema_version": "ui-tests-v1.0.0"}, {"doc-entities", "doc-source"})

    message = excinfo.value.message
    assert excinfo.value.code == Code.CONTRACT_MISMATCH
    assert message == "expected one of ['doc-entities', 'doc-source'], got 'ui-tests'"


def test_check_input_accepts_a_single_string_expected_as_a_one_element_set():
    payload = _valid_payload()

    assert compat.check_input(payload, "doc-entities") == CONTRACT_ID


# ---------------------------------------------------------------------------
# check_input step 3: structural validation against the bundled schema.
# ---------------------------------------------------------------------------


def test_check_input_structurally_invalid_payload_raises_schema_validation_failed():
    payload = _valid_payload()
    del payload["metadata"]["source"]

    with pytest.raises(ContractError) as excinfo:
        compat.check_input(payload, "doc-entities")

    assert excinfo.value.code == Code.SCHEMA_VALIDATION_FAILED


def test_check_input_returns_the_contract_id_on_success():
    payload = _valid_payload()

    assert compat.check_input(payload, {"doc-entities", "doc-source"}) == "doc-entities-v1.0.0"


def test_check_input_never_raises_or_warns_on_an_unfamiliar_producer_version():
    # metadata.producer.version is audit-only (R6) - check_input never reads it, only
    # metadata.producer.utilities_version (and only inside the step-3 error path at that).
    payload = _valid_payload(producer=factories.producer(version="not-a-version-anyone-has-seen-before"))

    result = compat.check_input(payload, "doc-entities")

    assert result == CONTRACT_ID


# ---------------------------------------------------------------------------
# schema_validation_error
# ---------------------------------------------------------------------------


def test_schema_validation_error_names_both_versions_and_the_failing_path():
    payload = _valid_payload(producer=factories.producer(utilities_version="0.4.0"))
    payload["metadata"]["stats"]["field_occupancy"] = {"entities[].not_a_real_field": 1}
    errors = validate(payload, schema_export.load_schema(CONTRACT_ID))

    error = compat.schema_validation_error(errors, payload)

    assert error.code == Code.SCHEMA_VALIDATION_FAILED
    assert "file written by utilities '0.4.0'" in error.message
    assert f"this is utilities {compat.installed_utilities_version()!r}" in error.message


def test_schema_validation_error_appends_pin_alignment_hint_when_versions_differ(mocker):
    mocker.patch("living_doc_utilities.contracts.compat.installed_utilities_version", return_value="9.9.9")
    payload = {"metadata": {"producer": {"utilities_version": "0.5.0"}}}

    error = compat.schema_validation_error([_dummy_error()], payload)

    assert "the components run different utilities versions" in error.message


def test_schema_validation_error_omits_hint_when_versions_are_equal(mocker):
    mocker.patch("living_doc_utilities.contracts.compat.installed_utilities_version", return_value="0.5.0")
    payload = {"metadata": {"producer": {"utilities_version": "0.5.0"}}}

    error = compat.schema_validation_error([_dummy_error()], payload)

    assert "the components run different utilities versions" not in error.message


def test_schema_validation_error_omits_hint_when_producer_version_is_absent(mocker):
    mocker.patch("living_doc_utilities.contracts.compat.installed_utilities_version", return_value="0.5.0")

    error = compat.schema_validation_error([_dummy_error()], {})

    assert "the components run different utilities versions" not in error.message
    assert "file written by utilities None" in error.message


def _dummy_error() -> JsonSchemaValidationError:
    return JsonSchemaValidationError("boom")
