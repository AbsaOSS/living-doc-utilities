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
The coverage-matrix-v1.0.0 contract: per-aspect acceptance-criterion coverage over the
corpus (docs/contracts.md, section 4, "Coverage"). Coverage is computed only for `active`
and `deprecated` acceptance criteria; `in_review` and `planned` criteria are never counted,
and their test activity is reported as a warning instead (STALE_AC_REF and friends,
docs/contracts.md section 5).
"""

from typing import Annotated, Literal, get_args

from pydantic import BaseModel, Field, StringConstraints, model_validator

from living_doc_utilities.contracts.common import VERSION_PATTERN, ContractModel, LifecycleState, View
from living_doc_utilities.contracts.envelope import ContractWarning, Metadata

CONTRACT_ID: Literal["coverage-matrix-v1.0.0"] = "coverage-matrix-v1.0.0"

# The only two entity states a coverage row is ever computed for (docs/contracts.md,
# "Coverage" - `in_review` and `planned` acceptance criteria are never counted).
CountedState = Literal["active", "deprecated"]
COUNTED_STATES: frozenset[str] = frozenset(get_args(CountedState))

CoverageStatus = Literal["covered", "partially_covered", "not_covered"]
AspectStatus = Literal["covered", "not_covered"]


class AspectCoverage(ContractModel):
    """One aspect of an acceptance criterion's per-aspect breakdown."""

    aspect: str
    status: AspectStatus
    scenario_ids: list[str] = Field(default_factory=list)


class AcCoverage(ContractModel):
    """One acceptance criterion's resolved coverage row."""

    ac_id: str
    state: CountedState
    status: CoverageStatus
    aspects: list[AspectCoverage] = Field(default_factory=list)
    scenario_ids: list[str] = Field(default_factory=list)


class EntityCoverage(ContractModel):
    """A User Story or Functionality's acceptance criteria, each with its coverage row.

    `state` is the entity's own lifecycle state, which is independent of which of its
    acceptance criteria are counted (docs/contracts.md, "Coverage": counting is decided per
    AC, "in both views" - never by the parent entity's state). A `planned`/`in_review`
    entity can still own `active`/`deprecated` acceptance criteria that must be counted, so
    this is the full `LifecycleState`, not `CountedState`.
    """

    entity_id: str
    type: Literal["DocumentedUserStory", "DocumentedFunctionality"]
    title: str
    state: LifecycleState
    acceptance_criteria: list[AcCoverage] = Field(default_factory=list)


class PlannedSummary(ContractModel):
    """Planned (not-yet-implemented) acceptance-criteria totals, rendered only in the inner
    view (docs/contracts.md, "Coverage")."""

    total: int = Field(ge=0)
    backlog: int = Field(ge=0)
    by_target_version: dict[Annotated[str, StringConstraints(pattern=VERSION_PATTERN)], Annotated[int, Field(ge=0)]] = (
        Field(default_factory=dict)
    )


class Document(ContractModel):
    """What the generator filters by."""

    view: View


class CoverageMatrixResult(ContractModel):
    """The coverage-matrix-v1.0.0 artifact."""

    schema_version: Literal["coverage-matrix-v1.0.0"] = CONTRACT_ID
    metadata: Metadata
    warnings: list[ContractWarning] = Field(default_factory=list)
    document: Document
    entities: list[EntityCoverage] = Field(default_factory=list)
    planned_summary: PlannedSummary

    @model_validator(mode="after")
    def _check_acceptance_criteria_belong_to_this_entity(self) -> "CoverageMatrixResult":
        for entity in self.entities:
            prefix = f"{entity.entity_id}-"
            for ac in entity.acceptance_criteria:
                if not ac.ac_id.startswith(prefix):
                    raise ValueError(
                        f"acceptance criterion id '{ac.ac_id}' does not belong to entity '{entity.entity_id}'"
                    )
        return self


# Declares this contract's record roots (docs/contracts.md, section 1) - see
# doc_entities.RECORD_ROOTS.
RECORD_ROOTS: dict[str, type[BaseModel]] = {"entities": EntityCoverage}
