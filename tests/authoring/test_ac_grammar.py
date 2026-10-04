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

"""The acceptance-criterion header and extension grammar, and every `MALFORMED_AC` / `UNPARSED_AC_LINE` trigger."""

from pathlib import Path

import pytest

from living_doc_utilities.authoring.ac_grammar import parse_acceptance_criteria
from living_doc_utilities.authoring.issue_body import parse_issue_body
from living_doc_utilities.authoring.normalize import SourceFormat, normalize
from living_doc_utilities.contracts.codes import Code

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "agentic_toolkit_descope.md"


def _parse_one(text: str, entity_id: str = "US-001"):
    acs, warnings = parse_acceptance_criteria(text, entity_id=entity_id)
    return acs, warnings


def test_active_form_with_version():
    """An AC header with an explicit version and "active" state parses to that state, version and description."""
    acs, warnings = _parse_one("AC:US-001-01 (v1.2.0 - active)\n- desc\n")

    assert warnings == []
    assert len(acs) == 1
    ac = acs[0]
    assert ac.state == "active"
    assert ac.version == "1.2.0"
    assert ac.description == "desc"


def test_planned_form_with_target_version():
    """An AC header in "planned" state with a target version parses to that state and version."""
    acs, warnings = _parse_one("AC:US-001-01 (v1.3.0 - planned)\n- desc\n")

    assert warnings == []
    ac = acs[0]
    assert ac.state == "planned"
    assert ac.version == "1.3.0"


def test_planned_backlog_form_without_version():
    """A "planned" AC header with no version parses to state "planned" with a null version."""
    acs, warnings = _parse_one("AC:US-001-01 (planned)\n- desc\n")

    assert warnings == []
    ac = acs[0]
    assert ac.state == "planned"
    assert ac.version is None


def test_deprecated_form_with_removal_planned():
    """A "deprecated" AC header with a "removal planned" version captures both the current and removal versions."""
    acs, warnings = _parse_one("AC:US-001-04 (v1.0.0 - deprecated - removal planned v2.0.0)\n- desc\n")

    assert warnings == []
    ac = acs[0]
    assert ac.state == "deprecated"
    assert ac.version == "1.0.0"
    assert ac.removal_planned == "2.0.0"


def test_every_acceptance_criterion_level_extension_parses():
    """Every AC-level extension (aspect, error code, rationale, preconditions, scope) parses onto its own field."""
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
    """An AC header with an unrecognised state, a missing version, or a bare "v1" form is rejected as malformed."""
    acs, warnings = _parse_one(f"AC:US-001-01 ({inner})\n- desc\n")

    assert acs == []
    assert [w.code for w in warnings] == [Code.MALFORMED_AC.name]


def test_header_with_no_id_is_malformed():
    """An AC header missing its id is rejected as malformed."""
    acs, warnings = _parse_one("AC: (v1.0.0 - active)\n- desc\n")

    assert acs == []
    assert [w.code for w in warnings] == [Code.MALFORMED_AC.name]


def test_legacy_descoped_state_converts_to_version_less_planned():
    """A legacy "descoped" AC state converts to version-less "planned" with a legacy-state warning, kept rationale."""
    acs, warnings = _parse_one("AC:US-001-03 (v1.2.0 - descoped)\n- desc\n- Rationale: deferred\n")

    assert [w.code for w in warnings] == [Code.LEGACY_AC_STATE.name]
    ac = acs[0]
    assert ac.state == "planned"
    assert ac.version is None
    assert ac.rationale == "deferred"


def test_defect_form_parses_correctly_after_normalize_runs_first():
    """An AC header normalized from a short version and non-canonical state still parses to the canonical form."""
    raw = "AC:US-001-01 (v1.0 - In Review)\n- desc\n"
    normalized = normalize(raw, SourceFormat.ISSUE_BODY, "DocumentedUserStory")

    acs, warnings = _parse_one(normalized.text)

    assert warnings == []
    ac = acs[0]
    assert ac.state == "in_review"
    assert ac.version == "1.0.0"


