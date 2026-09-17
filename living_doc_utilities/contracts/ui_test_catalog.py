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
The ui-test-catalog-v1.0.0 contract: a transform's normalized scenario catalog for a
generator, grouped by feature file and then by what each scenario links to. The ui-tests
Scenario model is reused directly rather than redeclared here.
"""

from typing import Literal

from pydantic import BaseModel, Field

from living_doc_utilities.contracts.common import ContractModel, View
from living_doc_utilities.contracts.envelope import ContractWarning, Metadata
from living_doc_utilities.contracts.ui_tests import Scenario

CONTRACT_ID: Literal["ui-test-catalog-v1.0.0"] = "ui-test-catalog-v1.0.0"


class LinkedScenarios(ContractModel):
    """The scenarios linked to one entity (a User Story or a Functionality)."""

    entity_id: str
    scenarios: list[Scenario] = Field(default_factory=list)


class FeatureFileCatalog(ContractModel):
    """One `.feature` file's scenarios, grouped into: linked to a User Story, linked to a
    Functionality, or unlinked."""

    feature_file: str
    linked_to_user_story: list[LinkedScenarios] = Field(default_factory=list)
    linked_to_functionality: list[LinkedScenarios] = Field(default_factory=list)
    unlinked: list[Scenario] = Field(default_factory=list)


class Document(ContractModel):
    """What the generator filters by."""

    view: View


class UiTestCatalogResult(ContractModel):
    """The ui-test-catalog-v1.0.0 artifact."""

    schema_version: Literal["ui-test-catalog-v1.0.0"] = CONTRACT_ID
    metadata: Metadata
    warnings: list[ContractWarning] = Field(default_factory=list)
    document: Document
    feature_files: list[FeatureFileCatalog] = Field(default_factory=list)


# Declares this contract's record roots (docs/contracts.md, section 1) - see
# doc_entities.RECORD_ROOTS.
RECORD_ROOTS: dict[str, type[BaseModel]] = {"feature_files": FeatureFileCatalog}
