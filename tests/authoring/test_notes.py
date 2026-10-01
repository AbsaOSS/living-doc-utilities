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
The entity-level `notes` field across all three parsers: a bullet list that round-trips, that
nothing ever interprets, and that the criterion grammar reports rather than accepts on an AC.
"""

import pytest

from living_doc_utilities.authoring.feature_header import parse_feature_header
from living_doc_utilities.authoring.issue_body import parse_issue_body
from living_doc_utilities.authoring.normalize import RULE_BULLET_MARKER, SourceFormat, normalize
from living_doc_utilities.authoring.page_object import parse_page_object
from living_doc_utilities.authoring.status import derive_statuses
from living_doc_utilities.contracts.codes import Code

# --- the field, on each authoring surface ---------------------------------------------

_US_BODY = """\
## Description

As a customer, I can sign in.

## Status

active

## Notes

- The sign-in form markup lives in the shared identity template.
- The screen is called "Sign in" to customers.

## Acceptance Criteria

### AC:US-001-01 (v1.0.0 - active)

- Valid credentials land on the dashboard.
"""

_FEATURE_BODY = """\
## Description

The login screen.

## Surface Type

UI

## Owners

Identity Team

## User Stories

none

## Functionalities

none

## Notes

- The surface can change without any commit in this repository.
"""

_FUNC_BODY = """\
## Description

Validates a password.

## Status

active

## Parent Feature

FEAT-001

## Func Type

field_validation

## Notes

- The complexity policy itself is owned server-side.
"""

_US_HEADER_WITH_NOTES = """\
# =============================================================================
# LIVING DOC — US-001 · Sample Story
# =============================================================================
# status:          active
# business_value:
#   - Value one.
# notes:
#   - The sign-in form markup lives in the shared identity template.
#   - The screen is called "Sign in" to customers.
#
# acceptance_criteria:
#
#   AC:US-001-01 (v1.0.0 - active)
#     - Valid credentials land on the dashboard.
# =============================================================================

@US_ID:US-001
Feature: Sample Story
"""

_FUNC_HEADER_WITH_NOTES = """\
# =============================================================================
# LIVING DOC — FUNC-001 · Sample Functionality
# =============================================================================
# status:    active
# parent:    FEAT-001
# func_type: field_validation
# notes:
#   - The complexity policy itself is owned server-side.
# =============================================================================

@FUNC_ID:FUNC-001
Feature: Sample Functionality
"""

_PAGE_OBJECT_WITH_NOTES = """\
/* =============================================================================
 * LIVING DOC — FEAT-042 · Account Setup Wizard
 * =============================================================================
 * surface_type:          UI
 * route:                 /app/accounts/setup
 * owners:                Platform Team
 * purpose:               Multi-step wizard for creating a new account.
 * user_stories:          none
 * functionalities:       none
 * external_dependencies: none
 * page-object:           AccountSetupWizardPage.ts
 * notes:
 *   - Step order is fixed; the review step cannot be skipped.
 *   - The wizard shares one URL with its step files.
 * ============================================================================= */
