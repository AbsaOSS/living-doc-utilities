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

"""`derive_statuses`: every US/Functionality and Feature derivation row and every `STATUS_AC_MISMATCH` row."""

import pytest

from living_doc_utilities.authoring.issue_body import ParsedEntity
from living_doc_utilities.authoring.status import derive_statuses
from living_doc_utilities.contracts.codes import Code
from living_doc_utilities.contracts.common import AcceptanceCriterion


def _ac(seq: int, state: str, **overrides) -> AcceptanceCriterion:
    fields = {"id": f"US-001-{seq:02d}", "state": state, "version": "1.0.0", "description": "desc"}
    if state == "planned" and "version" not in overrides:
        fields.pop("version")
    if state == "deprecated":
        fields.setdefault("removal_planned", "2.0.0")
    fields.update(overrides)
    return AcceptanceCriterion(**fields)


def _us(entity_id="US-001", state=None, acceptance_criteria=None, **overrides) -> ParsedEntity:
    fields = {
        "entity_id": entity_id,
        "type": "DocumentedUserStory",
        "title": f"{entity_id} · Sample",
        "state": state,
        "acceptance_criteria": acceptance_criteria or [],
    }
    fields.update(overrides)
    return ParsedEntity(**fields)


def _feature(entity_id="FEAT-001", **overrides) -> ParsedEntity:
    fields = {"entity_id": entity_id, "type": "DocumentedFeature", "title": f"{entity_id} · Sample"}
    fields.update(overrides)
    return ParsedEntity(**fields)


def _func(entity_id="FUNC-001", state="active", parent=None, **overrides) -> ParsedEntity:
    fields = {
        "entity_id": entity_id,
        "type": "DocumentedFunctionality",
        "title": f"{entity_id} · Sample",
        "state": state,
        "parent": parent,
    }
    fields.update(overrides)
    return ParsedEntity(**fields)


# --- User Story / Functionality: MISSING_STATUS derivation table -----------------------


@pytest.mark.parametrize(
    "ac_states, expected_state",
    [
        (["active", "planned"], "active"),
        (["in_review", "planned"], "in_review"),
        (["deprecated", "deprecated"], "deprecated"),
        (["planned", "deprecated"], "planned"),
        ([], "planned"),
    ],
)
def test_missing_status_derives_from_acceptance_criteria(ac_states, expected_state):
    """A User Story or Functionality with no authored state derives one from its acceptance criteria per the table."""
    acs = [_ac(i + 1, state) for i, state in enumerate(ac_states)]
    entities, warnings = derive_statuses([_us(acceptance_criteria=acs)])

    assert entities[0].state == expected_state
    assert entities[0].state_origin == "authored"
    assert [w.code for w in warnings] == [Code.MISSING_STATUS.name]


# --- STATUS_AC_MISMATCH ------------------------------------------------------------------


@pytest.mark.parametrize(
    "authored, ac_states, expect_mismatch",
    [
        ("planned", ["active"], True),
        ("planned", ["deprecated"], True),
        ("planned", ["planned"], False),
        ("active", ["planned", "in_review"], True),
        ("active", [], False),
        ("active", ["active"], False),
        ("deprecated", ["active"], True),
        ("deprecated", ["in_review"], True),
        ("deprecated", ["planned"], True),
        ("deprecated", ["deprecated"], False),
        ("in_review", [], False),
        ("in_review", ["planned"], False),
        ("in_review", ["active"], False),
        ("in_review", ["deprecated"], False),
    ],
)
def test_status_ac_mismatch_table(authored, ac_states, expect_mismatch):
    """The authored state always wins over the AC-derived one; mismatch warns only for the documented combinations."""
    acs = [_ac(i + 1, state) for i, state in enumerate(ac_states)]
    entities, warnings = derive_statuses([_us(state=authored, acceptance_criteria=acs)])

    assert entities[0].state == authored  # authored value always wins
    codes = [w.code for w in warnings]
    assert (Code.STATUS_AC_MISMATCH.name in codes) is expect_mismatch


def test_in_review_never_mismatches_for_any_ac_combination():
    """An authored "in_review" state never triggers STATUS_AC_MISMATCH, regardless of the ACs' own states."""
    for ac_states in ([], ["planned"], ["active"], ["in_review"], ["deprecated"], ["active", "deprecated"]):
        acs = [_ac(i + 1, state) for i, state in enumerate(ac_states)]
        _entities, warnings = derive_statuses([_us(state="in_review", acceptance_criteria=acs)])
        assert Code.STATUS_AC_MISMATCH.name not in [w.code for w in warnings]


# --- Feature derivation ------------------------------------------------------------------


