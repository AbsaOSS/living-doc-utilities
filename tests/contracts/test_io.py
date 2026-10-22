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

"""`io.py` (R12): the one read path and the one validate-then-atomic-rename write path for contract artifacts."""

import json
import os
from datetime import datetime

import pytest
from pydantic import ConfigDict

from living_doc_utilities.contracts import compat, io
from living_doc_utilities.contracts.codes import Code, ContractError
from living_doc_utilities.contracts.coverage_matrix import CoverageMatrixResult
from living_doc_utilities.contracts.doc_entities import CONTRACT_ID as DOC_ENTITIES_CONTRACT_ID
from living_doc_utilities.contracts.doc_entities import DocEntitiesResult
from living_doc_utilities.contracts.doc_source import CONTRACT_ID as DOC_SOURCE_CONTRACT_ID
from living_doc_utilities.contracts.envelope import Cardinality, Stats
from living_doc_utilities.contracts.ui_test_catalog import UiTestCatalogResult
from living_doc_utilities.contracts.ui_tests import UITestsResult
from tests.contracts import factories


class _TamperedDocEntities(DocEntitiesResult):
    """A DocEntitiesResult with an extra field, so the schema's `additionalProperties: false` rejects it on write.

    Real contract models use `extra="forbid"`, so this is the only way to build an instance the schema rejects.
    """

    model_config = ConfigDict(extra="allow")
    unexpected_field: str = "surprise"


def _valid_doc_entities_result(**metadata_overrides) -> DocEntitiesResult:
    return DocEntitiesResult(metadata=factories.metadata(**metadata_overrides), entities=[factories.user_story()])


def _doc_entities_result_with_misowned_ac(**metadata_overrides) -> DocEntitiesResult:
    # model_copy(update=...) skips validators, so it builds a payload that passes the schema yet fails the model's rule.
    result = _valid_doc_entities_result(**metadata_overrides)
    misowned_entity = result.entities[0].model_copy(
        update={"acceptance_criteria": [factories.acceptance_criterion(parent_id="US-999")]}
    )
    return result.model_copy(update={"entities": [misowned_entity]})


def _matching_producer():
    # The file's producer.utilities_version equals the installed one, so no pin-alignment hint is expected.
    return factories.producer(utilities_version=compat.installed_utilities_version())


def _leftover_tmp_files(directory) -> list:
    return [path for path in directory.iterdir() if path.name.startswith(".") and path.suffix == ".tmp"]


# ---------------------------------------------------------------------------
# read_artifact
# ---------------------------------------------------------------------------


def test_read_artifact_returns_the_correctly_typed_model(tmp_path):
    """read_artifact returns an instance of the artifact's own typed result model, never a raw dict or subtype."""
    path = tmp_path / "doc-entities.json"
    path.write_text(_valid_doc_entities_result().model_dump_json(), encoding="utf-8")

    loaded = io.read_artifact(path, "doc-entities")

    assert isinstance(loaded, DocEntitiesResult)
    assert type(loaded) is DocEntitiesResult  # noqa: E721 - never a raw dict, never a subtype
    assert loaded.entities[0].entity_id == "US-001"


def test_read_artifact_missing_schema_version_raises_invalid_contract_id(tmp_path):
    """A file with no schema_version field is rejected by read_artifact as an invalid contract id."""
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"not": "a contract"}), encoding="utf-8")

    with pytest.raises(ContractError) as excinfo:
        io.read_artifact(path, "doc-entities")

    assert excinfo.value.code == Code.INVALID_CONTRACT_ID


def test_read_artifact_malformed_schema_version_raises_invalid_contract_id(tmp_path):
    """A file whose schema_version doesn't match the expected id shape is rejected by read_artifact as invalid."""
    path = tmp_path / "bad.json"
    payload = json.loads(_valid_doc_entities_result().model_dump_json())
    payload["schema_version"] = "not-a-valid-id"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ContractError) as excinfo:
        io.read_artifact(path, "doc-entities")

    assert excinfo.value.code == Code.INVALID_CONTRACT_ID


