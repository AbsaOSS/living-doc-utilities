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
docs/contracts.md, R12 check 3 ("full-sample test") and section 4 ("Rendering rules"): the
two shared test helpers every component - not just this package - builds its own R12/R11
tests on.

`full_sample` builds one valid, deterministic instance of a named contract from
state-consistent records that *jointly* populate every optional field the contract defines,
so that a fixture exists against which "nothing was lost" and "nothing is missing" are
statements with content, rather than something an ordinary hand-picked fixture could pass by
accident. `shown_paths` encodes section 4's field-by-view table, so a generator's own tests
assert against it instead of a copy that drifts.
"""

from datetime import datetime, timezone
from typing import Callable

from living_doc_utilities.contracts import (
    coverage_matrix,
    doc_entities,
    doc_source,
    generator_ready,
    ui_test_catalog,
    ui_tests,
)
from living_doc_utilities.contracts.common import AcceptanceCriterion, SourceRef, Timestamps
from living_doc_utilities.contracts.doc_entities import Entity, PageRef
from living_doc_utilities.contracts.envelope import (
    AuditStats,
    Cardinality,
    Metadata,
    Producer,
    Run,
    Source,
    SourceInputEntry,
    Stats,
)
from living_doc_utilities.contracts.registry import ContractResult
from living_doc_utilities.contracts.ui_tests import AcLink, Scenario

_UTILITIES_VERSION = "0.5.1"

# ---------------------------------------------------------------------------
# Shared building blocks: one set of state-consistent entities and scenarios, reused as-is
# everywhere a contract's shape calls for entities or scenarios - including doc-source's
# three separately-rooted lists and ui-test-catalog's three separate groupings, each of
# which needs its own full field coverage since metadata.stats.field_occupancy (R11) is
# computed independently per record root.
# ---------------------------------------------------------------------------


def _github_source_ref(native_id: str, native_type: str) -> SourceRef:
    return SourceRef(
        system="GitHub",
        native_id=native_id,
        native_type=native_type,
        url=f"https://github.com/absaoss/payments-service/issues/{native_id}",
        tracker_state="open",
    )


def _azure_devops_source_ref(native_id: str, native_type: str) -> SourceRef:
    return SourceRef(
        system="AzureDevOps",
        native_id=native_id,
        native_type=native_type,
        url=f"https://dev.azure.com/absaoss/payments/_workitems/edit/{native_id}",
        tracker_state="Closed",
        area_path="Payments\\Checkout",
        iteration_path="Payments\\Sprint 12",
    )


def _acceptance_criteria(parent_id: str) -> list[AcceptanceCriterion]:
    """Every acceptance-criterion-level extension, jointly: an `active` AC carrying aspect,
    preconditions, not_in_scope, rationale and placeholder_values; a `planned` AC targeted at
    a future version; and a separate backlog `planned` AC with none."""
    return [
        AcceptanceCriterion(
            id=f"{parent_id}-01",
            state="active",
            version="1.0.0",
            description="A customer can complete checkout with a single saved payment method.",
            aspect=["desktop", "mobile"],
            preconditions=["The cart has at least one item."],
            not_in_scope=["International shipping."],
            rationale="Keeping checkout to one step reduces cart abandonment.",
            placeholder_values={"user_role": ["customer", "guest"]},
        ),
        AcceptanceCriterion(
            id=f"{parent_id}-02",
            state="planned",
            version="1.6.0",
            description="A customer can split payment across two saved cards.",
        ),
        AcceptanceCriterion(
            id=f"{parent_id}-03",
            state="planned",
            description="A customer can pay with a digital wallet.",
        ),
    ]


def _deprecated_acceptance_criteria(parent_id: str) -> list[AcceptanceCriterion]:
    return [
        AcceptanceCriterion(
            id=f"{parent_id}-01",
            state="deprecated",
            version="1.5.0",
            removal_planned="2.1.0",
            description="A customer can check out as a guest, without creating an account.",
        )
    ]


def _entities() -> list[Entity]:
    """One of each entity kind, jointly covering every leaf path doc-entities, doc-source and
    generator-ready declare for their Entity-shaped record roots (docs/contracts.md, R12
    check 3): an active User Story with every entity-level extension and every
    acceptance-criterion-level extension; a deprecated User Story with its deprecation fields
    and a deprecated acceptance criterion; a Feature with a derived state, a stub_reason and
    both a primary and a cross-reference page; a Functionality with a rationale. No entity
    carries a field its own state makes meaningless."""
    user_story_active = Entity(
        entity_id="US-001",
        source_ref=_github_source_ref("501", "User Story"),
        type="DocumentedUserStory",
        title="Checkout with a saved payment method",
        state="active",
        state_origin="authored",
        tags=["checkout", "payments"],
        timestamps=Timestamps(
            created_at=datetime(2026, 1, 5, tzinfo=timezone.utc),
            updated_at=datetime(2026, 2, 10, tzinfo=timezone.utc),
        ),
        narrative="As a customer, I want to check out with a saved payment method, "
        "so that I can complete my purchase quickly.",
        source="https://github.com/absaoss/payments-service/issues/42",
        business_value=["Reduces cart abandonment."],
        acceptance_criteria=_acceptance_criteria("US-001"),
        preconditions=["The customer is signed in."],
        not_in_scope=["Guest checkout."],
    )

    user_story_deprecated = Entity(
        entity_id="US-002",
        source_ref=_azure_devops_source_ref("4021", "User Story"),
        type="DocumentedUserStory",
        title="Checkout as a guest",
        state="deprecated",
        state_origin="authored",
        timestamps=Timestamps(closed_at=datetime(2026, 6, 1, tzinfo=timezone.utc)),
        narrative="As a guest, I want to check out without creating an account.",
        acceptance_criteria=_deprecated_acceptance_criteria("US-002"),
        deprecated_at="2026-06-01",
        deprecation_reason="Superseded by the unified checkout flow.",
        superseded_by="US-010",
    )

    feature = Entity(
        entity_id="FEAT-001",
        source_ref=_github_source_ref("77", "Feature"),
        type="DocumentedFeature",
        title="Checkout page",
        state="active",
        state_origin="derived",
        purpose="The page where a customer reviews and confirms an order.",
        surface_type="page",
        owners=["team-payments"],
        user_stories=["US-001"],
        functionalities=["FUNC-001"],
        external_dependencies=["payments-api"],
        stub_reason="surface not yet instrumented: awaiting UI test coverage",
        wizard_steps=["cart-review", "payment", "confirmation"],
        pages=[
            PageRef(
                is_primary=True,
                route="/checkout",
                page_object="CheckoutPage.ts",
                owners=["team-payments"],
                purpose="The screen where a customer reviews and confirms an order.",
            ),
            PageRef(
                is_primary=False,
                route="/checkout/confirmation",
                page_object="CheckoutConfirmationPage.ts",
                owners=["team-payments"],
                purpose="The screen shown after a successful payment.",
                functionalities=["FUNC-001"],
            ),
        ],
    )

    functionality = Entity(
        entity_id="FUNC-001",
        source_ref=_github_source_ref("88", "Functionality"),
        type="DocumentedFunctionality",
        title="Validate card number",
        state="active",
        state_origin="authored",
        narrative="Validates the card number using the Luhn algorithm before submission.",
        parent="FEAT-001",
        func_type="API",
        rationale="Prevents obviously invalid card numbers from reaching the payment gateway.",
    )

    return [user_story_active, user_story_deprecated, feature, functionality]


def _scenarios() -> list[Scenario]:
    """Two scenarios jointly covering every leaf path ui-tests and ui-test-catalog declare
    for their Scenario-shaped record roots: one tagged, GitHub-sourced and aspect-linked; one
    Azure-DevOps-sourced (covering source_ref.area_path/iteration_path) and un-aspected."""
    return [
        Scenario(
            scenario_id="SCN-001",
            title="Customer completes checkout with a saved card",
            source_ref=_github_source_ref("checkout.feature", "Scenario"),
            tags=["smoke"],
            acceptance_criteria=[AcLink(id="US-001-01", aspect="desktop")],
        ),
        Scenario(
            scenario_id="SCN-002",
            title="Customer completes checkout as a guest",
            source_ref=_azure_devops_source_ref("checkout.feature#12", "Scenario"),
            acceptance_criteria=[AcLink(id="US-002-01")],
        ),
    ]


def _metadata(*, transform: bool) -> Metadata:
    producer_name = "AbsaOSS/living-doc-toolkit" if transform else "AbsaOSS/living-doc-collector-gh"
    return Metadata(
        producer=Producer(name=producer_name, version="0.2.0", build="abc1234", utilities_version=_UTILITIES_VERSION),
        run=Run(run_id="1001", run_attempt="1", actor="ci-bot", workflow="docs", ref="refs/heads/main", sha="deadbeef"),
        source=Source(
            project_id="payments",
            systems=["GitHub"],
            organizations=["absaoss"],
            repositories=["absaoss/payments-service"],
            extraction_mode="markdown",
        ),
        generated_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        stats=Stats(cardinality=Cardinality()),
        source_inputs=[_source_input_entry()] if transform else [],
    )


def _source_input_entry() -> SourceInputEntry:
    return SourceInputEntry(
        schema_version=doc_entities.CONTRACT_ID,
        producer=Producer(
            name="AbsaOSS/living-doc-collector-gh", version="0.2.0", utilities_version=_UTILITIES_VERSION
        ),
        source=Source(
            project_id="payments",
            systems=["GitHub"],
            organizations=["absaoss"],
            repositories=["absaoss/payments-service"],
        ),
        stats=AuditStats(cardinality=Cardinality()),
        selected_stats=AuditStats(cardinality=Cardinality()),
    )


# ---------------------------------------------------------------------------
# One builder per contract, dispatched by full_sample().
# ---------------------------------------------------------------------------


def _doc_entities_sample() -> doc_entities.DocEntitiesResult:
    return doc_entities.DocEntitiesResult(metadata=_metadata(transform=False), entities=_entities())


def _doc_source_sample() -> doc_source.DocSourceResult:
    entities = _entities()
    return doc_source.DocSourceResult(
        metadata=_metadata(transform=False),
        user_stories=list(entities),
        features=list(entities),
        functionalities=list(entities),
    )


def _ui_tests_sample() -> ui_tests.UITestsResult:
    return ui_tests.UITestsResult(metadata=_metadata(transform=False), scenarios=_scenarios())


def _generator_ready_sample() -> generator_ready.GeneratorReadyResult:
    return generator_ready.GeneratorReadyResult(
        metadata=_metadata(transform=True),
        document=generator_ready.Document(
            title="Payments service",
            version="1.4.0",
            view="inner",
            selection_summary=generator_ready.SelectionSummary(
                total_entities=4,
                included_entities=4,
                excluded_entities=0,
                total_acceptance_criteria=4,
                included_acceptance_criteria=4,
                excluded_acceptance_criteria=0,
            ),
        ),
        content=generator_ready.Content(entities=_entities()),
    )


def _coverage_matrix_sample() -> coverage_matrix.CoverageMatrixResult:
    covered_via_aspects = coverage_matrix.EntityCoverage(
        entity_id="US-001",
        type="DocumentedUserStory",
        title="Checkout with a saved payment method",
        state="active",
        acceptance_criteria=[
            coverage_matrix.AcCoverage(
                ac_id="US-001-01",
                state="active",
                status="covered",
                aspects=[coverage_matrix.AspectCoverage(aspect="desktop", status="covered", scenario_ids=["SCN-001"])],
            )
        ],
    )
    covered_without_aspects = coverage_matrix.EntityCoverage(
        entity_id="FUNC-001",
        type="DocumentedFunctionality",
        title="Validate card number",
        state="active",
        acceptance_criteria=[
            coverage_matrix.AcCoverage(ac_id="FUNC-001-01", state="active", status="covered", scenario_ids=["SCN-002"])
        ],
    )
    return coverage_matrix.CoverageMatrixResult(
        metadata=_metadata(transform=True),
        document=coverage_matrix.Document(view="inner"),
        entities=[covered_via_aspects, covered_without_aspects],
        planned_summary=coverage_matrix.PlannedSummary(total=2, backlog=1, by_target_version={"1.6.0": 1}),
    )


def _ui_test_catalog_sample() -> ui_test_catalog.UiTestCatalogResult:
    scenarios = _scenarios()
    feature_file = ui_test_catalog.FeatureFileCatalog(
        feature_file="checkout.feature",
        linked_to_user_story=[ui_test_catalog.LinkedScenarios(entity_id="US-001", scenarios=list(scenarios))],
        linked_to_functionality=[ui_test_catalog.LinkedScenarios(entity_id="FUNC-001", scenarios=list(scenarios))],
        unlinked=list(scenarios),
    )
    return ui_test_catalog.UiTestCatalogResult(
        metadata=_metadata(transform=True),
        document=ui_test_catalog.Document(view="inner"),
        feature_files=[feature_file],
    )


_BUILDERS: dict[str, Callable[[], ContractResult]] = {
    doc_entities.CONTRACT_ID: _doc_entities_sample,
    doc_source.CONTRACT_ID: _doc_source_sample,
    ui_tests.CONTRACT_ID: _ui_tests_sample,
    generator_ready.CONTRACT_ID: _generator_ready_sample,
    coverage_matrix.CONTRACT_ID: _coverage_matrix_sample,
    ui_test_catalog.CONTRACT_ID: _ui_test_catalog_sample,
}


def full_sample(contract: str) -> ContractResult:
    """
    R12 check 3: one valid, deterministic instance of `contract`, built from state-consistent
    records that jointly populate every optional field the contract defines - see the module
    docstring. Takes no `view` parameter: filtering by view is a transform's job and setting
    `document.view` for presentation is a generator's job, so this always returns the fully
    populated, unfiltered record set.

    @param contract: one of the six contracts' CONTRACT_ID (e.g. "doc-entities-v1.0.0").
    @return: a fresh, schema-valid instance of that contract's result model.
    @raises ValueError: `contract` is not one of the six known contract ids.
    """
    builder = _BUILDERS.get(contract)
    if builder is None:
        raise ValueError(f"unknown contract id {contract!r}; expected one of {sorted(_BUILDERS)!r}")
    return builder()


# ---------------------------------------------------------------------------
# shown_paths: docs/contracts.md section 4 ("Rendering rules"), encoded once.
# ---------------------------------------------------------------------------

_ENTITY_PATH = "content.entities[]."

# Rows shown in both the inner and the release view.
_SHOWN_BOTH_VIEWS = frozenset(
    {
        f"{_ENTITY_PATH}state",  # US/FUNC state, and a Feature's derived state (marked "derived" in inner)
        f"{_ENTITY_PATH}not_in_scope[]",
        f"{_ENTITY_PATH}preconditions[]",
        f"{_ENTITY_PATH}acceptance_criteria[].not_in_scope[]",
        f"{_ENTITY_PATH}acceptance_criteria[].preconditions[]",
        f"{_ENTITY_PATH}acceptance_criteria[].removal_planned",
        # AC header (always canonical_header()), the AC's deprecated badge and, for a planned AC, the
        # "planned vX.Y.Z" / "backlog" label all read state + version. A planned AC only ever reaches a
        # generator in the inner view (the release filter drops it as a record), so the label needs no
        # separate inner-only path.
        f"{_ENTITY_PATH}acceptance_criteria[].state",
        f"{_ENTITY_PATH}acceptance_criteria[].version",
        f"{_ENTITY_PATH}acceptance_criteria[].aspect[]",
        f"{_ENTITY_PATH}acceptance_criteria[].rationale",
        f"{_ENTITY_PATH}acceptance_criteria[].placeholder_values",
        f"{_ENTITY_PATH}rationale",  # a Functionality's own rationale
    }
)

# Rows shown only in the inner view; hidden in release.
_SHOWN_INNER_ONLY = frozenset(
    {
        f"{_ENTITY_PATH}stub_reason",
        f"{_ENTITY_PATH}deprecated_at",
        f"{_ENTITY_PATH}deprecation_reason",
        f"{_ENTITY_PATH}source_ref.area_path",
        f"{_ENTITY_PATH}source_ref.iteration_path",
    }
)

# Never shown in either view (docs/contracts.md section 4): source_ref.native_type,
# source_ref.tracker_state - simply never added to either set above.

# coverage-matrix (docs/contracts.md section 4, "Coverage"): per-aspect coverage rows are presented
# in both views; the planned summary is presented in the inner view only. Paths under `planned_summary`
# are relative to the document root, since that block sits beside `entities[]`, not inside it.
_COVERAGE_PATH = "entities[].acceptance_criteria[]."
_COVERAGE_BOTH_VIEWS = frozenset(
    {f"{_COVERAGE_PATH}status", f"{_COVERAGE_PATH}aspects[].aspect", f"{_COVERAGE_PATH}aspects[].status"}
)
_COVERAGE_INNER_ONLY = frozenset(
    {"planned_summary.total", "planned_summary.backlog", "planned_summary.by_target_version"}
)

_VIEWS = ("inner", "release")


def shown_paths(contract: str, view: str) -> set[str]:
    """
    R12 check 3 / docs/contracts.md section 4: the field paths `view` shows for `contract`,
    so a generator's own tests assert against this instead of re-deriving the rendering table
    themselves. Supported for the three contracts a generator renders: `generator-ready`
    (the Entity/AcceptanceCriterion table), `coverage-matrix` (per-aspect coverage in both
    views, the planned summary in inner only) and `ui-test-catalog`, which has no
    view-dependent rows, so it shows nothing beyond its own record fields in either view.

    @param contract: "generator-ready-v1.0.0", "coverage-matrix-v1.0.0" or "ui-test-catalog-v1.0.0".
    @param view: "inner" or "release".
    @return: the set of field paths (R11 syntax) that view shows, for view-dependent presentation only.
    @raises ValueError: an unsupported contract or an unknown view.
    """
    supported = (generator_ready.CONTRACT_ID, coverage_matrix.CONTRACT_ID, ui_test_catalog.CONTRACT_ID)
    if contract not in supported:
        raise ValueError(f"shown_paths only supports {list(supported)!r}, got {contract!r}")
    if view not in _VIEWS:
        raise ValueError(f"view must be one of {_VIEWS!r}, got {view!r}")

    if contract == ui_test_catalog.CONTRACT_ID:
        return set()
    if contract == coverage_matrix.CONTRACT_ID:
        return set(_COVERAGE_BOTH_VIEWS) | (set(_COVERAGE_INNER_ONLY) if view == "inner" else set())

    paths = set(_SHOWN_BOTH_VIEWS)
    if view == "inner":
        paths |= _SHOWN_INNER_ONLY
    return paths
