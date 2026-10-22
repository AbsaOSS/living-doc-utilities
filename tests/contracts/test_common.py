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

"""Shared models in `common.py`: AC state/version/removal_planned rules and header, `SourceRef`, `Timestamps` and
the date-time pattern."""

import re

import pytest
from pydantic import ValidationError

from living_doc_utilities.contracts.common import DATE_TIME_PATTERN, AcceptanceCriterion, SourceRef, Timestamps
from tests.contracts import factories


def test_acceptance_criterion_planned_without_version_is_valid():
    """A planned AcceptanceCriterion is valid without a version."""
    ac = factories.acceptance_criterion(state="planned", version=None)

    assert ac.state == "planned"
    assert ac.version is None


def test_acceptance_criterion_requires_version_unless_planned():
    """A non-planned AcceptanceCriterion without a version is rejected."""
    with pytest.raises(ValidationError, match="version is required unless state is 'planned'"):
        factories.acceptance_criterion(state="active", version=None)


@pytest.mark.parametrize("state", ["in_review", "active", "deprecated"])
def test_acceptance_criterion_requires_version_for_every_non_planned_state(state):
    """Every non-planned state requires a version, not just 'active'."""
    with pytest.raises(ValidationError):
        factories.acceptance_criterion(state=state, version=None)


def test_acceptance_criterion_version_rejects_leading_v():
    """A version string with a leading 'v' is rejected."""
    with pytest.raises(ValidationError):
        factories.acceptance_criterion(version="v1.0.0")


def test_acceptance_criterion_version_accepts_semver_without_leading_v():
    """A version without the leading v is accepted."""
    ac = factories.acceptance_criterion(version="2.10.3")

    assert ac.version == "2.10.3"


def test_acceptance_criterion_state_enum_has_exactly_four_values():
    """The state field's JSON schema enum lists exactly the four lifecycle states, in order."""
    schema = AcceptanceCriterion.model_json_schema()

    assert schema["properties"]["state"]["enum"] == ["planned", "in_review", "active", "deprecated"]


def test_acceptance_criterion_forbids_unknown_field():
    """An AcceptanceCriterion rejects an unrecognized field."""
    with pytest.raises(ValidationError):
        factories.acceptance_criterion(unexpected_field="nope")


@pytest.mark.parametrize("bad_id", ["AC1", "US-001", "us-001-01", "US-001-1a"])
def test_acceptance_criterion_id_rejects_non_canonical_form(bad_id):
    """An id that isn't an owner prefix, then two runs of digits joined by hyphens, is rejected."""
    with pytest.raises(ValidationError):
        factories.acceptance_criterion(id=bad_id)


@pytest.mark.parametrize("good_id", ["US-001-01", "FUNC-001-01"])
def test_acceptance_criterion_id_accepts_each_owner_prefix(good_id):
    """A User Story or a Functionality, the two entity kinds that own criteria, can prefix an AC id."""
    assert factories.acceptance_criterion(id=good_id).id == good_id


@pytest.mark.parametrize("bad_id", ["FEAT-001-01", "JIRA-12-01"])
def test_acceptance_criterion_id_rejects_a_prefix_that_owns_no_criteria(bad_id):
    """A Feature owns no criteria and a foreign tracker key is no entity, so neither prefixes an AC id."""
    with pytest.raises(ValidationError):
        factories.acceptance_criterion(id=bad_id)


def test_acceptance_criterion_deprecated_requires_removal_planned():
    """A deprecated AcceptanceCriterion without removal_planned is rejected."""
    with pytest.raises(ValidationError, match="removal_planned is required when state is 'deprecated'"):
        factories.acceptance_criterion(state="deprecated", removal_planned=None)


def test_acceptance_criterion_deprecated_with_removal_planned_is_valid():
    """A deprecated AcceptanceCriterion with removal_planned set is valid."""
    ac = factories.acceptance_criterion(state="deprecated", removal_planned="2.0.0")

    assert ac.removal_planned == "2.0.0"


@pytest.mark.parametrize("state", ["planned", "in_review", "active"])
def test_acceptance_criterion_non_deprecated_rejects_removal_planned(state):
    """removal_planned is rejected on every non-deprecated state, not just the default."""
    overrides = {"state": state, "removal_planned": "2.0.0"}
    if state != "planned":
        overrides["version"] = "1.0.0"
    with pytest.raises(ValidationError, match="removal_planned is only valid when state is 'deprecated'"):
        factories.acceptance_criterion(**overrides)


def test_acceptance_criterion_placeholder_values_round_trip():
    """placeholder_values round-trips unchanged on a valid AcceptanceCriterion."""
    ac = factories.acceptance_criterion(placeholder_values={"user_role": ["admin", "guest"]})

    assert ac.placeholder_values == {"user_role": ["admin", "guest"]}


