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

from living_doc_utilities.contracts.codes import Code
from living_doc_utilities.contracts.envelope import ContractWarning

# A historical prefix such as "GH-" ahead of the real id is stripped simply by taking the
# *first* id-shaped run in the title: "GH-US-001" itself is not id-shaped (letters directly
# followed by "-" then digits fails to match starting at "GH", because what follows "GH-" is
# "US", not a digit), so the search naturally lands on "US-001".
# Imported by normalize.normalize_title, which needs the same id shape to find a title's
# id boundary - defined here, this module's own concern, rather than redefined there.
_ENTITY_ID_RE = re.compile(r"[A-Z]+-\d+")

# The `.feature`-banner / PageObject-banner title marker (living-doc's docs/guides/
# living-doc-header-types.md) - the one place both formats' title lines are recognised,
# so neither parser re-derives this pattern for itself.
_LIVING_DOC_TITLE_RE = re.compile(r"LIVING DOC\s*—\s*(?P<title>.+?)\s*$")


def extract_living_doc_title(lines: list[str]) -> Optional[str]:
    """Finds the 'LIVING DOC — ...' title text among `lines` (a `.feature` banner's
    comment lines, or a PageObject banner's `*`-content lines) and returns it stripped
    of surrounding whitespace. `None` when no such line is present."""
    for line in lines:
        title_m = _LIVING_DOC_TITLE_RE.search(line)
        if title_m:
            return title_m.group("title").strip()
    return None


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
                code=Code.MISSING_ENTITY_ID.name,
                message="Title carries no recognised entity-id prefix.",
                context=f"title={title!r}",
            )
        ]
    return match.group(0), []
