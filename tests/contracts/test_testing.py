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

"""`testing.py` (R12 check 3): `full_sample` validity and occupancy, and `shown_paths` per field-by-view row."""

import inspect
import json
import re
from collections import Counter
from dataclasses import dataclass
from typing import get_args

import jsonschema
import pytest

from living_doc_utilities.authoring import feature_header, issue_body, page_object
from living_doc_utilities.authoring.issue_body import ParsedEntity
from living_doc_utilities.authoring.relations import check_relations
from living_doc_utilities.authoring.status import derive_statuses
from living_doc_utilities.contracts import (
    coverage_matrix,
    doc_entities,
    doc_source,
    generator_ready,
    io,
    registry,
    schema_export,
    stats,
    testing,
    ui_test_catalog,
    ui_tests,
)
from living_doc_utilities.contracts.common import DATE_TIME_PATTERN, EntityCore
from living_doc_utilities.contracts.doc_entities import Entity

CONTRACTS = [(contract_id, spec.result_model, spec.record_roots) for contract_id, spec in registry.CONTRACTS.items()]
CONTRACT_IDS = [contract_id for contract_id, _, _ in CONTRACTS]


# ---------------------------------------------------------------------------
# full_sample: schema validity, exhaustive occupancy, determinism, no `view` parameter.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("contract_id, model, _record_roots", CONTRACTS, ids=CONTRACT_IDS)
def test_full_sample_is_the_right_model_and_validates_against_the_committed_schema(contract_id, model, _record_roots):
    """full_sample returns an instance of the contract's own result model, valid against its committed schema."""
    sample = testing.full_sample(contract_id)

    assert isinstance(sample, model)
    data = json.loads(sample.model_dump_json())
    jsonschema.validate(instance=data, schema=schema_export.load_schema(contract_id))


@pytest.mark.parametrize("contract_id, _model, record_roots", CONTRACTS, ids=CONTRACT_IDS)
def test_full_sample_has_non_zero_occupancy_for_every_leaf_path(contract_id, _model, record_roots):
    """Every leaf path is populated in full_sample; in doc-source every one but the paths its root's type never
    carries (`testing.py::NEVER_CARRIED_PATHS`), and those stay empty."""
    sample = testing.full_sample(contract_id)

    computed = stats.compute_stats(sample, record_roots, sample.metadata.stats.cardinality)
    expected_paths = schema_export.field_occupancy_paths(record_roots)
    never_carried = set()
    if contract_id == doc_source.CONTRACT_ID:
        never_carried = set().union(*testing.NEVER_CARRIED_PATHS.values())

    empty = {path for path in expected_paths if computed.field_occupancy.get(path, 0) == 0}
    zero_or_missing = sorted(empty - never_carried)
    filled_but_never_carried = sorted(never_carried - empty)
    assert zero_or_missing == [], f"{contract_id}: leaf path(s) with no occupancy in full_sample: {zero_or_missing}"
    assert filled_but_never_carried == [], f"{contract_id}: path(s) no producer writes: {filled_but_never_carried}"


def test_never_carried_paths_counts_per_doc_source_root():
    """The table holds, per root, the paths its type never carries: 19 for a User Story, 19 for a Feature, 17 for a
    Functionality, 55 in all, each a path of its own root."""
    table = testing.NEVER_CARRIED_PATHS
    root_paths = set(schema_export.field_occupancy_paths(doc_source.RECORD_ROOTS))

    counts = {root: len(paths) for root, paths in table.items()}
    assert counts == {"user_stories": 19, "features": 19, "functionalities": 17}
    for root, paths in table.items():
        assert all(path.startswith(f"{root}[].") and path in root_paths for path in paths), root
    # One sample per kind: a Feature owns no criteria, a User Story no pages, a Functionality no business value.
    assert "features[].acceptance_criteria[].id" in table["features"]
    assert "user_stories[].pages[].route" in table["user_stories"]
    assert "functionalities[].business_value[]" in table["functionalities"]
    assert "functionalities[].acceptance_criteria[].id" not in table["functionalities"]


