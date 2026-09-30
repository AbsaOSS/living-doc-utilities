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
Source-code inputs: a `UI` Feature's `feature_dependencies` target is `UNRESOLVED_RELATION`, as the canon expects.
Runs the parsers and `check_relations` over the source-code inputs, not the full collector.
"""

from living_doc_utilities.authoring.feature_header import parse_feature_header
from living_doc_utilities.authoring.page_object import parse_page_object
from living_doc_utilities.authoring.relations import check_relations
from living_doc_utilities.contracts.codes import Code
from tests.authoring.golden.helpers import read_fixture

# The header of AbsaOSS/living-doc's docs/examples/pageobject/RegistrationPage.ts at commit
# b00ca8c653dc09b58523d0fee9715657ae214905 (P35-LD12), verbatim; the class body is left out.
_CANON_REGISTRATION_PAGE = """\
/* =============================================================================
 * LIVING DOC — FEAT-003 · Registration Page
 * =============================================================================
 * surface_type:          UI
 * route:                 /register
 * owners:                Identity Team
 * purpose:               The screen where a new customer creates an account by entering an email and choosing a password.
 * user_stories:          none
 * functionalities:       none
 * external_dependencies: none
 * feature_dependencies:  FEAT-002
 * page-object:           RegistrationPage.ts
 * ============================================================================= */
"""


def test_a_ui_feature_dependency_is_unresolved_in_a_source_code_run_and_nothing_else():
    """A source-code project cannot document an `API` Feature yet, so FEAT-003 → FEAT-002 is only unresolved.
    Parsers plus `check_relations` only: the warning comes from `check_relations`, so no collector run is needed."""
    registration, registration_warnings = parse_page_object(_CANON_REGISTRATION_PAGE)
    login, login_warnings = parse_page_object(read_fixture("pageobject", "LoginPage.ts"))
    us_001, us_warnings = parse_feature_header(
        read_fixture("gherkin", "liv_doc_us", "us-001-customer-login.feature"), "DocumentedUserStory"
    )
    func_001, func_warnings = parse_feature_header(
        read_fixture("gherkin", "liv_doc_func", "func-001-validate-password-strength.feature"),
        "DocumentedFunctionality",
    )

    assert registration_warnings + login_warnings + us_warnings + func_warnings == []
    assert registration.entity.feature_dependencies == ["FEAT-002"]

    warnings = check_relations([registration.entity, login.entity, us_001, func_001])

    assert [(w.code, w.context) for w in warnings] == [
        (Code.UNRESOLVED_RELATION.name, "entity_id='FEAT-003' target='FEAT-002'")
    ]