"""


@pytest.mark.parametrize(
    "body, title, entity_type, expected",
    [
        (
            _US_BODY,
            "US-001 · Customer Login",
            "DocumentedUserStory",
            [
                "The sign-in form markup lives in the shared identity template.",
                'The screen is called "Sign in" to customers.',
            ],
        ),
        (
            _FEATURE_BODY,
            "FEAT-001 · Login Page",
            "DocumentedFeature",
            ["The surface can change without any commit in this repository."],
        ),
        (
            _FUNC_BODY,
            "FUNC-001 · Validate Password",
            "DocumentedFunctionality",
            ["The complexity policy itself is owned server-side."],
        ),
    ],
    ids=["user_story", "feature", "functionality"],
)
def test_an_authored_notes_section_round_trips_on_every_entity_type(body, title, entity_type, expected):
    """`## Notes` is a bullet list on all three types: each bullet becomes one entry and nothing warns."""
    entity, warnings = parse_issue_body(body, title, entity_type)

    assert entity is not None
    assert entity.notes == expected
    assert warnings == [], "a `## Notes` heading is a field now, not an UNKNOWN_SECTION"


@pytest.mark.parametrize(
    "text, entity_type, expected",
    [
        (
            _US_HEADER_WITH_NOTES,
            "DocumentedUserStory",
            [
                "The sign-in form markup lives in the shared identity template.",
                'The screen is called "Sign in" to customers.',
            ],
        ),
        (
            _FUNC_HEADER_WITH_NOTES,
            "DocumentedFunctionality",
            ["The complexity policy itself is owned server-side."],
        ),
    ],
    ids=["user_story", "functionality"],
)
def test_an_authored_notes_key_round_trips_through_the_feature_header_parser(text, entity_type, expected):
    """`# notes:` is a recognised bullet key on both `.feature`-header types, no longer an ignored key."""
    entity, warnings = parse_feature_header(text, entity_type)

    assert entity is not None
    assert entity.notes == expected
    assert warnings == [], "a `notes:` key is a field now, not an IGNORED_AUTHORED_KEY"


def test_an_authored_notes_key_round_trips_through_the_page_object_parser():
    """A full PageObject header's `notes:` bullet list reaches the Feature's `notes`, with no warning."""
    result, warnings = parse_page_object(_PAGE_OBJECT_WITH_NOTES)

    assert result is not None and result.entity is not None
    assert result.entity.notes == [
        "Step order is fixed; the review step cannot be skipped.",
        "The wizard shares one URL with its step files.",
    ]
    assert warnings == [], "a `notes:` key is a field now, not an IGNORED_AUTHORED_KEY"


def test_a_note_on_a_cross_reference_page_object_header_is_an_unrecognised_key():
    """A note is Feature-level, and a cross-reference header describes only its own page, so `notes:` is unknown."""
    text = (
        "/* =============================================================================\n"
        " * LIVING DOC — FEAT-042 · Account Setup Wizard  [cross-reference]\n"
        " * =============================================================================\n"
        " * parent-feat:     FEAT-042\n"
        " * route:           /app/accounts/setup\n"
        " * owners:          Platform Team\n"
        " * purpose:         Step 1 (Profile).\n"
        " * page-object:     AccountSetupWizardProfilePage.ts\n"
        " * notes:\n"
        " *   - A note belongs on the primary file.\n"
        " * ============================================================================= */\n"
    )
    result, warnings = parse_page_object(text)

    assert result is not None
    assert result.entity is None
    assert [w.code for w in warnings] == [Code.IGNORED_AUTHORED_KEY.name]
    assert warnings[0].message == "'notes:' is not a field this contract carries."


# --- a note is never interpreted ------------------------------------------------------

# A note whose text a naive parser would read as a field: the state word, the date and the key shape are all there.
_FIELD_SHAPED_NOTE_LINES = [
    "- status: deprecated",
    "- deprecated_at: 2026-01-01",
    "- superseded_by: US-002",
    "- The old flow was in_review until the rewrite landed.",
]


def test_a_field_shaped_note_changes_no_derived_state_and_raises_no_warning():
    """A note reading `status: deprecated` stays free text: the authored state, the deprecation fields and the
    warning list are all exactly what they are without it. The guard against `notes` acquiring semantics."""
    notes_block = "\n".join(_FIELD_SHAPED_NOTE_LINES)
    without = _US_BODY.replace("## Notes\n\n", "").replace(
        "- The sign-in form markup lives in the shared identity template.\n"
        '- The screen is called "Sign in" to customers.\n\n',
        "",
    )
    with_note = without.replace("## Acceptance Criteria", f"## Notes\n\n{notes_block}\n\n## Acceptance Criteria")

    plain, plain_warnings = parse_issue_body(without, "US-001 · Customer Login", "DocumentedUserStory")
    noted, noted_warnings = parse_issue_body(with_note, "US-001 · Customer Login", "DocumentedUserStory")

    assert plain is not None and noted is not None
    assert noted.notes == [line.removeprefix("- ") for line in _FIELD_SHAPED_NOTE_LINES]
    assert noted_warnings == plain_warnings == []

    plain_derived, plain_derive_warnings = derive_statuses([plain])
    noted_derived, noted_derive_warnings = derive_statuses([noted])

    assert noted_derive_warnings == plain_derive_warnings == []
    # Every field but `notes` is identical, so nothing read the note's text.
    assert noted_derived[0].model_dump(exclude={"notes"}) == plain_derived[0].model_dump(exclude={"notes"})
    assert noted_derived[0].state == "active"
    assert noted_derived[0].state_origin == "authored"
    assert noted_derived[0].deprecated_at is None
    assert noted_derived[0].superseded_by is None


def test_a_field_shaped_note_in_a_feature_header_changes_no_state_either():
    """The same guard on the `.feature`-header surface, where a bullet's wrapped line could read as a key."""
    notes_block = "\n".join(f"#   {line}" for line in _FIELD_SHAPED_NOTE_LINES)
    text = _US_HEADER_WITH_NOTES.replace(
        "#   - The sign-in form markup lives in the shared identity template.\n"
        '#   - The screen is called "Sign in" to customers.\n',
        f"{notes_block}\n",
    )

    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert entity is not None
    assert warnings == []
    assert entity.notes == [line.removeprefix("- ") for line in _FIELD_SHAPED_NOTE_LINES]
    assert entity.state == "active"
    assert entity.deprecated_at is None
    assert entity.superseded_by is None
    # The note names no criterion, so the header's one AC is still the only one.
    assert [ac.id for ac in entity.acceptance_criteria] == ["US-001-01"]