def test_every_entity_content_field_is_carried_by_some_type():
    """Each authored Entity field is declared for at least one type, so a new field cannot fall into every root's
    exceptions unnoticed, and no type names a field the model lacks."""
    carried = set().union(*testing._CONTENT_FIELDS_BY_TYPE.values())

    assert carried == set(Entity.model_fields) - set(EntityCore.model_fields)


# PageObject header keys whose Entity field has another name; `route` and `page-object` fill the Feature's pages.
_PAGE_OBJECT_KEY_FIELDS = {
    "stub-reason": "stub_reason",
    "wizard-steps": "wizard_steps",
    "route": "pages",
    "page-object": "pages",
}


def _fields_a_parser_writes(specs) -> set[str]:
    skipped = {issue_body._SectionKind.IGNORED_AUTHORED, issue_body._SectionKind.IGNORED}
    return {
        "acceptance_criteria" if spec.kind is issue_body._SectionKind.AC else spec.field_name
        for spec in specs.values()
        if spec.kind not in skipped
    }


@pytest.mark.parametrize("doc_type", list(testing._CONTENT_FIELDS_BY_TYPE))
def test_each_type_carries_exactly_the_fields_the_authoring_parsers_write_for_it(doc_type):
    """Beyond the identity fields, a type carries exactly what the issue-body, .feature-header and PageObject parsers
    write for it: a check on the never-carried table from outside the sample."""
    written = _fields_a_parser_writes(issue_body._SECTIONS_BY_TYPE[doc_type])
    written |= _fields_a_parser_writes(feature_header._KEYS_BY_TYPE.get(doc_type, {}))
    if doc_type == "DocumentedFeature":
        page_object_keys = page_object._FULL_HEADER_KEYS - set(page_object.IGNORED_AUTHORED_KEYS)
        written |= {_PAGE_OBJECT_KEY_FIELDS.get(key, key) for key in page_object_keys}

    assert written - set(EntityCore.model_fields) == testing._CONTENT_FIELDS_BY_TYPE[doc_type]


def test_doc_source_full_sample_holds_each_record_in_its_type_s_root_and_each_id_once():
    """Each doc-source root holds records of its own type only, and no entity id appears in two roots or twice."""
    sample = testing.full_sample(doc_source.CONTRACT_ID)
    ids = []

    for root, doc_type in doc_source.ROOT_TYPES.items():
        records = getattr(sample, root)
        assert records, root
        assert {record.type for record in records} == {doc_type}, root
        ids += [record.entity_id for record in records]
    assert len(ids) == len(set(ids)), Counter(ids).most_common(1)


# write_artifact fills these two itself; everything else must read back as written.
_FILLED_ON_WRITE = {"metadata": {"stats": True, "producer": {"utilities_version"}}}


@pytest.mark.parametrize("contract_id", CONTRACT_IDS)
def test_full_sample_round_trips_through_write_and_read(contract_id, tmp_path):
    """Each sample written with `write_artifact` reads back with `read_artifact`, unchanged but for its filled stats
    and utilities version."""
    sample = testing.full_sample(contract_id)
    destination = tmp_path / f"{contract_id}.json"

    io.write_artifact(sample, destination)
    loaded = io.read_artifact(destination, contract_id.rsplit("-v", 1)[0])

    assert type(loaded) is type(sample)
    assert loaded.model_dump(exclude=_FILLED_ON_WRITE) == sample.model_dump(exclude=_FILLED_ON_WRITE)


