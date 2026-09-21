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
docs/contracts.md, R12 "One read path, one write path, typed": read_artifact and
write_artifact are the only sanctioned way to read or write a contract artifact anywhere
in the fleet. No component reads a contract file with plain json.load(), and no component
writes one without going through the validate-then-atomic-rename sequence below.
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Union, cast

from pydantic import BaseModel, ValidationError

from living_doc_utilities.contracts import (
    compat,
    coverage_matrix,
    doc_entities,
    doc_source,
    generator_ready,
    schema_export,
    stats,
    ui_test_catalog,
    ui_tests,
    validation,
)
from living_doc_utilities.contracts.codes import Code, ContractError

# The six contract result models - a Union rather than a plain BaseModel so that
# read_artifact's/write_artifact's callers (and mypy) see the shared fields every one of
# them declares: schema_version, metadata, warnings.
ContractResult = Union[
    doc_entities.DocEntitiesResult,
    doc_source.DocSourceResult,
    ui_tests.UITestsResult,
    generator_ready.GeneratorReadyResult,
    coverage_matrix.CoverageMatrixResult,
    ui_test_catalog.UiTestCatalogResult,
]

# Every contract's result model and record roots, keyed by contract id - the only place
# read_artifact/write_artifact need to know which model a schema_version selects.
_CONTRACTS: dict[str, tuple[type[BaseModel], dict[str, type[BaseModel]]]] = {
    doc_entities.CONTRACT_ID: (doc_entities.DocEntitiesResult, doc_entities.RECORD_ROOTS),
    doc_source.CONTRACT_ID: (doc_source.DocSourceResult, doc_source.RECORD_ROOTS),
    ui_tests.CONTRACT_ID: (ui_tests.UITestsResult, ui_tests.RECORD_ROOTS),
    generator_ready.CONTRACT_ID: (generator_ready.GeneratorReadyResult, generator_ready.RECORD_ROOTS),
    coverage_matrix.CONTRACT_ID: (coverage_matrix.CoverageMatrixResult, coverage_matrix.RECORD_ROOTS),
    ui_test_catalog.CONTRACT_ID: (ui_test_catalog.UiTestCatalogResult, ui_test_catalog.RECORD_ROOTS),
}


def record_roots(contract_id: str) -> dict[str, type[BaseModel]]:
    """
    @param contract_id: one of the six contracts' CONTRACT_ID (e.g. "doc-entities-v1.0.0").
    @return: that contract's RECORD_ROOTS declaration.
    @raises ValueError: `contract_id` is not one of the six known contract ids.
    """
    try:
        return _CONTRACTS[contract_id][1]
    except KeyError:
        raise ValueError(f"unknown contract id {contract_id!r}; expected one of {sorted(_CONTRACTS)!r}") from None


def read_artifact(path: Union[str, Path], expected: Union[str, set[str]]) -> ContractResult:
    """
    The only sanctioned way to read a contract artifact (R12): loads the JSON at `path`,
    runs it through compat.check_input (R5), and returns the parsed, typed contract model.

    @param path: the artifact file to read.
    @param expected: a single contract name (e.g. "doc-entities") or a set of acceptable
        ones (e.g. {"doc-entities", "doc-source"}).
    @return: the parsed contract model - never a raw dict.
    @raises ContractError: INVALID_CONTRACT_ID, CONTRACT_MISMATCH or SCHEMA_VALIDATION_FAILED.
    """
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    contract_id = compat.check_input(payload, expected)
    model_cls, _ = _CONTRACTS[contract_id]
    try:
        return cast(ContractResult, model_cls.model_validate(payload))
    except ValidationError as exc:
        raise ContractError(
            Code.SCHEMA_VALIDATION_FAILED,
            f"{contract_id}: payload passed schema validation but failed model validation: {exc}",
        ) from exc


def write_artifact(result: ContractResult, path: Union[str, Path]) -> None:
    """
    The only sanctioned way to write a contract artifact (R12): fills metadata.stats and
    metadata.producer.utilities_version, validates the filled-in result in memory, and only
    on success writes it - to a temporary file in the destination's own directory, then an
    atomic rename - so a crash mid-write never leaves a partial or corrupt artifact where a
    later run would try to read it.

    @param result: a contract result model - its own schema_version selects the contract.
    @param path: the destination file path.
    @raises ContractError: SCHEMA_VALIDATION_FAILED - leaves no file on disk at all.
    """
    contract_id = result.schema_version
    if contract_id not in _CONTRACTS:
        raise ContractError(Code.INVALID_CONTRACT_ID, f"unknown schema_version {contract_id!r}")
    model_cls, record_roots = _CONTRACTS[contract_id]

    filled = result.model_copy(deep=True)
    reported_cardinality = filled.metadata.stats.cardinality
    filled.metadata.producer.utilities_version = compat.installed_utilities_version()
    filled.metadata.stats = stats.compute_stats(filled, record_roots, reported_cardinality)

    payload = json.loads(filled.model_dump_json())
    schema = schema_export.load_schema(contract_id)
    errors = validation.validate(payload, schema)
    if errors:
        raise compat.schema_validation_error(errors, payload)
    try:
        model_cls.model_validate(payload)
    except ValidationError as exc:
        raise ContractError(
            Code.SCHEMA_VALIDATION_FAILED,
            f"{contract_id}: payload passed schema validation but failed model validation: {exc}",
        ) from exc

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
