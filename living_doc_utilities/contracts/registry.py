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
The one place that knows all six contracts. Every contract module already exports
CONTRACT_ID, its own *Result model and RECORD_ROOTS; this module is the only place those
get collected into a table, so a reader that needs "every contract" - io, schema_export,
lineage, testing - has one place to read instead of its own hand-written copy of the same
six-row list.
"""

from dataclasses import dataclass
from typing import Union

from pydantic import BaseModel

from living_doc_utilities.contracts import (
    coverage_matrix,
    doc_entities,
    doc_source,
    generator_ready,
    ui_test_catalog,
    ui_tests,
)

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


@dataclass(frozen=True)
class ContractSpec:
    """One contract's registry row: its result model, its RECORD_ROOTS declaration, and
    whether it's a transform output - R7 requires metadata.source_inputs[] to carry at
    least one entry on a transform output, never on a collector output."""

    result_model: type[BaseModel]
    record_roots: dict[str, type[BaseModel]]
    is_transform: bool


# Every contract's result model, record roots and transform-ness, keyed by CONTRACT_ID - the
# only hand-written list of all six contracts; every other reader looks it up here instead of
# keeping its own copy.
_ROWS: tuple[tuple[str, type[BaseModel], dict[str, type[BaseModel]], bool], ...] = (
    (doc_entities.CONTRACT_ID, doc_entities.DocEntitiesResult, doc_entities.RECORD_ROOTS, False),
    (doc_source.CONTRACT_ID, doc_source.DocSourceResult, doc_source.RECORD_ROOTS, False),
    (ui_tests.CONTRACT_ID, ui_tests.UITestsResult, ui_tests.RECORD_ROOTS, False),
    (generator_ready.CONTRACT_ID, generator_ready.GeneratorReadyResult, generator_ready.RECORD_ROOTS, True),
    (coverage_matrix.CONTRACT_ID, coverage_matrix.CoverageMatrixResult, coverage_matrix.RECORD_ROOTS, True),
    (ui_test_catalog.CONTRACT_ID, ui_test_catalog.UiTestCatalogResult, ui_test_catalog.RECORD_ROOTS, True),
)

CONTRACTS: dict[str, ContractSpec] = {
    contract_id: ContractSpec(result_model, record_roots, is_transform)
    for contract_id, result_model, record_roots, is_transform in _ROWS
}


def record_roots(contract_id: str) -> dict[str, type[BaseModel]]:
    """
    @param contract_id: one of the six contracts' CONTRACT_ID (e.g. "doc-entities-v1.0.0").
    @return: that contract's RECORD_ROOTS declaration.
    @raises ValueError: `contract_id` is not one of the six known contract ids.
    """
    try:
        return CONTRACTS[contract_id].record_roots
    except KeyError:
        raise ValueError(f"unknown contract id {contract_id!r}; expected one of {sorted(CONTRACTS)!r}") from None