@pytest.mark.parametrize("contract_id", CONTRACT_IDS)
def test_every_date_time_a_full_sample_writes_matches_the_rfc_3339_pattern(contract_id, tmp_path):
    """`metadata.generated_at` and every `timestamps` value, as written, match `common.py::DATE_TIME_PATTERN`."""
    destination = tmp_path / f"{contract_id}.json"
    io.write_artifact(testing.full_sample(contract_id), destination)
    payload = json.loads(destination.read_text(encoding="utf-8"))
    values = [payload["metadata"]["generated_at"]]

    def collect(node):
        if isinstance(node, dict):
            values.extend(value for value in node.get("timestamps", {}).values() if value is not None)
            for value in node.values():
                collect(value)
        elif isinstance(node, list):
            for item in node:
                collect(item)

    collect(payload)
    assert all(re.search(DATE_TIME_PATTERN, value) for value in values), values
    if "Timestamps" in schema_export.load_schema(contract_id)["$defs"]:
        # Guards the check from passing on generated_at alone wherever entities carry timestamps.
        assert len(values) > 1, contract_id


@pytest.mark.parametrize("contract_id", CONTRACT_IDS)
def test_full_sample_is_deterministic(contract_id):
    """`testing.py::full_sample` returns an equal result across repeated calls for the same contract."""
    assert testing.full_sample(contract_id) == testing.full_sample(contract_id)


def test_full_sample_rejects_an_unknown_contract_id():
    """`testing.py::full_sample` raises for a contract id that isn't registered."""
    with pytest.raises(ValueError, match="unknown contract id"):
        testing.full_sample("not-a-real-contract-v1.0.0")


def test_full_sample_takes_no_view_parameter():
    """`testing.py::full_sample`'s signature has no 'view' parameter."""
    assert "view" not in inspect.signature(testing.full_sample).parameters


# ---------------------------------------------------------------------------
# State-consistency: no record carries a field its own state or type makes meaningless; one entity set throughout.
# ---------------------------------------------------------------------------


def _entities_by_contract():
    doc_source_sample = testing.full_sample(doc_source.CONTRACT_ID)
    return {
        doc_entities.CONTRACT_ID: list(testing.full_sample(doc_entities.CONTRACT_ID).entities),
        doc_source.CONTRACT_ID: [
            *doc_source_sample.user_stories,
            *doc_source_sample.features,
            *doc_source_sample.functionalities,
        ],
        generator_ready.CONTRACT_ID: list(testing.full_sample(generator_ready.CONTRACT_ID).content.entities),
    }


def _every_entity_across_full_samples():
    return [entity for entities in _entities_by_contract().values() for entity in entities]


def test_the_entity_carrying_full_samples_hold_one_entity_set():
    """doc-entities' entities, doc-source's three roots together and generator-ready's entities are the same
    records, each id once."""
    by_contract = _entities_by_contract()
    reference = {entity.entity_id: entity for entity in by_contract[doc_entities.CONTRACT_ID]}

    for contract_id, entities in by_contract.items():
        assert len(entities) == len(reference), contract_id
        assert {entity.entity_id: entity for entity in entities} == reference, contract_id


def test_the_entity_set_is_what_one_collector_run_settles_without_a_warning():
    """Every relation resolves to an entity of the type it expects, no authored state contradicts its criteria, and
    each Feature's state is the one its Functionalities derive (Parsers, "Relations", "Status derivation")."""
    entities = testing.full_sample(doc_entities.CONTRACT_ID).entities
    parsed = [ParsedEntity(**entity.model_dump(exclude={"source_ref", "tags", "timestamps"})) for entity in entities]
    # A collector run settles every Feature's state itself; the authored states stay as they are.
    unsettled = [
        (
            entity.model_copy(update={"state": None, "state_origin": None})
            if entity.type == "DocumentedFeature"
            else entity
        )
        for entity in parsed
    ]

    settled, status_warnings = derive_statuses(unsettled)

    assert check_relations(parsed) == []
    assert status_warnings == []
    assert [(entity.state, entity.state_origin) for entity in settled] == [
        (entity.state, entity.state_origin) for entity in entities
    ]


