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
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

# Version fields never carry a leading "v" - see docs/contracts.md, "Version format".
VERSION_PATTERN = r"^\d+\.\d+\.\d+$"

# An AC id is its parent entity's id plus a sequence number, conventionally zero-padded to two
# digits, e.g. "US-001-01" - mirrors living-doc's tools/examples_check.py AC_HEADER_RE / AC_TAG_RE
# (commit bfcc402ff998085cbf7bb91a7fd55ea8ac12c911), which does not itself fix the digit width.
AC_ID_PATTERN = r"^[A-Z]+-\d+-\d+$"

# A placeholder name from the AC-block grammar's placeholder_values, e.g. "<user_role>".
PLACEHOLDER_NAME_PATTERN = r"^[A-Za-z_][A-Za-z0-9_]*$"

# The three documentation types an entity can be. Also used as the fixed key set of
# metadata.stats.cardinality.entities_by_type (R9).
DocType = Literal["DocumentedUserStory", "DocumentedFeature", "DocumentedFunctionality"]

# An entity's and an acceptance criterion's lifecycle state (docs/contracts.md, "State and
# state_origin").
LifecycleState = Literal["planned", "in_review", "active", "deprecated"]

# A transform-output document's declared presentation (docs/contracts.md, section 4): shared by
# every contract that carries a `document` block (generator-ready, coverage-matrix,
# ui-test-catalog).
View = Literal["inner", "release"]


class ContractModel(BaseModel):
    """Shared base for every contract model: unknown fields are rejected (R9)."""

    model_config = ConfigDict(extra="forbid")


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
        """Renders this AC's canonical header text (docs/contracts.md, "AC header"):
        `AC:<id> (v<x.y.z> - <state>)`, or `AC:<id> (planned)` for a version-less
        backlog item - adding the leading `v` back, so a downstream generator never
        needs to import `authoring` just to render an acceptance-criterion header.
        """
        if self.version is None:
            return f"AC:{self.id} ({self.state})"
        inner = f"v{self.version} - {self.state}"
        if self.state == "deprecated" and self.removal_planned is not None:
            inner += f" - removal planned v{self.removal_planned}"
        return f"AC:{self.id} ({inner})"


class EntityCore(ContractModel):
    """Identity, provenance and lifecycle fields shared by every documented entity."""

    entity_id: str
    source_ref: SourceRef
    type: DocType
    title: str
    state: LifecycleState
    state_origin: Literal["authored", "derived"]
    tags: list[str] = Field(default_factory=list)
    timestamps: Timestamps = Field(default_factory=Timestamps)
