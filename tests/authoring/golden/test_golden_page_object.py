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

"""`LoginPage.ts` yields a stub FEAT-001 with no authored state, and a derived `active` state with FUNC-001."""

from living_doc_utilities.authoring.feature_header import parse_feature_header
from living_doc_utilities.authoring.page_object import parse_page_object
from living_doc_utilities.authoring.status import derive_statuses
from living_doc_utilities.contracts.codes import Code
from tests.authoring.golden.helpers import load_expected, read_fixture


def test_login_page_produces_feat_001_with_stub_reason_and_no_authored_state():
    """A PageObject header with no `status:` key produces an entity with no authored state and its `stub_reason` set."""
    text = read_fixture("pageobject", "LoginPage.ts")
    result, warnings = parse_page_object(text)

    assert warnings == []
    assert result is not None
    entity = result.entity
    assert entity is not None
    assert entity.entity_id == "FEAT-001"
    assert entity.state is None
    assert entity.stub_reason == (
        "Login template carries no test-id attributes yet; surface documented from the interface spec. "
        "discovered 2026-09-08"
    )

    expected = load_expected("feat-001-login-page.json")
    assert entity.purpose == expected["purpose"]
    assert entity.surface_type == expected["surface_type"]
    assert entity.owners == expected["owners"]
    assert entity.user_stories == expected["user_stories"]
    assert entity.functionalities == expected["functionalities"]
    assert entity.external_dependencies == expected["external_dependencies"]


def test_feature_state_derives_active_alongside_func_001():
    """A stub Feature derives to state active with state_origin derived once its child functionality is also parsed."""
    po_text = read_fixture("pageobject", "LoginPage.ts")
    po_result, po_warnings = parse_page_object(po_text)

    func_text = read_fixture("gherkin", "liv_doc_func", "func-001-validate-password-strength.feature")
    func_entity, func_warnings = parse_feature_header(func_text, "DocumentedFunctionality")

    assert po_warnings == []
    assert func_warnings == []

    derived, derive_warnings = derive_statuses([po_result.entity, func_entity])
    by_id = {e.entity_id: e for e in derived}

    assert derive_warnings == []
    assert by_id["FEAT-001"].state == "active"
    assert by_id["FEAT-001"].state_origin == "derived"


def test_status_key_is_ignored_with_the_documented_message():
    """A PageObject header's `status:` key is ignored with a message pointing authors at `stub-reason:` instead."""
    # The golden LoginPage.ts carries no `status:` key, so this test uses its own minimal synthetic header.
    text = (
        "/* =============================================================================\n"
        " * LIVING DOC — FEAT-002 · Sample Page\n"
        " * =============================================================================\n"
        " * surface_type:          UI\n"
        " * route:                 /sample\n"
        " * owners:                Sample Team\n"
        " * status:                candidate\n"
        " * purpose:               A sample page.\n"
        " * user_stories:          none\n"
        " * functionalities:       none\n"
        " * external_dependencies: none\n"
        " * page-object:           SamplePage.ts\n"
        " * ============================================================================= */\n"
    )
    result, warnings = parse_page_object(text)

    assert result is not None
    assert result.entity is not None
    assert result.entity.state is None
    assert [w.code for w in warnings] == [Code.IGNORED_AUTHORED_KEY.name]
    assert warnings[0].message == "Feature state is derived; use `stub-reason:` for an uninstrumented surface"