def test_unassignable_ac_block_line_produces_unparsed_ac_line():
    """An AC block line with no colon or recognised keyword is reported as unparsed without dropping the criterion."""
    text = "AC:US-001-01 (v1.0.0 - active)\n- desc\n- this line has no colon or recognised keyword\n"
    acs, warnings = _parse_one(text)

    assert len(acs) == 1
    assert [w.code for w in warnings] == [Code.UNPARSED_AC_LINE.name]


@pytest.mark.parametrize(
    "inner",
    ["v1.2.0 - active", "v1.3.0 - planned", "planned", "v1.0.0 - deprecated - removal planned v2.0.0"],
)
def test_canonical_header_round_trips_through_normalize_and_ac_grammar_again(inner):
    """An AC's canonical header, re-normalized and re-parsed, reproduces the identical criterion and header text."""
    text = f"AC:US-001-01 ({inner})\n- desc\n"
    acs, _ = _parse_one(text)
    ac = acs[0]

    header = ac.canonical_header()
    renormalized = normalize(f"{header}\n- desc\n", SourceFormat.ISSUE_BODY, "DocumentedUserStory")
    acs_again, warnings_again = _parse_one(renormalized.text)

    assert warnings_again == []
    assert acs_again[0] == ac
    assert acs_again[0].canonical_header() == header


def test_fenced_ac_example_is_never_parsed_as_a_real_criterion():
    """AC-header-shaped text inside a fenced code block is not parsed as a real acceptance criterion."""
    text = (
        "AC:US-001-01 (v1.0.0 - active)\n"
        "- desc\n"
        "\n"
        "```\n"
        "AC:US-999-01 (v9.9.9 - active)\n"
        "- this is a quoted example, not a real AC\n"
        "```\n"
    )
    acs, warnings = _parse_one(text)

    assert [ac.id for ac in acs] == ["US-001-01"]
    assert warnings == []


@pytest.mark.parametrize("inner", ["V1.0.0 - active", "1.0.0 - active"], ids=["uppercase_v", "missing_v"])
def test_non_canonical_version_prefix_is_malformed(inner):
    """An AC header whose version lacks the canonical lowercase "v" prefix is rejected as malformed."""
    acs, warnings = _parse_one(f"AC:US-001-01 ({inner})\n- desc\n")

    assert acs == []
    assert [w.code for w in warnings] == [Code.MALFORMED_AC.name]


def test_complete_feature_file_stops_at_the_closing_banner():
    """In a full feature-file header, the last AC's block stops at the closing banner, not the Feature/scenario body."""
    text = (
        "# =============================================================================\n"
        "# LIVING DOC — FUNC-1 · Password Strength\n"
        "# =============================================================================\n"
        "# status: active\n"
        "# parent: FEAT-1\n"
        "# func_type: field_validation\n"
        "#\n"
        "# acceptance_criteria:\n"
        "#\n"
        "#   AC:FUNC-1-01 (v1.0.0 - active)\n"
        "#     - rejects a weak password\n"
        "# =============================================================================\n"
        "\n"
        "@FUNC_ID:FUNC-1\n"
        "Feature: Password Strength\n"
        "\n"
        "  # AC:FUNC-1-01 (v1.0.0 - active) - rejects a weak password\n"
        "  @AC:FUNC-1-01\n"
        "  Scenario: weak password rejected\n"
        "    Given a weak password\n"
        "    When submitted\n"
        "    Then it is rejected\n"
    )
    normalized = normalize(text, SourceFormat.FEATURE_HEADER, "DocumentedFunctionality")

    acs, warnings = parse_acceptance_criteria(normalized.text, entity_id="FUNC-1")

    assert len(acs) == 1
    ac = acs[0]
    assert ac.id == "FUNC-1-01"
    assert ac.state == "active"
    assert ac.description == "rejects a weak password"
    assert warnings == []


