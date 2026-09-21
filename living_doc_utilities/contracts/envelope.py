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
The shared metadata envelope (docs/contracts.md, "The metadata envelope"): one model
reused by every contract, parametrised only in metadata.stats.field_occupancy's key
enum, which schema_export.py fills in per contract.
"""

from datetime import datetime
from typing import Annotated, Literal, Optional

from pydantic import Field, StringConstraints, model_validator

from living_doc_utilities.contracts.common import ContractModel, DocType

# A collector's own project id: lowercase alphanumeric plus hyphen, starting alphanumeric.
PROJECT_ID_PATTERN = r"^[a-z0-9][a-z0-9-]*$"

# A warning code, and the key pattern of metadata.stats.cardinality.warnings_by_code.
WARNING_CODE_PATTERN = r"^[A-Z][A-Z0-9_]*$"

# The key pattern of the *audit* field_occupancy maps carried in metadata.source_inputs[]
# (R9): a record-relative path belonging to the input's own contract, so it is
# pattern-checked rather than enumerated. A contract's *own* field_occupancy is enumerated
# instead - see schema_export.py.
AUDIT_FIELD_PATH_PATTERN = r"^[a-z][a-z0-9_]*(\[\])?(\.[a-z][a-z0-9_]*(\[\])?)*$"

# schema_version format shared by every contract artifact (R4/R5): "<name>-v<major.minor.patch>",
# name = lowercase-alphanumeric segments joined by single hyphens; group 1 is the name alone.
CONTRACT_ID_PATTERN = r"^([a-z0-9]+(?:-[a-z0-9]+)*)-v\d+\.\d+\.\d+$"


class Producer(ContractModel):
    """Identifies the tool that wrote this specific file (R6)."""

    name: str
    version: str
    build: Optional[str] = None
    utilities_version: str


class Run(ContractModel):
    """CI run context the file was produced under. Audit information only."""

    run_id: Optional[str] = None
    run_attempt: Optional[str] = None
    actor: Optional[str] = None
    workflow: Optional[str] = None
    ref: Optional[str] = None
    sha: Optional[str] = None


class Source(ContractModel):
    """Identifies the one project, and the systems/organizations/repositories, a file documents."""

    project_id: str = Field(pattern=PROJECT_ID_PATTERN)
    systems: list[Literal["GitHub", "AzureDevOps"]] = Field(default_factory=list)
    organizations: list[str] = Field(default_factory=list)
    repositories: list[str] = Field(default_factory=list)
    extraction_mode: Optional[Literal["markdown", "field-map"]] = None

    @model_validator(mode="after")
    def _check_repositories_reference_known_organizations(self) -> "Source":
        known_organizations = set(self.organizations)
        for repository in self.repositories:
            organization = repository.split("/", 1)[0]
            if organization not in known_organizations:
                raise ValueError(
                    f"repositories entry '{repository}' references organization '{organization}', "
                    "which is not listed in organizations"
                )
        return self


class Cardinality(ContractModel):
    """Fixed record counts carried in metadata.stats.cardinality (R11)."""

    entities: int = 0
    entities_by_type: dict[DocType, int] = Field(default_factory=dict)
    acceptance_criteria: int = 0
    scenarios: int = 0
    warnings_by_code: dict[Annotated[str, StringConstraints(pattern=WARNING_CODE_PATTERN)], int] = Field(
        default_factory=dict
    )
    sources_configured: int = 0
    sources_failed: int = 0
    unresolved_refs: int = 0
    entities_skipped: int = 0


class Stats(ContractModel):
    """A file's own metadata.stats: cardinality plus field_occupancy keyed by that file's
    own contract paths. schema_export.py enumerates the allowed keys per contract."""

    cardinality: Cardinality
    field_occupancy: dict[str, int] = Field(default_factory=dict)


class AuditStats(ContractModel):
    """The stats carried per input inside metadata.source_inputs[] (R7): an audit record of
    another contract's paths, so field_occupancy is pattern-checked rather than enumerated."""

    cardinality: Cardinality
    field_occupancy: dict[Annotated[str, StringConstraints(pattern=AUDIT_FIELD_PATH_PATTERN)], int] = Field(
        default_factory=dict
    )


class SourceInputEntry(ContractModel):
    """One transform input's provenance and stats (R7). Collector outputs carry none."""

    schema_version: str = Field(pattern=CONTRACT_ID_PATTERN)
    producer: Producer
    run: Run = Field(default_factory=Run)
    source: Source
    stats: AuditStats
    selected_stats: AuditStats


class Metadata(ContractModel):
    """The envelope every contract artifact carries under its top-level metadata key."""

    producer: Producer
    run: Run = Field(default_factory=Run)
    source: Source
    generated_at: datetime
    stats: Stats
    source_inputs: list[SourceInputEntry] = Field(default_factory=list)


class ContractWarning(ContractModel):
    """One entry of an artifact's top-level warnings[] array."""

    code: str = Field(pattern=WARNING_CODE_PATTERN)
    message: str
    context: Optional[str] = None


def check_transform_source_inputs(metadata: Metadata) -> None:
    """R7: a transform output's metadata.source_inputs[] always has at least one entry - a
    transform always has at least its documentation input. Only a collector output (which
    has no artifact input) legitimately carries an empty list, so this is called by each
    transform-output result model (generator-ready, coverage-matrix, ui-test-catalog), never
    by Metadata itself.
    """
    if not metadata.source_inputs:
        raise ValueError("metadata.source_inputs must have at least one entry for a transform output (R7)")
