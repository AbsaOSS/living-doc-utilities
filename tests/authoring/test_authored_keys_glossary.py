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
Every key the project's glossary defines for an entity or an acceptance criterion maps
either to a real model field (tests/contracts/test_authored_field_set.py's `ALL_HEADINGS`)
or appears in one parser's `IGNORED_AUTHORED_KEYS` with a reason - nothing is silently
dropped. Both `IGNORED_AUTHORED_KEY` and `UNKNOWN_SECTION` are exercised here too.
"""

from living_doc_utilities.authoring import issue_body, page_object
from living_doc_utilities.authoring.issue_body import parse_issue_body
from living_doc_utilities.authoring.page_object import parse_page_object
from living_doc_utilities.contracts.codes import Code
from tests.contracts.test_authored_field_set import ALL_HEADINGS

# The two glossary-defined keys with no model field (a Feature's status is derived, never
# authored - docs/contracts.md), one per authoring surface that could carry it.
_IGNORED_KEYS = [
    ("Status", issue_body.IGNORED_AUTHORED_KEYS, "issue body"),
    ("status", page_object.IGNORED_AUTHORED_KEYS, "PageObject header"),
]


def test_every_mapped_heading_has_a_field_and_every_ignored_key_has_a_reason():
    # ALL_HEADINGS already proves the "maps to a field" half (imported, not duplicated).
    assert len(ALL_HEADINGS) > 0
    for key, mapping, surface in _IGNORED_KEYS:
        assert key in mapping, f"{key!r} missing from IGNORED_AUTHORED_KEYS for {surface}"
        assert mapping[key], f"{key!r} in {surface}'s IGNORED_AUTHORED_KEYS carries no reason"


def test_ignored_authored_key_is_exercised_for_feature_status_in_both_forms():
    entity, warnings = parse_issue_body(
        "## Description\n\nd\n\n## Status\n\nactive\n\n## Surface Type\n\nUI\n\n"
        "## Owners\n\nTeam\n\n## User Stories\n\nnone\n\n## Functionalities\n\nnone\n",
        "FEAT-001 · Sample",
        "DocumentedFeature",
    )
    assert entity is not None
    assert [w.code for w in warnings] == ["IGNORED_AUTHORED_KEY"]
    assert warnings[0].message == issue_body.IGNORED_AUTHORED_KEYS["Status"]

    po_text = (
        "/* ===\n * LIVING DOC — FEAT-002 · Sample\n * ===\n"
        " * surface_type: UI\n * route: /s\n * owners: Team\n * status: candidate\n"
        " * purpose: p\n * user_stories: none\n * functionalities: none\n"
        " * external_dependencies: none\n * page-object: S.ts\n * === */\n"
    )
    result, po_warnings = parse_page_object(po_text)
    assert result is not None and result.entity is not None
    assert [w.code for w in po_warnings] == ["IGNORED_AUTHORED_KEY"]
    assert po_warnings[0].message == page_object.IGNORED_AUTHORED_KEYS["status"]


def test_unknown_section_is_exercised_for_an_unrecognised_issue_body_heading():
    entity, warnings = parse_issue_body(
        "## Description\n\nd\n\n## Nonsense Heading\n\nv\n", "US-001 · Sample", "DocumentedUserStory"
    )
    assert entity is not None
    assert [w.code for w in warnings] == [Code.UNKNOWN_SECTION.name]
