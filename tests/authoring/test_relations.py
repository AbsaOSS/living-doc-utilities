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

"""`check_relations`: `UNRESOLVED_RELATION`, `RELATION_MISMATCH` and `RELATION_TYPE_MISMATCH`."""

import pytest

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
    # FUNC-002's real parent lists it back, so only the Feature-side check can catch FEAT-001's stale claim.
    feature = _feature(entity_id="FEAT-001", functionalities=["FUNC-002"])
    real_parent = _feature(entity_id="FEAT-003", functionalities=["FUNC-002"])
    func = _func(entity_id="FUNC-002", parent="FEAT-003")

    warnings = check_relations([feature, real_parent, func])

    assert [w.code for w in warnings] == [Code.RELATION_MISMATCH.name]


def test_no_mismatch_when_feature_declares_no_functionalities_list_at_all():
    """A Feature linked to a Functionality only via its parent, with no functionalities list of its own, is fine."""
    # Linked purely via `parent`; an absent `functionalities` list means "nothing declared", not "declared empty".
    feature = _feature()
    func = _func(parent="FEAT-001")

    warnings = check_relations([feature, func])

    assert warnings == []


def test_relation_type_mismatch_when_a_functionality_id_is_copy_pasted_into_user_stories():
    """A Functionality id mistakenly listed in user_stories is flagged as a type mismatch, not silently accepted."""
    # FUNC-001 exists in the set, so a plain by_id lookup alone finds nothing wrong despite the wrong entity type.
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
    # A wrong-type target short-circuits the back-link check, which is meaningless against a non-Functionality.
    feature = _feature(functionalities=["US-001"])
    story = _us(parent="FEAT-999")

    warnings = check_relations([feature, story])

    assert [w.code for w in warnings] == [Code.RELATION_TYPE_MISMATCH.name]


