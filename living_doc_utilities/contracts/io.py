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
R12: `read_artifact`/`write_artifact` are the only sanctioned way to read or write a
contract artifact anywhere in the fleet - never plain json.load(), never a write outside
the validate-then-atomic-rename sequence below.
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Union, cast

from pydantic import BaseModel, ValidationError

from living_doc_utilities.contracts import compat, registry, schema_export, stats, validation
from living_doc_utilities.contracts.codes import Code, ContractError
from living_doc_utilities.contracts.registry import ContractResult


def _model_validate_or_raise(model_cls: type[BaseModel], contract_id: str, payload: Any) -> BaseModel:
    """Re-validates payload against its typed model after schema validation passed - the only way
    to catch a cross-field rule (e.g. an entity's AC-ownership check) plain JSON Schema cannot express."""
    try:
        return model_cls.model_validate(payload)
    except ValidationError as exc:
        raise ContractError(
            Code.SCHEMA_VALIDATION_FAILED,
            f"{contract_id}: payload passed schema validation but failed model validation: {exc}",
        ) from exc


def read_artifact(path: Union[str, Path], expected: Union[str, set[str]]) -> ContractResult:
    """The only sanctioned way to read a contract artifact (R12): loads `path`, runs it through
    `compat.py::check_input` (R5) and returns the typed contract model.

    @param path: the artifact file to read.
    @param expected: a single contract name (e.g. "doc-entities") or a set of acceptable
        ones (e.g. {"doc-entities", "doc-source"}).
    @return: the parsed contract model - never a raw dict.
    @raises ContractError: INVALID_CONTRACT_ID, CONTRACT_MISMATCH or SCHEMA_VALIDATION_FAILED.
    """
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    contract_id = compat.check_input(payload, expected)
    spec = registry.CONTRACTS[contract_id]
    return cast(ContractResult, _model_validate_or_raise(spec.result_model, contract_id, payload))


def write_artifact(result: ContractResult, path: Union[str, Path]) -> None:
    """The only sanctioned way to write a contract artifact (R12): fills metadata.stats and
    producer.utilities_version, validates in memory, then writes via temp file + atomic rename,
    so a crash never leaves a partial or corrupt artifact.

    @param result: a contract result model - its own schema_version selects the contract.
    @param path: the destination file path.
    @raises ContractError: INVALID_CONTRACT_ID for an unknown schema_version, or
        SCHEMA_VALIDATION_FAILED - either way the destination is never created or modified.
    """
    contract_id = result.schema_version
    if contract_id not in registry.CONTRACTS:
        raise ContractError(Code.INVALID_CONTRACT_ID, f"unknown schema_version {contract_id!r}")
    spec = registry.CONTRACTS[contract_id]

    filled = result.model_copy(deep=True)
    reported_cardinality = filled.metadata.stats.cardinality
    filled.metadata.producer.utilities_version = compat.installed_utilities_version()
    filled.metadata.stats = stats.compute_stats(filled, spec.record_roots, reported_cardinality)

    payload = filled.model_dump(mode="json")
    schema = schema_export.load_schema(contract_id)
    errors = validation.validate(payload, schema)
    if errors:
        raise compat.schema_validation_error(errors, payload)
    _model_validate_or_raise(spec.result_model, contract_id, payload)

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, tmp_name = tempfile.mkstemp(dir=str(destination.parent), prefix=f".{destination.name}.", suffix=".tmp")
    try:
        # Explicit newline: text mode would write CRLF on Windows.
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as tmp_file:
            tmp_file.write(json.dumps(payload, indent=2) + "\n")
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
        os.replace(tmp_name, destination)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise
