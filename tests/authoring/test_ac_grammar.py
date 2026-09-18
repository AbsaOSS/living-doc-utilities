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
The acceptance-criterion header and extension grammar: the four states, the
version-less `planned` backlog form, the deprecated/removal-planned form, every
acceptance-criterion-level extension, the legacy `descoped` conversion, and every
`MALFORMED_AC` / `UNPARSED_AC_LINE` trigger (docs/contracts.md, "Errors and warnings").
"""

from pathlib import Path

import pytest

from living_doc_utilities.authoring.ac_grammar import (
    LEGACY_AC_STATE,
    MALFORMED_AC,
    UNPARSED_AC_LINE,
    parse_acceptance_criteria,
)
from living_doc_utilities.authoring.normalize import SourceFormat, normalize

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "agentic_toolkit_descope.md"


def _parse_one(text: str, entity_id: str = "US-001"):
    acs, warnings = parse_acceptance_criteria(text, entity_id=entity_id)
    return acs, warnings


def test_active_form_with_version():
    acs, warnings = _parse_one("AC:US-001-01 (v1.2.0 - active)\n- desc\n")

    assert warnings == []
    assert len(acs) == 1
    ac = acs[0]
    assert ac.state == "active"
    assert ac.version == "1.2.0"
    assert ac.description == "desc"


def test_planned_form_with_target_version():
    acs, warnings = _parse_one("AC:US-001-01 (v1.3.0 - planned)\n- desc\n")

    assert warnings == []
    ac = acs[0]
    assert ac.state == "planned"
    assert ac.version == "1.3.0"


def test_planned_backlog_form_without_version():
    acs, warnings = _parse_one("AC:US-001-01 (planned)\n- desc\n")

    assert warnings == []
    ac = acs[0]
    assert ac.state == "planned"
    assert ac.version is None


def test_deprecated_form_with_removal_planned():
    acs, warnings = _parse_one("AC:US-001-04 (v1.0.0 - deprecated - removal planned v2.0.0)\n- desc\n")

    assert warnings == []
    ac = acs[0]
    assert ac.state == "deprecated"
    assert ac.version == "1.0.0"
    assert ac.removal_planned == "2.0.0"


def test_every_acceptance_criterion_level_extension_parses():
    text = (
        "AC:FUNC-001-02 (v1.0.0 - active)\n"
        "- Raises {error code} when the credential check fails.\n"
        "- Aspect: minimum-length, character-classes\n"
        "- Error code: INVALID_PASSWORD, USER_NOT_FOUND, ACCOUNT_LOCKED\n"
        "- Rationale: Distinct error codes per failure reason.\n"
        "preconditions:\n"
        "  - A registered customer account exists.\n"
        "not_in_scope:\n"
        "  - Rate limiting.\n"
    )
    acs, warnings = _parse_one(text, entity_id="FUNC-001")

    assert warnings == []
    ac = acs[0]
    assert ac.description == "Raises {error code} when the credential check fails."
    assert ac.aspect == ["minimum-length", "character-classes"]
    assert ac.placeholder_values == {"error_code": ["INVALID_PASSWORD", "USER_NOT_FOUND", "ACCOUNT_LOCKED"]}
    assert ac.rationale == "Distinct error codes per failure reason."
    assert ac.preconditions == ["A registered customer account exists."]
    assert ac.not_in_scope == ["Rate limiting."]


@pytest.mark.parametrize(
    "inner",
    [
        "v1.0.0 - done",
        "active",
        "v1 - active",
    ],
    ids=["unknown_state", "missing_version", "unversioned_short_form"],
)
def test_malformed_headers_produce_malformed_ac(inner):
    acs, warnings = _parse_one(f"AC:US-001-01 ({inner})\n- desc\n")

    assert acs == []
    assert [w.code for w in warnings] == [MALFORMED_AC]


def test_header_with_no_id_is_malformed():
    acs, warnings = _parse_one("AC: (v1.0.0 - active)\n- desc\n")

    assert acs == []
    assert [w.code for w in warnings] == [MALFORMED_AC]


def test_legacy_descoped_state_converts_to_version_less_planned():
    acs, warnings = _parse_one("AC:US-001-03 (v1.2.0 - descoped)\n- desc\n- Rationale: deferred\n")

    assert [w.code for w in warnings] == [LEGACY_AC_STATE]
    ac = acs[0]
    assert ac.state == "planned"
    assert ac.version is None
    assert ac.rationale == "deferred"


def test_defect_form_parses_correctly_after_normalize_runs_first():
    raw = "AC:US-001-01 (v1.0 - In Review)\n- desc\n"
    normalized = normalize(raw, SourceFormat.ISSUE_BODY, "DocumentedUserStory")

    acs, warnings = _parse_one(normalized.text)

    assert warnings == []
    ac = acs[0]
    assert ac.state == "in_review"
    assert ac.version == "1.0.0"


def test_unassignable_ac_block_line_produces_unparsed_ac_line():
    text = "AC:US-001-01 (v1.0.0 - active)\n- desc\n- this line has no colon or recognised keyword\n"
    acs, warnings = _parse_one(text)

    assert len(acs) == 1
    assert [w.code for w in warnings] == [UNPARSED_AC_LINE]


@pytest.mark.parametrize(
    "inner",
    ["v1.2.0 - active", "v1.3.0 - planned", "planned", "v1.0.0 - deprecated - removal planned v2.0.0"],
)
def test_canonical_header_round_trips_through_normalize_and_ac_grammar_again(inner):
    text = f"AC:US-001-01 ({inner})\n- desc\n"
    acs, _ = _parse_one(text)
    ac = acs[0]

    header = ac.canonical_header()
    renormalized = normalize(f"{header}\n- desc\n", SourceFormat.ISSUE_BODY, "DocumentedUserStory")
    acs_again, warnings_again = _parse_one(renormalized.text)

    assert warnings_again == []
    assert acs_again[0] == ac
    assert acs_again[0].canonical_header() == header


def test_agentic_toolkit_descope_fixture_round_trips_with_only_legacy_warning():
    raw_text = FIXTURE_PATH.read_text(encoding="utf-8")
    # Strip the file's own provenance comment (an HTML comment block, not AC content).
    _, _, after_comment = raw_text.partition("-->")
    fixture_text = after_comment.strip("\n") + "\n"

    normalized = normalize(fixture_text, SourceFormat.ISSUE_BODY, "DocumentedUserStory")
    acs, warnings = parse_acceptance_criteria(normalized.text, entity_id="US-042")

    assert [w.code for w in warnings] == [LEGACY_AC_STATE]
    assert len(acs) == 1
    ac = acs[0]
    assert ac.id == "US-042-03"
    assert ac.state == "planned"
    assert ac.version is None
    assert ac.description == "Promo codes can be stacked and applied in defined priority order."
    assert ac.rationale == "Promo stacking rule deferred — too complex for current sprint"