def test_acceptance_criterion_placeholder_values_rejects_bad_key():
    """placeholder_values rejects a key that isn't a valid placeholder name."""
    with pytest.raises(ValidationError):
        factories.acceptance_criterion(placeholder_values={"not a valid name!": ["admin"]})


def test_source_ref_accepts_github_system():
    """A GitHub SourceRef is valid and leaves the Azure DevOps-only fields unset."""
    ref = factories.github_source_ref()

    assert ref.system == "GitHub"
    assert ref.area_path is None
    assert ref.iteration_path is None


def test_source_ref_accepts_azure_devops_system():
    """An Azure DevOps SourceRef is valid and carries its area_path/iteration_path fields."""
    ref = factories.azure_devops_source_ref()

    assert ref.system == "AzureDevOps"
    assert ref.area_path == "Payments\\Checkout"
    assert ref.iteration_path == "Payments\\Sprint 12"


def test_source_ref_rejects_unknown_system():
    """A SourceRef with a system outside GitHub/AzureDevOps is rejected."""
    with pytest.raises(ValidationError):
        factories.github_source_ref(system="Jira")


def test_source_ref_forbids_unknown_field():
    """A SourceRef rejects an unrecognized field."""
    with pytest.raises(ValidationError):
        SourceRef(
            system="GitHub",
            native_id="1",
            native_type="User Story",
            url="https://example.invalid/1",
            tracker_state="open",
            unexpected_field="nope",
        )


def test_canonical_header_renders_version_and_state():
    """canonical_header() renders the id, version, and state for a versioned AcceptanceCriterion."""
    ac = factories.acceptance_criterion(state="active", version="1.2.0")

    assert ac.canonical_header() == "AC:US-001-01 (v1.2.0 - active)"


def test_canonical_header_renders_version_less_planned():
    """canonical_header() renders a planned AcceptanceCriterion without a version segment."""
    ac = factories.acceptance_criterion(state="planned", version=None)

    assert ac.canonical_header() == "AC:US-001-01 (planned)"


def test_canonical_header_renders_deprecated_with_removal_planned():
    """canonical_header() renders a deprecated AcceptanceCriterion with its removal-planned version."""
    ac = factories.acceptance_criterion(state="deprecated", version="1.0.0", removal_planned="2.0.0")

    assert ac.canonical_header() == "AC:US-001-01 (v1.0.0 - deprecated - removal planned v2.0.0)"


def test_timestamps_default_to_none():
    """A Timestamps built with no arguments leaves every field unset rather than erroring."""
    timestamps = Timestamps()

    assert timestamps.created_at is None
    assert timestamps.updated_at is None
    assert timestamps.closed_at is None


# The RFC 3339 shape `DATE_TIME_PATTERN` checks, and what the model (AwareDatetime) checks beyond it.
_AWARE_DATE_TIMES = [
    "2026-03-01T00:00:00Z",
    "2026-03-01T00:00:00+02:00",
    "2026-03-01T00:00:00.123Z",
    "2026-03-01t00:00:00z",
]


@pytest.mark.parametrize("value", _AWARE_DATE_TIMES)
def test_an_aware_rfc_3339_date_time_passes_the_pattern_and_the_model(value):
    """A date-time with its offset matches `DATE_TIME_PATTERN` and validates as a Timestamps value."""
    assert re.search(DATE_TIME_PATTERN, value)
    assert Timestamps(created_at=value).created_at.utcoffset() is not None


@pytest.mark.parametrize("value", factories.NOT_RFC_3339_DATE_TIMES)
def test_a_value_that_is_no_rfc_3339_date_time_fails_the_pattern(value):
    """No offset, a date alone, a Unix time, a space for `T` and a snapshot placeholder all fail the pattern."""
    assert re.search(DATE_TIME_PATTERN, value) is None


@pytest.mark.parametrize("field", ["created_at", "updated_at", "closed_at"])
@pytest.mark.parametrize("value", ["2026-03-01T00:00:00", "2026-03-01"])
def test_the_model_rejects_a_date_time_without_an_offset(field, value):
    """Each Timestamps field is an AwareDatetime: a value without a UTC offset fails the model too."""
    with pytest.raises(ValidationError, match=field) as excinfo:
        Timestamps(**{field: value})

    assert [error["type"] for error in excinfo.value.errors()] == ["timezone_aware"]


@pytest.mark.parametrize(
    "value",
    ["2026-13-01T00:00:00Z", "2026-02-30T00:00:00Z", "2026-03-01T25:00:00Z", "2026-03-01T00:61:00Z"],
    ids=["month-13", "february-30", "hour-25", "minute-61"],
)
def test_an_impossible_date_passes_the_pattern_and_fails_the_model(value):
    """The pattern checks the shape only; the model rejects an impossible month, day, hour or minute."""
    assert re.search(DATE_TIME_PATTERN, value)
    with pytest.raises(ValidationError, match="closed_at") as excinfo:
        Timestamps(closed_at=value)

    assert [error["type"] for error in excinfo.value.errors()] == ["datetime_from_date_parsing"]
