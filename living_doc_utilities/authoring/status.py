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
`derive_statuses` (docs/contracts.md, "State and `state_origin`"): settles every entity's
final `state`/`state_origin` in one pass, after all entities in a run have been parsed and
their relations built. A User Story / Functionality's state is authored, falling back to a
derivation from its own acceptance criteria only when missing; a Feature's state is always
derived - from its deprecation, else its Functionalities, else its User Stories, else
`active` with an `ORPHAN_FEATURE` warning.
"""

from typing import Iterable

from living_doc_utilities.authoring.issue_body import ParsedEntity
from living_doc_utilities.contracts.codes import Code
from living_doc_utilities.contracts.common import AcceptanceCriterion
from living_doc_utilities.contracts.envelope import ContractWarning


# active > in_review > (all-deprecated) > planned - shared by both derivation tables (a User
# Story/Functionality deriving from its own ACs, and a Feature deriving from its linked
# Functionalities'/User Stories' already-settled states): the strongest signal in the group
# wins, "everything has retired" is itself a signal, and "nothing to go on" is `planned`.
def _majority_state(states: Iterable[str]) -> str:
    state_list = list(states)
    state_set = set(state_list)
    if "active" in state_set:
        return "active"
    if "in_review" in state_set:
        return "in_review"
    if state_list and state_set <= {"deprecated"}:
        return "deprecated"
    return "planned"


def _ac_states(acceptance_criteria: list[AcceptanceCriterion]) -> list[str]:
    return [ac.state for ac in acceptance_criteria]


def _is_mismatch(authored: str, acceptance_criteria: list[AcceptanceCriterion]) -> bool:
    states = set(_ac_states(acceptance_criteria))
    if authored == "planned":
        return bool(states & {"active", "deprecated"})
    if authored == "active":
        return bool(acceptance_criteria) and not (states & {"active", "deprecated"})
    if authored == "deprecated":
        return bool(states & {"active", "in_review", "planned"})
    return False  # "in_review" never mismatches, regardless of AC states


def _derive_us_or_func(entity: ParsedEntity, warnings: list[ContractWarning]) -> ParsedEntity:
    if entity.state is None:
        state = _majority_state(_ac_states(entity.acceptance_criteria))
        warnings.append(
            ContractWarning(
                code=Code.MISSING_STATUS.name,
                message="No authored status; derived from acceptance criteria.",
                context=f"entity_id={entity.entity_id!r} derived={state!r}",
            )
        )
        return entity.model_copy(update={"state": state, "state_origin": "authored"})

    if _is_mismatch(entity.state, entity.acceptance_criteria):
        warnings.append(
            ContractWarning(
                code=Code.STATUS_AC_MISMATCH.name,
                message="Authored status contradicts the entity's own acceptance criteria.",
                context=f"entity_id={entity.entity_id!r} authored={entity.state!r}",
            )
        )
    return entity.model_copy(update={"state_origin": "authored"})


def _linked_functionalities(feature: ParsedEntity, by_id: dict[str, ParsedEntity]) -> list[ParsedEntity]:
    return [
        other
        for other in by_id.values()
        if other.type == "DocumentedFunctionality"
        and (other.parent == feature.entity_id or (other.parent is None and other.entity_id in feature.functionalities))
    ]


def _linked_user_stories(feature: ParsedEntity, by_id: dict[str, ParsedEntity]) -> list[ParsedEntity]:
    return [
        other
        for other in by_id.values()
        if other.type == "DocumentedUserStory" and other.entity_id in feature.user_stories
    ]


def _derive_feature(
    feature: ParsedEntity, resolved_non_features: dict[str, ParsedEntity], warnings: list[ContractWarning]
) -> ParsedEntity:
    if feature.deprecated_at is not None:
        return feature.model_copy(update={"state": "deprecated", "state_origin": "derived"})

    linked_functionalities = _linked_functionalities(feature, resolved_non_features)
    if linked_functionalities:
        state = _majority_state(f.state for f in linked_functionalities if f.state is not None)
        return feature.model_copy(update={"state": state, "state_origin": "derived"})

    linked_user_stories = _linked_user_stories(feature, resolved_non_features)
    if linked_user_stories:
        state = _majority_state(u.state for u in linked_user_stories if u.state is not None)
        return feature.model_copy(update={"state": state, "state_origin": "derived"})

    warnings.append(
        ContractWarning(
            code=Code.ORPHAN_FEATURE.name,
            message="Feature has no linked Functionality and no linked User Story in this run.",
            context=f"entity_id={feature.entity_id!r}",
        )
    )
    return feature.model_copy(update={"state": "active", "state_origin": "derived"})


def derive_statuses(entities: list[ParsedEntity]) -> tuple[list[ParsedEntity], list[ContractWarning]]:
    """Settles `state`/`state_origin` on every entity. Non-Feature entities are resolved
    first (their own ACs are the only input they need); Features are resolved from those
    already-settled states, so input order never matters.
    """
    warnings: list[ContractWarning] = []
    resolved_non_features: dict[str, ParsedEntity] = {}
    for entity in entities:
        if entity.type != "DocumentedFeature":
            resolved_non_features[entity.entity_id] = _derive_us_or_func(entity, warnings)

    result: list[ParsedEntity] = []
    for entity in entities:
        if entity.type == "DocumentedFeature":
            result.append(_derive_feature(entity, resolved_non_features, warnings))
        else:
            result.append(resolved_non_features[entity.entity_id])

    return result, warnings
