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
`functionalities`.
"""

from living_doc_utilities.authoring.issue_body import ParsedEntity
from living_doc_utilities.contracts.envelope import ContractWarning

UNRESOLVED_RELATION = "UNRESOLVED_RELATION"
RELATION_MISMATCH = "RELATION_MISMATCH"


def _unresolved(entity: ParsedEntity, target_id: str, relation: str) -> ContractWarning:
    return ContractWarning(
        code=UNRESOLVED_RELATION,
        message=f"'{relation}' points outside the collected entity set.",
        context=f"entity_id={entity.entity_id!r} target={target_id!r}",
    )


def check_relations(entities: list[ParsedEntity]) -> list[ContractWarning]:
    """Checks every declared relation (`Feature.user_stories`, `Feature.functionalities`,
    `Functionality.parent`, any entity's `superseded_by`) against the given entity set."""
    warnings: list[ContractWarning] = []
    by_id = {entity.entity_id: entity for entity in entities}

    for entity in entities:
        if entity.type == "DocumentedFeature":
            for us_id in entity.user_stories:
                if us_id not in by_id:
                    warnings.append(_unresolved(entity, us_id, "user_stories"))
            for func_id in entity.functionalities:
                func = by_id.get(func_id)
                if func is None:
                    warnings.append(_unresolved(entity, func_id, "functionalities"))
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
            elif parent.functionalities and entity.entity_id not in parent.functionalities:
                warnings.append(
                    ContractWarning(
                        code=RELATION_MISMATCH,
                        message="Functionality's declared parent does not list it back in its own " "functionalities.",
                        context=f"entity_id={entity.entity_id!r} parent={entity.parent!r}",
                    )
                )

        if entity.superseded_by is not None and entity.superseded_by not in by_id:
            warnings.append(_unresolved(entity, entity.superseded_by, "superseded_by"))

    return warnings