def test_read_artifact_contract_mismatch_raises_contract_mismatch(tmp_path):
    """read_artifact rejects a file whose contract name doesn't match the single name it was asked to read."""
    path = tmp_path / "doc-entities.json"
    path.write_text(_valid_doc_entities_result().model_dump_json(), encoding="utf-8")

    with pytest.raises(ContractError) as excinfo:
        io.read_artifact(path, "doc-source")

    assert excinfo.value.code == Code.CONTRACT_MISMATCH


def test_read_artifact_contract_mismatch_with_a_two_name_expected_set_names_both(tmp_path):
    """read_artifact rejects a mismatched file against a two-name expected set, naming both expected names."""
    path = tmp_path / "ui-tests.json"
    result = UITestsResult(metadata=factories.metadata(), scenarios=[factories.scenario()])
    path.write_text(result.model_dump_json(), encoding="utf-8")

    with pytest.raises(ContractError) as excinfo:
        io.read_artifact(path, {DOC_ENTITIES_CONTRACT_ID.rsplit("-v", 1)[0], DOC_SOURCE_CONTRACT_ID.rsplit("-v", 1)[0]})

    assert excinfo.value.code == Code.CONTRACT_MISMATCH
    assert "'doc-entities'" in excinfo.value.message
    assert "'doc-source'" in excinfo.value.message


def test_read_artifact_unshipped_schema_version_raises_invalid_contract_id_with_the_pin_hint(tmp_path, mocker):
    """read_artifact rejects a known contract at an unshipped version as INVALID_CONTRACT_ID with the pin hint."""
    # The file's utilities_version equals the installed one: an edit by hand comes first, the hint still ends it.
    mocker.patch("living_doc_utilities.contracts.compat.installed_utilities_version", return_value="0.9.0")
    path = tmp_path / "doc-entities.json"
    result = _valid_doc_entities_result(producer=factories.producer(utilities_version="0.9.0"))
    payload = json.loads(result.model_dump_json())
    payload["schema_version"] = "doc-entities-v9.9.9"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ContractError) as excinfo:
        io.read_artifact(path, "doc-entities")

    assert excinfo.value.code == Code.INVALID_CONTRACT_ID
    assert excinfo.value.message == (
        "schema_version 'doc-entities-v9.9.9' is not a contract version this utilities ships "
        "(file written by utilities '0.9.0', this is utilities '0.9.0'); "
        "the file was edited by hand, or the components run different utilities versions — align the pins"
    )


def test_read_artifact_structurally_invalid_payload_raises_schema_validation_failed(tmp_path):
    """read_artifact rejects a file that is structurally invalid against its bundled schema."""
    path = tmp_path / "doc-entities.json"
    payload = json.loads(_valid_doc_entities_result().model_dump_json())
    del payload["metadata"]["source"]
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ContractError) as excinfo:
        io.read_artifact(path, "doc-entities")

    assert excinfo.value.code == Code.SCHEMA_VALIDATION_FAILED


def test_read_artifact_schema_valid_but_model_invalid_payload_raises_schema_validation_failed(tmp_path):
    """A schema-valid payload that fails the model's own cross-field rules is rejected as SCHEMA_VALIDATION_FAILED."""
    path = tmp_path / "doc-entities.json"
    path.write_text(_doc_entities_result_with_misowned_ac().model_dump_json(), encoding="utf-8")

    with pytest.raises(ContractError) as excinfo:
        io.read_artifact(path, "doc-entities")

    assert excinfo.value.code == Code.SCHEMA_VALIDATION_FAILED


# ---------------------------------------------------------------------------
# write_artifact: success path.
# ---------------------------------------------------------------------------


