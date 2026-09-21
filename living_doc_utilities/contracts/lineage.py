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
docs/contracts.md, R11: "Lineage tables are declared by the transform owner, checked by a
shared helper." Each transform in the repository that owns it declares its own table - one
entry per input leaf path, mapping it to where it lands in the output, or recording that it
was deliberately dropped - because the table changes whenever the transform's own code does.
This module ships only the two checks every such table is run through: `assert_complete` (a
new input field cannot ship without anyone deciding where it goes) and `check_field_loss` (a
mapped field that had data on the way in but none on the way out is a bug, not a legitimate
filter). No transform-specific table lives here.
"""

from dataclasses import dataclass
from typing import Mapping, Union

from pydantic import BaseModel

from living_doc_utilities.contracts import registry, schema_export
from living_doc_utilities.contracts.codes import Code, ContractError
from living_doc_utilities.contracts.envelope import AuditStats, Stats


@dataclass(frozen=True)
class Dropped:
    """Records that an input leaf path is deliberately not carried to the output, and why -
    e.g. a field a transform's view filter legitimately strips."""

    reason: str


# One input leaf path's fate: either the output leaf path it is carried to, or Dropped(reason).
LineageEntry = Union[str, Dropped]


@dataclass(frozen=True)
class LineageTable:
    """A transform's own field-lineage declaration: every input leaf path it knows about,
    each mapped to the output path it becomes or to an explicit Dropped(reason). Built and
    owned by the transform's repository, not by this package (docs/contracts.md, R11)."""

    entries: Mapping[str, LineageEntry]


def assert_complete(table: LineageTable, input_contract: Union[str, dict[str, type[BaseModel]]]) -> None:
    """
    R11: "a new contract field cannot ship without anyone deciding where it goes." Fails when
    `input_contract` has a leaf path that `table` says nothing about at all - neither mapped
    to an output path nor explicitly marked Dropped.

    @param table: the transform's own lineage table.
    @param input_contract: the input contract's CONTRACT_ID (e.g. "doc-entities-v1.0.0"), or its
        RECORD_ROOTS declaration directly, as schema_export and stats read a contract's shape.
    @raises AssertionError: naming every input leaf path the table has no entry for.
    @raises ValueError: `input_contract` is a contract id that is not one of the six known ids.
    """
    record_roots = registry.record_roots(input_contract) if isinstance(input_contract, str) else input_contract
    expected_paths = set(schema_export.field_occupancy_paths(record_roots))
    missing = expected_paths - table.entries.keys()
    if missing:
        raise AssertionError(f"lineage table is missing an entry for: {sorted(missing)}")


def check_field_loss(table: LineageTable, input_selected_stats: AuditStats, output_stats: Stats) -> None:
    """
    R11's transform-time hard error: for every path `table` maps to an output path (skipping the ones marked Dropped,
    which are a legitimate, declared omission rather than a loss), a mapped path with non-zero input occupancy and zero
    output occupancy means the transform silently lost a field that was actually authored - raised as `FIELD_LOSS`
    naming the path and both occupancies, for every such path in one error. `input_selected_stats` must already be the
    occupancy computed over the records the transform's view filter *kept* for this input (R7's `selected_stats`), so a
    record dropped by a legitimate view filter is never mistaken for a field loss.

    @param table: the transform's own lineage table.
    @param input_selected_stats: the input's `selected_stats` for this run (R7) - occupancy
        over the records the view filter kept, not the input's raw, unfiltered occupancy.
    @param output_stats: the transform output's own `metadata.stats`.
    @raises ContractError: FIELD_LOSS, naming every lost path with its input occupancy and its
        mapped output path's occupancy.
    """
    lost = []
    for input_path, entry in table.entries.items():
        if isinstance(entry, Dropped):
            continue
        output_path = entry
        input_occupancy = input_selected_stats.field_occupancy.get(input_path, 0)
        output_occupancy = output_stats.field_occupancy.get(output_path, 0)
        if input_occupancy > 0 and output_occupancy == 0:
            lost.append(
                f"'{input_path}' had occupancy {input_occupancy} on input but its mapped "
                f"output path '{output_path}' has occupancy 0"
            )
    if lost:
        raise ContractError(Code.FIELD_LOSS, "; ".join(lost))