def test_a_note_whose_wrapped_line_reads_as_a_page_object_key_is_still_just_a_note():
    """`status:` is a key the PageObject parser recognises only to drop, so a note wrapping onto a line that
    reads `status: deprecated` is the sharpest case: it stays the note's own text and raises no ignored-key
    warning, because a line deeper than the item's `- ` is never a key."""
    text = _PAGE_OBJECT_WITH_NOTES.replace(
        " *   - The wizard shares one URL with its step files.\n",
        " *   - The old single-page flow was\n *     status: deprecated until the rewrite landed.\n",
    )
    result, warnings = parse_page_object(text)

    assert result is not None and result.entity is not None
    assert warnings == [], "the note's wrapped line must not be read as the `status:` key"
    assert result.entity.notes == [
        "Step order is fixed; the review step cannot be skipped.",
        "The old single-page flow was status: deprecated until the rewrite landed.",
    ]
    assert result.entity.state is None


# --- a note on an acceptance criterion is reported, never accepted --------------------


def test_an_ac_level_notes_key_in_an_issue_body_is_reported_and_reads_as_no_field():
    """`notes:` inside a criterion block is `UNPARSED_AC_LINE`, for the key line and each line deeper than it."""
    # The flat issue-body layout: a criterion sub-key sits at its bullets' own level, as `preconditions:` does.
    body = """\
## Description

As a customer, I can sign in.

## Status

active

## Acceptance Criteria

### AC:US-001-01 (v1.0.0 - active)

- Valid credentials land on the dashboard.
notes:
  - A note has no home on a criterion.
  - Nor does this one.
"""
    entity, warnings = parse_issue_body(body, "US-001 · Customer Login", "DocumentedUserStory")

    assert entity is not None
    assert [w.code for w in warnings] == [Code.UNPARSED_AC_LINE.name] * 3
    criterion = entity.acceptance_criteria[0]
    assert criterion.description == "Valid credentials land on the dashboard."
    assert criterion.preconditions == criterion.not_in_scope == []
    assert criterion.rationale is None
    assert criterion.placeholder_values == {}
    # Notes on an AC stay out of the contract; only the entity carries the field.
    assert "notes" not in type(criterion).model_fields
    assert entity.notes == []


def test_an_ac_level_notes_key_deeper_than_the_description_bullet_is_that_bullets_text():
    """Which rule owns an AC-level `notes:` is decided by its indent, and the deeper-line rule wins.

    A line deeper than the open item's `- ` is that item's text, never a key, whatever it reads like
    (`normalize.py::ItemText`). So this shape raises nothing and no `notes` field appears: the key text
    stays inside the description string, as authored. The unknown-sub-key rule only reaches a key at the
    criterion's own content level, the case above."""
    body = """\
## Description

As a customer, I can sign in.

## Status

active

## Acceptance Criteria

### AC:US-001-01 (v1.0.0 - active)

- Valid credentials land on the dashboard.
  notes:
    - A note has no home on a criterion.
"""
    entity, warnings = parse_issue_body(body, "US-001 · Customer Login", "DocumentedUserStory")

    assert entity is not None
    assert warnings == []
    criterion = entity.acceptance_criteria[0]
    assert criterion.description == (
        "Valid credentials land on the dashboard. notes:\n    - A note has no home on a criterion."
    )
    assert entity.notes == []