def test_write_artifact_creates_the_parent_directory_and_writes_the_file(tmp_path):
    """write_artifact creates any missing parent directories and writes a schema_version-stamped file."""
    destination = tmp_path / "nested" / "dir" / "doc-entities.json"
    result = _valid_doc_entities_result(producer=_matching_producer())

    io.write_artifact(result, destination)

    assert destination.exists()
    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["schema_version"] == DOC_ENTITIES_CONTRACT_ID
    assert payload["metadata"]["producer"]["utilities_version"] == compat.installed_utilities_version()


def test_write_artifact_writes_lf_line_endings_only(tmp_path):
    """write_artifact always writes LF-only line endings, even on platforms that default to CRLF."""
    # Text mode would write CRLF on Windows.
    destination = tmp_path / "doc-entities.json"

    io.write_artifact(_valid_doc_entities_result(producer=_matching_producer()), destination)

    content = destination.read_bytes()
    assert b"\r" not in content
    assert content.endswith(b"}\n")


def test_write_artifact_fills_metadata_stats_from_the_result_itself(tmp_path):
    """write_artifact recomputes metadata.stats.cardinality from the result's own entities before writing."""
    destination = tmp_path / "doc-entities.json"
    result = _valid_doc_entities_result(producer=_matching_producer())

    io.write_artifact(result, destination)

    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["metadata"]["stats"]["cardinality"]["entities"] == 1
    assert payload["metadata"]["stats"]["cardinality"]["entities_by_type"] == {"DocumentedUserStory": 1}


def test_write_artifact_preserves_the_passthrough_cardinality_fields_from_the_original_stats(tmp_path):
    """write_artifact preserves the caller-supplied passthrough cardinality fields unchanged."""
    destination = tmp_path / "doc-entities.json"
    result = _valid_doc_entities_result(
        producer=_matching_producer(),
        stats=Stats(cardinality=Cardinality(sources_configured=4, sources_failed=1, unresolved_refs=2, entities_skipped=3)),
    )

    io.write_artifact(result, destination)

    payload = json.loads(destination.read_text(encoding="utf-8"))
    cardinality = payload["metadata"]["stats"]["cardinality"]
    assert cardinality["sources_configured"] == 4
    assert cardinality["sources_failed"] == 1
    assert cardinality["unresolved_refs"] == 2
    assert cardinality["entities_skipped"] == 3


def test_write_artifact_does_not_mutate_the_caller_owned_result(tmp_path):
    """write_artifact never mutates the caller's own result object, even though it writes a modified copy."""
    destination = tmp_path / "doc-entities.json"
    result = _valid_doc_entities_result(producer=factories.producer(utilities_version="0.0.1"))

    io.write_artifact(result, destination)

    assert result.metadata.producer.utilities_version == "0.0.1"


# ---------------------------------------------------------------------------
# write_artifact: SCHEMA_VALIDATION_FAILED leaves no file (and no leftover temp file) at all.
# ---------------------------------------------------------------------------


def test_write_artifact_schema_validation_failure_names_both_versions_with_hint_when_they_differ(tmp_path, mocker):
    """A schema validation failure names both utilities versions, with a hint when they differ."""
    # write_artifact fills utilities_version before validating, so a skew needs the installed version to change.
    destination = tmp_path / "doc-entities.json"
    mocker.patch(
        "living_doc_utilities.contracts.compat.installed_utilities_version",
        side_effect=["1.0.0", "2.0.0"],
    )
    result = _TamperedDocEntities(metadata=factories.metadata(), entities=[factories.user_story()])

    with pytest.raises(ContractError) as excinfo:
        io.write_artifact(result, destination)

    assert excinfo.value.code == Code.SCHEMA_VALIDATION_FAILED
    assert "utilities '1.0.0'" in excinfo.value.message
    assert "utilities '2.0.0'" in excinfo.value.message
    assert "the components run different utilities versions" in excinfo.value.message
    assert not destination.exists()
    assert _leftover_tmp_files(tmp_path) == []


