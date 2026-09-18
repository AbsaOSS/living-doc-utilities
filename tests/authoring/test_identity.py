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

"""entity_id extraction from a title (docs/contracts.md, "Entity identity")."""

import pytest

from living_doc_utilities.authoring.identity import MISSING_ENTITY_ID, derive_entity_id


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
    entity_id, warnings = derive_entity_id(title)

    assert entity_id == "US-001"
    assert warnings == []


def test_title_with_no_parseable_id_produces_no_entity_and_a_warning():
    entity_id, warnings = derive_entity_id("Customer Login")

    assert entity_id is None
    assert [w.code for w in warnings] == [MISSING_ENTITY_ID]
    assert "Customer Login" in warnings[0].context
