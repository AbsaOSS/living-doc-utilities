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

"""The shared envelope models: `Source` consistency checks, `Cardinality` constraints, `ContractWarning`."""

import json

import jsonschema
import pytest
from pydantic import ValidationError

from living_doc_utilities.contracts import generator_ready, schema_export, testing
from living_doc_utilities.contracts.envelope import Cardinality, ContractWarning, Source
from tests.contracts import factories


def test_source_requires_project_id():
    """Source construction without a project_id raises a validation error."""
    with pytest.raises(ValidationError):
        Source(organizations=[], repositories=[])


@pytest.mark.parametrize("project_id", ["Payments", "-payments", "payments_service", "", "payments!"])
def test_source_project_id_pattern_rejects_invalid_values(project_id):
    """Source.project_id rejects values that don't match its lowercase-slug pattern."""
    with pytest.raises(ValidationError):
        factories.source(project_id=project_id)


@pytest.mark.parametrize("project_id", ["payments", "payments-service", "p1"])
def test_source_project_id_pattern_accepts_valid_values(project_id):
    """Source.project_id accepts lowercase-slug values matching its pattern."""
    assert factories.source(project_id=project_id).project_id == project_id


def test_source_repository_org_must_be_listed_in_organizations():
    """A repository whose org isn't also listed in organizations is rejected."""
    with pytest.raises(ValidationError, match="not listed in organizations"):
        factories.source(organizations=["absaoss"], repositories=["other-org/payments-service"])


def test_source_organization_without_repository_is_valid():
    """An organization listed with no matching repository entry is still valid."""
    result = factories.source(organizations=["absaoss", "other-org"], repositories=["absaoss/payments-service"])

    assert result.organizations == ["absaoss", "other-org"]
    assert result.repositories == ["absaoss/payments-service"]


def test_source_systems_accepts_github_and_azure_devops():
    """Source.systems accepts both 'GitHub' and 'AzureDevOps' values."""
    result = factories.source(systems=["GitHub", "AzureDevOps"])

    assert result.systems == ["GitHub", "AzureDevOps"]


def test_source_extraction_mode_defaults_to_none():
    """Source.extraction_mode defaults to None when not given."""
    assert factories.source().extraction_mode is None


def test_cardinality_has_exactly_the_documented_keys():
    """Cardinality has exactly its nine documented fields, no more and no fewer."""
    assert set(Cardinality.model_fields) == {
        "entities",
        "entities_by_type",
        "acceptance_criteria",
        "scenarios",
        "warnings_by_code",
        "sources_configured",
        "sources_failed",
        "unresolved_refs",
        "entities_skipped",
    }


def test_cardinality_defaults_every_count_to_zero():
    """A Cardinality built with no arguments defaults every count field to zero/empty, not unset."""
    result = factories.cardinality()

    assert result.entities == 0
    assert result.acceptance_criteria == 0
    assert result.scenarios == 0
    assert result.sources_configured == 0
    assert result.sources_failed == 0
    assert result.unresolved_refs == 0
    assert result.entities_skipped == 0
    assert not result.entities_by_type
    assert not result.warnings_by_code


def test_cardinality_entities_by_type_rejects_unknown_documentation_type():
    """Cardinality.entities_by_type rejects a key that isn't a known documentation type."""
    with pytest.raises(ValidationError):
        factories.cardinality(entities_by_type={"NotADocType": 1})


def test_cardinality_warnings_by_code_rejects_lowercase_code():
    """Cardinality.warnings_by_code rejects a code key that isn't uppercase."""
    with pytest.raises(ValidationError):
        factories.cardinality(warnings_by_code={"missing_status": 1})


@pytest.mark.parametrize("schema_version", ["a--x-v1.0.0", "Doc-v1.0.0"])
def test_source_input_entry_schema_version_pattern_rejects_invalid_values(schema_version):
    """SourceInputEntry.schema_version rejects values that don't match the contract-id pattern."""
    with pytest.raises(ValidationError):
        factories.source_input_entry(schema_version=schema_version)


@pytest.mark.parametrize("schema_version", ["doc-entities-v1.0.0", "doc2-entities-v1.0.0"])
def test_source_input_entry_schema_version_pattern_accepts_valid_values(schema_version):
    """SourceInputEntry.schema_version accepts values matching the contract-id pattern."""
    assert factories.source_input_entry(schema_version=schema_version).schema_version == schema_version


def test_metadata_source_inputs_defaults_to_empty_list():
    """Metadata.source_inputs defaults to an empty list when not given."""
    result = factories.metadata()

    assert result.source_inputs == []


def test_contract_warning_code_pattern_rejects_lowercase():
    """ContractWarning.code rejects a lowercase value."""
    with pytest.raises(ValidationError):
        ContractWarning(code="missing_status", message="...")


def test_contract_warning_round_trip():
    """A ContractWarning keeps its code, message and context unchanged after construction."""
    warning = ContractWarning(code="MISSING_STATUS", message="No authored status.", context="US-001")

    assert warning.code == "MISSING_STATUS"
    assert warning.context == "US-001"


def test_contract_warning_with_no_location_field_validates():
    """`entity_id`, `ac_id`, `line_no` and `path` are optional: a warning that knows none of them still validates."""
    warning = ContractWarning(code="HTML_CONTENT_DROPPED", message="Dropped: script=1.")

    assert (warning.entity_id, warning.ac_id, warning.line_no, warning.path) == (None, None, None, None)


def test_contract_warning_carries_every_location_field():
    """A warning names its entity, its criterion, its 1-based line and its file, beside its free-text context."""
    warning = ContractWarning(
        code="MALFORMED_AC",
        message="Acceptance-criterion header is malformed.",
        context="entity='FUNC-001' line_no=13 header='#   AC:FUNC-001-01 (v1.0.0 - activ)'",
        entity_id="FUNC-001",
        ac_id="FUNC-001-01",
        line_no=13,
        path="features/func-001.feature",
    )

    assert ContractWarning.model_validate(warning.model_dump(mode="json")) == warning


@pytest.mark.parametrize("ac_id", ["FEAT-001-01", "US-001", "us-001-01", ""])
def test_contract_warning_rejects_an_invalid_ac_id(ac_id):
    """`ac_id` holds a valid criterion id (`AC_ID_PATTERN`) only; an invalid one stays in `context`."""
    with pytest.raises(ValidationError):
        ContractWarning(code="MALFORMED_AC", message="...", ac_id=ac_id)


@pytest.mark.parametrize("line_no", [0, -1])
def test_contract_warning_rejects_a_line_number_below_one(line_no):
    """`line_no` is a 1-based input line."""
    with pytest.raises(ValidationError):
        ContractWarning(code="AUTHORING_WARNING", message="...", line_no=line_no)


@pytest.mark.parametrize("field, value", [("ac_id", "FEAT-001-01"), ("line_no", 0)])
def test_contract_warning_schema_rejects_what_the_model_rejects(field, value):
    """The committed schema holds `ac_id` to its pattern and `line_no` to its minimum, as the model does."""
    sample = testing.full_sample(generator_ready.CONTRACT_ID)
    data = json.loads(sample.model_dump_json())
    data["warnings"][0][field] = value

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=data, schema=schema_export.load_schema(generator_ready.CONTRACT_ID))
