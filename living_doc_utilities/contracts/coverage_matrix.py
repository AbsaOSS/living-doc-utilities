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
corpus. Computed only for `active`/`deprecated` acceptance criteria; `in_review`/`planned`
are never counted, their test activity reported as a warning instead.
"""

import math
from fractions import Fraction
from typing import Annotated, Iterable, Literal, Optional

from pydantic import BaseModel, Field, StringConstraints, model_validator

from living_doc_utilities.contracts.common import (
    AC_ID_PATTERN,
    VERSION_PATTERN,
    ContractModel,
    LifecycleState,
    ViewDocument,
    check_ac_ids_owned,
)
from living_doc_utilities.contracts.envelope import ContractWarning, Metadata, check_transform_source_inputs

CONTRACT_ID: Literal["coverage-matrix-v1.0.0"] = "coverage-matrix-v1.0.0"

# The only two states a coverage row is computed for; in_review/planned ACs are never counted.
CountedState = Literal["active", "deprecated"]

CoverageStatus = Literal["covered", "partially_covered", "not_covered"]
AspectStatus = Literal["covered", "not_covered"]


def _check_status_evidence(status: str, scenario_ids: list[str]) -> None:
    """Status is evidence-backed by scenario_ids: covered only when there's at least one
    linked scenario - shared by AspectCoverage's own check and AcCoverage's no-aspects case."""
    expected = "covered" if scenario_ids else "not_covered"
    if status != expected:
        raise ValueError(f"status must be '{expected}' given scenario_ids={scenario_ids!r}, got '{status}'")


class AspectCoverage(ContractModel):
    """One aspect of an acceptance criterion's per-aspect breakdown."""

    aspect: str
    status: AspectStatus
    scenario_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_status_matches_scenario_ids(self) -> "AspectCoverage":
        _check_status_evidence(self.status, self.scenario_ids)
        return self


class AcCoverage(ContractModel):
    """One acceptance criterion's resolved coverage row."""

    ac_id: str = Field(pattern=AC_ID_PATTERN)
    state: CountedState
    status: CoverageStatus
    aspects: list[AspectCoverage] = Field(default_factory=list)
    scenario_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_status_matches_aspects(self) -> "AcCoverage":
        # With aspects: covered when every aspect is, not_covered when none is, else partially_covered.
        # Without: plain covered/not_covered.
        if not self.aspects:
            if self.status == "partially_covered":
                raise ValueError("status cannot be 'partially_covered' when aspects is empty")
            _check_status_evidence(self.status, self.scenario_ids)
            return self
        covered = self.covered_aspects()
        if covered == len(self.aspects):
            expected = "covered"
        elif covered == 0:
            expected = "not_covered"
        else:
            expected = "partially_covered"
        if self.status != expected:
            raise ValueError(
                f"status must be '{expected}' given aspects={[a.status for a in self.aspects]!r}, got '{self.status}'"
            )
        return self

    def covered_aspects(self) -> int:
        """How many of this row's aspects are covered: the covered side of a covered/declared figure, e.g. 1/3."""
        return sum(1 for aspect in self.aspects if aspect.status == "covered")

    def weight(self) -> Fraction:
        """This row's share of a coverage figure: 1 covered, 0 not_covered, covered/declared aspects otherwise."""
        if self.status == "partially_covered":
            return Fraction(self.covered_aspects(), len(self.aspects))
        return Fraction(1 if self.status == "covered" else 0)


def _percentage(weights: Fraction, counted: int) -> Optional[float]:
    """`weights` over `counted` rows as a percentage, rounded once to one decimal, ROUND_HALF_UP; None for 0 rows.
    The exact Fraction is rounded directly, so no float or Decimal step can round it a second time."""
    if counted == 0:
        return None
    tenths = math.floor(weights * 1000 / counted + Fraction(1, 2))
    return tenths / 10


