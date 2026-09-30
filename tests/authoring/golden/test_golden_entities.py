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

"""Parsing and status-deriving the six canonical issue bodies together reproduces each golden entity."""

from living_doc_utilities.authoring.issue_body import parse_issue_body
from living_doc_utilities.authoring.status import derive_statuses
from living_doc_utilities.contracts.codes import Code
from tests.authoring.golden.helpers import load_expected, read_fixture, to_entity_dict

_ENTITIES = [
    ("us-001-customer-login.md", "US-001 · Customer Login", "DocumentedUserStory", "us-001-customer-login.json"),
    ("feat-001-login-page.md", "FEAT-001 · Login Page", "DocumentedFeature", "feat-001-login-page.json"),
    (
        "feat-002-breached-password-check.md",
        "FEAT-002 · Breached Password Check",
        "DocumentedFeature",
        "feat-002-breached-password-check.json",
    ),
    (
        "feat-003-registration-page.md",
        "FEAT-003 · Registration Page",
        "DocumentedFeature",
        "feat-003-registration-page.json",
    ),
    (
        "func-001-validate-password-strength.md",
        "FUNC-001 · Login Page - Validate Password Strength",
        "DocumentedFunctionality",
        "func-001-validate-password-strength.json",
    ),
    (
        "func-002-reject-breached-password.md",
        "FUNC-002 · Login Page - Reject Breached Password",
        "DocumentedFunctionality",
        "func-002-reject-breached-password.json",
    ),
]


def _parse_all():
    parsed = []
    warnings = []
    for filename, title, entity_type, _expected_name in _ENTITIES:
        text = read_fixture("gh-issues", filename)
        entity, entity_warnings = parse_issue_body(text, title, entity_type)
        assert entity is not None, f"{filename} failed to parse an entity"
        parsed.append(entity)
        warnings.extend(entity_warnings)
    derived, derive_warnings = derive_statuses(parsed)
    return derived, warnings + derive_warnings


def test_golden_entities_match_hand_written_json():
    """Parsing and status-deriving the six canonical issue bodies reproduces each hand-written golden entity."""
    derived, _warnings = _parse_all()
    by_id = {entity.entity_id: entity for entity in derived}

    for _filename, _title, _entity_type, expected_name in _ENTITIES:
        expected = load_expected(expected_name)
        actual = to_entity_dict(by_id[expected["entity_id"]])
        assert actual == expected, f"mismatch for {expected['entity_id']}"


def test_golden_run_produces_exactly_the_expected_corpus_warnings():
    """The six canonical issue bodies produce one warning: FEAT-003 links no entity, so its state is derived orphan."""
    _derived, warnings = _parse_all()
    assert [(w.code, w.context) for w in warnings] == [(Code.ORPHAN_FEATURE.name, "entity_id='FEAT-003'")]


def test_the_notes_of_the_one_corpus_entity_that_carries_them_round_trip():
    """FEAT-001 is the corpus's single `## Notes` instance: both bullets reach `notes`, wrapped lines joined."""
    derived, _warnings = _parse_all()
    by_id = {entity.entity_id: entity for entity in derived}

    assert by_id["FEAT-001"].notes == load_expected("feat-001-login-page.json")["notes"]
    assert len(by_id["FEAT-001"].notes) == 2
    # Every other corpus entity authors no note, so the field defaults to empty rather than to None.
    assert all(by_id[entity_id].notes == [] for entity_id in by_id if entity_id != "FEAT-001")
