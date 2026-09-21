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
The doc-entities-v1.0.0 contract: the issue-tracker collectors' output. One flat
entities[] list, each item a User Story, Feature or Functionality (docs/contracts.md,
section 1).
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from living_doc_utilities.contracts.common import AcceptanceCriterion, ContractModel, EntityCore, check_ac_ids_owned
from living_doc_utilities.contracts.envelope import ContractWarning, Metadata

CONTRACT_ID: Literal["doc-entities-v1.0.0"] = "doc-entities-v1.0.0"


class PageRef(ContractModel):
    """One PageObject file backing a Feature's surface - the full header or a
    cross-reference one (living-doc's docs/guides/living-doc-header-types.md,
    "Feature in a PageObject File"). Exactly one of a Feature's pages is the full
    header; the rest are cross-reference headers pointing back via `parent-feat`.
    """

    is_primary: bool = False
    route: str
    page_object: str
    owners: list[str] = Field(default_factory=list)
    purpose: str
    # A cross-reference page may scope functionalities to a subset of the Feature's;
    # empty means "not scoped - inherits the Feature's full functionalities list".
    functionalities: list[str] = Field(default_factory=list)


class Entity(EntityCore):
    """A documented User Story, Feature or Functionality.

    Every authored field of every entity type lives here, at its authored level; a field
    that does not apply to a given entity's type is simply absent. Which headings are
    required for which type is a parsing-time concern (a later package) - this model only
    fixes the contract's shape. The cross-cutting invariants that are structural, not
    parsing-time, are enforced below: a Feature's state is always derived, stub_reason
    only ever describes a Feature, and every acceptance criterion's id belongs to its
    entity.
    """

    # User Story / Functionality description; a Feature's is `purpose` instead (the two
    # authored forms - .feature header vs PageObject header - use different key names).
    narrative: Optional[str] = None
    # Feature description (PageObject header's `purpose:`).
    purpose: Optional[str] = None
    # User Story / Functionality .feature-header optional key: a pointer back to this
    # entity's issue-tracker counterpart, when one also exists.
    source: Optional[str] = None

    # User Story
    business_value: list[str] = Field(default_factory=list)
    acceptance_criteria: list[AcceptanceCriterion] = Field(default_factory=list)
    preconditions: list[str] = Field(default_factory=list)
    not_in_scope: list[str] = Field(default_factory=list)
    deprecated_at: Optional[str] = None
    deprecation_reason: Optional[str] = None
    superseded_by: Optional[str] = None

    # Feature
    surface_type: Optional[str] = None
    owners: list[str] = Field(default_factory=list)
    user_stories: list[str] = Field(default_factory=list)
    functionalities: list[str] = Field(default_factory=list)
    external_dependencies: list[str] = Field(default_factory=list)
    stub_reason: Optional[str] = None
    wizard_steps: list[str] = Field(default_factory=list)
    pages: list[PageRef] = Field(default_factory=list)

    # Functionality
    parent: Optional[str] = None
    func_type: Optional[str] = None
    rationale: Optional[str] = None

    @model_validator(mode="after")
    def _check_state_origin(self) -> "Entity":
        expected = "derived" if self.type == "DocumentedFeature" else "authored"
        if self.state_origin != expected:
            raise ValueError(
                f"state_origin must be '{expected}' for type '{self.type}' "
                "(a Feature's state is always derived; a User Story or Functionality's is always authored)"
            )
        return self

    @model_validator(mode="after")
    def _check_stub_reason_is_feature_only(self) -> "Entity":
        if self.stub_reason is not None and self.type != "DocumentedFeature":
            raise ValueError("stub_reason is only valid on a Feature")
        return self

    @model_validator(mode="after")
    def _check_acceptance_criteria_belong_to_this_entity(self) -> "Entity":
        check_ac_ids_owned(self.entity_id, (ac.id for ac in self.acceptance_criteria))
        return self

    @model_validator(mode="after")
    def _check_pages_have_exactly_one_primary(self) -> "Entity":
        if not self.pages:
            return self
        primary_count = sum(1 for page in self.pages if page.is_primary)
        if primary_count != 1:
            raise ValueError(f"a non-empty pages list must have exactly one primary PageRef, found {primary_count}")
        return self


class DocEntitiesResult(ContractModel):
    """The doc-entities-v1.0.0 artifact."""

    schema_version: Literal["doc-entities-v1.0.0"] = CONTRACT_ID
    metadata: Metadata
    warnings: list[ContractWarning] = Field(default_factory=list)
    entities: list[Entity] = Field(default_factory=list)


# Declares this contract's record roots (docs/contracts.md, section 1): the array levels
# that hold its records, read by schema_export.py to build metadata.stats.field_occupancy's
# key enum, and by the future stats/lineage helpers and shared test helpers (R1).
RECORD_ROOTS: dict[str, type[BaseModel]] = {"entities": Entity}
