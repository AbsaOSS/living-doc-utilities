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
Omission-parity for every cross-field model_validator rule schema_export mirrors into the
schema as `allOf` if/then/else (`schema_export._inject_cross_field_constraints`).

That function exists because `model_json_schema()` drops `model_validator`s outright and the
schemas are published as standalone release assets for non-Python consumers (R1/R2), so a
plain `jsonschema` validator has to reject what Pydantic rejects on its own. Plain JSON
Schema's `properties` keyword is a no-op on an *absent* key, so a block written without an
accompanying `required` silently mis-validates an omitted-but-defaulted field instead of
raising it. This exact mistake recurred four separate times in PR #131 as new rules were
added (`Entity.pages[].is_primary`, `AcCoverage.aspects`, `Metadata.source_inputs`,
`AspectCoverage.scenario_ids`), each caught by a separate review round instead of by one
general check.

This module is that one general check: for every optional/defaulted field a rule in
`_inject_cross_field_constraints` touches, it takes `full_sample(contract)`, drops that one
key, and asserts a plain `jsonschema.validate` agrees with what the Pydantic model does for
the same omission (constructed with the key omitted), and that both match the outcome the rule
contract requires (`OmissionCase.rejected`): they must never diverge, and never agree on the wrong answer. This is the only place this repository tests key-omission
parity; PR #131's one-off tests (`test_pages_primary_omitted_entirely_is_rejected_by_jsonschema_too`
and its siblings) were the worked examples this generalizes and have been removed in its
favour.

