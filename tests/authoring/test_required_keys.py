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

"""The required-keys table and `missing_required_keys`: each header's missing key, on its title line."""

import pytest

from living_doc_utilities.authoring import feature_header, issue_body, page_object
from living_doc_utilities.authoring.framing import _slugify_section
from living_doc_utilities.authoring.normalize import SourceFormat, normalize_framed
from living_doc_utilities.authoring.required_keys import CROSS_REFERENCE, REQUIRED_KEYS, missing_required_keys
from living_doc_utilities.contracts.codes import Code

_US_WITHOUT_BUSINESS_VALUE = """\
# =============================================================================
# LIVING DOC — US-001 · Sample Story
# =============================================================================
# status: active
#
# acceptance_criteria:
#
#   AC:US-001-01 (v1.0.0 - active)
#     - desc
# =============================================================================

Feature: Sample Story
"""

_FUNC_WITHOUT_PARENT_AND_FUNC_TYPE = """\
# =============================================================================
# LIVING DOC — FUNC-001 · Sample Functionality
# =============================================================================
# status: active
#
# acceptance_criteria:
#
#   AC:FUNC-001-01 (v1.0.0 - active)
#     - desc
# =============================================================================

Feature: Sample Functionality
"""

_CROSS_REFERENCE_WITHOUT_ROUTE = """\
/* =============================================================================
 * LIVING DOC — FEAT-042 · Account Setup Wizard  [cross-reference]
 * =============================================================================
 * parent-feat:     FEAT-042
 * owners:          Platform Team
 * purpose:         Step 1 (Profile) — user profile fields.
 * page-object:     AccountSetupWizardProfilePage.ts
 * ============================================================================= */
"""

_FULL_PAGE_OBJECT = """\
/* =============================================================================
 * LIVING DOC — FEAT-042 · Account Setup Wizard
 * =============================================================================
 * surface_type:          UI
 * route:                 /app/accounts/setup
 * owners:                Platform Team
 * purpose:               Multi-step wizard for creating and configuring a new account.
 * user_stories:          US-10
 * functionalities:       FUNC-005
 * external_dependencies: none
 * page-object:           AccountSetupWizardPage.ts
 * ============================================================================= */
"""


def _missing(text, fmt, entity_type):
    _, frame = normalize_framed(text, fmt, entity_type)
    return missing_required_keys(frame, fmt, entity_type)


@pytest.mark.parametrize(
    "header, recognised",
    [
        ("DocumentedUserStory", set(feature_header._KEYS_BY_TYPE["DocumentedUserStory"])),
        ("DocumentedFunctionality", set(feature_header._KEYS_BY_TYPE["DocumentedFunctionality"])),
    ],
)
def test_every_required_feature_key_is_a_key_the_feature_parser_reads(header, recognised):
    """A `.feature` header's required keys are all keys `parse_feature_header` reads for that entity type."""
    assert set(REQUIRED_KEYS[SourceFormat.FEATURE_HEADER][header]) <= recognised


@pytest.mark.parametrize(
    "header, recognised",
    [("DocumentedFeature", page_object._FULL_HEADER_KEYS), (CROSS_REFERENCE, page_object._CROSS_REFERENCE_KEYS)],
)
def test_every_required_page_object_key_is_a_key_the_page_object_parser_reads(header, recognised):
    """A PageObject header's required keys are all keys `parse_page_object` reads for that header kind."""
    assert set(REQUIRED_KEYS[SourceFormat.PAGE_OBJECT][header]) <= recognised


@pytest.mark.parametrize("header", ["DocumentedUserStory", "DocumentedFeature", "DocumentedFunctionality"])
def test_every_required_issue_heading_is_a_heading_the_issue_body_parser_reads(header):
    """An issue body's required headings, as authored, are all headings `parse_issue_body` reads for that type."""
    slugs = {_slugify_section(heading) for heading in REQUIRED_KEYS[SourceFormat.ISSUE_BODY][header]}
    assert slugs <= set(issue_body._SECTIONS_BY_TYPE[header])


def test_a_missing_feature_key_is_reported_on_the_title_line_with_its_entity():
    """A User Story header without `business_value:` gets one `MISSING_REQUIRED_KEY`, on the title line."""
    warnings = _missing(_US_WITHOUT_BUSINESS_VALUE, SourceFormat.FEATURE_HEADER, "DocumentedUserStory")

    assert [(w.code, w.line_no, w.entity_id) for w in warnings] == [(Code.MISSING_REQUIRED_KEY.name, 2, "US-001")]
    assert warnings[0].message == "Required key 'business_value:' is missing."


def test_each_missing_key_is_reported_in_table_order():
    """A Functionality header without `parent:` and `func_type:` gets one warning per key, in the table's order."""
    warnings = _missing(_FUNC_WITHOUT_PARENT_AND_FUNC_TYPE, SourceFormat.FEATURE_HEADER, "DocumentedFunctionality")

    assert [w.message for w in warnings] == [
        "Required key 'parent:' is missing.",
        "Required key 'func_type:' is missing.",
    ]


def test_a_cross_reference_header_is_checked_against_the_cross_reference_keys():
    """A PageObject header with `parent-feat:` is checked against the cross-reference keys, not the full ones."""
    warnings = _missing(_CROSS_REFERENCE_WITHOUT_ROUTE, SourceFormat.PAGE_OBJECT, "DocumentedFeature")

    assert [(w.message, w.line_no, w.entity_id) for w in warnings] == [
        ("Required key 'route:' is missing.", 2, "FEAT-042")
    ]


def test_a_complete_header_has_no_missing_key():
    """A full PageObject header that carries every required key gets no warning."""
    assert _missing(_FULL_PAGE_OBJECT, SourceFormat.PAGE_OBJECT, "DocumentedFeature") == []


def test_a_header_without_an_entity_id_reports_no_missing_key():
    """A file with no living-doc title gets no `MISSING_REQUIRED_KEY`: the parser's `MISSING_ENTITY_ID` covers it."""
    assert _missing("Feature: No header\n", SourceFormat.FEATURE_HEADER, "DocumentedUserStory") == []


@pytest.mark.parametrize(
    "fmt, entity_type",
    [(SourceFormat.FEATURE_HEADER, "DocumentedFeature"), (SourceFormat.PAGE_OBJECT, "DocumentedUserStory")],
)
def test_an_entity_type_the_format_does_not_carry_is_refused(fmt, entity_type):
    """A `.feature` header is never a Feature's, and a PageObject never a User Story's: `ValueError`, not `KeyError`."""
    _, frame = normalize_framed(_US_WITHOUT_BUSINESS_VALUE, fmt, entity_type)

    with pytest.raises(ValueError, match=entity_type):
        missing_required_keys(frame, fmt, entity_type)


def test_an_issue_body_frame_is_refused():
    """`missing_required_keys` reads a `.feature` or PageObject header only; an issue body raises `ValueError`."""
    _, frame = normalize_framed("## Description\n\nd\n", SourceFormat.ISSUE_BODY, "DocumentedUserStory")

    with pytest.raises(ValueError, match="issue_body"):
        missing_required_keys(frame, SourceFormat.ISSUE_BODY, "DocumentedUserStory")
