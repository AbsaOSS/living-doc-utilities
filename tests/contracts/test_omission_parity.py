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

"""Omitting a key a cross-field rule touches is judged the same by Pydantic and the exported JSON Schema."""

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
    """One optional field a mirrored cross-field rule touches, located by `path` in `contract_id`'s dumped sample."""

    case_id: str
    contract_id: str
    path: tuple[PathKey, ...]
    rejected: bool


# Rules left unencoded (listed in `schema_export.py::_inject_cross_field_constraints`) are out of scope here.
CASES = [
    # `doc_entities.py::Entity._check_pages_have_exactly_one_primary`: a dropped primary flag is rejected by both.
    OmissionCase(
        "pages_is_primary_on_the_primary_page",
        doc_entities.CONTRACT_ID,
        ("entities", 2, "pages", 0, "is_primary"),
        rejected=True,
    ),
    # `doc_entities.py::Entity._check_stub_reason_is_feature_only`: omitting stub_reason is harmless on any entity.
    OmissionCase(
        "stub_reason_on_a_feature", doc_entities.CONTRACT_ID, ("entities", 2, "stub_reason"), rejected=False
    ),
    OmissionCase(
        "stub_reason_on_a_non_feature", doc_entities.CONTRACT_ID, ("entities", 0, "stub_reason"), rejected=False
    ),
    # `common.py::AcceptanceCriterion._check_version_required_unless_planned`: version is required unless planned.
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
    # `common.py::AcceptanceCriterion._check_removal_planned_only_when_deprecated`: only when deprecated.
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
    # `coverage_matrix.py::AcCoverage._check_status_matches_aspects`: without aspects, covered needs scenario_ids.
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
    # `coverage_matrix.py::AspectCoverage._check_status_matches_scenario_ids`: a covered aspect needs a scenario.
    OmissionCase(
        "aspect_coverage_scenario_ids_with_a_covered_status",
        coverage_matrix.CONTRACT_ID,
        ("entities", 0, "acceptance_criteria", 0, "aspects", 0, "scenario_ids"),
        rejected=True,
    ),
    # Metadata.source_inputs: minItems 1 on transform outputs only (R7), so one case per transform contract.
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
    """Pydantic and the exported schema agree on whether omitting this key is valid, and match the rule."""
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
