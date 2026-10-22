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
valid, deterministic contract instance from one entity set a producer could write, its records jointly
covering every optional field their types carry; `NEVER_CARRIED_PATHS` names the doc-source paths
no type carries, which its sample leaves empty; `shown_paths` encodes the field-by-view rendering
table, so tests assert against it instead of a drifting copy.
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
from living_doc_utilities.contracts.common import AcceptanceCriterion, DocType, EntityCore, SourceRef, Timestamps
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
from living_doc_utilities.contracts.schema_export import field_occupancy_paths
from living_doc_utilities.contracts.ui_tests import AcLink, Scenario

_UTILITIES_VERSION = "0.5.1"

# ---------------------------------------------------------------------------
# The one entity set and the scenarios every sample reuses. doc-source holds the set split by type, one root per
# type, and R11 counts each root on its own: a root fills every path but those its type never carries.
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


# The keyword AC's folded name and its declared values; the coverage sample covers one of them.
_PAYMENT_FIELD_KEYWORD = "payment_field"
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
            placeholder_values={_PAYMENT_FIELD_KEYWORD: list(_PAYMENT_FIELDS)},
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


# The Functionality's keyword AC: its folded name and its declared values. No scenario links that Functionality.
_DECLINE_REASON_KEYWORD = "decline_reason"
_DECLINE_REASONS = ("expired", "blocked")


def _functionality_acceptance_criteria(parent_id: str) -> list[AcceptanceCriterion]:
    """Every acceptance-criterion-level extension on a Functionality, jointly, since doc-source counts its root
    apart: an `active` `Aspect:` AC with preconditions, not_in_scope and rationale; a targeted and a backlog
    `planned` AC; an `active` keyword AC; and a `deprecated` AC with its planned removal, which an `active`
    entity may hold (Parsers, "Status derivation")."""
    return [
        AcceptanceCriterion(
            id=f"{parent_id}-01",
            state="active",
            version="1.2.0",
            description="The API charges a saved card and returns the payment id.",
            aspect=["visa", "mastercard"],
            preconditions=["The card is saved to the customer's account."],
            not_in_scope=["Refunds."],
            rationale="The payment id lets the checkout page confirm the order without a second call.",
        ),
        AcceptanceCriterion(
            id=f"{parent_id}-02",
            state="planned",
            version="1.7.0",
            description="The API charges a saved card in the customer's own currency.",
        ),
        AcceptanceCriterion(
            id=f"{parent_id}-03",
            state="planned",
            description="The API charges a saved card in instalments.",
        ),
        AcceptanceCriterion(
            id=f"{parent_id}-04",
            state="active",
            version="1.2.0",
            description="The API declines a charge on a card that is {decline-reason}.",
            aspect=list(_DECLINE_REASONS),
            placeholder_values={_DECLINE_REASON_KEYWORD: list(_DECLINE_REASONS)},
        ),
        AcceptanceCriterion(
            id=f"{parent_id}-05",
            state="deprecated",
            version="1.2.0",
            removal_planned="2.0.0",
            description="The API returns the card's last four digits with the payment id.",
        ),
    ]


def _closed_timestamps() -> Timestamps:
    return Timestamps(
        created_at=datetime(2025, 2, 3, tzinfo=timezone.utc),
        updated_at=datetime(2026, 4, 20, tzinfo=timezone.utc),
        closed_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
    )


