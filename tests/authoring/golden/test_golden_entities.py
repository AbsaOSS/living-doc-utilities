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
The guarantee acceptance criterion: `parse_issue_body` followed by `derive_statuses`
reproduces the hand-written golden entity for each of the project's three canonical example
issue bodies, run together (so FEAT-001's derived state depends on FUNC-001's authored one,
exactly as a real collector run would see them).
"""

from living_doc_utilities.authoring.issue_body import parse_issue_body
from living_doc_utilities.authoring.status import derive_statuses
from tests.authoring.golden.helpers import load_expected, read_fixture, to_entity_dict

_ENTITIES = [
    ("us-001-customer-login.md", "US-001 · Customer Login", "DocumentedUserStory", "us-001-customer-login.json"),
    ("feat-001-login-page.md", "FEAT-001 · Login Page", "DocumentedFeature", "feat-001-login-page.json"),
    (
        "func-001-validate-password-strength.md",
        "FUNC-001 · Login Page - Validate Password Strength",
        "DocumentedFunctionality",
        "func-001-validate-password-strength.json",
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
    derived, _warnings = _parse_all()
    by_id = {entity.entity_id: entity for entity in derived}

    for _filename, _title, _entity_type, expected_name in _ENTITIES:
        expected = load_expected(expected_name)
        actual = to_entity_dict(by_id[expected["entity_id"]])
        assert actual == expected, f"mismatch for {expected['entity_id']}"


def test_golden_run_produces_no_warnings():
    _derived, warnings = _parse_all()
    assert warnings == []