def test_agentic_toolkit_descope_fixture_round_trips_with_only_legacy_warning():
    """A real-world descoped-AC fixture round-trips through normalize and parsing with only the legacy-state warning."""
    raw_text = FIXTURE_PATH.read_text(encoding="utf-8")
    # Strip the file's own provenance comment (an HTML comment block, not AC content).
    _, _, after_comment = raw_text.partition("-->")
    fixture_text = after_comment.strip("\n") + "\n"

    normalized = normalize(fixture_text, SourceFormat.ISSUE_BODY, "DocumentedUserStory")
    acs, warnings = parse_acceptance_criteria(normalized.text, entity_id="US-042")

    assert [w.code for w in warnings] == [Code.LEGACY_AC_STATE.name]
    assert len(acs) == 1
    ac = acs[0]
    assert ac.id == "US-042-03"
    assert ac.state == "planned"
    assert ac.version is None
    assert ac.description == "Promo codes can be stacked and applied in defined priority order."
    assert ac.rationale == "Promo stacking rule deferred — too complex for current sprint"


# --- indentation: a line's level decides what it belongs to (DEC-44) ---------------------------


def _feature_block(*lines: str) -> str:
    """A `.feature`-header criterion at the canon's levels: header at 2, content at 4."""
    return "\n".join(["#   AC:US-001-01 (v1.0.0 - active)", *(f"#     {line}" for line in lines)]) + "\n"


def test_a_bullet_back_at_criterion_level_closes_an_indented_sub_list():
    """After `preconditions:` with deeper items, a `- Aspect:` back at the key's indent is the criterion's aspect."""
    text = _feature_block(
        "- Valid credentials land on the dashboard.",
        "preconditions:",
        "  - An account exists.",
        "- Aspect: security",
    )
    acs, warnings = _parse_one(text)

    assert warnings == []
    assert acs[0].preconditions == ["An account exists."]
    assert acs[0].aspect == ["security"]


def test_a_sub_list_item_wrapped_deeper_stays_part_of_that_item():
    """A sub-list item's wrapped line, deeper than its `- `, is appended to it and closes nothing."""
    text = _feature_block(
        "- desc",
        "not_in_scope:",
        "  - Social sign-in, tracked",
        "    separately.",
        "- Aspect: mobile",
    )
    acs, warnings = _parse_one(text)

    assert warnings == []
    assert acs[0].not_in_scope == ["Social sign-in, tracked separately."]
    assert acs[0].aspect == ["mobile"]


def test_flat_sub_list_keeps_every_later_bullet_in_line_order():
    """Items at the sub-key's own indent (every issue body) keep the order rule: a later bullet joins the list."""
    text = "AC:US-001-01 (v1.0.0 - active)\n- desc\npreconditions:\n- An account exists.\n- Aspect: security\n"
    acs, warnings = _parse_one(text)

    assert warnings == []
    assert acs[0].preconditions == ["An account exists.", "Aspect: security"]
    assert acs[0].aspect == []


def test_unknown_sub_key_is_reported_with_exactly_the_lines_deeper_than_it():
    """An AC-level `notes:` and its two deeper bullets are `UNPARSED_AC_LINE`; the next content-level line is read."""
    text = _feature_block(
        "- desc",
        "notes:",
        "  - Owner: wallet team.",
        "  - Reviewed with security.",
        "- Aspect: security",
    )
    acs, warnings = _parse_one(text)

    assert [w.code for w in warnings] == [Code.UNPARSED_AC_LINE.name] * 3
    assert [w.context.split(" line=")[1] for w in warnings] == [
        "'notes:'",
        "'- Owner: wallet team.'",
        "'- Reviewed with security.'",
    ]
    assert acs[0].placeholder_values == {}
    assert acs[0].aspect == ["security"]