def _entities() -> list[Entity]:
    """The one entity set every entity-carrying sample holds, each id once. Per type, the records jointly cover every
    Entity-shaped leaf path that type carries - deprecation fields, a derived Feature state with pages, an `API`
    Feature, criteria on a User Story and on a Functionality - each only where its state and type allow it, and each
    relation names an entity of the type it expects (Parsers, "Relations")."""
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

    # US-002's successor, so its superseded_by resolves; the one User Story with notes.
    user_story_successor = Entity(
        entity_id="US-010",
        source_ref=_github_source_ref("512", "User Story"),
        type="DocumentedUserStory",
        title="Unified checkout",
        state="active",
        state_origin="authored",
        narrative="As a customer, I want one checkout flow, whether or not I have an account.",
        notes=["Guest checkout moved into this flow when US-002 was retired."],
    )

    # The API Feature FEAT-001's feature_dependencies names; its state is derived from FUNC-002.
    api_feature = Entity(
        entity_id="FEAT-002",
        source_ref=_github_source_ref("78", "Feature"),
        type="DocumentedFeature",
        title="Payments API",
        state="active",
        state_origin="derived",
        purpose="The API the checkout page charges a customer's payment method through.",
        surface_type="API",
        owners=["team-payments"],
        functionalities=["FUNC-002"],
    )

    api_functionality = Entity(
        entity_id="FUNC-002",
        source_ref=_github_source_ref("89", "Functionality"),
        type="DocumentedFunctionality",
        title="Charge a saved card",
        state="active",
        state_origin="authored",
        narrative="Charges a customer's saved card and returns the payment id.",
        notes=["The API reads a card token from the vault; it never stores the card number."],
        acceptance_criteria=_functionality_acceptance_criteria("FUNC-002"),
        parent="FEAT-002",
        func_type="API",
        rationale="One call per charge keeps a retried request from charging the card twice.",
    )

    # Retired with its one Functionality, so its derived state is deprecated too; a Feature has no deprecation date.
    # A page, as a PageObject header writes it: a source scan has no form for an API Feature yet (Parsers, "Relations").
    feature_deprecated = Entity(
        entity_id="FEAT-003",
        source_ref=_azure_devops_source_ref("4105", "Feature"),
        type="DocumentedFeature",
        title="Legacy payment page",
        state="deprecated",
        state_origin="derived",
        tags=["payments", "legacy"],
        timestamps=_closed_timestamps(),
        purpose="The legacy gateway's page where a customer typed in card details.",
        surface_type="page",
        owners=["team-payments"],
        functionalities=["FUNC-003"],
        deprecation_reason="The checkout page took over the payment step.",
        superseded_by="FEAT-001",
        pages=[
            PageRef(
                is_primary=True,
                route="/checkout/legacy-payment",
                page_object="LegacyPaymentPage.ts",
                owners=["team-payments"],
                purpose="The screen where a customer typed in card details for the legacy gateway.",
            )
        ],
    )

    functionality_deprecated = Entity(
        entity_id="FUNC-003",
        source_ref=_azure_devops_source_ref("4106", "Functionality"),
        type="DocumentedFunctionality",
        title="Charge through the legacy gateway",
        state="deprecated",
        state_origin="authored",
        tags=["payments", "legacy"],
        timestamps=_closed_timestamps(),
        narrative="Charges a card through the legacy payment gateway.",
        source="https://dev.azure.com/absaoss/payments/_workitems/edit/3988",
        preconditions=["The merchant account at the legacy gateway is still open."],
        not_in_scope=["Saved cards."],
        deprecated_at="2026-05-01",
        deprecation_reason="Charging a saved card through the Payments API replaced it.",
        superseded_by="FUNC-002",
        parent="FEAT-003",
        func_type="API",
        rationale="Kept until every merchant account has moved to the Payments API.",
    )

    return [
        user_story_active,
        user_story_deprecated,
        feature,
        functionality,
        user_story_successor,
        api_feature,
        api_functionality,
        feature_deprecated,
        functionality_deprecated,
    ]


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