def test_an_ac_level_notes_key_whose_items_sit_at_its_own_level_reports_only_the_items():
    """The flat layout with no line deeper than the key: `P35-UT8`'s rule needs a deeper following line, so the
    key line is read as the description's wrapped text and only its items are reported. Recorded, not relied on -
    the key's text reaching `description` is a limitation of that rule, unchanged by this task."""
    body = """\
## Description

As a customer, I can sign in.

## Status

active

## Acceptance Criteria

### AC:US-001-01 (v1.0.0 - active)

- Valid credentials land on the dashboard.

notes:

- A note has no home on a criterion.
"""
    entity, warnings = parse_issue_body(body, "US-001 · Customer Login", "DocumentedUserStory")

    assert entity is not None
    assert [w.code for w in warnings] == [Code.UNPARSED_AC_LINE.name]
    assert entity.acceptance_criteria[0].description == "Valid credentials land on the dashboard. notes:"
    assert entity.notes == []


def test_an_ac_level_notes_key_in_a_feature_header_is_reported_and_reads_as_no_field():
    """The same diagnostic on the `.feature`-header surface: the key line and each deeper line are reported."""
    text = """\
# =============================================================================
# LIVING DOC — US-001 · Sample Story
# =============================================================================
# status:          active
#
# acceptance_criteria:
#
#   AC:US-001-01 (v1.0.0 - active)
#     - Valid credentials land on the dashboard.
#     notes:
#       - A note has no home on a criterion.
#       - Nor does this one.
# =============================================================================

@US_ID:US-001
Feature: Sample Story
"""
    entity, warnings = parse_feature_header(text, "DocumentedUserStory")

    assert entity is not None
    assert [w.code for w in warnings] == [Code.UNPARSED_AC_LINE.name] * 3
    criterion = entity.acceptance_criteria[0]
    assert criterion.description == "Valid credentials land on the dashboard."
    assert criterion.preconditions == criterion.not_in_scope == []
    assert entity.notes == []


# --- what a note's own list loses is reported, like every other bullet field ----------


def test_page_object_notes_text_before_the_first_bullet_is_reported():
    """`notes:` gives the PageObject parser its first bullet field, so its dropped text now warns too."""
    text = _PAGE_OBJECT_WITH_NOTES.replace(
        " * notes:\n", " * notes:                 This sentence sits outside any bullet.\n"
    )
    result, warnings = parse_page_object(text)

    assert result is not None and result.entity is not None
    assert [w.code for w in warnings] == [Code.UNPARSED_BULLET_LINE.name]
    assert "This sentence sits outside any bullet." in warnings[0].message
    assert warnings[0].context == "entity_id='FEAT-042' field='notes'"
    assert result.entity.notes == [
        "Step order is fixed; the review step cannot be skipped.",
        "The wizard shares one URL with its step files.",
    ]


def test_page_object_notes_line_shallower_than_its_list_is_reported_as_misindented():
    """A `notes:` item shallower than the list's own level fits no level and is dropped with `MISINDENTED_LINE`."""
    text = _PAGE_OBJECT_WITH_NOTES.replace(
        " *   - The wizard shares one URL with its step files.\n",
        " * - The wizard shares one URL with its step files.\n",
    )
    result, warnings = parse_page_object(text)

    assert result is not None and result.entity is not None
    assert [w.code for w in warnings] == [Code.MISINDENTED_LINE.name]
    assert warnings[0].context == (
        "entity_id='FEAT-042' field='notes' line='- The wizard shares one URL with its step files.'"
    )
    assert result.entity.notes == ["Step order is fixed; the review step cannot be skipped."]


@pytest.mark.parametrize("marker", ["•", "*", "–", "—", "+"], ids=["dot", "star", "en_dash", "em_dash", "plus"])
def test_a_note_written_with_a_non_canonical_bullet_marker_is_still_read(marker):
    """Rule 1 reaches a PageObject `notes:` list, so a `•`-marked note is read exactly as a `-`-marked one."""
    text = _PAGE_OBJECT_WITH_NOTES.replace(" *   - ", f" *   {marker} ")
    result, warnings = parse_page_object(text)

    assert result is not None and result.entity is not None
    assert warnings == []
    assert result.entity.notes == [
        "Step order is fixed; the review step cannot be skipped.",
        "The wizard shares one URL with its step files.",
    ]


