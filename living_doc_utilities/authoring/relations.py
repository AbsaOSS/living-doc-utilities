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
Cross-entity relation checking, run once per collector run over the whole collected set:
`UNRESOLVED_RELATION` for a relation pointing outside it, `RELATION_MISMATCH` for one that
contradicts another, `RELATION_TYPE_MISMATCH` for one resolving to the wrong entity type - or,
for a `feature_dependencies` target, to a Feature that is not an `API` surface.
"""

from typing import Iterator, Optional

from living_doc_utilities.authoring.issue_body import ParsedEntity
from living_doc_utilities.contracts.codes import Code
from living_doc_utilities.contracts.envelope import ContractWarning


def _unresolved(entity: ParsedEntity, target_id: str, relation: str) -> ContractWarning:
    return ContractWarning(
        code=Code.UNRESOLVED_RELATION.name,
        message=f"'{relation}' points outside the collected entity set.",
        context=f"entity_id={entity.entity_id!r} target={target_id!r}",
        entity_id=entity.entity_id,
    )


def _type_mismatch(
    entity: ParsedEntity, field: str, target: ParsedEntity, expected_type: str, actual_type: Optional[str] = None
) -> ContractWarning:
    """`actual_type` describes the target in the message when its type alone is not the mismatch."""
    actual_type = target.type if actual_type is None else actual_type
    return ContractWarning(
        code=Code.RELATION_TYPE_MISMATCH.name,
        message=f"'{field}' resolves to {target.entity_id!r}, a {actual_type}, not the expected {expected_type}.",
        context=(
            f"entity_id={entity.entity_id!r} field={field!r} target={target.entity_id!r} "
            f"actual_type={actual_type!r} expected_type={expected_type!r}"
        ),
        entity_id=entity.entity_id,
    )


def _feature_dependency_warning(entity: ParsedEntity, target: ParsedEntity) -> list[ContractWarning]:
    """A resolved `feature_dependencies` target breaks a canon rule when it is the declaring
    Feature itself (`RELATION_MISMATCH`) or a Feature with no `API` surface
    (`RELATION_TYPE_MISMATCH`): only a surface with a contract anchor can be called."""
    if target.entity_id == entity.entity_id:
        return [
            ContractWarning(
                code=Code.RELATION_MISMATCH.name,
                message="Feature declares a feature dependency on itself.",
                context=f"entity_id={entity.entity_id!r} target={target.entity_id!r}",
                entity_id=entity.entity_id,
            )
        ]
    if target.surface_type != "API":
        actual = f"{target.type} with surface_type={target.surface_type!r}"
        return [_type_mismatch(entity, "feature_dependencies", target, "API DocumentedFeature", actual)]
    return []


def _relations_of(entity: ParsedEntity) -> Iterator[tuple[str, str, str]]:
    """Every `(field, target_id, expected_type)` relation `entity` declares, in the order
    `check_relations` reports them in: a Feature's `user_stories`, `functionalities` then
    `feature_dependencies`, a Functionality's `parent`, then any entity's `superseded_by` last."""
    if entity.type == "DocumentedFeature":
        for us_id in entity.user_stories:
            yield "user_stories", us_id, "DocumentedUserStory"
        for func_id in entity.functionalities:
            yield "functionalities", func_id, "DocumentedFunctionality"
        for feat_id in entity.feature_dependencies:
            yield "feature_dependencies", feat_id, "DocumentedFeature"
    if entity.type == "DocumentedFunctionality" and entity.parent is not None:
        yield "parent", entity.parent, "DocumentedFeature"
    if entity.superseded_by is not None:
        yield "superseded_by", entity.superseded_by, entity.type


def check_relations(entities: list[ParsedEntity]) -> list[ContractWarning]:
    """Checks every declared relation against the entity set: it resolves within it
    (`UNRESOLVED_RELATION`), the target has the expected type (`RELATION_TYPE_MISMATCH`), a
    resolved `functionalities`/`parent` link back-references consistently (`RELATION_MISMATCH`), and a
    `feature_dependencies` target is an `API` Feature other than the declaring Feature itself."""
    warnings: list[ContractWarning] = []
    by_id = {entity.entity_id: entity for entity in entities}

    for entity in entities:
        for field, target_id, expected_type in _relations_of(entity):
            target = by_id.get(target_id)
            if target is None:
                warnings.append(_unresolved(entity, target_id, field))
                continue
            if target.type != expected_type:
                warnings.append(_type_mismatch(entity, field, target, expected_type))
                continue

            if field == "feature_dependencies":
                warnings.extend(_feature_dependency_warning(entity, target))
            elif field == "functionalities" and target.parent is not None and target.parent != entity.entity_id:
                warnings.append(
                    ContractWarning(
                        code=Code.RELATION_MISMATCH.name,
                        message="Feature's declared functionality does not list it back as its own parent.",
                        context=f"entity_id={entity.entity_id!r} functionality={target_id!r}",
                        entity_id=entity.entity_id,
                    )
                )
            elif field == "parent" and target.functionalities and entity.entity_id not in target.functionalities:
                warnings.append(
                    ContractWarning(
                        code=Code.RELATION_MISMATCH.name,
                        message="Functionality's declared parent does not list it back in its own " "functionalities.",
                        context=f"entity_id={entity.entity_id!r} parent={target_id!r}",
                        entity_id=entity.entity_id,
                    )
                )

    return warnings
