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
Every information-losing skip a parser in this package can take is reported as a coded
`ContractWarning`, never as a bare `logging` call that the caller has no structured way to
see. `test_no_authoring_module_uses_the_logging_module` proves the second half statically
(nothing to log through, so there is nothing to lose); the parametrized case below proves
the first half dynamically, with a log-capture fixture confirming no log record fires
alongside the warning either.
"""

import logging
from pathlib import Path

import pytest

from living_doc_utilities.authoring.ac_grammar import parse_acceptance_criteria
from living_doc_utilities.authoring.feature_header import parse_feature_header
from living_doc_utilities.authoring.identity import derive_entity_id
from living_doc_utilities.authoring.issue_body import parse_issue_body
from living_doc_utilities.authoring.page_object import parse_page_object
from living_doc_utilities.authoring.scenario import parse_scenarios
from living_doc_utilities.contracts.envelope import ContractWarning

AUTHORING_DIR = Path(__file__).resolve().parents[2] / "living_doc_utilities" / "authoring"


def test_no_authoring_module_uses_the_logging_module():
    """No module under `living_doc_utilities/authoring` imports the `logging` module; warnings carry state instead."""
    offenders = [path.name for path in AUTHORING_DIR.glob("*.py") if "import logging" in path.read_text(encoding="utf-8")]
    assert offenders == []


def _skip_cases():
    yield "identity", lambda: derive_entity_id("No id here")[1]
    yield "issue_body_unknown_section", lambda: parse_issue_body(
        "## Description\n\nd\n\n## Nonsense\n\nv\n", "US-001 · S", "DocumentedUserStory"
    )[1]
    yield "issue_body_missing_id", lambda: parse_issue_body("## Description\n\nd\n", "No id", "DocumentedUserStory")[1]
    yield "feature_header_missing_id", lambda: parse_feature_header("# not a header\n", "DocumentedUserStory")[1]
    yield "page_object_missing_id", lambda: parse_page_object("/* no title */\n")[1]
    yield "ac_grammar_malformed", lambda: parse_acceptance_criteria("AC: (v1.0.0 - active)\n- desc\n")[1]
    yield "scenario_malformed_tag", lambda: parse_scenarios(
        "Feature: S\n\n  @AC:not-valid\n  Scenario: Sc\n    Given a step\n", "DocumentedUserStory"
    )[1]


@pytest.mark.parametrize("name, produce_warnings", list(_skip_cases()), ids=[c[0] for c in _skip_cases()])
def test_information_losing_skip_produces_a_coded_warning_and_no_log_record(name, produce_warnings, caplog):
    """Every parser's information-losing skip produces a coded `ContractWarning`, never a bare `logging` record."""
    with caplog.at_level(logging.DEBUG):
        warnings = produce_warnings()

    assert warnings, f"{name} produced no warnings for its skip case"
    for warning in warnings:
        assert isinstance(warning, ContractWarning)
        assert warning.code
        assert warning.message
    assert caplog.records == []
