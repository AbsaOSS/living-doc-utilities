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
docs/contracts.md, R11: computes a contract result's own metadata.stats - cardinality and
field_occupancy - from the result model itself. "Each contract declares its own record
roots in its contract module. The stats helper (R11) ... reads the declaration from that
one place" - so this module takes a contract's RECORD_ROOTS declaration as an explicit
argument rather than keeping its own copy of which model belongs to which contract.
"""

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Sequence

from pydantic import BaseModel

from living_doc_utilities.contracts.common import AcceptanceCriterion, DocType
from living_doc_utilities.contracts.coverage_matrix import AcCoverage
from living_doc_utilities.contracts.envelope import Cardinality, Stats
from living_doc_utilities.contracts.schema_export import _unwrap
from living_doc_utilities.contracts.ui_tests import Scenario

# Record types whose lists tally into cardinality.acceptance_criteria / .scenarios
# wherever they occur in a contract's record-root subtree - doc-entities/doc-source/
# generator-ready nest AcceptanceCriterion under Entity, coverage-matrix nests AcCoverage
# under EntityCoverage, and ui-test-catalog nests Scenario several levels under
# FeatureFileCatalog; matching by type, not by field name or nesting depth, covers all of
# them with one rule.
_ACCEPTANCE_CRITERION_TYPES = (AcceptanceCriterion, AcCoverage)


def _is_empty(value: Any) -> bool:
    """R11: "null, "", [] and {} all count as empty; a present-but-empty field is not
    carried information."""
    return value is None or value == "" or value == [] or value == {}


def _is_entity_shaped(model: type[BaseModel]) -> bool:
    """An entity-identity record (docs/contracts.md, "Entity identity"): every documented
    entity and every coverage-matrix EntityCoverage row carries both entity_id and type."""
    fields = model.model_fields
    return "entity_id" in fields and "type" in fields


def _get_by_dotted_path(obj: Any, dotted: str) -> Any:
    for part in dotted.split("."):
        obj = getattr(obj, part)
    return obj


@dataclass
class _WalkState:
    """The recursive walk's accumulated output: field_occupancy, the entities_by_type
    breakdown, and the entities/acceptance_criteria/scenarios running totals."""

    occupancy: dict[str, int] = field(default_factory=dict)
    entities_by_type: "Counter[DocType]" = field(default_factory=Counter)
    entities: int = 0
    acceptance_criteria: int = 0
    scenarios: int = 0


def _walk(instances: Sequence[Any], model: type[BaseModel], prefix: str, state: _WalkState) -> None:
    if _is_entity_shaped(model):
        state.entities += len(instances)
        for instance in instances:
            state.entities_by_type[instance.type] += 1
    if issubclass(model, _ACCEPTANCE_CRITERION_TYPES):
        state.acceptance_criteria += len(instances)
    if issubclass(model, Scenario):
        state.scenarios += len(instances)

    for field_name, field_info in model.model_fields.items():
        item_type, is_array = _unwrap(field_info.annotation)
        path = f"{prefix}{field_name}[]" if is_array else f"{prefix}{field_name}"
        if isinstance(item_type, type) and issubclass(item_type, BaseModel):
            if is_array:
                nested = [item for instance in instances for item in getattr(instance, field_name)]
            else:
                nested = [value for instance in instances if (value := getattr(instance, field_name)) is not None]
            _walk(nested, item_type, f"{path}.", state)
        else:
            state.occupancy[path] = sum(1 for instance in instances if not _is_empty(getattr(instance, field_name)))


def compute_stats(result: BaseModel, record_roots: dict[str, type[BaseModel]], reported: Cardinality) -> Stats:
    """
    Computes a fresh metadata.stats for `result`: cardinality (entities, entities_by_type,
    acceptance_criteria, scenarios and warnings_by_code are derived from `result` itself;
    sources_configured, sources_failed, unresolved_refs and entities_skipped are carried
    over from `reported` unchanged - R11 says these four "are filled from what the
    producing collector or transform reports, not computed by this helper itself") and
    field_occupancy (keyed by record-relative path, starting at each of `record_roots`'
    own root).

    @param result: a contract result model instance.
    @param record_roots: the contract's RECORD_ROOTS declaration (its own module's constant).
    @param reported: the caller's own Cardinality; only its sources_configured,
        sources_failed, unresolved_refs and entities_skipped are read - the rest of this
        function's output is computed fresh from `result`.
    @return: the computed Stats, ready to assign to result.metadata.stats.
    """
    state = _WalkState()
    for root_name, root_model in record_roots.items():
        instances = list(_get_by_dotted_path(result, root_name))
        _walk(instances, root_model, f"{root_name}[].", state)

    warnings_by_code: "Counter[str]" = Counter(warning.code for warning in getattr(result, "warnings", []))

    cardinality = Cardinality(
        entities=state.entities,
        entities_by_type=dict(state.entities_by_type),
        acceptance_criteria=state.acceptance_criteria,
        scenarios=state.scenarios,
        warnings_by_code=dict(warnings_by_code),
        sources_configured=reported.sources_configured,
        sources_failed=reported.sources_failed,
        unresolved_refs=reported.unresolved_refs,
        entities_skipped=reported.entities_skipped,
    )
    return Stats(cardinality=cardinality, field_occupancy=state.occupancy)
