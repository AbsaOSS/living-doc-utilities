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

"""entity_id extraction from a title (identity.py::derive_entity_id)."""

import pytest

from living_doc_utilities.authoring.identity import derive_entity_id
from living_doc_utilities.contracts.codes import Code


@pytest.mark.parametrize(
    "title",
    [
        "US-001 · Customer Login",
        "US-001 - Customer Login",
        "US-001: Customer Login",
        "GH-US-001 · Customer Login",
    ],
)
def test_valid_title_prefixes_extract_us_001(title):
    """Any of the accepted id-prefix separators (`·`, `-`, `:`, and the `GH-` source prefix) still yield US-001."""
    entity_id, warnings = derive_entity_id(title)

    assert entity_id == "US-001"
    assert warnings == []


def test_title_with_no_parseable_id_produces_no_entity_and_a_warning():
    """A title with no parseable entity id yields no id and a `MISSING_ENTITY_ID` warning that quotes the title."""
    entity_id, warnings = derive_entity_id("Customer Login")

    assert entity_id is None
    assert [w.code for w in warnings] == [Code.MISSING_ENTITY_ID.name]
    assert "Customer Login" in warnings[0].context


@pytest.mark.parametrize(
    "title, expected",
    [
        ("US-001 · Customer Login", "US-001"),
        ("FEAT-002 · Login", "FEAT-002"),
        ("FUNC-003 · Login Page - Validate Password Strength", "FUNC-003"),
    ],
)
def test_each_canon_prefix_is_an_entity_id(title, expected):
    """Each of the canon's three prefixes (`US-`, `FEAT-`, `FUNC-`) yields its id."""
    entity_id, warnings = derive_entity_id(title)

    assert entity_id == expected
    assert warnings == []


@pytest.mark.parametrize(
    "title, expected",
    [
        ("GH-US-001 · Customer Login", "US-001"),
        ("BUG-7 fix for US-001", "US-001"),
    ],
)
def test_other_tracker_keys_are_not_entity_ids(title, expected):
    """A tracker key outside the canon's prefixes (`BUG-7`) is passed over for the first real id after it."""
    entity_id, warnings = derive_entity_id(title)

    assert entity_id == expected
    assert warnings == []


def test_title_naming_only_another_tracker_key_has_no_entity_id():
    """A title whose only id-shaped run is a foreign key (`JIRA-12`) yields no id and a `MISSING_ENTITY_ID` warning."""
    entity_id, warnings = derive_entity_id("JIRA-12 · Customer Login")

    assert entity_id is None
    assert [w.code for w in warnings] == [Code.MISSING_ENTITY_ID.name]


@pytest.mark.parametrize(
    "title", ["US-001abc · Customer Login", "XUS-001 · Customer Login", "GH_US-001 · Customer Login"]
)
def test_an_id_run_glued_to_other_word_characters_is_not_an_entity_id(title):
    """An id must stand as a whole word: a letter, digit or `_` glued before or after it (`XUS-001`, `US-001abc`,
    `GH_US-001`) makes it no id; only a separator such as the `-` in `GH-US-001` lets it stand."""
    entity_id, warnings = derive_entity_id(title)

    assert entity_id is None
    assert [w.code for w in warnings] == [Code.MISSING_ENTITY_ID.name]
