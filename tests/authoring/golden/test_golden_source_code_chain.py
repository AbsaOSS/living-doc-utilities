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


def test_a_ui_feature_dependency_is_unresolved_in_a_source_code_run_and_nothing_else():
    """A source-code project cannot document an `API` Feature yet, so FEAT-003 → FEAT-002 is only unresolved.
    Parsers plus `check_relations` only: the warning comes from `check_relations`, so no collector run is needed."""
    registration, registration_warnings = parse_page_object(read_fixture("pageobject", "RegistrationPage.ts"))
    login, login_warnings = parse_page_object(read_fixture("pageobject", "LoginPage.ts"))
    us_001, us_warnings = parse_feature_header(
        read_fixture("gherkin", "liv_doc_us", "us-001-customer-login.feature"), "DocumentedUserStory"
    )
    func_001, func_001_warnings = parse_feature_header(
        read_fixture("gherkin", "liv_doc_func", "func-001-validate-password-strength.feature"),
        "DocumentedFunctionality",
    )
    func_002, func_002_warnings = parse_feature_header(
        read_fixture("gherkin", "liv_doc_func", "func-002-reject-breached-password.feature"),
        "DocumentedFunctionality",
    )

    assert (
        registration_warnings + login_warnings + us_warnings + func_001_warnings + func_002_warnings == []
    ), "a canon source-code input parses with no warning of its own"
    assert registration.entity.feature_dependencies == ["FEAT-002"]

    warnings = check_relations([registration.entity, login.entity, us_001, func_001, func_002])

    assert [(w.code, w.context) for w in warnings] == [
        (Code.UNRESOLVED_RELATION.name, "entity_id='FEAT-003' target='FEAT-002'")
    ]


def test_no_source_code_input_of_the_corpus_authors_a_note():
    """The canon's source-code corpus carries no `notes:` key, so every entity it yields has an empty `notes`."""
    registration, _ = parse_page_object(read_fixture("pageobject", "RegistrationPage.ts"))
    login, _ = parse_page_object(read_fixture("pageobject", "LoginPage.ts"))
    us_001, _ = parse_feature_header(
        read_fixture("gherkin", "liv_doc_us", "us-001-customer-login.feature"), "DocumentedUserStory"
    )

    assert registration.entity.notes == []
    assert login.entity.notes == []
    assert us_001.notes == []