# The Entity fields each type carries beyond EntityCore's, which every entity has. A field belongs to a type when an
# authoring format writes it for that type: docs/authoring/parsers.md's "Issue body", "Feature header" and
# "PageObject header" key tables, and living-doc's docs/guides/living-doc-header-types.md sections 1 to 3. Never read
# from the model: it accepts any field on any type.
_CONTENT_FIELDS_BY_TYPE: dict[DocType, frozenset[str]] = {
    "DocumentedUserStory": frozenset(
        {
            "narrative",
            "source",
            "notes",
            "business_value",
            "acceptance_criteria",
            "preconditions",
            "not_in_scope",
            "deprecated_at",
            "deprecation_reason",
            "superseded_by",
        }
    ),
    "DocumentedFeature": frozenset(
        {
            "purpose",
            "notes",
            "deprecation_reason",
            "superseded_by",
            "surface_type",
            "owners",
            "user_stories",
            "functionalities",
            "external_dependencies",
            "feature_dependencies",
            "stub_reason",
            "wizard_steps",
            "pages",
        }
    ),
    "DocumentedFunctionality": frozenset(
        {
            "narrative",
            "source",
            "notes",
            "acceptance_criteria",
            "preconditions",
            "not_in_scope",
            "deprecated_at",
            "deprecation_reason",
            "superseded_by",
            "parent",
            "func_type",
            "rationale",
        }
    ),
}


def _never_carried_paths(root: str, doc_type: DocType) -> frozenset[str]:
    """`root`'s leaf paths whose top-level Entity field `doc_type` does not carry, with every path below that field."""
    carried = _CONTENT_FIELDS_BY_TYPE[doc_type] | set(EntityCore.model_fields)
    prefix = f"{root}[]."
    return frozenset(
        path
        for path in field_occupancy_paths({root: Entity})
        if path.removeprefix(prefix).split(".")[0].removesuffix("[]") not in carried
    )


# R12 check 3's exceptions: per doc-source root, the paths its type never carries. full_sample leaves exactly these
# empty, since only a record no producer writes could fill one; a collector's own full-sample test may use them too.
NEVER_CARRIED_PATHS: dict[str, frozenset[str]] = {
    root: _never_carried_paths(root, doc_type) for root, doc_type in doc_source.ROOT_TYPES.items()
}


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
    """The entity set split by type, each record in its type's root, as a collector writes it."""
    entities = _entities()
    by_root = {
        root: [entity for entity in entities if entity.type == doc_type]
        for root, doc_type in doc_source.ROOT_TYPES.items()
    }
    return doc_source.DocSourceResult(
        metadata=_metadata(transform=False),
        user_stories=by_root["user_stories"],
        features=by_root["features"],
        functionalities=by_root["functionalities"],
    )


def _ui_tests_sample() -> ui_tests.UITestsResult:
    return ui_tests.UITestsResult(metadata=_metadata(transform=False), scenarios=_scenarios())


# The commit the collector read the warnings' files at.
_COLLECTED_SHA = "4f2c1e9a7b3d5f6081a2c3d4e5f60718293a4b5c"


def _blob_url(path: str) -> str:
    """A file's permalink at the collected commit. The entities link GitHub issues, so no entity's URL places a line."""
    return f"https://github.com/absaoss/payments-service/blob/{_COLLECTED_SHA}/{path}"


def _not_loaded_warnings() -> list[ContractWarning]:
    """What was not loaded from the input, as a collector reports it: a dropped criterion with every location
    field, which therefore no entity or coverage row holds; a criterion line no field reads; and a file whose
    entity was never emitted, which names no entity. Each links its file at the collected commit."""
    feature_file = "features/checkout.feature"
    refund_file = "features/refund.feature"
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
            source_url=_blob_url(feature_file),
        ),
        ContractWarning(
            code=Code.UNPARSED_AC_LINE.name,
            message="Bullet 'device' is not a keyword: the description names no '{device}'.",
            context="entity='US-001' header='#   AC:US-001-01 (v1.0.0 - active)' line_no=17 line='- device: tablet'",
            entity_id="US-001",
            ac_id="US-001-01",
            line_no=17,
            path=feature_file,
            source_url=_blob_url(feature_file),
        ),
        ContractWarning(
            code=Code.MISSING_ENTITY_ID.name,
            message="Feature-header banner carries no 'LIVING DOC — ...' title line.",
            context="title='' line_no=1",
            line_no=1,
            path=refund_file,
            source_url=_blob_url(refund_file),
        ),
    ]