def test_an_unknown_sub_key_inside_a_nested_sub_list_does_not_end_that_list():
    """A `notes:` at a nested list's item level is reported with its own deeper lines only: the list stays open."""
    text = _feature_block(
        "- desc",
        "preconditions:",
        "  - An account exists.",
        "  notes:",
        "    - Owner: wallet team.",
        "  - The account is verified.",
        "- Aspect: security",
    )
    acs, warnings = _parse_one(text)

    # `notes:` sits at the items' indent, so `docs/authoring/ac-grammar.md` reads the next line at that indent
    # normally; closing the list here dropped every later item.
    assert acs[0].preconditions == ["An account exists.", "The account is verified."]
    assert acs[0].aspect == ["security"]
    assert [w.code for w in warnings] == [Code.UNPARSED_AC_LINE.name] * 2
    assert [w.context.split(" line=")[1] for w in warnings] == ["'notes:'", "'- Owner: wallet team.'"]


def test_a_line_deeper_than_an_aspect_item_is_reported_not_appended():
    """`Aspect:` takes no wrapped text, so a line deeper than its `- ` fills nothing and is `UNPARSED_AC_LINE`."""
    text = _feature_block("- desc", "- Aspect: security", "  also mobile")
    acs, warnings = _parse_one(text)

    assert acs[0].aspect == ["security"]
    assert [w.code for w in warnings] == [Code.UNPARSED_AC_LINE.name]
    assert [w.context.split(" line=")[1] for w in warnings] == ["'also mobile'"]


def test_a_block_opening_with_a_non_bullet_line_reports_it_and_the_criterion_is_malformed():
    """A block whose only line carries no `- ` has nothing to continue: the line is reported, the criterion dropped."""
    acs, warnings = _parse_one("AC:US-001-01 (v1.0.0 - active)\n  prose with no bullet\n")

    # No bullet means no description, so the criterion cannot be built at all — both halves are reported.
    assert acs == []
    assert [w.code for w in warnings] == [Code.UNPARSED_AC_LINE.name, Code.MALFORMED_AC.name]
    assert "line='prose with no bullet'" in warnings[0].context


def test_a_nested_item_between_two_open_levels_is_dropped_then_the_list_resumes():
    """A nested `- ` matching no open level is `MISINDENTED_LINE`; a later item back at an open level is kept."""
    text = _feature_block(
        "- Parent.",
        "  - B.",
        "    - C.",
        "   - D.",
        "  - E.",
    )
    acs, warnings = _parse_one(text)

    # `- D.` at indent 3 backs out of `- C.` without reaching `- B.`'s level, so it and nothing else is dropped;
    # `- E.` returns to an open level and is kept (`normalize.py::ItemText.fragment` clears the drop).
    assert acs[0].description == "Parent.\n  - B.\n    - C.\n  - E."
    assert [w.code for w in warnings] == [Code.MISINDENTED_LINE.name]
    assert [w.context.split(" line=")[1] for w in warnings] == ["'- D.'"]


def test_a_line_wrapped_deeper_than_a_criterion_item_is_never_an_ac_header():
    """A description's wrapped line reading `AC:<id> (...)` is its text, not a second criterion."""
    text = _feature_block("- Mirrors the rule of", "  AC:US-001-02 (v1.0.0 - active)")
    acs, warnings = _parse_one(text)

    assert warnings == []
    assert [ac.id for ac in acs] == ["US-001-01"]
    assert acs[0].description == "Mirrors the rule of AC:US-001-02 (v1.0.0 - active)"


def test_a_bullet_between_a_sub_key_and_its_items_is_misindented_and_dropped():
    """`- Aspect:` at 5, between `preconditions:` at 4 and its items at 6, fits no level: `MISINDENTED_LINE`."""
    text = "#   AC:US-001-01 (v1.0.0 - active)\n#     - desc\n#     preconditions:\n#       - An account exists.\n"
    text += "#      - Aspect: security\n#     - Rationale: Kept.\n"
    acs, warnings = _parse_one(text)

    assert [(w.code, w.context.split(" line=")[1]) for w in warnings] == [
        (Code.MISINDENTED_LINE.name, "'- Aspect: security'")
    ]
    assert acs[0].preconditions == ["An account exists."]
    assert acs[0].aspect == []
    assert acs[0].rationale == "Kept."


