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
Shared value objects used by every contract model: the extra="forbid" base class,
the acceptance-criterion grammar, entity identity/provenance, and timestamps.
"""

from datetime import datetime
from typing import Annotated, Iterable, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

# Version fields never carry a leading "v".
VERSION_PATTERN = r"^\d+\.\d+\.\d+$"

# AC id = parent id + sequence, conventionally zero-padded (e.g. "US-001-01"); the digit width is not enforced.
AC_ID_PATTERN = r"^[A-Z]+-\d+-\d+$"

# A placeholder name from the AC-block grammar's placeholder_values, e.g. "<user_role>".
PLACEHOLDER_NAME_PATTERN = r"^[A-Za-z_][A-Za-z0-9_]*$"

# The three documentation types an entity can be; also cardinality.entities_by_type's fixed key set (R9).
DocType = Literal["DocumentedUserStory", "DocumentedFeature", "DocumentedFunctionality"]

# An entity's and an acceptance criterion's lifecycle state.
LifecycleState = Literal["planned", "in_review", "active", "deprecated"]

# Whether state came from the author or was derived; shared so ParsedEntity's state_origin uses the same literals.
StateOrigin = Literal["authored", "derived"]

# A transform-output document's declared presentation, shared by generator-ready/coverage-matrix/ui-test-catalog.
View = Literal["inner", "release"]


class ContractModel(BaseModel):
    """Shared base for every contract model: unknown fields are rejected (R9)."""

    model_config = ConfigDict(extra="forbid")


class ViewDocument(ContractModel):
    """What a generator filters by. Shared as-is by coverage-matrix and ui-test-catalog,
    whose own `document` block carries no other field; generator-ready's own Document
    subclasses this to add its extra fields."""

    view: View


class Timestamps(ContractModel):
    """Creation, update and close timestamps for an entity."""

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None


class SourceRef(ContractModel):
    """Provenance pointer back to the tracking system an entity or scenario came from."""

    system: Literal["GitHub", "AzureDevOps"]
    native_id: str
    native_type: str
    url: str
    tracker_state: str
    area_path: Optional[str] = None
    iteration_path: Optional[str] = None


class AcceptanceCriterion(ContractModel):
    """One acceptance criterion, in the AC-block grammar's shape."""

    id: str = Field(pattern=AC_ID_PATTERN)
    state: LifecycleState
    version: Optional[str] = Field(default=None, pattern=VERSION_PATTERN)
    description: str
    aspect: list[str] = Field(default_factory=list)
    preconditions: list[str] = Field(default_factory=list)
    not_in_scope: list[str] = Field(default_factory=list)
    removal_planned: Optional[str] = Field(default=None, pattern=VERSION_PATTERN)
    rationale: Optional[str] = None
    placeholder_values: dict[Annotated[str, StringConstraints(pattern=PLACEHOLDER_NAME_PATTERN)], list[str]] = Field(
        default_factory=dict
    )

    @model_validator(mode="after")
    def _check_version_required_unless_planned(self) -> "AcceptanceCriterion":
        if self.state != "planned" and self.version is None:
            raise ValueError("version is required unless state is 'planned'")
        return self

    @model_validator(mode="after")
    def _check_removal_planned_only_when_deprecated(self) -> "AcceptanceCriterion":
        if self.state == "deprecated" and self.removal_planned is None:
            raise ValueError("removal_planned is required when state is 'deprecated'")
        if self.state != "deprecated" and self.removal_planned is not None:
            raise ValueError("removal_planned is only valid when state is 'deprecated'")
        return self

    def canonical_header(self) -> str:
        """Renders this AC's canonical header text: `AC:<id> (v<x.y.z> - <state>)`, or
        `AC:<id> (planned)` for a version-less backlog item - the leading `v` added back so a
        downstream generator never needs to import `authoring` just to render a header."""
        if self.version is None:
            return f"AC:{self.id} ({self.state})"
        inner = f"v{self.version} - {self.state}"
        if self.state == "deprecated" and self.removal_planned is not None:
            inner += f" - removal planned v{self.removal_planned}"
        return f"AC:{self.id} ({inner})"


def check_ac_ids_owned(entity_id: str, ac_ids: Iterable[str]) -> None:
    """Checks that every acceptance-criterion id under an entity is that entity's own id plus "-" plus a
    sequence number. Shared by `doc_entities.py::Entity` and `coverage_matrix.py::CoverageMatrixResult`.

    @param entity_id: the owning entity's id.
    @param ac_ids: that entity's own acceptance-criterion ids.
    @raises ValueError: naming the first id that does not start with "<entity_id>-".
    """
    prefix = f"{entity_id}-"
    for ac_id in ac_ids:
        if not ac_id.startswith(prefix):
            raise ValueError(f"acceptance criterion id '{ac_id}' does not belong to entity '{entity_id}'")


class EntityCore(ContractModel):
    """Identity, provenance and lifecycle fields shared by every documented entity."""

    entity_id: str
    source_ref: SourceRef
    type: DocType
    title: str
    state: LifecycleState
    state_origin: StateOrigin
    tags: list[str] = Field(default_factory=list)
    timestamps: Timestamps = Field(default_factory=Timestamps)
