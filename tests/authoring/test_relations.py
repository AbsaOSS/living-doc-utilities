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

"""`check_relations`: `UNRESOLVED_RELATION` and `RELATION_MISMATCH` (docs/contracts.md)."""

from living_doc_utilities.authoring.issue_body import ParsedEntity
from living_doc_utilities.authoring.relations import (
    RELATION_MISMATCH,
    UNRESOLVED_RELATION,
    check_relations,
)


def _feature(entity_id="FEAT-001", **overrides) -> ParsedEntity:
    fields = {"entity_id": entity_id, "type": "DocumentedFeature", "title": f"{entity_id} · Sample"}
    fields.update(overrides)
    return ParsedEntity(**fields)


def _func(entity_id="FUNC-001", **overrides) -> ParsedEntity:
    fields = {"entity_id": entity_id, "type": "DocumentedFunctionality", "title": f"{entity_id} · Sample"}
    fields.update(overrides)
    return ParsedEntity(**fields)


def _us(entity_id="US-001", **overrides) -> ParsedEntity:
    fields = {"entity_id": entity_id, "type": "DocumentedUserStory", "title": f"{entity_id} · Sample"}
    fields.update(overrides)
    return ParsedEntity(**fields)


def test_unresolved_relation_for_a_feature_pointing_outside_the_run():
    feature = _feature(user_stories=["US-999"], functionalities=["FUNC-999"])

    warnings = check_relations([feature])

    codes = [w.code for w in warnings]
    assert codes.count(UNRESOLVED_RELATION) == 2


def test_unresolved_relation_for_a_functionality_parent_and_superseded_by():
    func = _func(parent="FEAT-999", superseded_by="FUNC-888")

    warnings = check_relations([func])

    assert [w.code for w in warnings] == [UNRESOLVED_RELATION, UNRESOLVED_RELATION]


def test_relation_mismatch_when_feature_does_not_list_its_functionality_back():
    feature = _feature(functionalities=["FUNC-002"])
    func = _func(parent="FEAT-001")
    other_func = _func(entity_id="FUNC-002", parent="FEAT-001")

    warnings = check_relations([feature, func, other_func])

    assert [w.code for w in warnings] == [RELATION_MISMATCH]


def test_no_warnings_for_a_consistent_relation_set():
    feature = _feature(functionalities=["FUNC-001"], user_stories=["US-001"])
    func = _func(parent="FEAT-001")
    story = _us()

    warnings = check_relations([feature, func, story])

    assert warnings == []


def test_no_mismatch_when_feature_declares_no_functionalities_list_at_all():
    # Linked purely via `parent`, with the Feature carrying no `functionalities` list of
    # its own (empty list means "nothing declared", not "declared as empty").
    feature = _feature()
    func = _func(parent="FEAT-001")

    warnings = check_relations([feature, func])

    assert warnings == []
