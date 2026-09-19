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
Tests for contracts.lineage (docs/contracts.md, R11): assert_complete and check_field_loss,
exercised only against synthetic record roots and tables - the real, component-owned tables
live in the repository that owns each transform, not here.
"""

import re
from pathlib import Path

import pytest
from pydantic import BaseModel

from living_doc_utilities.contracts import lineage
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
    table = LineageTable({"items[].a": "out[].a"})  # "items[].b" has no entry at all

    with pytest.raises(AssertionError, match=r"items\[\]\.b"):
        lineage.assert_complete(table, _SYNTHETIC_ROOTS)


def test_assert_complete_passes_on_a_complete_table_of_mapped_and_dropped_entries():
    table = LineageTable({"items[].a": "out[].a", "items[].b": Dropped("not carried downstream")})

    lineage.assert_complete(table, _SYNTHETIC_ROOTS)  # must not raise


def test_assert_complete_passes_when_every_leaf_path_is_explicitly_dropped():
    table = LineageTable({"items[].a": Dropped("reason a"), "items[].b": Dropped("reason b")})

    lineage.assert_complete(table, _SYNTHETIC_ROOTS)  # must not raise


# ---------------------------------------------------------------------------
# check_field_loss
# ---------------------------------------------------------------------------


def test_check_field_loss_raises_field_loss_for_a_mapped_path_with_input_gt_0_output_0():
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


def test_check_field_loss_raises_when_the_mapped_output_path_is_entirely_absent():
    # The output's field_occupancy simply has no entry for the mapped path - equivalent to 0.
    table = LineageTable({"items[].a": "out[].a"})
    input_selected_stats = AuditStats(cardinality=Cardinality(), field_occupancy={"items[].a": 3})
    output_stats = Stats(cardinality=Cardinality(), field_occupancy={})

    with pytest.raises(ContractError):
        lineage.check_field_loss(table, input_selected_stats, output_stats)


def test_check_field_loss_does_not_raise_when_the_output_still_has_occupancy():
    table = LineageTable({"items[].a": "out[].a"})
    input_selected_stats = AuditStats(cardinality=Cardinality(), field_occupancy={"items[].a": 3})
    output_stats = Stats(cardinality=Cardinality(), field_occupancy={"out[].a": 2})

    lineage.check_field_loss(table, input_selected_stats, output_stats)  # must not raise


def test_check_field_loss_does_not_raise_for_a_path_explicitly_marked_dropped():
    table = LineageTable({"items[].a": Dropped("legitimately not carried")})
    input_selected_stats = AuditStats(cardinality=Cardinality(), field_occupancy={"items[].a": 3})
    output_stats = Stats(cardinality=Cardinality(), field_occupancy={})

    lineage.check_field_loss(table, input_selected_stats, output_stats)  # must not raise


def test_check_field_loss_does_not_raise_when_a_view_filter_legitimately_removed_the_records():
    # A record dropped because a view legitimately filtered it out (e.g. the release view
    # drops `planned` acceptance criteria) shows up as *input* occupancy already at 0, because
    # `input_selected_stats` is computed over the records the view filter kept (R7) - so this
    # is indistinguishable, by design, from "there was never anything here to lose".
    table = LineageTable({"items[].a": "out[].a"})
    input_selected_stats = AuditStats(cardinality=Cardinality(), field_occupancy={"items[].a": 0})
    output_stats = Stats(cardinality=Cardinality(), field_occupancy={"out[].a": 0})

    lineage.check_field_loss(table, input_selected_stats, output_stats)  # must not raise


# ---------------------------------------------------------------------------
# Machinery only: no transform-specific table lives in this module.
# ---------------------------------------------------------------------------


def test_lineage_module_declares_no_transform_specific_table():
    source = Path(lineage.__file__).read_text(encoding="utf-8")

    assert not re.search(r"normalize-issues|coverage-matrix", source)