def test_generator_ready_selection_summary_counts_the_entity_set():
    """The unfiltered generator-ready sample counts every entity and criterion of the set as included."""
    sample = testing.full_sample(generator_ready.CONTRACT_ID)
    entities = sample.content.entities
    criteria = sum(len(entity.acceptance_criteria) for entity in entities)

    assert sample.document.selection_summary == generator_ready.SelectionSummary(
        total_entities=len(entities),
        included_entities=len(entities),
        excluded_entities=0,
        total_acceptance_criteria=criteria,
        included_acceptance_criteria=criteria,
        excluded_acceptance_criteria=0,
    )


def test_no_deprecated_only_field_is_populated_on_a_non_deprecated_entity():
    """deprecated_at, deprecation_reason and superseded_by stay unset on every non-deprecated entity."""
    for entity in _every_entity_across_full_samples():
        if entity.state != "deprecated":
            assert entity.deprecated_at is None, entity.entity_id
            assert entity.deprecation_reason is None, entity.entity_id
            assert entity.superseded_by is None, entity.entity_id


def test_a_deprecated_entity_of_every_type_carries_its_deprecation_fields():
    """full_sample includes a deprecated entity of every type, each with its deprecation fields populated; a Feature
    carries no deprecation date (Parsers, "Issue body")."""
    # Guards the check above from passing vacuously when full_sample has no deprecated entity.
    deprecated = [entity for entity in _every_entity_across_full_samples() if entity.state == "deprecated"]

    assert {entity.type for entity in deprecated} == set(doc_source.ROOT_TYPES.values())
    for entity in deprecated:
        assert (entity.deprecated_at is None) == (entity.type == "DocumentedFeature"), entity.entity_id
        assert entity.deprecation_reason is not None, entity.entity_id


def test_no_acceptance_criterion_outside_planned_is_version_less():
    """Every acceptance criterion not in the 'planned' state carries a version."""
    for entity in _every_entity_across_full_samples():
        for ac in entity.acceptance_criteria:
            if ac.state != "planned":
                assert ac.version is not None, ac.id


def test_full_sample_includes_a_targeted_and_a_backlog_planned_acceptance_criterion():
    """Each entity-carrying full_sample includes both a version-targeted and a version-less (backlog) planned AC."""
    for contract_id, entities in _entities_by_contract().items():
        planned = [ac for entity in entities for ac in entity.acceptance_criteria if ac.state == "planned"]

        assert any(ac.version is not None for ac in planned), f"{contract_id}: expected a targeted planned AC"
        assert any(ac.version is None for ac in planned), f"{contract_id}: expected a backlog planned AC"


def test_full_sample_declares_each_criterion_s_variants_once():
    """living-doc's "AC variants": no AC carries both `Aspect:` and a keyword; a keyword AC's `aspect` is its values."""
    criteria = [ac for entities in _entities_by_contract().values() for entity in entities for ac in entity.acceptance_criteria]

    for ac in criteria:
        assert len(ac.placeholder_values) <= 1, ac.id
        if ac.placeholder_values:
            assert ac.aspect == next(iter(ac.placeholder_values.values())), ac.id
    # Guards the check above from passing vacuously: both spellings occur.
    assert any(ac.aspect and not ac.placeholder_values for ac in criteria)
    assert any(ac.placeholder_values for ac in criteria)


def test_coverage_matrix_full_sample_has_every_row_status_a_deprecated_row_and_an_unaveraged_root():
    """Coverage-matrix's full_sample holds a covered, a 1-of-3 partially_covered, a not_covered and a deprecated row."""
    sample = testing.full_sample(coverage_matrix.CONTRACT_ID)
    rows = [row for entity in sample.entities for row in entity.acceptance_criteria]
    partial = next(row for row in rows if row.status == "partially_covered")

    assert {row.status for row in rows} == {"covered", "partially_covered", "not_covered"}
    assert (partial.covered_aspects(), len(partial.aspects)) == (1, 3)
    assert any(row.state == "deprecated" for row in rows)
    # The entity set grew: US-010 and FUNC-003 own no counted row, and no scenario links FUNC-002's three rows, so
    # the matrix fell from 58.3 (7/3 over 4 rows) to 7/3 over 7 rows.
    assert [entity.summary.coverage_pct for entity in sample.entities] == [44.4, 100.0, None, None, 0.0, None]
    assert sample.summary.coverage_pct == 33.3


