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

"""The doc-source contract: its three list record roots, the one type each holds, and their reuse of doc-entities'
`Entity` model."""

import json
from typing import get_args

import jsonschema
import pytest
from pydantic import ValidationError

from living_doc_utilities.contracts import compat, io, schema_export
from living_doc_utilities.contracts.codes import Code, ContractError
from living_doc_utilities.contracts.common import DocType
from living_doc_utilities.contracts.doc_entities import Entity
from living_doc_utilities.contracts.doc_source import CONTRACT_ID, RECORD_ROOTS, ROOT_TYPES, DocSourceResult
from tests.contracts import factories

# One builder per type; each new record takes an id of its own, so only its root is wrong.
_RECORD_BY_TYPE = {
    "DocumentedUserStory": lambda: factories.user_story(entity_id="US-002"),
    "DocumentedFeature": lambda: factories.feature(entity_id="FEAT-002"),
    "DocumentedFunctionality": lambda: factories.functionality(entity_id="FUNC-002"),
}

# Every root with every type it must not hold.
_MISPLACED = [
    (root, doc_type) for root, root_type in ROOT_TYPES.items() for doc_type in _RECORD_BY_TYPE if doc_type != root_type
]
_MISPLACED_IDS = [f"{doc_type}-in-{root}" for root, doc_type in _MISPLACED]


def _type_pure_result(**metadata_overrides) -> DocSourceResult:
    return DocSourceResult(
        metadata=factories.metadata(**metadata_overrides),
        user_stories=[factories.user_story()],
        features=[factories.feature()],
        functionalities=[factories.functionality()],
    )


def _with_a_misplaced_record(root: str, doc_type: str) -> DocSourceResult:
    # model_copy(update=...) skips validators, so the misplaced record reaches write_artifact's schema step.
    result = _type_pure_result(producer=factories.producer(utilities_version=compat.installed_utilities_version()))
    return result.model_copy(update={root: [*getattr(result, root), _RECORD_BY_TYPE[doc_type]()]})


def test_doc_source_uses_the_three_list_record_roots():
    """DocSourceResult exposes user_stories/features/functionalities as separate lists, no items key."""
    result = DocSourceResult(
        metadata=factories.metadata(),
        user_stories=[factories.user_story()],
        features=[factories.feature()],
        functionalities=[factories.functionality()],
    )

    assert len(result.user_stories) == 1
    assert len(result.features) == 1
    assert len(result.functionalities) == 1
    assert "items" not in DocSourceResult.model_fields


def test_doc_source_lists_default_to_empty():
    """Each of the three record-root lists defaults to empty when not supplied."""
    result = DocSourceResult(metadata=factories.metadata())

    assert result.user_stories == []
    assert result.features == []
    assert result.functionalities == []


def test_doc_source_entity_is_the_same_shared_model_as_doc_entities():
    """All three doc-source record roots use the same shared `Entity` model as doc-entities."""
    assert RECORD_ROOTS == {
        "user_stories": Entity,
        "features": Entity,
        "functionalities": Entity,
    }


def test_doc_source_reuses_doc_entities_validators():
    """`DocSourceResult` enforces the same `state_origin` validator that doc-entities uses."""
    with pytest.raises(ValidationError, match="state_origin must be 'derived'"):
        DocSourceResult(metadata=factories.metadata(), features=[factories.feature(state_origin="authored")])


def test_doc_source_result_schema_version_is_the_contract_id():
    """`DocSourceResult.schema_version` equals the module's own `CONTRACT_ID`."""
    result = DocSourceResult(metadata=factories.metadata())

    assert result.schema_version == CONTRACT_ID == "doc-source-v1.0.0"


def test_doc_source_forbids_unknown_top_level_field():
    """`DocSourceResult` rejects an unrecognised top-level field."""
    with pytest.raises(ValidationError):
        DocSourceResult(metadata=factories.metadata(), items=[])


# ---------------------------------------------------------------------------
# One entity type per record root, in the model, the committed schema, and both io helpers.
# ---------------------------------------------------------------------------


