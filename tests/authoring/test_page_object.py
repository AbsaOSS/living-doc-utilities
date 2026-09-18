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

"""PageObject header parsing: full header, cross-reference header, unrecognised key, and
`normalize`-before-grammar."""

from living_doc_utilities.authoring.page_object import IGNORED_AUTHORED_KEY, parse_page_object

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
    assert result.entity.wizard_steps == ["Profile", "Preferences", "Review", "Confirm"]
    assert result.page_ref.is_primary is True
    assert result.page_ref.route == "/app/accounts/setup"
    assert result.page_ref.page_object == "AccountSetupWizardPage.ts"


def test_cross_reference_header_produces_no_entity_but_a_page_ref():
    result, warnings = parse_page_object(_CROSS_REFERENCE_HEADER)

    assert warnings == []
    assert result.entity is None
    assert result.parent_feat == "FEAT-042"
    assert result.page_ref.is_primary is False
    assert result.page_ref.functionalities == ["FUNC-005"]
    assert result.page_ref.page_object == "AccountSetupWizardProfilePage.ts"


def test_unrecognised_key_produces_ignored_authored_key():
    result, warnings = parse_page_object(_HEADER_WITH_UNKNOWN_KEY)

    assert result is not None
    assert [w.code for w in warnings] == [IGNORED_AUTHORED_KEY]
    assert "query_params" in warnings[0].message


def test_missing_title_line_produces_missing_entity_id():
    text = "/* ===\n * no title here\n * === */\n"
    result, warnings = parse_page_object(text)

    assert result is None
    assert [w.code for w in warnings] == ["MISSING_ENTITY_ID"]


def test_en_dash_input_is_normalized_before_extraction():
    # The id-to-title separator (an en dash here, instead of the canonical " · ") is
    # `normalize`'s job (rule 5); the "LIVING DOC — " marker ahead of the id is left
    # untouched by `normalize` itself (normalize.py), so it stays the literal em dash canon
    # always uses there.
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