Not every cross-field rule is mirrored into the schema at all - id-ownership prefix checks and
`CoverageMatrixResult.PlannedSummary`'s total-equals-backlog-plus-targeted identity are
documented exceptions (schema_export._inject_cross_field_constraints's own docstring) because
plain JSON Schema cannot express them. This test only has to hold for whatever *is* mirrored.
"""

import json
from dataclasses import dataclass
from typing import Any, Union

import jsonschema
import pytest
from pydantic import BaseModel, ValidationError

from living_doc_utilities.contracts import (
    coverage_matrix,
    doc_entities,
    generator_ready,
    schema_export,
    testing,
    ui_test_catalog,
)

PathKey = Union[str, int]


@dataclass(frozen=True)
class OmissionCase:
    """One optional/defaulted field a schema_export cross-field rule touches: `contract_id`
    identifies which contract's full_sample to build and which schema to validate against;
    `path` locates the field inside that sample's dumped JSON, as a sequence of dict keys and
    list indices; `rejected` is what the rule contract says omitting that key must do, so the test
    catches both validators being wrong the same way, not just diverging."""

    case_id: str
    contract_id: str
    path: tuple[PathKey, ...]
    rejected: bool


CASES = [
    # Entity._check_pages_have_exactly_one_primary (PageRef.is_primary): dropping the only
    # primary page's is_primary must be rejected by both - PR #131's original defect.
    OmissionCase(
        "pages_is_primary_on_the_primary_page",
        doc_entities.CONTRACT_ID,
        ("entities", 2, "pages", 0, "is_primary"),
        rejected=True,
    ),
    # Entity._check_stub_reason_is_feature_only (Entity.stub_reason): omitting it is harmless
    # on a Feature (it already has a value; None or absent are both fine) and on a non-Feature
    # (it is already None).
    OmissionCase(
        "stub_reason_on_a_feature", doc_entities.CONTRACT_ID, ("entities", 2, "stub_reason"), rejected=False
    ),
    OmissionCase(
        "stub_reason_on_a_non_feature", doc_entities.CONTRACT_ID, ("entities", 0, "stub_reason"), rejected=False
    ),
    # AcceptanceCriterion._check_version_required_unless_planned (AcceptanceCriterion.version):
    # required unless planned; optional (targeted or not) when planned.
    OmissionCase(
        "ac_version_on_a_non_planned_ac",
        doc_entities.CONTRACT_ID,
        ("entities", 0, "acceptance_criteria", 0, "version"),
        rejected=True,
    ),
    OmissionCase(
        "ac_version_on_a_targeted_planned_ac",
        doc_entities.CONTRACT_ID,
        ("entities", 0, "acceptance_criteria", 1, "version"),
        rejected=False,
    ),
    # AcceptanceCriterion._check_removal_planned_only_when_deprecated (removal_planned):
    # required when deprecated; must stay unset otherwise.
    OmissionCase(
        "ac_removal_planned_on_a_deprecated_ac",
        doc_entities.CONTRACT_ID,
        ("entities", 1, "acceptance_criteria", 0, "removal_planned"),
        rejected=True,
    ),
    OmissionCase(
        "ac_removal_planned_on_a_non_deprecated_ac",
        doc_entities.CONTRACT_ID,
        ("entities", 0, "acceptance_criteria", 0, "removal_planned"),
        rejected=False,
    ),
    # AcCoverage._check_status_matches_aspects (AcCoverage.aspects, AcCoverage.scenario_ids):
    # without aspects a `covered` status needs scenario_ids, so dropping the aspects (which leaves
    # scenario_ids empty) is rejected; with aspects present the AC-level scenario_ids is irrelevant.
    OmissionCase(
        "ac_coverage_aspects_with_a_covered_status",
        coverage_matrix.CONTRACT_ID,
        ("entities", 0, "acceptance_criteria", 0, "aspects"),
        rejected=True,
    ),
    OmissionCase(
        "ac_coverage_scenario_ids_with_aspects_present",
        coverage_matrix.CONTRACT_ID,
        ("entities", 0, "acceptance_criteria", 0, "scenario_ids"),
        rejected=False,
    ),
    OmissionCase(
        "ac_coverage_scenario_ids_without_aspects",
        coverage_matrix.CONTRACT_ID,
        ("entities", 1, "acceptance_criteria", 0, "scenario_ids"),
        rejected=True,
    ),
    # AspectCoverage._check_status_matches_scenario_ids (AspectCoverage.scenario_ids): a covered
    # aspect needs at least one scenario.
    OmissionCase(
        "aspect_coverage_scenario_ids_with_a_covered_status",
        coverage_matrix.CONTRACT_ID,
        ("entities", 0, "acceptance_criteria", 0, "aspects", 0, "scenario_ids"),
        rejected=True,
    ),
    # Metadata.source_inputs: required with minItems 1 on transform outputs only (R7) - one
    # case per transform contract, since the rule is injected conditionally per contract id.
    OmissionCase(
        "source_inputs_on_generator_ready",
        generator_ready.CONTRACT_ID,
        ("metadata", "source_inputs"),
        rejected=True,
    ),
    OmissionCase(
        "source_inputs_on_coverage_matrix",
        coverage_matrix.CONTRACT_ID,
        ("metadata", "source_inputs"),
        rejected=True,
    ),
    OmissionCase(
        "source_inputs_on_ui_test_catalog",
        ui_test_catalog.CONTRACT_ID,
        ("metadata", "source_inputs"),
        rejected=True,
    ),
]


def _drop_key(data: Any, path: tuple[PathKey, ...]) -> None:
    container = data
    for key in path[:-1]:
        container = container[key]
    assert path[-1] in container, f"expected key {path[-1]!r} to be present at {path!r} before dropping it"
    del container[path[-1]]


def _pydantic_rejects(model_cls: type[BaseModel], data: dict) -> bool:
    try:
        model_cls.model_validate(data)
    except ValidationError:
        return True
    return False


def _jsonschema_rejects(data: dict, schema: dict) -> bool:
    return bool(list(jsonschema.Draft202012Validator(schema).iter_errors(data)))


@pytest.mark.parametrize("case", CASES, ids=[case.case_id for case in CASES])
def test_omitting_the_key_entirely_is_treated_the_same_by_pydantic_and_jsonschema(case: OmissionCase):
    """Pydantic and the exported JSON Schema agree on whether omitting this key is valid, and
    that agreed answer matches what the cross-field rule requires."""
    sample = testing.full_sample(case.contract_id)
    model_cls = type(sample)
    data = json.loads(sample.model_dump_json())

    _drop_key(data, case.path)

    pydantic_rejects = _pydantic_rejects(model_cls, data)
    jsonschema_rejects = _jsonschema_rejects(data, schema_export.load_schema(case.contract_id))

    assert pydantic_rejects == jsonschema_rejects, (
        f"{case.case_id}: pydantic {'rejects' if pydantic_rejects else 'accepts'} the omission, "
        f"jsonschema {'rejects' if jsonschema_rejects else 'accepts'} it - they must agree"
    )
    assert pydantic_rejects == case.rejected, (
        f"{case.case_id}: the rule contract says the omission must be "
        f"{'rejected' if case.rejected else 'accepted'}, but both validators "
        f"{'reject' if pydantic_rejects else 'accept'} it"
    )