def test_root_types_name_one_type_per_record_root():
    """`ROOT_TYPES` maps each record root, and only those, to the type its name says, and covers every `DocType`."""
    assert ROOT_TYPES == {
        "user_stories": "DocumentedUserStory",
        "features": "DocumentedFeature",
        "functionalities": "DocumentedFunctionality",
    }
    assert set(ROOT_TYPES) == set(RECORD_ROOTS)
    assert sorted(ROOT_TYPES.values()) == sorted(get_args(DocType))


def test_a_type_pure_doc_source_validates_in_the_model_the_schema_and_both_io_helpers(tmp_path):
    """Each record in its type's root passes Pydantic and the committed schema, is written and reads back."""
    result = _type_pure_result(producer=factories.producer(utilities_version=compat.installed_utilities_version()))
    destination = tmp_path / "doc-source.json"

    DocSourceResult.model_validate(result.model_dump())
    jsonschema.validate(instance=json.loads(result.model_dump_json()), schema=schema_export.load_schema(CONTRACT_ID))
    io.write_artifact(result, destination)
    loaded = io.read_artifact(destination, "doc-source")

    assert loaded.model_dump(exclude={"metadata"}) == result.model_dump(exclude={"metadata"})


@pytest.mark.parametrize("root, doc_type", _MISPLACED, ids=_MISPLACED_IDS)
def test_a_record_in_another_type_s_root_is_rejected_by_the_model(root, doc_type):
    """The model names the root, the record's index and its type, and the one type the root holds."""
    data = _with_a_misplaced_record(root, doc_type).model_dump()
    message = rf"{root}\[1\] is a '{doc_type}' record .*{root}\[\] holds only '{ROOT_TYPES[root]}'"

    with pytest.raises(ValidationError, match=message):
        DocSourceResult.model_validate(data)


@pytest.mark.parametrize("root, doc_type", _MISPLACED, ids=_MISPLACED_IDS)
def test_a_record_in_another_type_s_root_is_rejected_by_the_committed_schema(root, doc_type):
    """The exported schema rejects the same record at its `type`, as Pydantic does."""
    data = json.loads(_with_a_misplaced_record(root, doc_type).model_dump_json())

    errors = list(jsonschema.Draft202012Validator(schema_export.load_schema(CONTRACT_ID)).iter_errors(data))

    assert [(error.json_path, error.validator) for error in errors] == [(f"$.{root}[1].type", "const")]


@pytest.mark.parametrize("root, doc_type", _MISPLACED, ids=_MISPLACED_IDS)
def test_read_artifact_rejects_a_record_in_another_type_s_root_as_schema_validation_failed(root, doc_type, tmp_path):
    """read_artifact stops such a file at R5 step 3, naming the record's `type` path."""
    path = tmp_path / "doc-source.json"
    path.write_text(_with_a_misplaced_record(root, doc_type).model_dump_json(), encoding="utf-8")

    with pytest.raises(ContractError) as excinfo:
        io.read_artifact(path, "doc-source")

    assert excinfo.value.code == Code.SCHEMA_VALIDATION_FAILED
    assert excinfo.value.message.startswith(f"$.{root}[1].type: ")


@pytest.mark.parametrize("root, doc_type", _MISPLACED, ids=_MISPLACED_IDS)
def test_write_artifact_rejects_a_record_in_another_type_s_root_and_writes_nothing(root, doc_type, tmp_path):
    """write_artifact fails such a result as SCHEMA_VALIDATION_FAILED and creates no file."""
    destination = tmp_path / "doc-source.json"

    with pytest.raises(ContractError) as excinfo:
        io.write_artifact(_with_a_misplaced_record(root, doc_type), destination)

    assert excinfo.value.code == Code.SCHEMA_VALIDATION_FAILED
    assert excinfo.value.message.startswith(f"$.{root}[1].type: ")
    assert list(tmp_path.iterdir()) == []