def test_a_note_list_mixing_canonical_and_non_canonical_markers_still_splits_per_item():
    """The case that would otherwise merge silently: without rule 1 the `•` item has no marker the reader
    knows, so it joins the open item instead of starting the next one, and nothing warns."""
    text = _PAGE_OBJECT_WITH_NOTES.replace(
        " *   - The wizard shares one URL with its step files.\n",
        " *   • The wizard shares one URL with its step files.\n",
    )
    result, warnings = parse_page_object(text)

    assert result is not None and result.entity is not None
    assert warnings == []
    assert result.entity.notes == [
        "Step order is fixed; the review step cannot be skipped.",
        "The wizard shares one URL with its step files.",
    ]


def test_rule_one_does_not_reach_a_jsdoc_notes_block_further_down_the_file():
    """The header comment's `*/` closes rule 1 for the rest of the file, so a JSDoc block with a `notes:`
    line of its own is never rewritten - normalisation never touches TypeScript."""
    # A `•` in the header *and* one in the JSDoc, so the test shows the rule firing on one and not the other.
    text = _PAGE_OBJECT_WITH_NOTES.replace(" *   - ", " *   • ") + (
        "\nexport class AccountSetupWizardPage {\n"
        "  /**\n"
        "   * notes:\n"
        "   *   • Not a living-doc note; a JSDoc line of its own.\n"
        "   */\n"
        "  async goto(): Promise<void> {}\n"
        "}\n"
    )
    normalized = normalize(text, SourceFormat.PAGE_OBJECT, "DocumentedFeature")

    # The JSDoc line keeps its marker; the header's two note lines lost theirs to rule 1.
    assert "   *   • Not a living-doc note; a JSDoc line of its own." in normalized.lines
    assert [change.rule for change in normalized.changes] == [RULE_BULLET_MARKER, RULE_BULLET_MARKER]
    assert [change.after for change in normalized.changes] == [
        " *   - Step order is fixed; the review step cannot be skipped.",
        " *   - The wizard shares one URL with its step files.",
    ]

    result, warnings = parse_page_object(text)
    assert result is not None and result.entity is not None
    assert warnings == []
    assert result.entity.notes == [
        "Step order is fixed; the review step cannot be skipped.",
        "The wizard shares one URL with its step files.",
    ]


def test_a_nested_note_stays_inside_its_parents_string_as_extracted():
    """A note is a bullet field, so `DEC-45`'s nested-item form applies with no rule of its own."""
    text = _PAGE_OBJECT_WITH_NOTES.replace(
        " *   - The wizard shares one URL with its step files.\n",
        " *     - The step files each carry a cross-reference header.\n",
    )
    result, warnings = parse_page_object(text)

    assert result is not None and result.entity is not None
    assert warnings == []
    assert result.entity.notes == [
        "Step order is fixed; the review step cannot be skipped.\n  - The step files each carry a cross-reference header."
    ]


# --- a note's text never decides how the header is read --------------------------------


def test_a_note_whose_wrapped_line_reads_as_parent_feat_does_not_make_a_cross_reference_header():
    """`parent-feat:` picks the key set, so it is read as a key and not scanned for: a note's wrapped
    line may say it and is still that note's text. Branching here cost the whole Feature (#168)."""
    text = _PAGE_OBJECT_WITH_NOTES.replace(
        " *   - The wizard shares one URL with its step files.\n",
        " *   - The wizard owns its own header; the\n *     parent-feat: convention is for its step files.\n",
    )
    result, warnings = parse_page_object(text)

    assert result is not None and warnings == []
    # The full header survived: an entity, no `parent_feat`, and the note kept its wrapped line.
    assert result.parent_feat is None
    assert result.entity is not None
    assert result.entity.notes == [
        "Step order is fixed; the review step cannot be skipped.",
        "The wizard owns its own header; the parent-feat: convention is for its step files.",
    ]


