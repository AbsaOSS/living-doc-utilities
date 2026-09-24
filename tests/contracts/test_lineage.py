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

"""`lineage` (R11): `assert_complete` and `check_field_loss` against synthetic record roots and tables."""

import re
from pathlib import Path

import pytest
from pydantic import BaseModel

from living_doc_utilities.contracts import doc_entities, lineage, schema_export
from living_doc_utilities.contracts.codes import Code, ContractError
from living_doc_utilities.contracts.envelope import AuditStats, Cardinality, Stats
from living_doc_utilities.contracts.lineage import Dropped, LineageTable


class _Leaf(BaseModel):
    a: str
    b: str


_SYNTHETIC_ROOTS: dict[str, type[BaseModel]] = {"items": _Leaf}


# ---------------------------------------------------------------------------
# assert_complete
# ---------------------------------------------------------------------------


def test_assert_complete_fails_on_a_table_missing_one_leaf_path():
    """`assert_complete` raises, naming the path, when one leaf path has no entry at all."""
    table = LineageTable({"items[].a": "out[].a"})  # "items[].b" has no entry at all

    with pytest.raises(AssertionError, match=r"items\[\]\.b"):
        lineage.assert_complete(table, _SYNTHETIC_ROOTS)


def test_assert_complete_passes_on_a_complete_table_of_mapped_and_dropped_entries():
    """`assert_complete` does not raise when every leaf path is either mapped or explicitly dropped."""
    table = LineageTable({"items[].a": "out[].a", "items[].b": Dropped("not carried downstream")})

    lineage.assert_complete(table, _SYNTHETIC_ROOTS)  # must not raise


def test_assert_complete_passes_when_every_leaf_path_is_explicitly_dropped():
    """`assert_complete` does not raise when every leaf path is explicitly dropped, with none mapped."""
    table = LineageTable({"items[].a": Dropped("reason a"), "items[].b": Dropped("reason b")})

    lineage.assert_complete(table, _SYNTHETIC_ROOTS)  # must not raise


def test_assert_complete_accepts_a_contract_id_in_place_of_its_record_roots():
    """assert_complete accepts a contract id directly, resolving it to that contract's record roots."""
    every_path = schema_export.field_occupancy_paths(doc_entities.RECORD_ROOTS)
    complete = LineageTable({path: Dropped("not carried") for path in every_path})

    lineage.assert_complete(complete, doc_entities.CONTRACT_ID)  # must not raise
    with pytest.raises(AssertionError, match=r"entities\[\]\.entity_id"):
        lineage.assert_complete(LineageTable({}), doc_entities.CONTRACT_ID)


def test_assert_complete_rejects_an_unknown_contract_id():
    """`assert_complete` raises `ValueError` when given a contract id it does not recognise."""
    with pytest.raises(ValueError, match="unknown contract id"):
        lineage.assert_complete(LineageTable({}), "not-a-contract-v1.0.0")


# ---------------------------------------------------------------------------
# check_field_loss
# ---------------------------------------------------------------------------


def test_check_field_loss_raises_field_loss_for_a_mapped_path_with_input_gt_0_output_0():
    """A mapped field present on input but absent on output raises FIELD_LOSS naming both paths and the lost count."""
    table = LineageTable({"items[].a": "out[].a"})
    input_selected_stats = AuditStats(cardinality=Cardinality(), field_occupancy={"items[].a": 3})
    output_stats = Stats(cardinality=Cardinality(), field_occupancy={"out[].a": 0})

    with pytest.raises(ContractError) as exc_info:
        lineage.check_field_loss(table, input_selected_stats, output_stats)

    assert exc_info.value.code == Code.FIELD_LOSS
    message = str(exc_info.value)
    assert "items[].a" in message
    assert "out[].a" in message
    assert "3" in message


def test_check_field_loss_reports_every_lost_path_in_one_error():
    """All lost paths across a table are collected into a single raised error, not one per path."""
    table = LineageTable({"items[].a": "out[].a", "items[].b": "out[].b", "items[].c": "out[].c"})
    input_selected_stats = AuditStats(
        cardinality=Cardinality(), field_occupancy={"items[].a": 3, "items[].b": 2, "items[].c": 1}
    )
    output_stats = Stats(cardinality=Cardinality(), field_occupancy={"out[].b": 2})

    with pytest.raises(ContractError) as exc_info:
        lineage.check_field_loss(table, input_selected_stats, output_stats)

    message = str(exc_info.value)
    assert "items[].a" in message and "items[].c" in message
    assert "items[].b" not in message


def test_check_field_loss_raises_when_the_mapped_output_path_is_entirely_absent():
    """A mapped output path missing from field_occupancy entirely is treated the same as zero."""
    table = LineageTable({"items[].a": "out[].a"})
    input_selected_stats = AuditStats(cardinality=Cardinality(), field_occupancy={"items[].a": 3})
    output_stats = Stats(cardinality=Cardinality(), field_occupancy={})

    with pytest.raises(ContractError):
        lineage.check_field_loss(table, input_selected_stats, output_stats)


def test_check_field_loss_does_not_raise_when_the_output_still_has_occupancy():
    """A mapped path with any non-zero output occupancy passes, even if lower than the input."""
    table = LineageTable({"items[].a": "out[].a"})
    input_selected_stats = AuditStats(cardinality=Cardinality(), field_occupancy={"items[].a": 3})
    output_stats = Stats(cardinality=Cardinality(), field_occupancy={"out[].a": 2})

    lineage.check_field_loss(table, input_selected_stats, output_stats)  # must not raise


def test_check_field_loss_does_not_raise_for_a_path_explicitly_marked_dropped():
    """A path explicitly marked Dropped in the table is exempt from field-loss checking."""
    table = LineageTable({"items[].a": Dropped("legitimately not carried")})
    input_selected_stats = AuditStats(cardinality=Cardinality(), field_occupancy={"items[].a": 3})
    output_stats = Stats(cardinality=Cardinality(), field_occupancy={})

    lineage.check_field_loss(table, input_selected_stats, output_stats)  # must not raise


def test_check_field_loss_does_not_raise_when_a_view_filter_legitimately_removed_the_records():
    """A path with zero *input* occupancy (already filtered out by the view) never raises field loss."""
    # A view-filtered record shows as input occupancy 0 (R7 selected_stats), so it looks like "nothing to lose".
    table = LineageTable({"items[].a": "out[].a"})
    input_selected_stats = AuditStats(cardinality=Cardinality(), field_occupancy={"items[].a": 0})
    output_stats = Stats(cardinality=Cardinality(), field_occupancy={"out[].a": 0})

    lineage.check_field_loss(table, input_selected_stats, output_stats)  # must not raise


# ---------------------------------------------------------------------------
# Machinery only: no transform-specific table lives in this module.
# ---------------------------------------------------------------------------


def test_lineage_module_declares_no_transform_specific_table():
    """The `lineage` module's own source names no transform-specific lineage table; it is machinery only."""
    source = Path(lineage.__file__).read_text(encoding="utf-8")

    assert not re.search(r"normalize-issues|coverage-matrix", source)
