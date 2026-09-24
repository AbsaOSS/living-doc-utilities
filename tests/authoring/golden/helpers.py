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
Shared helpers for the golden-fixture tests: fixture/expected-JSON loading, and turning a
`ParsedEntity` into the same shape as a hand-written golden JSON file - a full `Entity`
dict with `source_ref` excluded (source_ref is collector-filled, never parser-filled).
Not a test module itself - no test_* functions live here.
"""

import json
from pathlib import Path

from living_doc_utilities.authoring.issue_body import ParsedEntity
from living_doc_utilities.contracts.common import SourceRef
from living_doc_utilities.contracts.doc_entities import Entity

GOLDEN_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "golden"

_DUMMY_SOURCE_REF = SourceRef(
    system="GitHub",
    native_id="1",
    native_type="dummy",
    url="https://github.com/absaoss/living-doc-utilities/issues/1",
    tracker_state="open",
)


def read_fixture(*parts: str) -> str:
    return (GOLDEN_DIR.joinpath(*parts)).read_text(encoding="utf-8")


def load_expected(name: str) -> dict:
    return json.loads((GOLDEN_DIR / "expected" / name).read_text(encoding="utf-8"))


def to_entity_dict(parsed: ParsedEntity) -> dict:
    """Builds a full, schema-valid `Entity` from `parsed` (a dummy `source_ref`, empty
    `tags`, default `timestamps`) and dumps it with `source_ref` excluded - the same shape
    as a hand-written golden JSON file. `parsed`'s own fields are exactly `Entity`'s minus
    `source_ref`/`tags`/`timestamps` (both derive from `EntityContent` plus identity), so
    no field list is spelled here.
    """
    entity = Entity(source_ref=_DUMMY_SOURCE_REF, **parsed.model_dump())
    dumped = entity.model_dump(mode="json")
    del dumped["source_ref"]
    return dumped