def test_a_cross_reference_header_is_still_detected_through_a_wrapped_purpose():
    """The companion case: `parent-feat:` on a real cross-reference header is still found, with the
    canon's wrapped `purpose:` value in the value column (living-doc-header-types.md)."""
    text = """\
/* =============================================================================
 * LIVING DOC — FEAT-042 · Account Setup Wizard  [cross-reference]
 * =============================================================================
 * parent-feat:     FEAT-042
 * route:           /app/accounts/setup
 * owners:          Platform Team
 * purpose:         Step 1 (Profile) - user profile fields: display name,
 *                  and role selection.
 * page-object:     AccountSetupWizardProfilePage.ts
 * ============================================================================= */
"""
    result, warnings = parse_page_object(text)

    assert result is not None and warnings == []
    assert result.parent_feat == "FEAT-042"
    assert result.entity is None


def test_a_note_that_mentions_living_doc_is_still_a_note():
    """The banner-title guard matches the title line, not the words: a note may say `LIVING DOC`.
    Testing for the substring closed the list and dropped every note after it, silently (#168)."""
    text = _PAGE_OBJECT_WITH_NOTES.replace(
        " *   - Step order is fixed; the review step cannot be skipped.\n",
        " *   - The LIVING DOC banner above names the owning Feature.\n",
    )
    result, warnings = parse_page_object(text)

    assert result is not None and result.entity is not None
    assert warnings == []
    assert result.entity.notes == [
        "The LIVING DOC banner above names the owning Feature.",
        "The wizard shares one URL with its step files.",
    ]


def test_a_note_quoting_a_whole_banner_title_is_still_a_note():
    """The sharpest form of the guard above: a note may quote the title form itself, em-dash and all.
    Testing the form and not the words still read the note's own text as a boundary, so the list closed
    at that item and every note was dropped - silently, since a closed key loses no text (#168)."""
    text = _PAGE_OBJECT_WITH_NOTES.replace(
        " *   - Step order is fixed; the review step cannot be skipped.\n",
        " *   - See the LIVING DOC — FEAT-002 · Breached Password Check banner for the API surface.\n",
    )
    result, warnings = parse_page_object(text)

    assert result is not None and result.entity is not None
    assert warnings == []
    assert result.entity.notes == [
        "See the LIVING DOC — FEAT-002 · Breached Password Check banner for the API surface.",
        "The wizard shares one URL with its step files.",
    ]
    # The banner's own title still names the entity; the note never competed with it.
    assert result.entity.entity_id == "FEAT-042"


def test_a_quoted_banner_title_in_a_note_does_not_stop_rule_one():
    """The normaliser reads the same `po_section_break`, so the item after the quoting note is still
    inside the list and its non-canonical marker is still corrected."""
    text = _PAGE_OBJECT_WITH_NOTES.replace(
        " *   - Step order is fixed; the review step cannot be skipped.\n",
        " *   - See the LIVING DOC — FEAT-002 · Breached Password Check banner.\n"
        " *   • Step order is fixed; the review step cannot be skipped.\n",
    )
    normalized = normalize(text, SourceFormat.PAGE_OBJECT, "DocumentedFeature")

    assert " *   - Step order is fixed; the review step cannot be skipped." in normalized.lines
    assert [c.rule for c in normalized.changes] == [RULE_BULLET_MARKER]


def test_rule_one_stops_at_a_bare_comment_close_as_it_does_at_the_banner():
    """`_PO_LINE_RE` leaves only `/` in a bare ` */`'s content, so the close has to be read off the raw
    line - otherwise a later JSDoc `notes:` re-opens rule 1 and normalisation rewrites TypeScript."""
    text = _PAGE_OBJECT_WITH_NOTES.replace(
        " * ============================================================================= */\n", " */\n"
    ) + (
        "\nexport class AccountSetupWizardPage {\n"
        "  /**\n"
        "   * notes:\n"
        "   *   • Not a living-doc note; a JSDoc line of its own.\n"
        "   */\n"
        "  async goto(): Promise<void> {}\n"
        "}\n"
    )
    normalized = normalize(text, SourceFormat.PAGE_OBJECT, "DocumentedFeature")

    assert "   *   • Not a living-doc note; a JSDoc line of its own." in normalized.lines
    assert normalized.changes == []

    # The bare close also ends the list for the parser, so it raises no MISINDENTED_LINE of its own.
    result, warnings = parse_page_object(text)
    assert result is not None and result.entity is not None
    assert warnings == []
    assert result.entity.notes == [
        "Step order is fixed; the review step cannot be skipped.",
        "The wizard shares one URL with its step files.",
    ]