def test_write_artifact_schema_validation_failure_omits_hint_when_versions_match(tmp_path):
    """A schema validation failure omits the pin-alignment hint when the file's and installed versions match."""
    # write_artifact overwrites producer.utilities_version before validating, so the two versions agree by construction.
    destination = tmp_path / "doc-entities.json"
    result = _TamperedDocEntities(
        metadata=factories.metadata(producer=factories.producer(utilities_version="9.8.7")),
        entities=[factories.user_story()],
    )

    with pytest.raises(ContractError) as excinfo:
        io.write_artifact(result, destination)

    assert excinfo.value.code == Code.SCHEMA_VALIDATION_FAILED
    assert f"utilities {compat.installed_utilities_version()!r}" in excinfo.value.message
    assert "the components run different utilities versions" not in excinfo.value.message
    assert not destination.exists()
    assert _leftover_tmp_files(tmp_path) == []


def test_write_artifact_schema_valid_but_model_invalid_payload_raises_schema_validation_failed(tmp_path):
    """write_artifact rejects a schema-valid result that fails the model's own cross-field rules, writing nothing."""
    # model_copy(update=...) bypasses validators, so the pre-write model re-validation is what must catch this.
    destination = tmp_path / "doc-entities.json"
    result = _doc_entities_result_with_misowned_ac(producer=_matching_producer())

    with pytest.raises(ContractError) as excinfo:
        io.write_artifact(result, destination)

    assert excinfo.value.code == Code.SCHEMA_VALIDATION_FAILED
    assert not destination.exists()
    assert _leftover_tmp_files(tmp_path) == []


def test_write_artifact_schema_validation_failure_creates_no_directory_at_all(tmp_path):
    """A write_artifact failure creates no destination directory at all, not even an empty one."""
    destination = tmp_path / "never" / "created" / "doc-entities.json"
    result = _TamperedDocEntities(metadata=factories.metadata(producer=_matching_producer()), entities=[factories.user_story()])

    with pytest.raises(ContractError):
        io.write_artifact(result, destination)

    assert not destination.parent.exists()


def test_write_artifact_unknown_schema_version_raises_invalid_contract_id(tmp_path):
    """write_artifact rejects a result whose schema_version names no known contract, and writes no file."""
    result = _valid_doc_entities_result(producer=_matching_producer())
    result.schema_version = "not-a-real-contract-v1.0.0"

    with pytest.raises(ContractError) as excinfo:
        io.write_artifact(result, tmp_path / "x.json")

    assert excinfo.value.code == Code.INVALID_CONTRACT_ID
    assert not (tmp_path / "x.json").exists()


# ---------------------------------------------------------------------------
# write_artifact: a crash between temp-file creation and the final rename leaves nothing.
# ---------------------------------------------------------------------------


def test_write_artifact_cleans_up_the_temp_file_when_the_atomic_rename_crashes(tmp_path, monkeypatch):
    """If the final atomic rename crashes, write_artifact leaves neither the destination file nor a temp file."""
    destination = tmp_path / "doc-entities.json"
    result = _valid_doc_entities_result(producer=_matching_producer())

    def _boom(*_args, **_kwargs):
        raise OSError("simulated crash between write and rename")

    monkeypatch.setattr(os, "replace", _boom)

    with pytest.raises(OSError, match="simulated crash"):
        io.write_artifact(result, destination)

    assert not destination.exists()
    assert _leftover_tmp_files(tmp_path) == []


# ---------------------------------------------------------------------------
# Round-trip sanity: coverage-matrix and ui-test-catalog.
# ---------------------------------------------------------------------------


def test_coverage_matrix_round_trips_through_write_and_read(tmp_path):
    """A CoverageMatrixResult written by write_artifact and read back by read_artifact round-trips unchanged."""
    destination = tmp_path / "coverage-matrix.json"
    result = CoverageMatrixResult(
        metadata=factories.transform_metadata(producer=_matching_producer()),
        document=factories.coverage_matrix_document(),
        entities=[factories.entity_coverage(entity_id="US-001")],
        planned_summary=factories.planned_summary(),
        summary=factories.matrix_summary([factories.entity_coverage(entity_id="US-001")]),
    )

    io.write_artifact(result, destination)
    loaded = io.read_artifact(destination, "coverage-matrix")

    assert isinstance(loaded, CoverageMatrixResult)
    assert loaded.entities[0].entity_id == "US-001"
    assert loaded.planned_summary.total == 3
    assert loaded.document.view == "release"


