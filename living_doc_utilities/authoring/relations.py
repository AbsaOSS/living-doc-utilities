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
Cross-entity relation checking, run once per collector run over the whole collected set
(docs/contracts.md's collector warnings table): `UNRESOLVED_RELATION` for a relation that
points outside that set, `RELATION_MISMATCH` for one that contradicts another - e.g. a
Functionality's declared `parent` whose Feature doesn't list it back in its own
`functionalities` - and `RELATION_TYPE_MISMATCH` for one that resolves inside the set but
to an entity of the wrong type - e.g. a Functionality's id copy-pasted into a Feature's
`user_stories`.
"""

from living_doc_utilities.authoring.issue_body import ParsedEntity
from living_doc_utilities.contracts.envelope import ContractWarning

UNRESOLVED_RELATION = "UNRESOLVED_RELATION"
RELATION_MISMATCH = "RELATION_MISMATCH"
RELATION_TYPE_MISMATCH = "RELATION_TYPE_MISMATCH"


def _unresolved(entity: ParsedEntity, target_id: str, relation: str) -> ContractWarning:
    return ContractWarning(
        code=UNRESOLVED_RELATION,
        message=f"'{relation}' points outside the collected entity set.",
        context=f"entity_id={entity.entity_id!r} target={target_id!r}",
    )


def _type_mismatch(entity: ParsedEntity, field: str, target: ParsedEntity, expected_type: str) -> ContractWarning:
    return ContractWarning(
        code=RELATION_TYPE_MISMATCH,
        message=f"'{field}' resolves to {target.entity_id!r}, a {target.type}, not the expected {expected_type}.",
        context=(
            f"entity_id={entity.entity_id!r} field={field!r} target={target.entity_id!r} "
            f"actual_type={target.type!r} expected_type={expected_type!r}"
        ),
    )


def check_relations(entities: list[ParsedEntity]) -> list[ContractWarning]:
    """Checks every declared relation (`Feature.user_stories`, `Feature.functionalities`,
    `Functionality.parent`, any entity's `superseded_by`) against the given entity set: that
    it resolves within it (`UNRESOLVED_RELATION`), and that the resolved target is of the
    field's expected type (`RELATION_TYPE_MISMATCH`)."""
    warnings: list[ContractWarning] = []
    by_id = {entity.entity_id: entity for entity in entities}

    for entity in entities:
        if entity.type == "DocumentedFeature":
            for us_id in entity.user_stories:
                story = by_id.get(us_id)
                if story is None:
                    warnings.append(_unresolved(entity, us_id, "user_stories"))
                elif story.type != "DocumentedUserStory":
                    warnings.append(_type_mismatch(entity, "user_stories", story, "DocumentedUserStory"))
            for func_id in entity.functionalities:
                func = by_id.get(func_id)
                if func is None:
                    warnings.append(_unresolved(entity, func_id, "functionalities"))
                elif func.type != "DocumentedFunctionality":
                    warnings.append(_type_mismatch(entity, "functionalities", func, "DocumentedFunctionality"))
                elif func.parent is not None and func.parent != entity.entity_id:
                    warnings.append(
                        ContractWarning(
                            code=RELATION_MISMATCH,
                            message="Feature's declared functionality does not list it back as its own parent.",
                            context=f"entity_id={entity.entity_id!r} functionality={func_id!r}",
                        )
                    )

        if entity.type == "DocumentedFunctionality" and entity.parent is not None:
            parent = by_id.get(entity.parent)
            if parent is None:
                warnings.append(_unresolved(entity, entity.parent, "parent"))
            elif parent.type != "DocumentedFeature":
                warnings.append(_type_mismatch(entity, "parent", parent, "DocumentedFeature"))
            elif parent.functionalities and entity.entity_id not in parent.functionalities:
                warnings.append(
                    ContractWarning(
                        code=RELATION_MISMATCH,
                        message="Functionality's declared parent does not list it back in its own " "functionalities.",
                        context=f"entity_id={entity.entity_id!r} parent={entity.parent!r}",
                    )
                )

        if entity.superseded_by is not None:
            target = by_id.get(entity.superseded_by)
            if target is None:
                warnings.append(_unresolved(entity, entity.superseded_by, "superseded_by"))
            elif target.type != entity.type:
                warnings.append(_type_mismatch(entity, "superseded_by", target, entity.type))

    return warnings