def test_feature_authored_deprecated_at_does_not_win_over_active_functionalities():
    """An authored deprecated_at on a Feature does not drive its state; it still comes from its Functionalities."""
    feature = _feature(deprecated_at="2026-01-01", functionalities=["FUNC-001"])
    func = _func(state="active", parent="FEAT-001")

    entities, warnings = derive_statuses([feature, func])
    by_id = {e.entity_id: e for e in entities}

    assert by_id["FEAT-001"].state == "active"
    assert by_id["FEAT-001"].state_origin == "derived"
    assert warnings == []


def test_feature_is_deprecated_once_every_functionality_is():
    """A Feature derives deprecated from its Functionalities alone, once every one of them is deprecated - and takes
    no deprecation date from them: a Feature has none (DEC-47)."""
    feature = _feature(functionalities=["FUNC-001", "FUNC-002"])
    funcs = [
        _func(state="deprecated", parent="FEAT-001", deprecated_at="2026-01-01"),
        _func(entity_id="FUNC-002", state="deprecated", parent="FEAT-001", deprecated_at="2026-02-01"),
    ]

    entities, _warnings = derive_statuses([feature, *funcs])
    by_id = {e.entity_id: e for e in entities}

    assert by_id["FEAT-001"].state == "deprecated"
    assert by_id["FEAT-001"].state_origin == "derived"
    assert by_id["FEAT-001"].deprecated_at is None


def test_feature_is_not_deprecated_while_any_functionality_is_live():
    """One active Functionality keeps the Feature active, however many of its siblings are deprecated."""
    feature = _feature(functionalities=["FUNC-001", "FUNC-002"])
    funcs = [
        _func(state="deprecated", parent="FEAT-001"),
        _func(entity_id="FUNC-002", state="active", parent="FEAT-001"),
    ]

    entities, _warnings = derive_statuses([feature, *funcs])
    by_id = {e.entity_id: e for e in entities}

    assert by_id["FEAT-001"].state == "active"


def test_feature_derives_from_linked_functionalities_via_parent():
    """A Feature's derived state follows the state of a Functionality that names it as parent."""
    feature = _feature()
    func = _func(state="active", parent="FEAT-001")

    entities, _warnings = derive_statuses([feature, func])
    by_id = {e.entity_id: e for e in entities}

    assert by_id["FEAT-001"].state == "active"
    assert by_id["FEAT-001"].state_origin == "derived"


def test_feature_derives_from_own_functionalities_list_when_func_has_no_parent():
    """A Feature derives its state from its own functionalities list when the linked Functionality has no parent."""
    feature = _feature(functionalities=["FUNC-001"])
    func = _func(state="in_review", parent=None)

    entities, _warnings = derive_statuses([feature, func])
    by_id = {e.entity_id: e for e in entities}

    assert by_id["FEAT-001"].state == "in_review"
    assert by_id["FEAT-001"].state_origin == "derived"


def test_feature_with_only_linked_user_stories_is_a_feature_without_functionality():
    """Linked User Stories never stand in for Functionalities: such a Feature derives planned with
    FEATURE_WITHOUT_FUNCTIONALITY."""
    feature = _feature(user_stories=["US-001"])
    story = _us(state="active")

    entities, warnings = derive_statuses([feature, story])
    by_id = {e.entity_id: e for e in entities}

    assert by_id["FEAT-001"].state == "planned"
    assert by_id["FEAT-001"].state_origin == "derived"
    assert [(w.code, w.context) for w in warnings] == [
        (Code.FEATURE_WITHOUT_FUNCTIONALITY.name, "entity_id='FEAT-001'")
    ]


def test_feature_without_functionality_derives_planned_with_a_warning():
    """A Feature with no linked Functionality derives planned, with a FEATURE_WITHOUT_FUNCTIONALITY warning."""
    entities, warnings = derive_statuses([_feature()])

    assert entities[0].state == "planned"
    assert entities[0].state_origin == "derived"
    assert [w.code for w in warnings] == [Code.FEATURE_WITHOUT_FUNCTIONALITY.name]


def test_the_feature_without_functionality_warning_names_both_possibilities_and_the_choice():
    """The warning's message names a missing Functionality as the only trigger, both possibilities, and the choice."""
    _entities, warnings = derive_statuses([_feature()])

    assert warnings[0].context == "entity_id='FEAT-001'"
    assert warnings[0].message.startswith("Feature has no linked Functionality in this run")
    assert "User Story" not in warnings[0].message
    assert "not yet" in warnings[0].message and "retired" in warnings[0].message
    assert "Author its Functionalities, or remove the Feature." in warnings[0].message
