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
The generator-ready-v1.0.0 contract: a transform's output for a generator
(docs/contracts.md, section 1). Every authored entity and acceptance-criterion field is
carried at its authored level under content.entities[] - the doc-entities Entity and
AcceptanceCriterion models are reused directly rather than redeclared here.
"""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from living_doc_utilities.contracts.common import ContractModel, View
from living_doc_utilities.contracts.doc_entities import Entity
from living_doc_utilities.contracts.envelope import ContractWarning, Metadata, check_transform_source_inputs

CONTRACT_ID: Literal["generator-ready-v1.0.0"] = "generator-ready-v1.0.0"


class SelectionSummary(ContractModel):
    """Counts of what the transform's view filter kept and dropped (docs/contracts.md,
    section 4). A record: exactly these six named properties, nothing else.

    `total_entities == included_entities + excluded_entities` always holds: the producer
    derives `excluded_entities` as `total_entities - included_entities` over one fixed
    entity set, so it is a guaranteed identity, not a coincidence - the same check does not
    apply to the three acceptance-criteria fields, because the producer only reports
    view-filtered criteria for entities it kept and never tallies criteria belonging to a
    dropped entity, so those three fields are not established as a disjoint partition. This
    identity is Pydantic-only: JSON Schema has no keyword for a sum across sibling
    properties, so a consumer validating raw JSON against the generated schema alone (not
    through this model) cannot catch a violation.
    """

    total_entities: int = Field(ge=0)
    included_entities: int = Field(ge=0)
    excluded_entities: int = Field(ge=0)
    total_acceptance_criteria: int = Field(ge=0)
    included_acceptance_criteria: int = Field(ge=0)
    excluded_acceptance_criteria: int = Field(ge=0)

    @model_validator(mode="after")
    def _check_entity_total(self) -> "SelectionSummary":
        if self.total_entities != self.included_entities + self.excluded_entities:
            raise ValueError("total_entities must equal included_entities + excluded_entities")
        return self


class Document(ContractModel):
    """What the generator titles and filters by (docs/contracts.md, "The metadata envelope")."""

    title: str
    version: str
    view: View
    selection_summary: SelectionSummary


class Content(ContractModel):
    """The transform's selected entities, each carried at its full authored shape."""

    entities: list[Entity] = Field(default_factory=list)


class GeneratorReadyResult(ContractModel):
    """The generator-ready-v1.0.0 artifact."""

    schema_version: Literal["generator-ready-v1.0.0"] = CONTRACT_ID
    metadata: Metadata
    warnings: list[ContractWarning] = Field(default_factory=list)
    document: Document
    content: Content

    @model_validator(mode="after")
    def _check_source_inputs_not_empty(self) -> "GeneratorReadyResult":
        check_transform_source_inputs(self.metadata)
        return self


# Declares this contract's record roots (docs/contracts.md, section 1) - see
# doc_entities.RECORD_ROOTS. The root is nested under `content`, matching R11's
# `content.entities[]` field_occupancy path prefix.
RECORD_ROOTS: dict[str, type[BaseModel]] = {"content.entities": Entity}
