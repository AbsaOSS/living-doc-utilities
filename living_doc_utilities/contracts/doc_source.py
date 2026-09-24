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
The doc-source-v1.0.0 contract: the source-scanning collector's output. Three record
roots - user_stories[], features[], functionalities[] - each holding the same Entity shape as doc-entities.
"""

from typing import Literal

from pydantic import BaseModel, Field

from living_doc_utilities.contracts.common import ContractModel
from living_doc_utilities.contracts.doc_entities import Entity
from living_doc_utilities.contracts.envelope import ContractWarning, Metadata

CONTRACT_ID: Literal["doc-source-v1.0.0"] = "doc-source-v1.0.0"


class DocSourceResult(ContractModel):
    """The doc-source-v1.0.0 artifact."""

    schema_version: Literal["doc-source-v1.0.0"] = CONTRACT_ID
    metadata: Metadata
    warnings: list[ContractWarning] = Field(default_factory=list)
    user_stories: list[Entity] = Field(default_factory=list)
    features: list[Entity] = Field(default_factory=list)
    functionalities: list[Entity] = Field(default_factory=list)


# This contract's record roots; see `doc_entities.py::RECORD_ROOTS`.
RECORD_ROOTS: dict[str, type[BaseModel]] = {
    "user_stories": Entity,
    "features": Entity,
    "functionalities": Entity,
}