def _generator_ready_sample() -> generator_ready.GeneratorReadyResult:
    """The whole entity set, unfiltered, so selection_summary counts every entity and criterion as included."""
    entities = _entities()
    criteria = sum(len(entity.acceptance_criteria) for entity in entities)
    return generator_ready.GeneratorReadyResult(
        metadata=_metadata(transform=True),
        document=generator_ready.Document(
            title="Payments service",
            version="1.4.0",
            view="inner",
            selection_summary=generator_ready.SelectionSummary(
                total_entities=len(entities),
                included_entities=len(entities),
                excluded_entities=0,
                total_acceptance_criteria=criteria,
                included_acceptance_criteria=criteria,
                excluded_acceptance_criteria=0,
            ),
        ),
        content=generator_ready.Content(entities=entities),
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
    """What one coverage run over the entity set and the ui-tests sample gives: an entity per User Story and
    Functionality, in the set's order, a row per counted criterion, and planned_summary over the planned ones.
    Each row status occurs - covered, partially_covered (1 of 3), not_covered - with deprecated rows and entities
    with no counted row. US-001 is 44.4 (1 + 1/3 + 0 over 3 rows), US-002 100.0, FUNC-002 0.0 (no scenario links
    it); the matrix is 33.3 (7/3 over 7 rows), not the 48.1 mean of the three entity percentages."""
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
                keyword=_PAYMENT_FIELD_KEYWORD,
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
    successor_user_story = _entity_coverage(
        [], entity_id="US-010", type="DocumentedUserStory", title="Unified checkout", state="active"
    )
    api_functionality = _entity_coverage(
        [
            coverage_matrix.AcCoverage(
                ac_id="FUNC-002-01",
                state="active",
                status="not_covered",
                aspects=[_aspect("visa"), _aspect("mastercard")],
            ),
            coverage_matrix.AcCoverage(
                ac_id="FUNC-002-04",
                state="active",
                status="not_covered",
                keyword=_DECLINE_REASON_KEYWORD,
                aspects=[_aspect(reason) for reason in _DECLINE_REASONS],
            ),
            coverage_matrix.AcCoverage(ac_id="FUNC-002-05", state="deprecated", status="not_covered"),
        ],
        entity_id="FUNC-002",
        type="DocumentedFunctionality",
        title="Charge a saved card",
        state="active",
    )
    deprecated_functionality = _entity_coverage(
        [],
        entity_id="FUNC-003",
        type="DocumentedFunctionality",
        title="Charge through the legacy gateway",
        state="deprecated",
    )
    entities = [
        user_story,
        deprecated_user_story,
        functionality,
        successor_user_story,
        api_functionality,
        deprecated_functionality,
    ]
    return coverage_matrix.CoverageMatrixResult(
        metadata=_metadata(transform=True),
        document=coverage_matrix.Document(view="inner"),
        entities=entities,
        # US-001-02 and FUNC-002-02 are targeted, US-001-03 and FUNC-002-03 backlog.
        planned_summary=coverage_matrix.PlannedSummary(total=4, backlog=2, by_target_version={"1.6.0": 1, "1.7.0": 1}),
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
    """R12 check 3: one valid, deterministic instance of `contract`, built from the one entity set, covering every
    optional field jointly; in doc-source, every one but NEVER_CARRIED_PATHS. Always unfiltered - filtering by
    view is a transform's job.

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
    | {f"{_WARNING_PATH}{name}" for name in ("code", "message", "line_no", "path", "source_url")}
)

# Never shown in either view: source_ref.native_type, source_ref.tracker_state (absent from both sets above).

# Per-aspect rows, labelled by their keyword, and the coverage summaries (each entity's and the matrix's) show in
# both views; planned_summary (root-relative, beside entities[]) shows in inner only.
_COVERAGE_PATH = "entities[].acceptance_criteria[]."
_SUMMARY_FIELDS = ("counted_acs", "covered_acs", "partially_covered_acs", "not_covered_acs", "coverage_pct")
_COVERAGE_BOTH_VIEWS = frozenset(
    {f"{_COVERAGE_PATH}{name}" for name in ("status", "keyword", "aspects[].aspect", "aspects[].status")}
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
