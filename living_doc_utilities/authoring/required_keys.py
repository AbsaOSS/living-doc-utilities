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
The tables of the keys each authored header must carry and of the tag each `.feature` file must carry, and the checks
that report a missing one. The parsers stay lenient and never read them; the authored-input check and `living-doc`'s
corpus checker do.
"""

from typing import Optional

from living_doc_utilities.authoring.accounting import located
from living_doc_utilities.authoring.framing import Frame, feature_line, feature_tags, sections
from living_doc_utilities.authoring.identity import derive_entity_id, extract_living_doc_title
from living_doc_utilities.authoring.normalize import SourceFormat
from living_doc_utilities.contracts.codes import Code
from living_doc_utilities.contracts.common import DocType
from living_doc_utilities.contracts.envelope import ContractWarning

# The header a PageObject with `parent-feat:` carries; a full PageObject header is the Feature's own.
CROSS_REFERENCE = "cross-reference"

# The keys every PageObject header must carry about its own page.
_PAGE_KEYS = ("route", "owners", "purpose")

# Source format -> header (an entity type, or `CROSS_REFERENCE`) -> its required keys, as authored: a `.feature` or
# PageObject key without its colon, an issue body's `##` heading text.
REQUIRED_KEYS: dict[SourceFormat, dict[str, tuple[str, ...]]] = {
    SourceFormat.FEATURE_HEADER: {
        "DocumentedUserStory": ("status", "business_value", "acceptance_criteria"),
        "DocumentedFunctionality": ("status", "parent", "func_type", "acceptance_criteria"),
    },
    SourceFormat.PAGE_OBJECT: {
        "DocumentedFeature": (
            "surface_type",
            *_PAGE_KEYS,
            "user_stories",
            "functionalities",
            "external_dependencies",
            "page-object",
        ),
        CROSS_REFERENCE: ("parent-feat", *_PAGE_KEYS, "page-object"),
    },
    SourceFormat.ISSUE_BODY: {
        "DocumentedUserStory": ("Description", "Status", "Business Value", "Acceptance Criteria"),
        "DocumentedFeature": ("Description", "Surface Type", "Owners", "User Stories", "Functionalities"),
        "DocumentedFunctionality": ("Description", "Status", "Parent Feature", "Func Type", "Acceptance Criteria"),
    },
}

# Entity type -> the feature-level tag its `.feature` file must carry above `Feature:`, as authored, and the id type
# its value names.
REQUIRED_TAGS: dict[str, tuple[str, str]] = {
    "DocumentedUserStory": ("@US_ID:", "US"),
    "DocumentedFunctionality": ("@FUNC_ID:", "FUNC"),
}


def _named_entity(frame: Frame) -> Optional[tuple[str, int]]:
    """The entity id the header's title line names and that line's number, or None when it names none."""
    if frame.title is None:
        return None
    title = extract_living_doc_title([frame.title.line.raw])
    entity_id = None if title is None else derive_entity_id(title)[0]
    return None if entity_id is None else (entity_id, frame.title.number)


def missing_required_keys(frame: Frame, source_format: SourceFormat, entity_type: DocType) -> list[ContractWarning]:
    """`MISSING_REQUIRED_KEY` for each required key a `.feature` or PageObject header's `frame` lacks, in the table's
    order, on the title line. `[]` when the header names no entity: the parser reports `MISSING_ENTITY_ID` then.
    @raises ValueError: for any other source format, or an entity type its format never carries."""
    if source_format not in (SourceFormat.FEATURE_HEADER, SourceFormat.PAGE_OBJECT):
        raise ValueError(f"missing_required_keys reads a .feature or PageObject header, not {source_format.value}")
    if entity_type not in REQUIRED_KEYS[source_format]:
        raise ValueError(f"a {source_format.value} header never carries a {entity_type}")
    named = _named_entity(frame)
    if named is None:
        return []
    entity_id, number = named

    present = {section.name for section in sections(frame)}
    header: str = entity_type
    if source_format == SourceFormat.PAGE_OBJECT and "parent-feat" in present:
        header = CROSS_REFERENCE
    return [
        located(
            Code.MISSING_REQUIRED_KEY,
            f"Required key '{key}:' is missing.",
            f"entity_id={entity_id!r} key={key!r} line_no={number}",
            entity_id,
            number,
        )
        for key in REQUIRED_KEYS[source_format][header]
        if key not in present
    ]


def missing_required_tag(frame: Frame, entity_type: DocType) -> list[ContractWarning]:
    """`MISSING_REQUIRED_KEY` when no tag above a `.feature` file's `Feature:` line is its entity type's required tag
    naming an id of that type, on the `Feature:` line (the title line without one). `frame` is the file's header frame.
    `[]` when the header names no entity: the parser reports `MISSING_ENTITY_ID` then.
    @raises ValueError: for an entity type a `.feature` file never carries."""
    if entity_type not in REQUIRED_TAGS:
        raise ValueError(f"a .feature file never carries a {entity_type}")
    named = _named_entity(frame)
    if named is None:
        return []
    entity_id, title_number = named

    tag, id_type = REQUIRED_TAGS[entity_type]
    values = [token[len(tag) :] for token in feature_tags(frame) if token.startswith(tag)]
    if any(derive_entity_id(value)[0] == value and value.startswith(f"{id_type}-") for value in values):
        return []
    feature = feature_line(frame)
    number = title_number if feature is None else feature.number
    return [
        located(
            Code.MISSING_REQUIRED_KEY,
            f"Required tag '{tag}' is missing.",
            f"entity_id={entity_id!r} tag={tag!r} line_no={number}",
            entity_id,
            number,
        )
    ]
