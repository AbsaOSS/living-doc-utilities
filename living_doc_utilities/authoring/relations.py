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
contradicts another, `RELATION_TYPE_MISMATCH` for one resolving to the wrong entity type.
"""

from typing import Iterator

from living_doc_utilities.authoring.issue_body import ParsedEntity
from living_doc_utilities.contracts.codes import Code
from living_doc_utilities.contracts.envelope import ContractWarning


def _unresolved(entity: ParsedEntity, target_id: str, relation: str) -> ContractWarning:
    return ContractWarning(
        code=Code.UNRESOLVED_RELATION.name,
        message=f"'{relation}' points outside the collected entity set.",
        context=f"entity_id={entity.entity_id!r} target={target_id!r}",
    )


def _type_mismatch(entity: ParsedEntity, field: str, target: ParsedEntity, expected_type: str) -> ContractWarning:
    return ContractWarning(
        code=Code.RELATION_TYPE_MISMATCH.name,
        message=f"'{field}' resolves to {target.entity_id!r}, a {target.type}, not the expected {expected_type}.",
        context=(
            f"entity_id={entity.entity_id!r} field={field!r} target={target.entity_id!r} "
            f"actual_type={target.type!r} expected_type={expected_type!r}"
        ),
    )


def _relations_of(entity: ParsedEntity) -> Iterator[tuple[str, str, str]]:
    """Every `(field, target_id, expected_type)` relation `entity` declares, in the order
    `check_relations` reports them in: a Feature's `user_stories` then `functionalities`,
    a Functionality's `parent`, then any entity's `superseded_by` last."""
    if entity.type == "DocumentedFeature":
        for us_id in entity.user_stories:
            yield "user_stories", us_id, "DocumentedUserStory"
        for func_id in entity.functionalities:
            yield "functionalities", func_id, "DocumentedFunctionality"
    if entity.type == "DocumentedFunctionality" and entity.parent is not None:
        yield "parent", entity.parent, "DocumentedFeature"
    if entity.superseded_by is not None:
        yield "superseded_by", entity.superseded_by, entity.type


def check_relations(entities: list[ParsedEntity]) -> list[ContractWarning]:
    """Checks every declared relation against the entity set: it resolves within it
    (`UNRESOLVED_RELATION`), the target has the expected type (`RELATION_TYPE_MISMATCH`), and a
    resolved `functionalities`/`parent` link back-references consistently (`RELATION_MISMATCH`)."""
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

            if field == "functionalities" and target.parent is not None and target.parent != entity.entity_id:
                warnings.append(
                    ContractWarning(
                        code=Code.RELATION_MISMATCH.name,
                        message="Feature's declared functionality does not list it back as its own parent.",
                        context=f"entity_id={entity.entity_id!r} functionality={target_id!r}",
                    )
                )
            elif field == "parent" and target.functionalities and entity.entity_id not in target.functionalities:
                warnings.append(
                    ContractWarning(
                        code=Code.RELATION_MISMATCH.name,
                        message="Functionality's declared parent does not list it back in its own " "functionalities.",
                        context=f"entity_id={entity.entity_id!r} parent={target_id!r}",
                    )
                )

    return warnings