def test_ui_test_catalog_round_trips_through_write_and_read(tmp_path):
    """A UiTestCatalogResult written by write_artifact and read back by read_artifact round-trips unchanged."""
    destination = tmp_path / "ui-test-catalog.json"
    result = UiTestCatalogResult(
        metadata=factories.transform_metadata(producer=_matching_producer()),
        document=factories.ui_test_catalog_document(),
        feature_files=[factories.feature_file_catalog()],
    )

    io.write_artifact(result, destination)
    loaded = io.read_artifact(destination, "ui-test-catalog")

    assert isinstance(loaded, UiTestCatalogResult)
    assert loaded.feature_files[0].feature_file == "checkout.feature"
    assert loaded.feature_files[0].linked_to_user_story[0].entity_id == "US-001"


# ---------------------------------------------------------------------------
# Date-times: a value that is no RFC 3339 date-time with an offset fails at the schema step, on read and on write.
# ---------------------------------------------------------------------------

_DATE_TIME_FIELDS = {"generated_at": "$.metadata.generated_at", "closed_at": "$.entities[0].timestamps.closed_at"}


def _doc_entities_result_with_date_time(field: str, value: str) -> DocEntitiesResult:
    # model_copy(update=...) skips validators, so the value reaches write_artifact's schema step as written.
    result = _valid_doc_entities_result(producer=_matching_producer())
    if field == "generated_at":
        return result.model_copy(update={"metadata": result.metadata.model_copy(update={field: value})})
    entity = result.entities[0]
    timestamps = entity.timestamps.model_copy(update={field: value})
    return result.model_copy(update={"entities": [entity.model_copy(update={"timestamps": timestamps})]})


def _assert_failed_at_the_schema_step(error: ContractError, field: str) -> None:
    assert error.code == Code.SCHEMA_VALIDATION_FAILED
    assert error.message.startswith(f"{_DATE_TIME_FIELDS[field]}: ")
    assert "passed schema validation" not in error.message


def _doc_entities_file_with_date_time(tmp_path, field: str, value):
    path = tmp_path / "doc-entities.json"
    payload = json.loads(_valid_doc_entities_result().model_dump_json())
    if field == "generated_at":
        payload["metadata"]["generated_at"] = value
    else:
        payload["entities"][0]["timestamps"][field] = value
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


@pytest.mark.parametrize("field", list(_DATE_TIME_FIELDS))
@pytest.mark.parametrize("value", factories.NOT_RFC_3339_DATE_TIMES)
def test_read_artifact_fails_a_date_time_that_is_no_rfc_3339_date_time_at_the_schema_step(field, value, tmp_path):
    """read_artifact stops the value at R5 step 3, and the message names the field."""
    path = _doc_entities_file_with_date_time(tmp_path, field, value)

    with pytest.raises(ContractError) as excinfo:
        io.read_artifact(path, "doc-entities")

    _assert_failed_at_the_schema_step(excinfo.value, field)


@pytest.mark.parametrize("field", list(_DATE_TIME_FIELDS))
def test_read_artifact_fails_a_unix_time_number_at_the_schema_step(field, tmp_path):
    """A Unix time written as a JSON number, which the model would read as UTC, stops at R5 step 3."""
    path = _doc_entities_file_with_date_time(tmp_path, field, 1772323200)

    with pytest.raises(ContractError) as excinfo:
        io.read_artifact(path, "doc-entities")

    _assert_failed_at_the_schema_step(excinfo.value, field)