def test_a_line_shallower_than_the_blocks_content_level_is_misindented():
    """The first bullet sets the content level (4); a `- ` at 3 fits no level and fills nothing."""
    text = _feature_block("- desc") + "#    - Aspect: security\n"
    acs, warnings = _parse_one(text)

    assert [w.code for w in warnings] == [Code.MISINDENTED_LINE.name]
    assert acs[0].aspect == []


def test_a_nested_precondition_item_is_kept_in_its_parents_string():
    """A criterion's sub-list item may nest too: the child stays in its parent's entry, as extracted."""
    text = _feature_block(
        "- desc",
        "preconditions:",
        "  - An account exists.",
        "    - It is not locked.",
        "- Aspect: security",
    )
    acs, warnings = _parse_one(text)

    assert warnings == []
    assert acs[0].preconditions == ["An account exists.\n  - It is not locked."]
    assert acs[0].aspect == ["security"]


@pytest.mark.parametrize(
    "after",
    [["- Aspect: reporting"], []],
    ids=["followed_by_a_bullet", "last_line_of_the_block"],
)
def test_a_bare_key_with_nothing_deeper_under_it_is_wrapped_text(after):
    """`totals:` at the item's own indent ends a wrapped description, as it always did: no key, no warning."""
    text = _feature_block("- The summary page lists the account", "totals:", *after)
    acs, warnings = _parse_one(text)

    assert warnings == []
    assert acs[0].description == "The summary page lists the account totals:"
    assert acs[0].aspect == (["reporting"] if after else [])


def test_a_flat_unknown_key_is_read_as_wrapped_text_and_its_bullets_as_criterion_lines():
    """A `notes:` whose bullet sits at its own indent reads as wrapped text, exactly as it always did."""
    text = _feature_block("- desc", "notes:", "- Owner: wallet team.")
    acs, warnings = _parse_one(text)

    assert warnings == []
    assert acs[0].description == "desc notes:"
    assert acs[0].placeholder_values == {"owner": ["wallet team."]}


def test_sub_list_state_resets_between_criterion_blocks():
    """A flat `preconditions:` list ends with its criterion: the next criterion's `- Aspect:` is its aspect."""
    text = _feature_block("- d1", "preconditions:", "- An account exists.")
    text += "#   AC:US-001-02 (v1.0.0 - active)\n#     - d2\n#     - Aspect: security\n"
    acs, warnings = _parse_one(text)

    assert warnings == []
    assert acs[0].preconditions == ["An account exists."]
    assert (acs[1].preconditions, acs[1].aspect) == ([], ["security"])


# --- D22: a criterion with nothing under its header -------------------------------------------------------


@pytest.mark.parametrize(
    "body",
    [
        "## Acceptance Criteria\n\n### AC:US-001-01 (v1.0.0 - active)\n",
        "## Acceptance Criteria\n\n### AC:US-001-01 (v1.0.0 - active)\n\n### AC:US-001-02 (v1.0.0 - active)\n\n- d\n",
    ],
    ids=["alone", "before_a_valid_one"],
)
def test_a_criterion_with_nothing_under_its_header_is_reported_and_the_rest_is_read(body):
    """`D22`: an empty criterion block no longer raises; that criterion is dropped with `MALFORMED_AC` naming the
    missing description, and every other criterion is read."""
    entity, warnings = parse_issue_body(body, "US-001 · S", "DocumentedUserStory")

    assert entity is not None
    assert [ac.id for ac in entity.acceptance_criteria] == (["US-001-02"] if "US-001-02" in body else [])
    assert [(w.code, w.message) for w in warnings] == [
        (Code.MALFORMED_AC.name, "Acceptance criterion has no description line.")
    ]
    assert "line_no=3" in warnings[0].context
