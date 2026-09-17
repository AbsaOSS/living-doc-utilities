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
The ui-tests-v1.0.0 contract: the source-scanning collector's .feature-derived output.
One scenarios[] list (docs/contracts.md, section 1).
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

from living_doc_utilities.contracts.common import AC_ID_PATTERN, ContractModel, SourceRef
from living_doc_utilities.contracts.envelope import ContractWarning, Metadata

CONTRACT_ID: Literal["ui-tests-v1.0.0"] = "ui-tests-v1.0.0"


class AcLink(ContractModel):
    """One `@AC:<id>[/aspect:<value>]` scenario tag (living-doc's AC_TAG_RE): a scenario may
    carry several, each pairing a specific acceptance criterion with the specific aspect of
    it this scenario covers - or no aspect at all."""

    id: str = Field(pattern=AC_ID_PATTERN)
    aspect: Optional[str] = None


class Scenario(ContractModel):
    """One Gherkin scenario."""

    scenario_id: str
    title: str
    source_ref: SourceRef
    tags: list[str] = Field(default_factory=list)
    acceptance_criteria: list[AcLink] = Field(default_factory=list)


class UITestsResult(ContractModel):
    """The ui-tests-v1.0.0 artifact."""

    schema_version: Literal["ui-tests-v1.0.0"] = CONTRACT_ID
    metadata: Metadata
    warnings: list[ContractWarning] = Field(default_factory=list)
    scenarios: list[Scenario] = Field(default_factory=list)


# Declares this contract's record roots (docs/contracts.md, section 1) - see doc_entities.RECORD_ROOTS.
RECORD_ROOTS: dict[str, type[BaseModel]] = {"scenarios": Scenario}