def test_coverage_matrix_full_sample_is_one_coverage_run_over_the_entity_set():
    """An entity per User Story and Functionality of the set, in its order, with a row per counted criterion, and a
    planned_summary over the set's planned criteria: what the toolkit computes from the other samples."""
    entities = [
        entity
        for entity in testing.full_sample(generator_ready.CONTRACT_ID).content.entities
        if entity.type != "DocumentedFeature"
    ]
    sample = testing.full_sample(coverage_matrix.CONTRACT_ID)
    counted = set(get_args(coverage_matrix.CountedState))
    planned = [ac for entity in entities for ac in entity.acceptance_criteria if ac.state == "planned"]

    identity = [(entity.entity_id, entity.type, entity.title, entity.state) for entity in entities]
    assert [(entity.entity_id, entity.type, entity.title, entity.state) for entity in sample.entities] == identity
    for coverage, entity in zip(sample.entities, entities, strict=True):
        counted_criteria = [(ac.id, ac.state) for ac in entity.acceptance_criteria if ac.state in counted]
        assert [(row.ac_id, row.state) for row in coverage.acceptance_criteria] == counted_criteria, entity.entity_id
    assert sample.planned_summary == coverage_matrix.PlannedSummary(
        total=len(planned),
        backlog=sum(1 for ac in planned if ac.version is None),
        by_target_version=dict(Counter(ac.version for ac in planned if ac.version is not None)),
    )
    # Guards the row check from passing vacuously: a Functionality owns counted rows too.
    assert any(entity.type == "DocumentedFunctionality" and entity.acceptance_criteria for entity in sample.entities)


def test_full_samples_agree_on_every_criterion_and_scenario_link():
    """A generator joins the samples by criterion id: each coverage row names a criterion the entities hold, with
    that criterion's aspects, each covered by exactly the scenarios that link it; the dropped criterion is in none."""
    generator_sample = testing.full_sample(generator_ready.CONTRACT_ID)
    criteria = {ac.id: ac for entity in generator_sample.content.entities for ac in entity.acceptance_criteria}
    links = [
        (link.id, link.aspect, scenario.scenario_id)
        for scenario in testing.full_sample(ui_tests.CONTRACT_ID).scenarios
        for link in scenario.acceptance_criteria
    ]
    rows = [row for entity in testing.full_sample(coverage_matrix.CONTRACT_ID).entities for row in entity.acceptance_criteria]
    dropped = next(warning.ac_id for warning in generator_sample.warnings if warning.code == "MALFORMED_AC")

    assert all(ac_id in criteria and (aspect is None or aspect in criteria[ac_id].aspect) for ac_id, aspect, _ in links)
    for row in rows:
        assert row.ac_id in criteria, row.ac_id
        assert [aspect.aspect for aspect in row.aspects] == criteria[row.ac_id].aspect, row.ac_id
        for aspect in row.aspects:
            linking = [scn for ac_id, value, scn in links if ac_id == row.ac_id and value in (None, aspect.aspect)]
            assert aspect.scenario_ids == linking, (row.ac_id, aspect.aspect)
        if not row.aspects:
            assert row.scenario_ids == [scn for ac_id, _, scn in links if ac_id == row.ac_id], row.ac_id
    assert dropped not in criteria and dropped not in {row.ac_id for row in rows}


