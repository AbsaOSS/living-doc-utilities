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
Shared test helpers every component builds its own R12/R11 tests on: `full_sample` builds one
valid, deterministic contract instance covering every optional field jointly; `shown_paths`
encodes the field-by-view rendering table, so tests assert against it instead of a drifting copy.
"""

from datetime import datetime, timezone
from typing import Any, Callable

from living_doc_utilities.contracts import (
    coverage_matrix,
    doc_entities,
    doc_source,
    generator_ready,
    ui_test_catalog,
    ui_tests,
)
from living_doc_utilities.contracts.codes import Code
from living_doc_utilities.contracts.common import AcceptanceCriterion, SourceRef, Timestamps
from living_doc_utilities.contracts.doc_entities import Entity, PageRef
from living_doc_utilities.contracts.envelope import (
    AuditStats,
    Cardinality,
    ContractWarning,
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
# Shared entities/scenarios reused everywhere a contract needs them; full coverage per root, since R11 is per-root.
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


# The keyword AC's declared values; the coverage sample covers one of them.
_PAYMENT_FIELDS = ("card-holder", "expiry-date", "last-four-digits")


def _acceptance_criteria(parent_id: str) -> list[AcceptanceCriterion]:
    """Every acceptance-criterion-level extension, jointly: an `active` AC carrying `Aspect:`,
    preconditions, not_in_scope and rationale; a `planned` AC targeted at a future version; a
    separate backlog `planned` AC with none; an `active` AC declaring its variants by a
    keyword, so `aspect` holds the keyword's values and placeholder_values its one name; and an
    `active` `Aspect:` AC no scenario covers. No AC declares both (living-doc's header-types,
    "AC variants")."""
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
        AcceptanceCriterion(
            id=f"{parent_id}-04",
            state="active",
            version="1.0.0",
            description="The order summary shows the {payment-field} of the chosen saved card.",
            aspect=list(_PAYMENT_FIELDS),
            placeholder_values={"payment_field": list(_PAYMENT_FIELDS)},
        ),
        AcceptanceCriterion(
            id=f"{parent_id}-05",
            state="active",
            version="1.0.0",
            description="A customer can remove a saved payment method at checkout.",
            aspect=["desktop", "mobile"],
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
    """One of each entity kind, jointly covering every Entity-shaped leaf path doc-entities,
    doc-source and generator-ready declare - deprecation fields, a derived Feature state with
    pages, a Functionality rationale - each only where its own state allows it."""
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
        feature_dependencies=["FEAT-002"],
        stub_reason="surface not yet instrumented: awaiting UI test coverage",
        wizard_steps=["cart-review", "payment", "confirmation"],
        notes=["The checkout markup comes from the shared storefront template."],
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
                notes=["The confirmation screen is reached only through the payment step."],
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
    for their Scenario-shaped record roots: one tagged, GitHub-sourced and linked to each value
    of an `Aspect:` AC and to one value of a keyword AC; one Azure-DevOps-sourced (covering
    source_ref.area_path/iteration_path) with a bare link."""
    return [
        Scenario(
            scenario_id="SCN-001",
            title="Customer completes checkout with a saved card",
            source_ref=_github_source_ref("checkout.feature", "Scenario"),
            tags=["smoke"],
            acceptance_criteria=[
                AcLink(id="US-001-01", aspect="desktop"),
                AcLink(id="US-001-01", aspect="mobile"),
                AcLink(id="US-001-04", aspect=_PAYMENT_FIELDS[0]),
            ],
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


def _not_loaded_warnings() -> list[ContractWarning]:
    """What was not loaded from the input, as a collector reports it: a dropped criterion with every location
    field, which therefore no entity or coverage row holds; a criterion line no field reads; and a file whose
    entity was never emitted, which names no entity."""
    feature_file = "features/checkout.feature"
    return [
        ContractWarning(
            code=Code.MALFORMED_AC.name,
            message="Acceptance criterion declares its variants more than once (Aspect, payment_field); "
            "keep one 'Aspect:' or one keyword.",
            context="entity='US-001' line_no=31 header='#   AC:US-001-06 (v1.0.0 - active)'",
            entity_id="US-001",
            ac_id="US-001-06",
            line_no=31,
            path=feature_file,
        ),
        ContractWarning(
            code=Code.UNPARSED_AC_LINE.name,
            message="Bullet 'device' is not a keyword: the description names no '{device}'.",
            context="entity='US-001' header='#   AC:US-001-01 (v1.0.0 - active)' line_no=17 line='- device: tablet'",
            entity_id="US-001",
            ac_id="US-001-01",
            line_no=17,
            path=feature_file,
        ),
        ContractWarning(
            code=Code.MISSING_ENTITY_ID.name,
            message="Feature-header banner carries no 'LIVING DOC — ...' title line.",
            context="title='' line_no=1",
            line_no=1,
            path="features/refund.feature",
        ),
    ]


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
                total_acceptance_criteria=6,
                included_acceptance_criteria=6,
                excluded_acceptance_criteria=0,
            ),
        ),
        content=generator_ready.Content(entities=_entities()),
        warnings=_not_loaded_warnings(),
    )


