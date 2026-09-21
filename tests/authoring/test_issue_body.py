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
`parse_issue_body`: every canonical `##` heading (living-doc's docs/examples/README.md,
"GitHub issue-body layout (canonical)") lands on a real `ParsedEntity` field, an unrecognised
heading produces `UNKNOWN_SECTION`, a `## Status` heading on a Feature produces
`IGNORED_AUTHORED_KEY`, and entity-level `rationale` is a distinct field from an
acceptance-criterion's own `rationale`.
"""

from living_doc_utilities.authoring.issue_body import parse_issue_body
from living_doc_utilities.contracts.codes import Code

_USER_STORY_BODY = """\
## Description

A narrative sentence.

## Status

active

## Business Value

- Value one.

## Not In Scope

- Scope exclusion one.

## Preconditions

- Precondition one.

## Deprecated At

2026-01-01

## Deprecation Reason

Reason text.

## Superseded By

US-002

## Acceptance Criteria

### AC:US-001-01 (v1.0.0 - active)

- desc
"""

_FEATURE_BODY = """\
## Description

A purpose sentence.

## Status

active

## Surface Type

UI

## Owners

Team A

## User Stories

US-001

## Functionalities

FUNC-001

## External Dependencies

dep-api

## Deprecated At

2026-01-01

## Deprecation Reason

Reason text.

## Superseded By

FEAT-002
"""

_FUNCTIONALITY_BODY = """\
## Description

A narrative sentence.

## Status

active

## Parent Feature

FEAT-001

## Func Type

field_validation

## Rationale

- Reason for scoping.

## Preconditions

- Precondition one.

## Not In Scope

- Scope exclusion one.

## Deprecated At

2026-01-01

## Deprecation Reason

Reason text.

## Superseded By

FUNC-002

## Acceptance Criteria

### AC:FUNC-001-01 (v1.0.0 - active)

- desc
"""


def test_every_user_story_heading_lands_on_its_field():
    entity, warnings = parse_issue_body(_USER_STORY_BODY, "US-001 · Sample", "DocumentedUserStory")

    assert warnings == []
    assert entity.narrative == "A narrative sentence."
    assert entity.state == "active"
    assert entity.business_value == ["Value one."]
    assert entity.not_in_scope == ["Scope exclusion one."]
    assert entity.preconditions == ["Precondition one."]
    assert entity.deprecated_at == "2026-01-01"
    assert entity.deprecation_reason == "Reason text."
    assert entity.superseded_by == "US-002"
    assert [ac.id for ac in entity.acceptance_criteria] == ["US-001-01"]


def test_every_feature_heading_lands_on_its_field_and_status_is_ignored():
    entity, warnings = parse_issue_body(_FEATURE_BODY, "FEAT-001 · Sample", "DocumentedFeature")

    assert [w.code for w in warnings] == [Code.IGNORED_AUTHORED_KEY.name]
    assert warnings[0].message == "Feature state is derived; use `stub-reason:` for an uninstrumented surface"
    assert entity.state is None
    assert entity.purpose == "A purpose sentence."
    assert entity.surface_type == "UI"
    assert entity.owners == ["Team A"]
    assert entity.user_stories == ["US-001"]
    assert entity.functionalities == ["FUNC-001"]
    assert entity.external_dependencies == ["dep-api"]
    assert entity.deprecated_at == "2026-01-01"
    assert entity.deprecation_reason == "Reason text."
    assert entity.superseded_by == "FEAT-002"


def test_every_functionality_heading_lands_on_its_field():
    entity, warnings = parse_issue_body(_FUNCTIONALITY_BODY, "FUNC-001 · Sample", "DocumentedFunctionality")

    assert warnings == []
    assert entity.narrative == "A narrative sentence."
    assert entity.state == "active"
    assert entity.parent == "FEAT-001"
    assert entity.func_type == "field_validation"
    assert entity.rationale == "Reason for scoping."
    assert entity.preconditions == ["Precondition one."]
    assert entity.not_in_scope == ["Scope exclusion one."]
    assert entity.deprecated_at == "2026-01-01"
    assert entity.deprecation_reason == "Reason text."
    assert entity.superseded_by == "FUNC-002"
    assert [ac.id for ac in entity.acceptance_criteria] == ["FUNC-001-01"]


def test_unrecognised_heading_produces_unknown_section():
    body = "## Description\n\nSome text.\n\n## Totally Unknown Heading\n\nsome value\n"
    entity, warnings = parse_issue_body(body, "US-001 · Sample", "DocumentedUserStory")

    assert entity is not None
    assert [w.code for w in warnings] == [Code.UNKNOWN_SECTION.name]
    assert "Totally Unknown Heading" in warnings[0].message


def test_entity_level_rationale_does_not_affect_ac_level_rationale():
    body = (
        "## Description\n\ndesc\n\n## Status\n\nactive\n\n## Parent Feature\n\nFEAT-001\n\n"
        "## Func Type\n\nfield_validation\n\n## Rationale\n\n- Entity-level reason.\n\n"
        "## Acceptance Criteria\n\n### AC:FUNC-001-01 (v1.0.0 - active)\n\n- desc\n"
    )
    entity, warnings = parse_issue_body(body, "FUNC-001 · Sample", "DocumentedFunctionality")

    assert warnings == []
    assert entity.rationale == "Entity-level reason."
    assert entity.acceptance_criteria[0].rationale is None


def test_ac_level_rationale_does_not_affect_entity_level_rationale():
    body = (
        "## Description\n\ndesc\n\n## Status\n\nactive\n\n## Parent Feature\n\nFEAT-001\n\n"
        "## Func Type\n\nfield_validation\n\n"
        "## Acceptance Criteria\n\n### AC:FUNC-001-01 (v1.0.0 - active)\n\n- desc\n- Rationale: AC-level reason.\n"
    )
    entity, warnings = parse_issue_body(body, "FUNC-001 · Sample", "DocumentedFunctionality")

    assert warnings == []
    assert entity.rationale is None
    assert entity.acceptance_criteria[0].rationale == "AC-level reason."


def test_missing_entity_id_short_circuits_before_any_section_parsing():
    entity, warnings = parse_issue_body("## Description\n\ndesc\n", "No id here", "DocumentedUserStory")

    assert entity is None
    assert [w.code for w in warnings] == ["MISSING_ENTITY_ID"]


def test_en_dash_input_is_normalized_before_ac_grammar_runs():
    body = "## Description\n\ndesc\n\n## Status\n\nactive\n\n## Business Value\n\n- v\n\n" "## Acceptance Criteria\n\n### AC:US-001-01 (v1.0.0 – active)\n\n- desc\n"
    entity, warnings = parse_issue_body(body, "US-001 · Sample", "DocumentedUserStory")

    assert warnings == []
    assert entity.acceptance_criteria[0].state == "active"
    assert entity.acceptance_criteria[0].version == "1.0.0"