def test_each_coverage_row_names_its_criterion_s_keyword():
    """A coverage row's keyword is its criterion's one placeholder_values key, or None when the criterion has none."""
    generator_sample = testing.full_sample(generator_ready.CONTRACT_ID)
    coverage_sample = testing.full_sample(coverage_matrix.CONTRACT_ID)
    criteria = {ac.id: ac for entity in generator_sample.content.entities for ac in entity.acceptance_criteria}
    rows = [row for entity in coverage_sample.entities for row in entity.acceptance_criteria]
    keywords = {row.ac_id: row.keyword for row in rows}

    for row in rows:
        assert row.keyword == next(iter(criteria[row.ac_id].placeholder_values), None), row.ac_id
    assert keywords.pop("US-001-04") == "payment_field"
    assert keywords.pop("FUNC-002-04") == "decline_reason"
    assert set(keywords.values()) == {None}
    # Guards the None side from passing only on rows without variants: an `Aspect:` row has aspects and no keyword.
    assert any(row.aspects and row.keyword is None for row in rows)


# ---------------------------------------------------------------------------
# shown_paths: every row of testing.py's field-by-view table, for both views.
# ---------------------------------------------------------------------------

_CID = generator_ready.CONTRACT_ID
_INNER = "inner"
_RELEASE = "release"


@dataclass(frozen=True)
class ShownPathCase:
    """One row of the field-by-view rendering table (`testing.py::shown_paths`), for one view."""

    row: str
    view: str
    shown: tuple[str, ...] = ()
    hidden: tuple[str, ...] = ()