class CoverageSummary(ContractModel):
    """Counted acceptance-criteria totals and their coverage figure, over the rows it summarises: an entity's own
    rows, or every row of the matrix. Recomputed from those rows by the model that holds it."""

    counted_acs: int = Field(ge=0)
    covered_acs: int = Field(ge=0)
    partially_covered_acs: int = Field(ge=0)
    not_covered_acs: int = Field(ge=0)
    coverage_pct: Optional[float] = Field(ge=0, le=100)

    @classmethod
    def from_rows(cls, rows: Iterable[AcCoverage]) -> "CoverageSummary":
        """The summary of `rows`, each weighted by `AcCoverage.weight`; a producer writes exactly this.

        @param rows: the coverage rows to summarise.
        @return: the counts by status and `coverage_pct`, None when `rows` is empty.
        """
        rows = list(rows)
        return cls(
            counted_acs=len(rows),
            covered_acs=sum(1 for row in rows if row.status == "covered"),
            partially_covered_acs=sum(1 for row in rows if row.status == "partially_covered"),
            not_covered_acs=sum(1 for row in rows if row.status == "not_covered"),
            coverage_pct=_percentage(sum((row.weight() for row in rows), Fraction(0)), len(rows)),
        )


def _check_summary(summary: CoverageSummary, rows: Iterable[AcCoverage], owner: str) -> None:
    """A summary equals the one `CoverageSummary.from_rows` computes from the rows it summarises."""
    expected = CoverageSummary.from_rows(rows)
    if summary != expected:
        raise ValueError(
            f"summary of {owner} must equal the one computed from its rows: "
            f"expected {expected.model_dump()!r}, got {summary.model_dump()!r}"
        )


class EntityCoverage(ContractModel):
    """A User Story or Functionality's acceptance criteria, each with its coverage row.
    `state` is the entity's own lifecycle state (full `LifecycleState`, not `CountedState`) -
    independent of which ACs are counted; a planned/in_review entity can still own counted ACs."""

    entity_id: str
    type: Literal["DocumentedUserStory", "DocumentedFunctionality"]
    title: str
    state: LifecycleState
    acceptance_criteria: list[AcCoverage] = Field(default_factory=list)
    summary: CoverageSummary

    @model_validator(mode="after")
    def _check_summary_matches_rows(self) -> "EntityCoverage":
        _check_summary(self.summary, self.acceptance_criteria, f"entity '{self.entity_id}'")
        return self


class PlannedSummary(ContractModel):
    """Planned (not-yet-implemented) acceptance-criteria totals, rendered only in the inner view."""

    total: int = Field(ge=0)
    backlog: int = Field(ge=0)
    by_target_version: dict[Annotated[str, StringConstraints(pattern=VERSION_PATTERN)], Annotated[int, Field(ge=0)]] = (
        Field(default_factory=dict)
    )

    @model_validator(mode="after")
    def _check_total_equals_backlog_plus_targeted(self) -> "PlannedSummary":
        # Every planned AC is either backlog (no target version) or targeted at exactly one version.
        targeted = sum(self.by_target_version.values())
        if self.total != self.backlog + targeted:
            raise ValueError(
                f"total ({self.total}) must equal backlog ({self.backlog}) + "
                f"sum(by_target_version.values()) ({targeted})"
            )
        return self


Document = ViewDocument


class CoverageMatrixResult(ContractModel):
    """The coverage-matrix-v1.0.0 artifact."""

    schema_version: Literal["coverage-matrix-v1.0.0"] = CONTRACT_ID
    metadata: Metadata
    warnings: list[ContractWarning] = Field(default_factory=list)
    document: Document
    entities: list[EntityCoverage] = Field(default_factory=list)
    planned_summary: PlannedSummary
    summary: CoverageSummary

    @model_validator(mode="after")
    def _check_source_inputs_not_empty(self) -> "CoverageMatrixResult":
        check_transform_source_inputs(self.metadata)
        return self

    @model_validator(mode="after")
    def _check_acceptance_criteria_belong_to_this_entity(self) -> "CoverageMatrixResult":
        for entity in self.entities:
            check_ac_ids_owned(entity.entity_id, (ac.ac_id for ac in entity.acceptance_criteria))
        return self

    @model_validator(mode="after")
    def _check_summary_matches_every_row(self) -> "CoverageMatrixResult":
        # Every row of every entity, never the entities' own percentages: a 1-row entity weighs as 1 row, not as half.
        _check_summary(
            self.summary, (row for entity in self.entities for row in entity.acceptance_criteria), "the matrix"
        )
        return self


# This contract's record roots; see `doc_entities.py::RECORD_ROOTS`.
RECORD_ROOTS: dict[str, type[BaseModel]] = {"entities": EntityCoverage}
