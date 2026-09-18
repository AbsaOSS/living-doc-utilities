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
entity_id derivation from a title - a GitHub issue title, a `.feature` banner's title
text, or a PageObject banner's title text. The id itself (`US-001`, `FEAT-001`, ...) is
always written with a plain hyphen (docs/contracts.md's entity-id formats), so - unlike
the separator after it - it needs no normalisation before extraction.
"""

import re
from typing import Optional

from living_doc_utilities.contracts.envelope import ContractWarning

MISSING_ENTITY_ID = "MISSING_ENTITY_ID"

# A historical prefix such as "GH-" ahead of the real id is stripped simply by taking the
# *last* id-shaped run in the title: "GH-US-001" itself is not id-shaped (letters directly
# followed by "-" then digits fails to match starting at "GH", because what follows "GH-" is
# "US", not a digit), so the search naturally lands on "US-001".
_ENTITY_ID_RE = re.compile(r"[A-Z]+-\d+")


def derive_entity_id(title: str) -> tuple[Optional[str], list[ContractWarning]]:
    """Extracts the leading entity id from `title`. Returns `(None, [MISSING_ENTITY_ID])`
    when the title carries no parseable id - the caller (a collector) is responsible for
    adding location context to that warning and for counting the skip toward
    `cardinality.entities_skipped`.
    """
    match = _ENTITY_ID_RE.search(title)
    if match is None:
        return None, [
            ContractWarning(
                code=MISSING_ENTITY_ID,
                message="Title carries no recognised entity-id prefix.",
                context=f"title={title!r}",
            )
        ]
    return match.group(0), []
