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

"""PageObject header parsing: full and cross-reference headers, an unrecognised key, `normalize` before the grammar."""

import pytest

from living_doc_utilities.authoring.page_object import parse_page_object
from living_doc_utilities.contracts.codes import Code

_FULL_HEADER = """\
/* =============================================================================
 * LIVING DOC — FEAT-042 · Account Setup Wizard
 * =============================================================================
 * surface_type:          UI
 * route:                 /app/accounts/setup
 * owners:                Platform Team
 * wizard-steps:          Profile · Preferences · Review · Confirm
 * purpose:               Multi-step wizard for creating and configuring a new account.
 * user_stories:          US-10, US-12
 * functionalities:       FUNC-005, FUNC-006
 * external_dependencies: accounts-api
 * feature_dependencies:  FEAT-051, FEAT-052
 * page-object:           AccountSetupWizardPage.ts
 * ============================================================================= */
"""

_CROSS_REFERENCE_HEADER = """\
/* =============================================================================
 * LIVING DOC — FEAT-042 · Account Setup Wizard  [cross-reference]
 * =============================================================================
 * This file implements Step 1 (Profile) of the Account Setup Wizard.
 * The authoritative Feature header is in AccountSetupWizardPage.ts.
 *
 * parent-feat:     FEAT-042
 * route:           /app/accounts/setup
 * owners:          Platform Team
 * functionalities: FUNC-005
 * purpose:         Step 1 (Profile) — user profile fields.
 * page-object:     AccountSetupWizardProfilePage.ts
 * ============================================================================= */
"""

_HEADER_WITH_UNKNOWN_KEY = """\
/* =============================================================================
 * LIVING DOC — FEAT-043 · Sample Page
 * =============================================================================
 * surface_type: UI
 * route:        /sample
 * owners:       Team
 * purpose:      A sample page.
 * user_stories: none
 * functionalities: none
 * external_dependencies: none
 * page-object:  SamplePage.ts
 * query_params: foo=bar
 * ============================================================================= */
"""


def test_full_header_populates_the_feature_entity_and_its_page_ref():
    """A primary PageObject header populates both the Feature entity's fields and the page reference's own fields."""
    result, warnings = parse_page_object(_FULL_HEADER)

    assert warnings == []
    assert result.entity is not None
    assert result.parent_feat is None
    assert result.entity.entity_id == "FEAT-042"
    assert result.entity.surface_type == "UI"
    assert result.entity.owners == ["Platform Team"]
    assert result.entity.user_stories == ["US-10", "US-12"]
    assert result.entity.functionalities == ["FUNC-005", "FUNC-006"]
    assert result.entity.external_dependencies == ["accounts-api"]
    assert result.entity.feature_dependencies == ["FEAT-051", "FEAT-052"]
    assert result.entity.wizard_steps == ["Profile", "Preferences", "Review", "Confirm"]
    assert result.page_ref.is_primary is True
    assert result.page_ref.route == "/app/accounts/setup"
    assert result.page_ref.page_object == "AccountSetupWizardPage.ts"


def test_cross_reference_header_produces_no_entity_but_a_page_ref():
    """A `[cross-reference]` PageObject header produces a non-primary page reference and no Feature entity."""
    result, warnings = parse_page_object(_CROSS_REFERENCE_HEADER)

    assert warnings == []
    assert result.entity is None
    assert result.parent_feat == "FEAT-042"
    assert result.page_ref.is_primary is False
    assert result.page_ref.owners == ["Platform Team"]
    assert result.page_ref.functionalities == ["FUNC-005"]
    assert result.page_ref.page_object == "AccountSetupWizardProfilePage.ts"


def test_jsdoc_block_after_the_header_does_not_leak_into_it():
    """A JSDoc block after the header, even one with lines shaped like header keys, never overwrites header values."""
    text = (
        _FULL_HEADER
        + "\n"
        + "export class AccountSetupWizardPage {\n"
        + "  /**\n"
        + "   * route: /somewhere/unrelated\n"
        + "   * owners: Someone Else\n"
        + "   */\n"
        + "  async goto(): Promise<void> {}\n"
        + "}\n"
    )
    result, warnings = parse_page_object(text)

    assert warnings == []
    assert result.entity is not None
    assert result.entity.owners == ["Platform Team"]
    assert result.page_ref.route == "/app/accounts/setup"


def test_unrecognised_key_produces_ignored_authored_key():
    """An unrecognised PageObject-header key produces an `IGNORED_AUTHORED_KEY` warning naming that key."""
    result, warnings = parse_page_object(_HEADER_WITH_UNKNOWN_KEY)

    assert result is not None
    assert [w.code for w in warnings] == [Code.IGNORED_AUTHORED_KEY.name]
    assert "query_params" in warnings[0].message


def test_deprecated_at_on_a_full_header_is_ignored_authored_key():
    """A `deprecated_at:` key on a full PageObject header is `IGNORED_AUTHORED_KEY`, not parsed into the entity."""
    text = (
        "/* ===\n * LIVING DOC — FEAT-044 · Sample Page\n * ===\n"
        " * surface_type: UI\n * route: /s\n * owners: Team\n * deprecated_at: 2026-09-15\n"
        " * purpose: p\n * user_stories: none\n * functionalities: none\n"
        " * external_dependencies: none\n * page-object: S.ts\n * === */\n"
    )
    result, warnings = parse_page_object(text)

    assert result is not None and result.entity is not None
    assert [w.code for w in warnings] == [Code.IGNORED_AUTHORED_KEY.name]
    assert warnings[0].message == "Feature has no deprecation date"
    assert warnings[0].context == "entity_id='FEAT-044' line_no=7 key='deprecated_at:'"