SHOWN_PATH_CASES = [
    ShownPathCase("entity_state", _INNER, shown=("content.entities[].state",)),
    ShownPathCase("entity_state", _RELEASE, shown=("content.entities[].state",)),
    ShownPathCase("feature_stub_reason", _INNER, shown=("content.entities[].stub_reason",)),
    ShownPathCase("feature_stub_reason", _RELEASE, hidden=("content.entities[].stub_reason",)),
    ShownPathCase(
        "entity_not_in_scope_and_preconditions",
        _INNER,
        shown=("content.entities[].not_in_scope[]", "content.entities[].preconditions[]"),
    ),
    ShownPathCase(
        "entity_not_in_scope_and_preconditions",
        _RELEASE,
        shown=("content.entities[].not_in_scope[]", "content.entities[].preconditions[]"),
    ),
    ShownPathCase(
        "ac_not_in_scope_and_preconditions",
        _INNER,
        shown=(
            "content.entities[].acceptance_criteria[].not_in_scope[]",
            "content.entities[].acceptance_criteria[].preconditions[]",
        ),
    ),
    ShownPathCase(
        "ac_not_in_scope_and_preconditions",
        _RELEASE,
        shown=(
            "content.entities[].acceptance_criteria[].not_in_scope[]",
            "content.entities[].acceptance_criteria[].preconditions[]",
        ),
    ),
    ShownPathCase(
        "deprecation_date_and_reason",
        _INNER,
        shown=("content.entities[].deprecated_at", "content.entities[].deprecation_reason"),
    ),
    ShownPathCase(
        "deprecation_date_and_reason",
        _RELEASE,
        hidden=("content.entities[].deprecated_at", "content.entities[].deprecation_reason"),
    ),
    ShownPathCase("ac_removal_planned", _INNER, shown=("content.entities[].acceptance_criteria[].removal_planned",)),
    ShownPathCase(
        "ac_removal_planned", _RELEASE, shown=("content.entities[].acceptance_criteria[].removal_planned",)
    ),
    ShownPathCase(
        "ac_header_state_and_version",
        _INNER,
        shown=(
            "content.entities[].acceptance_criteria[].state",
            "content.entities[].acceptance_criteria[].version",
        ),
    ),
    ShownPathCase(
        "ac_header_state_and_version",
        _RELEASE,
        shown=(
            "content.entities[].acceptance_criteria[].state",
            "content.entities[].acceptance_criteria[].version",
        ),
    ),
    # Planned labels render from state + version, so these rows repeat the header row; release drops them as records.
    ShownPathCase(
        "ac_planned_with_target_version",
        _INNER,
        shown=(
            "content.entities[].acceptance_criteria[].state",
            "content.entities[].acceptance_criteria[].version",
        ),
    ),
    ShownPathCase(
        "ac_planned_without_version",
        _INNER,
        shown=(
            "content.entities[].acceptance_criteria[].state",
            "content.entities[].acceptance_criteria[].version",
        ),
    ),
    ShownPathCase("ac_aspect", _INNER, shown=("content.entities[].acceptance_criteria[].aspect[]",)),
    ShownPathCase("ac_aspect", _RELEASE, shown=("content.entities[].acceptance_criteria[].aspect[]",)),
    ShownPathCase(
        "ac_and_functionality_rationale",
        _INNER,
        shown=(
            "content.entities[].acceptance_criteria[].rationale",
            "content.entities[].acceptance_criteria[].placeholder_values",
            "content.entities[].rationale",
        ),
    ),
    ShownPathCase(
        "ac_and_functionality_rationale",
        _RELEASE,
        shown=(
            "content.entities[].acceptance_criteria[].rationale",
            "content.entities[].acceptance_criteria[].placeholder_values",
            "content.entities[].rationale",
        ),
    ),
    ShownPathCase(
        "source_ref_area_and_iteration_path",
        _INNER,
        shown=("content.entities[].source_ref.area_path", "content.entities[].source_ref.iteration_path"),
    ),
    ShownPathCase(
        "source_ref_area_and_iteration_path",
        _RELEASE,
        hidden=("content.entities[].source_ref.area_path", "content.entities[].source_ref.iteration_path"),
    ),
    ShownPathCase(
        "source_ref_native_type_and_tracker_state",
        _INNER,
        hidden=("content.entities[].source_ref.native_type", "content.entities[].source_ref.tracker_state"),
    ),
    ShownPathCase(
        "source_ref_native_type_and_tracker_state",
        _RELEASE,
        hidden=("content.entities[].source_ref.native_type", "content.entities[].source_ref.tracker_state"),
    ),
    # entity_id places a warning, under its entity or once for the document; it is not shown as text.
    ShownPathCase(
        "what_was_not_loaded",
        _INNER,
        shown=(
            "warnings[].code",
            "warnings[].message",
            "warnings[].line_no",
            "warnings[].path",
            "warnings[].source_url",
        ),
        hidden=("warnings[].entity_id", "warnings[].ac_id", "warnings[].context"),
    ),
    ShownPathCase(
        "what_was_not_loaded",
        _RELEASE,
        hidden=(
            "warnings[].code",
            "warnings[].message",
            "warnings[].line_no",
            "warnings[].path",
            "warnings[].source_url",
            "warnings[].entity_id",
            "warnings[].ac_id",
            "warnings[].context",
        ),
    ),
]


@pytest.mark.parametrize("case", SHOWN_PATH_CASES, ids=[f"{c.row}[{c.view}]" for c in SHOWN_PATH_CASES])
def test_shown_paths_matches_the_rendering_table_row(case: ShownPathCase):
    """shown_paths shows/hides exactly the paths this table row says, per view."""
    shown = testing.shown_paths(_CID, case.view)

    for path in case.shown:
        assert path in shown, f"{case.row} ({case.view}): expected {path!r} shown"
    for path in case.hidden:
        assert path not in shown, f"{case.row} ({case.view}): expected {path!r} hidden"


def test_shown_paths_release_view_shows_no_warning_path():
    """The release view never shows what was not loaded from the input."""
    assert not {path for path in testing.shown_paths(_CID, _RELEASE) if path.startswith("warnings[]")}


