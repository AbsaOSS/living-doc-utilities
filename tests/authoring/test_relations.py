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

"""`check_relations`: `UNRESOLVED_RELATION`, `RELATION_MISMATCH` and `RELATION_TYPE_MISMATCH`
(docs/contracts.md)."""

from living_doc_utilities.authoring.issue_body import ParsedEntity, parse_issue_body
from living_doc_utilities.authoring.relations import check_relations
from living_doc_utilities.authoring.status import derive_statuses
from living_doc_utilities.contracts.codes import Code
from tests.authoring.golden.helpers import read_fixture


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
    """A Feature referencing ids outside the collected set gets one unresolved-relation warning per dangling id."""
    feature = _feature(user_stories=["US-999"], functionalities=["FUNC-999"])

    warnings = check_relations([feature])

    codes = [w.code for w in warnings]
    assert codes.count(Code.UNRESOLVED_RELATION.name) == 2


def test_unresolved_relation_for_a_functionality_parent_and_superseded_by():
    """A Functionality whose parent and superseded-by point outside the run each get their own unresolved warning."""
    func = _func(parent="FEAT-999", superseded_by="FUNC-888")

    warnings = check_relations([func])

    assert [w.code for w in warnings] == [Code.UNRESOLVED_RELATION.name, Code.UNRESOLVED_RELATION.name]


def test_relation_mismatch_when_feature_does_not_list_its_functionality_back():
    """A Feature is flagged with a relation mismatch when it fails to list back a Functionality naming it as parent."""
    feature = _feature(functionalities=["FUNC-002"])
    func = _func(parent="FEAT-001")
    other_func = _func(entity_id="FUNC-002", parent="FEAT-001")

    warnings = check_relations([feature, func, other_func])

    assert [w.code for w in warnings] == [Code.RELATION_MISMATCH.name]


def test_no_warnings_for_a_consistent_relation_set():
    """A fully consistent, correctly cross-linked set of Feature, Functionality and User Story raises no warnings."""
    feature = _feature(functionalities=["FUNC-001"], user_stories=["US-001"])
    func = _func(parent="FEAT-001")
    story = _us()

    warnings = check_relations([feature, func, story])

    assert warnings == []


def test_relation_mismatch_when_feature_claims_a_functionality_parented_elsewhere():
    """A Feature's stale claim on a Functionality actually parented elsewhere is caught as a relation mismatch."""
    # FUNC-002's real parent is FEAT-003, which correctly lists it back - so the
    # Functionality-side check alone finds nothing wrong. FEAT-001's own claim on
    # FUNC-002 is still stale/incorrect and must be caught from the Feature side.
    feature = _feature(entity_id="FEAT-001", functionalities=["FUNC-002"])
    real_parent = _feature(entity_id="FEAT-003", functionalities=["FUNC-002"])
    func = _func(entity_id="FUNC-002", parent="FEAT-003")

    warnings = check_relations([feature, real_parent, func])

    assert [w.code for w in warnings] == [Code.RELATION_MISMATCH.name]


def test_no_mismatch_when_feature_declares_no_functionalities_list_at_all():
    """A Feature linked to a Functionality only via its parent, with no functionalities list of its own, is fine."""
    # Linked purely via `parent`, with the Feature carrying no `functionalities` list of
    # its own (empty list means "nothing declared", not "declared as empty").
    feature = _feature()
    func = _func(parent="FEAT-001")

    warnings = check_relations([feature, func])

    assert warnings == []


def test_relation_type_mismatch_when_a_functionality_id_is_copy_pasted_into_user_stories():
    """A Functionality id mistakenly listed in user_stories is flagged as a type mismatch, not silently accepted."""
    # The issue's concrete failure case: FUNC-001 exists in the collected set, so the
    # naive by_id lookup alone finds nothing wrong even though it's the wrong entity type.
    feature = _feature(user_stories=["FUNC-001"])
    func = _func()

    warnings = check_relations([feature, func])

    assert [w.code for w in warnings] == [Code.RELATION_TYPE_MISMATCH.name]
    context = warnings[0].context
    assert "entity_id='FEAT-001'" in context
    assert "field='user_stories'" in context
    assert "target='FUNC-001'" in context
    assert "actual_type='DocumentedFunctionality'" in context
    assert "expected_type='DocumentedUserStory'" in context


def test_relation_type_mismatch_when_a_user_story_id_is_copy_pasted_into_functionalities():
    """A User Story id mistakenly listed in a Feature's functionalities is flagged as a relation type mismatch."""
    feature = _feature(functionalities=["US-001"])
    story = _us()

    warnings = check_relations([feature, story])

    assert [w.code for w in warnings] == [Code.RELATION_TYPE_MISMATCH.name]
    context = warnings[0].context
    assert "entity_id='FEAT-001'" in context
    assert "field='functionalities'" in context
    assert "target='US-001'" in context
    assert "actual_type='DocumentedUserStory'" in context
    assert "expected_type='DocumentedFunctionality'" in context