def test_deprecated_at_on_a_cross_reference_header_is_ignored_authored_key():
    """A `deprecated_at:` key on a cross-reference PageObject header is `IGNORED_AUTHORED_KEY` too."""
    text = (
        "/* ===\n * LIVING DOC — FEAT-044 · Sample Page [cross-reference]\n * ===\n"
        " * parent-feat: FEAT-044\n * route: /s\n * owners: Team\n * deprecated_at: 2026-09-15\n"
        " * purpose: p\n * functionalities: none\n * page-object: S.ts\n * === */\n"
    )
    result, warnings = parse_page_object(text)

    assert result is not None and result.entity is None
    assert [w.code for w in warnings] == [Code.IGNORED_AUTHORED_KEY.name]
    assert warnings[0].message == "Feature has no deprecation date"


def test_missing_title_line_produces_missing_entity_id():
    """A PageObject header with no parseable title line yields no result and a `MISSING_ENTITY_ID` warning."""
    text = "/* ===\n * no title here\n * === */\n"
    result, warnings = parse_page_object(text)

    assert result is None
    assert [w.code for w in warnings] == ["MISSING_ENTITY_ID"]


def test_en_dash_input_is_normalized_before_extraction():
    """An en-dash id/title separator is normalized to the canonical form before the title and id are extracted."""
    # The en dash separator is normalize's job; the "LIVING DOC — " marker stays the literal em dash.
    text = (
        "/* =============================================================================\n"
        " * LIVING DOC — FEAT-044 – Dash Page\n"
        " * =============================================================================\n"
        " * surface_type: UI\n"
        " * route:        /dash\n"
        " * owners:       Team\n"
        " * purpose:      A page.\n"
        " * user_stories: none\n"
        " * functionalities: none\n"
        " * external_dependencies: none\n"
        " * page-object:  DashPage.ts\n"
        " * ============================================================================= */\n"
    )
    result, warnings = parse_page_object(text)

    assert warnings == []
    assert result is not None
    assert result.entity is not None
    assert result.entity.entity_id == "FEAT-044"
    assert result.entity.title == "FEAT-044 · Dash Page"


def _header(surface_type: str, extra: str = "") -> str:
    return (
        "/* =============================================================================\n"
        " * LIVING DOC — FEAT-003 · Registration Page\n"
        " * =============================================================================\n"
        f" * surface_type:          {surface_type}\n"
        " * route:                 /register\n"
        " * owners:                Identity Team\n"
        " * purpose:               A sample page.\n"
        " * user_stories:          none\n"
        " * functionalities:       none\n"
        " * external_dependencies: none\n"
        f"{extra}"
        " * page-object:           RegistrationPage.ts\n"
        " * ============================================================================= */\n"
    )


@pytest.mark.parametrize("surface_type", ["UI", "API"])
def test_full_header_feature_dependencies_is_a_comma_separated_id_list(surface_type):
    """`feature_dependencies:` on a full header parses like `user_stories:`, on a `UI` and an `API` Feature alike."""
    result, warnings = parse_page_object(_header(surface_type, " * feature_dependencies:  FEAT-002,FEAT-005\n"))

    assert warnings == []
    assert result.entity.surface_type == surface_type
    assert result.entity.feature_dependencies == ["FEAT-002", "FEAT-005"]


def test_full_header_without_feature_dependencies_leaves_it_empty():
    """The key is optional: a full header that omits it yields an empty `feature_dependencies`."""
    result, warnings = parse_page_object(_header("UI"))

    assert warnings == []
    assert result.entity.feature_dependencies == []


def test_full_header_retirement_keys_land_on_the_feature_with_no_warning():
    """`deprecation_reason:` and `superseded_by:` on a full header are scalars on the Feature, like `stub-reason:`."""
    extra = (
        " * deprecation_reason:    Replaced by the single sign-on flow;\n"
        " *                        retired once every tenant has migrated.\n"
        " * superseded_by:         FEAT-007\n"
    )
    result, warnings = parse_page_object(_header("UI", extra))

    assert warnings == []
    assert result.entity.deprecation_reason == "Replaced by the single sign-on flow; retired once every tenant has migrated."
    assert result.entity.superseded_by == "FEAT-007"


@pytest.mark.parametrize("key", ["feature_dependencies", "surface_type", "deprecation_reason", "superseded_by"])
def test_full_header_only_key_on_a_cross_reference_header_is_an_unrecognised_key(key):
    """A cross-reference header carries no full-header-only key: each is unrecognised, like any unknown key."""
    text = _CROSS_REFERENCE_HEADER.replace(
        " * page-object:     AccountSetupWizardProfilePage.ts\n",
        f" * page-object:     AccountSetupWizardProfilePage.ts\n * {key}: FEAT-002\n",
    )
    result, warnings = parse_page_object(text)

    assert result.entity is None
    assert [(w.code, w.message) for w in warnings] == [
        (Code.IGNORED_AUTHORED_KEY.name, f"'{key}:' is not a field this contract carries.")
    ]


def test_a_key_indented_deeper_than_the_key_level_is_a_second_line_of_the_key_above():
    """A key sits at the key level: one indented deeper is a further line of the key above. `route:` takes a single
    value, so the line is an `AUTHORING_ERROR` and is not read; the route stays whole."""
    header = _FULL_HEADER.replace(" * owners:                Platform Team", " *   owners:              Platform Team")
    result, warnings = parse_page_object(header)

    assert [w.code for w in warnings] == ["AUTHORING_ERROR"]
    assert "'route:' takes a single value" in warnings[0].message
    assert result.entity.owners == []
    assert result.page_ref.route == "/app/accounts/setup"