def _aspect(aspect: str, *scenario_ids: str) -> coverage_matrix.AspectCoverage:
    return coverage_matrix.AspectCoverage(
        aspect=aspect, status="covered" if scenario_ids else "not_covered", scenario_ids=list(scenario_ids)
    )


def _entity_coverage(rows: list[coverage_matrix.AcCoverage], **fields: Any) -> coverage_matrix.EntityCoverage:
    """An entity's coverage rows with the summary computed from them, as a producer writes it."""
    return coverage_matrix.EntityCoverage(
        acceptance_criteria=rows, summary=coverage_matrix.CoverageSummary.from_rows(rows), **fields
    )


def _coverage_matrix_sample() -> coverage_matrix.CoverageMatrixResult:
    """Each row status once - covered, partially_covered (1 of 3), not_covered - plus a deprecated row and an
    entity with no counted row. US-001 is 44.4 (1 + 1/3 + 0 over 3 rows), US-002 100.0, FUNC-001 None; the
    matrix is 58.3 (7/3 over 4 rows), not the 72.2 mean of the two entity percentages."""
    user_story = _entity_coverage(
        [
            coverage_matrix.AcCoverage(
                ac_id="US-001-01",
                state="active",
                status="covered",
                aspects=[_aspect("desktop", "SCN-001"), _aspect("mobile", "SCN-001")],
            ),
            coverage_matrix.AcCoverage(
                ac_id="US-001-04",
                state="active",
                status="partially_covered",
                aspects=[
                    _aspect(_PAYMENT_FIELDS[0], "SCN-001"),
                    _aspect(_PAYMENT_FIELDS[1]),
                    _aspect(_PAYMENT_FIELDS[2]),
                ],
            ),
            coverage_matrix.AcCoverage(
                ac_id="US-001-05",
                state="active",
                status="not_covered",
                aspects=[_aspect("desktop"), _aspect("mobile")],
            ),
        ],
        entity_id="US-001",
        type="DocumentedUserStory",
        title="Checkout with a saved payment method",
        state="active",
    )
    deprecated_user_story = _entity_coverage(
        [coverage_matrix.AcCoverage(ac_id="US-002-01", state="deprecated", status="covered", scenario_ids=["SCN-002"])],
        entity_id="US-002",
        type="DocumentedUserStory",
        title="Checkout as a guest",
        state="deprecated",
    )
    functionality = _entity_coverage(
        [], entity_id="FUNC-001", type="DocumentedFunctionality", title="Validate card number", state="active"
    )
    entities = [user_story, deprecated_user_story, functionality]
    return coverage_matrix.CoverageMatrixResult(
        metadata=_metadata(transform=True),
        document=coverage_matrix.Document(view="inner"),
        entities=entities,
        planned_summary=coverage_matrix.PlannedSummary(total=2, backlog=1, by_target_version={"1.6.0": 1}),
        summary=coverage_matrix.CoverageSummary.from_rows(
            row for entity in entities for row in entity.acceptance_criteria
        ),
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
    """R12 check 3: one valid, deterministic instance of `contract`, covering every optional field jointly.
    Always unfiltered - filtering by view is a transform's job.

    @param contract: one of the six contracts' CONTRACT_ID (e.g. "doc-entities-v1.0.0").
    @return: a fresh, schema-valid instance of that contract's result model.
    @raises ValueError: `contract` is not one of the six known contract ids.
    """
    builder = _BUILDERS.get(contract)
    if builder is None:
        raise ValueError(f"unknown contract id {contract!r}; expected one of {sorted(_BUILDERS)!r}")
    return builder()


# ---------------------------------------------------------------------------
# shown_paths: the field-by-view rendering table (R12 check 3), encoded once.
# ---------------------------------------------------------------------------

_ENTITY_PATH = "content.entities[]."

_SHOWN_BOTH_VIEWS = frozenset(
    {
        f"{_ENTITY_PATH}state",  # US/FUNC state, and a Feature's derived state (marked "derived" in inner)
        f"{_ENTITY_PATH}not_in_scope[]",
        f"{_ENTITY_PATH}preconditions[]",
        f"{_ENTITY_PATH}acceptance_criteria[].not_in_scope[]",
        f"{_ENTITY_PATH}acceptance_criteria[].preconditions[]",
        f"{_ENTITY_PATH}acceptance_criteria[].removal_planned",
        # AC header/badge/label all read state+version; a planned AC only reaches the inner view, so needs no own path.
        f"{_ENTITY_PATH}acceptance_criteria[].state",
        f"{_ENTITY_PATH}acceptance_criteria[].version",
        f"{_ENTITY_PATH}acceptance_criteria[].aspect[]",
        f"{_ENTITY_PATH}acceptance_criteria[].rationale",
        f"{_ENTITY_PATH}acceptance_criteria[].placeholder_values",
        f"{_ENTITY_PATH}rationale",  # a Functionality's own rationale
    }
)

# What was not loaded from the input: each warning under the entity its entity_id names, or once for the document
# when it names none the document holds. Its entity_id only places it; its ac_id and context are never shown.
_WARNING_PATH = "warnings[]."

_SHOWN_INNER_ONLY = frozenset(
    {
        f"{_ENTITY_PATH}stub_reason",
        f"{_ENTITY_PATH}deprecated_at",
        f"{_ENTITY_PATH}deprecation_reason",
        f"{_ENTITY_PATH}source_ref.area_path",
        f"{_ENTITY_PATH}source_ref.iteration_path",
    }
    | {f"{_WARNING_PATH}{name}" for name in ("code", "message", "line_no", "path")}
)

# Never shown in either view: source_ref.native_type, source_ref.tracker_state (absent from both sets above).

# Per-aspect rows and the coverage summaries (each entity's and the matrix's) show in both views;
# planned_summary (root-relative, beside entities[]) shows in inner only.
_COVERAGE_PATH = "entities[].acceptance_criteria[]."
_SUMMARY_FIELDS = ("counted_acs", "covered_acs", "partially_covered_acs", "not_covered_acs", "coverage_pct")
_COVERAGE_BOTH_VIEWS = frozenset(
    {f"{_COVERAGE_PATH}status", f"{_COVERAGE_PATH}aspects[].aspect", f"{_COVERAGE_PATH}aspects[].status"}
    | {f"{owner}summary.{name}" for owner in ("entities[].", "") for name in _SUMMARY_FIELDS}
)
_COVERAGE_INNER_ONLY = frozenset(
    {"planned_summary.total", "planned_summary.backlog", "planned_summary.by_target_version"}
)

_VIEWS = ("inner", "release")


def shown_paths(contract: str, view: str) -> set[str]:
    """R12 check 3: the field paths `view` shows for `contract`, so a generator's own tests
    assert against this instead of re-deriving the rendering table themselves.

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