def test_relation_type_mismatch_when_functionality_parent_resolves_to_a_non_feature():
    """A Functionality whose parent resolves to a non-Feature entity is flagged as a relation type mismatch."""
    func = _func(parent="US-001")
    story = _us()

    warnings = check_relations([func, story])

    assert [w.code for w in warnings] == [Code.RELATION_TYPE_MISMATCH.name]
    context = warnings[0].context
    assert "entity_id='FUNC-001'" in context
    assert "field='parent'" in context
    assert "target='US-001'" in context
    assert "actual_type='DocumentedUserStory'" in context
    assert "expected_type='DocumentedFeature'" in context


def test_relation_type_mismatch_when_superseded_by_resolves_to_a_different_type():
    """A superseded-by reference that resolves to an entity of a different type is flagged as a type mismatch."""
    story = _us(entity_id="US-001", superseded_by="FUNC-001")
    func = _func()

    warnings = check_relations([story, func])

    assert [w.code for w in warnings] == [Code.RELATION_TYPE_MISMATCH.name]
    context = warnings[0].context
    assert "entity_id='US-001'" in context
    assert "field='superseded_by'" in context
    assert "target='FUNC-001'" in context
    assert "actual_type='DocumentedFunctionality'" in context
    assert "expected_type='DocumentedUserStory'" in context


def test_type_mismatch_does_not_also_raise_relation_mismatch_for_functionalities():
    """A wrong-type functionalities target short-circuits the back-link check, raising only the type mismatch."""
    # A wrong-type target short-circuits the back-link consistency check - checking
    # `func.parent` against a non-Functionality target isn't a meaningful comparison.
    feature = _feature(functionalities=["US-001"])
    story = _us(parent="FEAT-999")

    warnings = check_relations([feature, story])

    assert [w.code for w in warnings] == [Code.RELATION_TYPE_MISMATCH.name]


def test_type_mismatch_does_not_also_raise_relation_mismatch_for_parent():
    """A wrong-type parent target short-circuits the back-link check, raising only the type mismatch."""
    # If the type check didn't short-circuit, the back-link elif below it would still run:
    # entity_id "FUNC-001" is not in story.functionalities, which would additionally raise
    # a (nonsensical) RELATION_MISMATCH on top of the type mismatch.
    func = _func(parent="US-001")
    story = _us(functionalities=["FUNC-999"])

    warnings = check_relations([func, story])

    assert [w.code for w in warnings] == [Code.RELATION_TYPE_MISMATCH.name]


def test_no_type_mismatch_for_a_correctly_typed_relation_set():
    """A correctly typed and cross-linked relation set produces no relation type mismatch warnings."""
    feature = _feature(functionalities=["FUNC-001"], user_stories=["US-001"])
    func = _func(parent="FEAT-001")
    story = _us()

    warnings = check_relations([feature, func, story])

    assert warnings == []


def test_check_relations_preserves_field_order_within_one_entity():
    """Relation warnings are reported per entity in a fixed field order: stories, functionalities, then superseder."""
    # Regression pin for the S-13 refactor (relations.py: check_relations iterates a
    # (field, target_id, expected_type) table instead of one hand-written block per
    # field): a Feature's user_stories must still be reported before its
    # functionalities before its superseded_by, and a Functionality's parent still
    # comes from that entity's own turn through `entities` - the same order the
    # original one-block-per-field code produced.
    feature = _feature(user_stories=["US-999"], functionalities=["FUNC-001"], superseded_by="FEAT-999")
    func = _func(parent="FEAT-002")

    warnings = check_relations([feature, func])

    assert [w.code for w in warnings] == [
        Code.UNRESOLVED_RELATION.name,
        Code.RELATION_MISMATCH.name,
        Code.UNRESOLVED_RELATION.name,
        Code.UNRESOLVED_RELATION.name,
    ]
    assert "target='US-999'" in warnings[0].context
    assert "functionality='FUNC-001'" in warnings[1].context
    assert "target='FEAT-999'" in warnings[2].context
    assert "target='FEAT-002'" in warnings[3].context


def test_no_relation_warnings_for_the_golden_entity_fixtures():
    """The project's canonical, correctly cross-linked golden fixtures clear relation checking with no warnings."""
    # Regression: the project's three canonical example issues (FEAT-001/FUNC-001/US-001),
    # correctly typed and cross-linked, must clear check_relations with no warnings at all.
    entities = [
        ("us-001-customer-login.md", "US-001 · Customer Login", "DocumentedUserStory"),
        ("feat-001-login-page.md", "FEAT-001 · Login Page", "DocumentedFeature"),
        (
            "func-001-validate-password-strength.md",
            "FUNC-001 · Login Page - Validate Password Strength",
            "DocumentedFunctionality",
        ),
    ]
    parsed = []
    for filename, title, entity_type in entities:
        text = read_fixture("gh-issues", filename)
        entity, _entity_warnings = parse_issue_body(text, title, entity_type)
        assert entity is not None
        parsed.append(entity)
    derived, _derive_warnings = derive_statuses(parsed)

    warnings = check_relations(derived)

    assert warnings == []