def test_type_mismatch_does_not_also_raise_relation_mismatch_for_parent():
    """A wrong-type parent target short-circuits the back-link check, raising only the type mismatch."""
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
    # Reporting order is user_stories, functionalities, superseded_by; a Functionality's parent comes on its own turn.
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
    entities = [
        ("us-001-customer-login.md", "US-001 · Customer Login", "DocumentedUserStory"),
        ("feat-001-login-page.md", "FEAT-001 · Login Page", "DocumentedFeature"),
        ("feat-002-breached-password-check.md", "FEAT-002 · Breached Password Check", "DocumentedFeature"),
        ("feat-003-registration-page.md", "FEAT-003 · Registration Page", "DocumentedFeature"),
        (
            "func-001-validate-password-strength.md",
            "FUNC-001 · Login Page - Validate Password Strength",
            "DocumentedFunctionality",
        ),
        (
            "func-002-reject-breached-password.md",
            "FUNC-002 · Login Page - Reject Breached Password",
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


# --- feature_dependencies -------------------------------------------------------------


@pytest.mark.parametrize("surface_type", ["UI", "API"])
def test_no_warning_for_a_feature_dependency_on_an_api_feature(surface_type):
    """A `UI` or an `API` Feature naming an `API` Feature in `feature_dependencies` raises nothing."""
    caller = _feature(surface_type=surface_type, feature_dependencies=["FEAT-002"])
    api = _feature(entity_id="FEAT-002", surface_type="API")

    assert check_relations([caller, api]) == []


def test_unresolved_relation_for_a_feature_dependency_outside_the_run():
    """A `feature_dependencies` target outside the collected set is `UNRESOLVED_RELATION`."""
    caller = _feature(surface_type="UI", feature_dependencies=["FEAT-999"])

    warnings = check_relations([caller])

    assert [(w.code, w.context) for w in warnings] == [
        (Code.UNRESOLVED_RELATION.name, "entity_id='FEAT-001' target='FEAT-999'")
    ]


def test_none_in_feature_dependencies_is_no_target():
    """The field has no `none` value; the shared id-list parser reads it as an empty list, so nothing is checked."""
    entity, warnings = parse_issue_body("## Feature Dependencies\n\nnone\n", "FEAT-001 · Sample", "DocumentedFeature")

    assert warnings == []
    assert entity.feature_dependencies == []
    assert check_relations([entity]) == []


@pytest.mark.parametrize("surface_type", ["UI", None])
def test_relation_type_mismatch_when_a_feature_dependency_is_not_an_api_feature(surface_type):
    """A `feature_dependencies` target that is a Feature without an `API` surface is `RELATION_TYPE_MISMATCH`."""
    caller = _feature(surface_type="UI", feature_dependencies=["FEAT-002"])
    target = _feature(entity_id="FEAT-002", surface_type=surface_type)

    warnings = check_relations([caller, target])

    actual = f"DocumentedFeature with surface_type={surface_type!r}"
    assert [(w.code, w.context) for w in warnings] == [
        (
            Code.RELATION_TYPE_MISMATCH.name,
            f"entity_id='FEAT-001' field='feature_dependencies' target='FEAT-002' "
            f"actual_type={actual!r} expected_type='API DocumentedFeature'",
        )
    ]


def test_relation_type_mismatch_when_a_feature_dependency_is_not_a_feature():
    """A `feature_dependencies` target that is a Functionality is `RELATION_TYPE_MISMATCH` on the entity type."""
    caller = _feature(feature_dependencies=["FUNC-001"])

    warnings = check_relations([caller, _func()])

    assert [(w.code, w.context) for w in warnings] == [
        (
            Code.RELATION_TYPE_MISMATCH.name,
            "entity_id='FEAT-001' field='feature_dependencies' target='FUNC-001' "
            "actual_type='DocumentedFunctionality' expected_type='DocumentedFeature'",
        )
    ]


@pytest.mark.parametrize("surface_type", ["UI", "API"])
def test_relation_mismatch_when_a_feature_depends_on_itself(surface_type):
    """A Feature naming itself in `feature_dependencies` is `RELATION_MISMATCH`, even an `API` one."""
    caller = _feature(surface_type=surface_type, feature_dependencies=["FEAT-001"])

    warnings = check_relations([caller])

    assert [(w.code, w.context) for w in warnings] == [
        (Code.RELATION_MISMATCH.name, "entity_id='FEAT-001' target='FEAT-001'")
    ]


def test_feature_dependencies_is_checked_after_functionalities_and_before_superseded_by():
    """A Feature's `feature_dependencies` is reported between its `functionalities` and its `superseded_by`."""
    caller = _feature(functionalities=["FUNC-999"], feature_dependencies=["FEAT-998"], superseded_by="FEAT-997")

    warnings = check_relations([caller])

    assert [w.context for w in warnings] == [
        "entity_id='FEAT-001' target='FUNC-999'",
        "entity_id='FEAT-001' target='FEAT-998'",
        "entity_id='FEAT-001' target='FEAT-997'",
    ]


def test_a_feature_keeps_exactly_its_authored_feature_dependencies():
    """Nothing is derived upward: a Feature's value is what is written on it, whatever its Functionalities carry."""
    feature, feature_warnings = parse_issue_body(
        "## Surface Type\n\nUI\n\n## Functionalities\n\nFUNC-001\n\n## Feature Dependencies\n\nFEAT-002\n",
        "FEAT-001 · Sample",
        "DocumentedFeature",
    )
    bare_feature, _bare_warnings = parse_issue_body(
        "## Surface Type\n\nUI\n\n## Functionalities\n\nFUNC-002\n", "FEAT-003 · Bare", "DocumentedFeature"
    )
    api = _feature(entity_id="FEAT-002", surface_type="API")
    # Even a Functionality built with the field directly (no parser puts it there) contributes nothing upward.
    funcs = [
        _func(parent="FEAT-001", feature_dependencies=["FEAT-005"]),
        _func(entity_id="FUNC-002", parent="FEAT-003", feature_dependencies=["FEAT-002"]),
    ]

    derived, _derive_warnings = derive_statuses([feature, bare_feature, api, *funcs])
    by_id = {entity.entity_id: entity for entity in derived}

    assert feature_warnings == []
    assert by_id["FEAT-001"].feature_dependencies == ["FEAT-002"]
    assert by_id["FEAT-003"].feature_dependencies == []
    # A Functionality is not a declaring entity for this relation, so its stray value is never traversed.
    assert check_relations(derived) == []


# Verbatim bodies of AbsaOSS/living-doc's docs/examples/gh-issues/feat-00{2,3}-*.md at commit
# b00ca8c653dc09b58523d0fee9715657ae214905 (P35-LD12), provenance comments left out.
_CANON_FEAT_002 = """\
## Description

The service contract a client calls to ask whether a candidate password appears in the breached-password
corpus.

## Surface Type

API

## Owners

Identity Team

## User Stories

US-001

## Functionalities

none
"""

_CANON_FEAT_003 = """\
## Description

The screen where a new customer creates an account by entering an email and choosing a password.

## Surface Type

UI

## Owners

Identity Team

## User Stories

none

## Functionalities

none

## Feature Dependencies

FEAT-002
"""


def test_canon_feat_003_to_feat_002_round_trips_through_the_issue_body_parser():
    """The canon's `feature_dependencies` pair parses with no warning and FEAT-003 → FEAT-002 resolves cleanly."""
    us_001, us_warnings = parse_issue_body(
        read_fixture("gh-issues", "us-001-customer-login.md"), "US-001 · Customer Login", "DocumentedUserStory"
    )
    feat_002, feat_002_warnings = parse_issue_body(
        _CANON_FEAT_002, "FEAT-002 · Breached Password Check", "DocumentedFeature"
    )
    feat_003, feat_003_warnings = parse_issue_body(_CANON_FEAT_003, "FEAT-003 · Registration Page", "DocumentedFeature")

    assert us_warnings + feat_002_warnings + feat_003_warnings == []
    assert feat_003.feature_dependencies == ["FEAT-002"]
    assert feat_002.feature_dependencies == []
    assert check_relations([us_001, feat_002, feat_003]) == []
