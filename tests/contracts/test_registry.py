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
Tests for contracts.registry: the one table every reader that needs "all six contracts"
looks up instead of keeping its own hand-written copy - this file pins that the registry,
testing._BUILDERS and the committed schema files never drift apart.
"""

from pathlib import Path

import pytest

from living_doc_utilities.contracts import doc_entities, registry, testing

SCHEMAS_DIR = Path(__file__).resolve().parents[2] / "living_doc_utilities" / "contracts" / "schemas"

_KNOWN_CONTRACT_IDS = {
    "doc-entities-v1.0.0",
    "doc-source-v1.0.0",
    "ui-tests-v1.0.0",
    "generator-ready-v1.0.0",
    "coverage-matrix-v1.0.0",
    "ui-test-catalog-v1.0.0",
}


def test_registry_covers_exactly_the_six_known_contract_ids():
    assert set(registry.CONTRACTS) == _KNOWN_CONTRACT_IDS


def test_registry_and_testing_builders_cover_the_same_ids():
    assert set(registry.CONTRACTS) == set(testing._BUILDERS)


def test_registry_and_the_committed_schema_files_cover_the_same_ids():
    schema_ids = {path.name.removesuffix("-schema.json") for path in SCHEMAS_DIR.glob("*-schema.json")}

    assert set(registry.CONTRACTS) == schema_ids


def test_registry_marks_exactly_the_three_transform_contracts():
    transform_ids = {contract_id for contract_id, spec in registry.CONTRACTS.items() if spec.is_transform}

    assert transform_ids == {"generator-ready-v1.0.0", "coverage-matrix-v1.0.0", "ui-test-catalog-v1.0.0"}


def test_record_roots_returns_the_contracts_own_declaration():
    assert registry.record_roots(doc_entities.CONTRACT_ID) is doc_entities.RECORD_ROOTS


def test_record_roots_rejects_an_unknown_contract_id():
    with pytest.raises(ValueError, match="unknown contract id"):
        registry.record_roots("not-a-contract-v1.0.0")
