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
Builders for minimal, schema-valid contract instances, shared by the contracts test suite.
Not a test module itself - no test_* functions live here.
"""

from datetime import datetime, timezone
from typing import Any, Optional

from living_doc_utilities.contracts.common import AcceptanceCriterion, SourceRef
from living_doc_utilities.contracts.coverage_matrix import (
    AcCoverage,
    AspectCoverage,
    EntityCoverage,
    PlannedSummary,
)
from living_doc_utilities.contracts.coverage_matrix import (
    Document as CoverageMatrixDocument,
)
from living_doc_utilities.contracts.doc_entities import Entity, PageRef
from living_doc_utilities.contracts.envelope import (
    AuditStats,
    Cardinality,
    Metadata,
    Producer,
    Source,
    SourceInputEntry,
    Stats,
)
from living_doc_utilities.contracts.generator_ready import Document as GeneratorReadyDocument
from living_doc_utilities.contracts.generator_ready import SelectionSummary
from living_doc_utilities.contracts.ui_test_catalog import (
    Document as UiTestCatalogDocument,
)
from living_doc_utilities.contracts.ui_test_catalog import (
    FeatureFileCatalog,
    LinkedScenarios,
)
from living_doc_utilities.contracts.ui_tests import AcLink, Scenario


def github_source_ref(native_id: str = "1", **overrides: Any) -> SourceRef:
    fields: dict[str, Any] = {
        "system": "GitHub",
        "native_id": native_id,
        "native_type": "User Story",
        "url": f"https://github.com/absaoss/payments-service/issues/{native_id}",
        "tracker_state": "open",
    }
    fields.update(overrides)
    return SourceRef(**fields)


def azure_devops_source_ref(native_id: str = "42", **overrides: Any) -> SourceRef:
    fields: dict[str, Any] = {
        "system": "AzureDevOps",
        "native_id": native_id,
        "native_type": "User Story",
        "url": f"https://dev.azure.com/absaoss/payments/_workitems/edit/{native_id}",
        "tracker_state": "Active",
        "area_path": "Payments\\Checkout",
        "iteration_path": "Payments\\Sprint 12",
    }
    fields.update(overrides)
    return SourceRef(**fields)


def acceptance_criterion(parent_id: str = "US-001", seq: int = 1, **overrides: Any) -> AcceptanceCriterion:
    fields: dict[str, Any] = {
        "id": f"{parent_id}-{seq:02d}",
        "state": "active",
        "version": "1.0.0",
        "description": "It works.",
    }
    fields.update(overrides)
    return AcceptanceCriterion(**fields)


def page_ref(**overrides: Any) -> PageRef:
    fields: dict[str, Any] = {
        "is_primary": True,
        "route": "/checkout",
        "page_object": "CheckoutPage.ts",
        "owners": ["team-payments"],
        "purpose": "The screen where a customer reviews and confirms an order.",
    }
    fields.update(overrides)
    return PageRef(**fields)


def user_story(entity_id: str = "US-001", **overrides: Any) -> Entity:
    fields: dict[str, Any] = {
        "entity_id": entity_id,
        "source_ref": github_source_ref(),
        "type": "DocumentedUserStory",
        "title": "A user story",
        "state": "active",
        "state_origin": "authored",
        "narrative": "As a user, I want...",
        "business_value": ["Reduces checkout time."],
        "acceptance_criteria": [acceptance_criterion(parent_id=entity_id)],
    }
    fields.update(overrides)
    return Entity(**fields)


def feature(entity_id: str = "FEAT-001", **overrides: Any) -> Entity:
    fields: dict[str, Any] = {
        "entity_id": entity_id,
        "source_ref": github_source_ref(),
        "type": "DocumentedFeature",
        "title": "A feature",
        "state": "active",
        "state_origin": "derived",
        "purpose": "The checkout page.",
        "surface_type": "page",
        "owners": ["team-payments"],
        "user_stories": ["US-001"],
        "functionalities": ["FUNC-001"],
        "pages": [page_ref()],
    }
    fields.update(overrides)
    return Entity(**fields)


def functionality(entity_id: str = "FUNC-001", **overrides: Any) -> Entity:
    fields: dict[str, Any] = {
        "entity_id": entity_id,
        "source_ref": github_source_ref(),
        "type": "DocumentedFunctionality",
        "title": "A functionality",
        "state": "active",
        "state_origin": "authored",
        "narrative": "Validates the card number.",
        "parent": "FEAT-001",
        "func_type": "API",
        "acceptance_criteria": [acceptance_criterion(parent_id=entity_id)],
    }
    fields.update(overrides)
    return Entity(**fields)


def ac_link(**overrides: Any) -> AcLink:
    fields: dict[str, Any] = {"id": "US-001-01", "aspect": None}
    fields.update(overrides)
    return AcLink(**fields)


def scenario(scenario_id: str = "SCN-001", **overrides: Any) -> Scenario:
    fields: dict[str, Any] = {
        "scenario_id": scenario_id,
        "title": "A scenario",
        "source_ref": github_source_ref(native_id="checkout.feature"),
        "acceptance_criteria": [ac_link()],
    }
    fields.update(overrides)
    return Scenario(**fields)


def producer(**overrides: Any) -> Producer:
    fields: dict[str, Any] = {
        "name": "AbsaOSS/living-doc-collector-gh",
        "version": "0.2.0",
        "utilities_version": "0.5.1",
    }
    fields.update(overrides)
    return Producer(**fields)


def source(**overrides: Any) -> Source:
    fields: dict[str, Any] = {
        "project_id": "payments",
        "systems": ["GitHub"],
        "organizations": ["absaoss"],
        "repositories": ["absaoss/payments-service"],
    }
    fields.update(overrides)
    return Source(**fields)


def cardinality(**overrides: Any) -> Cardinality:
    return Cardinality(**overrides)


def audit_stats(field_occupancy: Optional[dict[str, int]] = None) -> AuditStats:
    return AuditStats(cardinality=cardinality(), field_occupancy=field_occupancy or {})


def source_input_entry(
    schema_version: str = "doc-source-v1.0.0", field_occupancy: Optional[dict[str, int]] = None
) -> SourceInputEntry:
    return SourceInputEntry(
        schema_version=schema_version,
        producer=producer(),
        source=source(),
        stats=audit_stats(field_occupancy),
        selected_stats=audit_stats(field_occupancy),
    )


def metadata(**overrides: Any) -> Metadata:
    fields: dict[str, Any] = {
        "producer": producer(),
        "source": source(),
        "generated_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "stats": Stats(cardinality=cardinality()),
        "source_inputs": [],
    }
    fields.update(overrides)
    return Metadata(**fields)


def transform_metadata(**overrides: Any) -> Metadata:
    """metadata() with a non-empty source_inputs - for the three transform-output contracts
    (generator-ready, coverage-matrix, ui-test-catalog), whose result models require at
    least one entry (R7). Collector-output fixtures keep using metadata()."""
    fields: dict[str, Any] = {"source_inputs": [source_input_entry()]}
    fields.update(overrides)
    return metadata(**fields)


def selection_summary(**overrides: Any) -> SelectionSummary:
    fields: dict[str, Any] = {
        "total_entities": 10,
        "included_entities": 8,
        "excluded_entities": 2,
        "total_acceptance_criteria": 20,
        "included_acceptance_criteria": 15,
        "excluded_acceptance_criteria": 5,
    }
    fields.update(overrides)
    return SelectionSummary(**fields)


def generator_ready_document(**overrides: Any) -> GeneratorReadyDocument:
    fields: dict[str, Any] = {
        "title": "Payments service",
        "version": "1.4.0",
        "view": "release",
        "selection_summary": selection_summary(),
    }
    fields.update(overrides)
    return GeneratorReadyDocument(**fields)


def aspect_coverage(**overrides: Any) -> AspectCoverage:
    fields: dict[str, Any] = {"aspect": "checkout", "status": "covered", "scenario_ids": ["SCN-001"]}
    fields.update(overrides)
    return AspectCoverage(**fields)


def ac_coverage(parent_id: str = "US-001", seq: int = 1, **overrides: Any) -> AcCoverage:
    fields: dict[str, Any] = {
        "ac_id": f"{parent_id}-{seq:02d}",
        "state": "active",
        "status": "covered",
        "aspects": [],
        "scenario_ids": ["SCN-001"],
    }
    fields.update(overrides)
    return AcCoverage(**fields)


def entity_coverage(entity_id: str = "US-001", **overrides: Any) -> EntityCoverage:
    fields: dict[str, Any] = {
        "entity_id": entity_id,
        "type": "DocumentedUserStory",
        "title": "A user story",
        "state": "active",
        "acceptance_criteria": [ac_coverage(parent_id=entity_id)],
    }
    fields.update(overrides)
    return EntityCoverage(**fields)


def planned_summary(**overrides: Any) -> PlannedSummary:
    fields: dict[str, Any] = {"total": 3, "backlog": 1, "by_target_version": {"1.5.0": 2}}
    fields.update(overrides)
    return PlannedSummary(**fields)


def coverage_matrix_document(**overrides: Any) -> CoverageMatrixDocument:
    fields: dict[str, Any] = {"view": "release"}
    fields.update(overrides)
    return CoverageMatrixDocument(**fields)


def linked_scenarios(entity_id: str = "US-001", **overrides: Any) -> LinkedScenarios:
    fields: dict[str, Any] = {"entity_id": entity_id, "scenarios": [scenario()]}
    fields.update(overrides)
    return LinkedScenarios(**fields)


def feature_file_catalog(**overrides: Any) -> FeatureFileCatalog:
    fields: dict[str, Any] = {
        "feature_file": "checkout.feature",
        "linked_to_user_story": [linked_scenarios()],
        "linked_to_functionality": [],
        "unlinked": [],
    }
    fields.update(overrides)
    return FeatureFileCatalog(**fields)


def ui_test_catalog_document(**overrides: Any) -> UiTestCatalogDocument:
    fields: dict[str, Any] = {"view": "release"}
    fields.update(overrides)
    return UiTestCatalogDocument(**fields)