def test_generator_ready_full_sample_carries_what_was_not_loaded():
    """A dropped criterion with every location field, a criterion line, and a warning that names no entity, so a
    generator renders a warning under its entity and one for the whole document; each links its file's permalink."""
    warnings = testing.full_sample(_CID).warnings
    by_code = {warning.code: warning for warning in warnings}
    malformed = by_code["MALFORMED_AC"]
    entities = testing.full_sample(_CID).content.entities
    entity_ids = {entity.entity_id for entity in entities}
    entity_urls = {entity.source_ref.url for entity in entities}

    assert [warning.code for warning in warnings] == ["MALFORMED_AC", "UNPARSED_AC_LINE", "MISSING_ENTITY_ID"]
    assert None not in (malformed.entity_id, malformed.ac_id, malformed.line_no, malformed.path, malformed.source_url)
    assert by_code["UNPARSED_AC_LINE"].entity_id in entity_ids
    assert by_code["MISSING_ENTITY_ID"].entity_id is None and by_code["MISSING_ENTITY_ID"].line_no is not None
    commits = set()
    for warning in warnings:
        assert warning.path is not None and warning.source_url is not None, warning.code
        # A permalink pins the file at one commit: `<repo>/blob/<40-hex sha>/<path>`; the entities link issues instead.
        permalink = rf"https://github\.com/absaoss/payments-service/blob/([0-9a-f]{{40}})/{re.escape(warning.path)}"
        match = re.fullmatch(permalink, warning.source_url)
        assert match is not None, warning.code
        assert warning.source_url not in entity_urls, warning.code
        commits.add(match.group(1))
    assert len(commits) == 1


def test_shown_paths_rejects_an_unsupported_contract():
    """`testing.py::shown_paths` raises for a contract id, such as doc-entities, that it doesn't support."""
    with pytest.raises(ValueError, match="only supports"):
        testing.shown_paths(doc_entities.CONTRACT_ID, _INNER)


def test_shown_paths_coverage_matrix_shows_aspect_breakdown_in_both_views_and_planned_summary_in_inner_only():
    """Coverage-matrix's aspect breakdown and keyword label are shown in both views; planned_summary only in inner."""
    both = {
        "entities[].acceptance_criteria[].status",
        "entities[].acceptance_criteria[].keyword",
        "entities[].acceptance_criteria[].aspects[].aspect",
        "entities[].acceptance_criteria[].aspects[].status",
    }
    planned_summary = {"planned_summary.total", "planned_summary.backlog", "planned_summary.by_target_version"}
    inner = testing.shown_paths(coverage_matrix.CONTRACT_ID, _INNER)
    release = testing.shown_paths(coverage_matrix.CONTRACT_ID, _RELEASE)

    assert both <= inner and both <= release
    assert planned_summary <= inner
    assert not planned_summary & release


def test_shown_paths_coverage_matrix_shows_every_coverage_summary_in_both_views():
    """Each entity's and the matrix's coverage summary are shown in both views, like the per-aspect rows."""
    fields = ("counted_acs", "covered_acs", "partially_covered_acs", "not_covered_acs", "coverage_pct")
    summaries = {f"{owner}summary.{field}" for owner in ("entities[].", "") for field in fields}

    for view in (_INNER, _RELEASE):
        assert summaries <= testing.shown_paths(coverage_matrix.CONTRACT_ID, view)


def test_shown_paths_ui_test_catalog_has_no_view_dependent_rows():
    """ui-test-catalog's shown_paths returns an empty set for every view; it has no view-dependent rows."""
    for view in (_INNER, _RELEASE):
        assert testing.shown_paths(ui_test_catalog.CONTRACT_ID, view) == set()


def test_shown_paths_rejects_an_unknown_view():
    """`testing.py::shown_paths` raises for a view name that isn't 'inner' or 'release'."""
    with pytest.raises(ValueError, match="view"):
        testing.shown_paths(_CID, "somewhere-else")
