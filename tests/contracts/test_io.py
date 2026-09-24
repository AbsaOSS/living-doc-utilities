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


def test_read_artifact_accepts_a_string_path_as_well_as_a_path_object(tmp_path):
    """read_artifact accepts a plain string path as well as a Path object."""
    destination = tmp_path / "doc-entities.json"
    io.write_artifact(_valid_doc_entities_result(producer=_matching_producer()), destination)

    loaded = io.read_artifact(str(destination), "doc-entities")

    assert isinstance(loaded, DocEntitiesResult)