# Dumping a str from a datetime field warns that the value is unexpected; that value is the point here.
@pytest.mark.filterwarnings("ignore:Pydantic serializer warnings:UserWarning")
@pytest.mark.parametrize("field", list(_DATE_TIME_FIELDS))
@pytest.mark.parametrize("value", factories.NOT_RFC_3339_DATE_TIMES)
def test_write_artifact_fails_a_date_time_that_is_no_rfc_3339_date_time_and_writes_nothing(field, value, tmp_path):
    """write_artifact stops the value at its schema step, names the field and creates no file."""
    destination = tmp_path / "doc-entities.json"

    with pytest.raises(ContractError) as excinfo:
        io.write_artifact(_doc_entities_result_with_date_time(field, value), destination)

    _assert_failed_at_the_schema_step(excinfo.value, field)
    assert not destination.exists()
    assert _leftover_tmp_files(tmp_path) == []


def test_write_artifact_fails_a_naive_datetime_at_the_schema_step(tmp_path):
    """A naive datetime object dumps without an offset, so the schema step stops it before the model does."""
    destination = tmp_path / "doc-entities.json"

    with pytest.raises(ContractError) as excinfo:
        io.write_artifact(_doc_entities_result_with_date_time("generated_at", datetime(2026, 3, 1)), destination)

    _assert_failed_at_the_schema_step(excinfo.value, "generated_at")
    assert list(tmp_path.iterdir()) == []


# Python's `re.search`, which jsonschema applies a `pattern` with, lets `$` match before a final newline, so a
# trailing newline passes the schema step here; an ECMA-262 validator rejects it there. The pattern stays without a
# lookahead, which RE2-based validators cannot compile, so the model step is what stops it in Python.
_TRAILING_NEWLINE = "2026-03-01T00:00:00Z\n"
_MODEL_LOCATIONS = {"generated_at": "metadata.generated_at", "closed_at": "entities.0.timestamps.closed_at"}


def _assert_failed_at_the_model_step(error: ContractError, field: str) -> None:
    assert error.code == Code.SCHEMA_VALIDATION_FAILED
    assert "passed schema validation but failed model validation" in error.message
    assert _MODEL_LOCATIONS[field] in error.message


@pytest.mark.parametrize("field", list(_DATE_TIME_FIELDS))
def test_read_artifact_fails_a_date_time_with_a_trailing_newline_at_the_model_step(field, tmp_path):
    """A trailing newline passes Python's pattern check, and the model still fails it as SCHEMA_VALIDATION_FAILED."""
    path = _doc_entities_file_with_date_time(tmp_path, field, _TRAILING_NEWLINE)

    with pytest.raises(ContractError) as excinfo:
        io.read_artifact(path, "doc-entities")

    _assert_failed_at_the_model_step(excinfo.value, field)


# Dumping a str from a datetime field warns that the value is unexpected; that value is the point here.
@pytest.mark.filterwarnings("ignore:Pydantic serializer warnings:UserWarning")
@pytest.mark.parametrize("field", list(_DATE_TIME_FIELDS))
def test_write_artifact_fails_a_date_time_with_a_trailing_newline_and_writes_nothing(field, tmp_path):
    """write_artifact's model step fails the value the pattern let through, and creates no file."""
    destination = tmp_path / "doc-entities.json"

    with pytest.raises(ContractError) as excinfo:
        io.write_artifact(_doc_entities_result_with_date_time(field, _TRAILING_NEWLINE), destination)

    _assert_failed_at_the_model_step(excinfo.value, field)
    assert list(tmp_path.iterdir()) == []


def test_read_artifact_accepts_a_string_path_as_well_as_a_path_object(tmp_path):
    """read_artifact accepts a plain string path as well as a Path object."""
    destination = tmp_path / "doc-entities.json"
    io.write_artifact(_valid_doc_entities_result(producer=_matching_producer()), destination)

    loaded = io.read_artifact(str(destination), "doc-entities")

    assert isinstance(loaded, DocEntitiesResult)
