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
import pytest
from pydantic import ValidationError

from living_doc_utilities.contracts.common import AcceptanceCriterion, SourceRef, Timestamps
from tests.contracts import factories


def test_acceptance_criterion_planned_without_version_is_valid():
    ac = factories.acceptance_criterion(state="planned", version=None)

    assert ac.state == "planned"
    assert ac.version is None


def test_acceptance_criterion_requires_version_unless_planned():
    with pytest.raises(ValidationError, match="version is required unless state is 'planned'"):
        factories.acceptance_criterion(state="active", version=None)


@pytest.mark.parametrize("state", ["in_review", "active", "deprecated"])
def test_acceptance_criterion_requires_version_for_every_non_planned_state(state):
    with pytest.raises(ValidationError):
        factories.acceptance_criterion(state=state, version=None)


def test_acceptance_criterion_version_rejects_leading_v():
    with pytest.raises(ValidationError):
        factories.acceptance_criterion(version="v1.0.0")


def test_acceptance_criterion_version_accepts_semver_without_leading_v():
    ac = factories.acceptance_criterion(version="2.10.3")

    assert ac.version == "2.10.3"


def test_acceptance_criterion_state_enum_has_exactly_four_values():
    schema = AcceptanceCriterion.model_json_schema()

    assert schema["properties"]["state"]["enum"] == ["planned", "in_review", "active", "deprecated"]


def test_acceptance_criterion_forbids_unknown_field():
    with pytest.raises(ValidationError):
        factories.acceptance_criterion(unexpected_field="nope")


def test_acceptance_criterion_id_matches_parent_plus_sequence():
    ac = factories.acceptance_criterion(parent_id="US-001", seq=1)

    assert ac.id == "US-001-01"


@pytest.mark.parametrize("bad_id", ["AC1", "US-001", "us-001-01", "US-001-1a"])
def test_acceptance_criterion_id_rejects_non_canonical_form(bad_id):
    with pytest.raises(ValidationError):
        factories.acceptance_criterion(id=bad_id)


def test_acceptance_criterion_deprecated_requires_removal_planned():
    with pytest.raises(ValidationError, match="removal_planned is required when state is 'deprecated'"):
        factories.acceptance_criterion(state="deprecated", removal_planned=None)


def test_acceptance_criterion_deprecated_with_removal_planned_is_valid():
    ac = factories.acceptance_criterion(state="deprecated", removal_planned="2.0.0")

    assert ac.removal_planned == "2.0.0"


@pytest.mark.parametrize("state", ["planned", "in_review", "active"])
def test_acceptance_criterion_non_deprecated_rejects_removal_planned(state):
    overrides = {"state": state, "removal_planned": "2.0.0"}
    if state != "planned":
        overrides["version"] = "1.0.0"
    with pytest.raises(ValidationError, match="removal_planned is only valid when state is 'deprecated'"):
        factories.acceptance_criterion(**overrides)


def test_acceptance_criterion_placeholder_values_round_trip():
    ac = factories.acceptance_criterion(placeholder_values={"user_role": ["admin", "guest"]})

    assert ac.placeholder_values == {"user_role": ["admin", "guest"]}


def test_acceptance_criterion_placeholder_values_rejects_bad_key():
    with pytest.raises(ValidationError):
        factories.acceptance_criterion(placeholder_values={"not a valid name!": ["admin"]})


def test_source_ref_accepts_github_system():
    ref = factories.github_source_ref()

    assert ref.system == "GitHub"
    assert ref.area_path is None
    assert ref.iteration_path is None


def test_source_ref_accepts_azure_devops_system():
    ref = factories.azure_devops_source_ref()

    assert ref.system == "AzureDevOps"
    assert ref.area_path == "Payments\\Checkout"
    assert ref.iteration_path == "Payments\\Sprint 12"


def test_source_ref_rejects_unknown_system():
    with pytest.raises(ValidationError):
        factories.github_source_ref(system="Jira")


def test_source_ref_forbids_unknown_field():
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
    ac = factories.acceptance_criterion(state="active", version="1.2.0")

    assert ac.canonical_header() == "AC:US-001-01 (v1.2.0 - active)"


def test_canonical_header_renders_version_less_planned():
    ac = factories.acceptance_criterion(state="planned", version=None)

    assert ac.canonical_header() == "AC:US-001-01 (planned)"


def test_canonical_header_renders_deprecated_with_removal_planned():
    ac = factories.acceptance_criterion(state="deprecated", version="1.0.0", removal_planned="2.0.0")

    assert ac.canonical_header() == "AC:US-001-01 (v1.0.0 - deprecated - removal planned v2.0.0)"


def test_timestamps_default_to_none():
    timestamps = Timestamps()

    assert timestamps.created_at is None
    assert timestamps.updated_at is None
    assert timestamps.closed_at is None
