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
PageObject header parsing for a Feature. A PageObject carries no status and no deprecation
date - only `stub-reason:`, and on a full header `deprecation_reason:` / `superseded_by:`, none of
which drives the state. A full header describes the whole Feature plus its own page; a
cross-reference header (`parent-feat:` present) only describes its own page.
"""

import re
from dataclasses import dataclass, field
from typing import Optional

from living_doc_utilities.authoring.accounting import (
    UNCLOSED_COMMENT,
    at_title,
    first_occurrences,
    missing_title,
    scalar_lines,
    structural_warnings,
    unplaced_lines,
)
from living_doc_utilities.authoring.framing import Frame, Section, opening_value, sections, without_comment_close
from living_doc_utilities.authoring.identity import derive_entity_id, extract_living_doc_title
from living_doc_utilities.authoring.issue_body import IGNORED_AUTHORED_KEYS as _ISSUE_BODY_IGNORED_AUTHORED_KEYS
from living_doc_utilities.authoring.issue_body import (
    ParsedEntity,
    bullet_field_warnings,
    extract_bullets,
    split_id_list,
)
from living_doc_utilities.authoring.normalize import PO_BULLET_KEYS, SourceFormat, normalize_framed
from living_doc_utilities.contracts.codes import Code
from living_doc_utilities.contracts.doc_entities import PageRef
from living_doc_utilities.contracts.envelope import ContractWarning

# Glossary keys that map to no field, dropped for the same reason issue_body drops them (declared once, reused here).
IGNORED_AUTHORED_KEYS = {
    "status": _ISSUE_BODY_IGNORED_AUTHORED_KEYS["Status"],
    "deprecated_at": _ISSUE_BODY_IGNORED_AUTHORED_KEYS["Deprecated At"],
}

# Required + optional keys of a full header and a cross-reference header; status and deprecated_at are
# recognised only to be flagged.
_FULL_HEADER_KEYS = {
    "surface_type",
    "route",
    "owners",
    "purpose",
    "user_stories",
    "functionalities",
    "external_dependencies",
    "feature_dependencies",
    "page-object",
    "wizard-steps",
    "stub-reason",
    "deprecation_reason",
    "superseded_by",
    "notes",
    "status",
    "deprecated_at",
}
_CROSS_REFERENCE_KEYS = {
    "parent-feat",
    "route",
    "owners",
    "purpose",
    "page-object",
    "functionalities",
    "notes",
    "status",
    "deprecated_at",
}
# The keys whose value is a bullet list, whose items' wrapped lines are never read as a key and whose
# dropped text is reported. Declared in `normalize.py`, which frames the header by them, so the normaliser
# and this parser cannot disagree about which key holds a list. `notes:` is the canon's only one; its
# authored key is also its contract field, unlike the hyphenated keys above. A full header's notes are its
# Feature's; a cross-reference header's notes are its page's own (`PageRef.notes`), never merged into the Feature's.
_BULLET_KEYS = PO_BULLET_KEYS
# Keys whose value is one token - a surface type, a route, a file, an id: a further line is an AUTHORING_ERROR and
# is not read. Text and id lists may wrap.
_SINGLE_VALUE_KEYS = frozenset(
    {"surface_type", "route", "page-object", "parent-feat", "status", "deprecated_at", "superseded_by"}
)


@dataclass
class PageObjectResult:
    """One PageObject file's parse result. `entity` is only populated for a full header; a
    cross-reference header instead carries `parent_feat`, the Feature id its `page_ref`
    belongs to - the collector appends `page_ref`, with the page's own notes, onto that
    Feature's `pages` list."""

    page_ref: PageRef
    entity: Optional[ParsedEntity] = None
    parent_feat: Optional[str] = None


def _extract_title(frame: Frame) -> Optional[str]:
    title = None if frame.title is None else extract_living_doc_title([frame.title.line.raw])
    if title is None:
        return None
    # Strip an optional "[cross-reference]" suffix - cosmetic; parent-feat: is the authoritative format signal.
    return re.sub(r"\s*\[cross-reference]\s*$", "", title)


@dataclass
class _ReadKeys:
    """`_read_keys`' result: each known key's raw lines, a bullet key's lines' input numbers, each key's own
    line number, the unrecognised keys with theirs, and the warnings for lines no field reads."""

    raw_values: dict[str, list[str]] = field(default_factory=dict)
    numbers: dict[str, list[int]] = field(default_factory=dict)
    key_lines: dict[str, int] = field(default_factory=dict)
    unrecognised: list[tuple[str, int]] = field(default_factory=list)
    warnings: list[ContractWarning] = field(default_factory=list)


def _read_keys(keys: list[Section], known_keys: set[str], entity_id: str) -> _ReadKeys:
    """Each known key's raw lines - the key's own value first, then every line of its section - plus the
    unrecognised keys. The lines keep their indent, so a bullet key's list can be read from them; a scalar key's
    further lines are read by its value's type (`accounting.scalar_lines`), and `_joined` collapses them."""
    result = _ReadKeys()
    for key in keys:
        if key.name not in known_keys:
            result.unrecognised.append((key.name, key.opener.number))
            continue
        result.key_lines[key.name] = key.opener.number
        if key.name in _BULLET_KEYS:
            lines = [opening_value(key.opener)] + [framed.line.raw.rstrip() for framed in key.lines]
            result.numbers[key.name] = [key.opener.number] + [framed.number for framed in key.lines]
        else:
            lines, key_warnings = scalar_lines(key, key.name in _SINGLE_VALUE_KEYS, entity_id)
            result.warnings.extend(key_warnings)
        result.raw_values[key.name] = [without_comment_close(line) for line in lines]
    return result


def _joined(lines: list[str]) -> str:
    """A scalar key's lines as one value: each stripped, blanks dropped, joined with a space."""
    return " ".join(part for part in (line.strip() for line in lines) if part)


def parse_page_object(text: str) -> tuple[Optional[PageObjectResult], list[ContractWarning]]:
    """Parses one PageObject file's living-doc header. Returns `(None, [MISSING_ENTITY_ID])`
    when the banner carries no parseable title/id.
    """
    _, frame = normalize_framed(text, SourceFormat.PAGE_OBJECT, "DocumentedFeature")

    title = _extract_title(frame)
    if title is None:
        return None, [missing_title(frame, "PageObject"), *structural_warnings(frame, "", UNCLOSED_COMMENT)]

    entity_id, id_warnings = derive_entity_id(title)
    if entity_id is None:
        return None, at_title(id_warnings, frame)

    # `parent-feat:` picks the key set, so it is read from the frame's key sections like any other key: a
    # note's wrapped line may say `parent-feat:` and is still only that note's text (#168).
    frame, repeated = first_occurrences(frame, entity_id)
    keys = sections(frame)
    is_cross_reference = any(key.name == "parent-feat" for key in keys)
    known_keys = _CROSS_REFERENCE_KEYS if is_cross_reference else _FULL_HEADER_KEYS
    read = _read_keys(keys, known_keys, entity_id)
    raw_values = read.raw_values
    values = {key: _joined(lines) for key, lines in raw_values.items() if key not in _BULLET_KEYS}

    # A cross-reference header may open with prose before its first key; the canon allows it.
    warnings: list[ContractWarning] = structural_warnings(frame, entity_id) + repeated + read.warnings
    warnings.extend(unplaced_lines(frame, entity_id, skip_intro=is_cross_reference))
    for key, number in read.unrecognised:
        warnings.append(
            ContractWarning(
                code=Code.IGNORED_AUTHORED_KEY.name,
                message=f"'{key}:' is not a field this contract carries.",
                context=f"entity_id={entity_id!r} line_no={number}",
            )
        )
    for key, lines in raw_values.items():
        if key in _BULLET_KEYS:
            warnings.extend(bullet_field_warnings(entity_id, key, lines, read.numbers[key]))
    for key, reason in IGNORED_AUTHORED_KEYS.items():
        if key in values:
            warnings.append(
                ContractWarning(
                    code=Code.IGNORED_AUTHORED_KEY.name,
                    message=reason,
                    context=f"entity_id={entity_id!r} line_no={read.key_lines[key]} key='{key}:'",
                )
            )

    if is_cross_reference:
        page_ref = PageRef(
            is_primary=False,
            route=values.get("route", ""),
            page_object=values.get("page-object", ""),
            owners=split_id_list(values.get("owners")),
            purpose=values.get("purpose", ""),
            functionalities=split_id_list(values.get("functionalities")),
            notes=extract_bullets(raw_values.get("notes", [])),
        )
        return PageObjectResult(page_ref=page_ref, entity=None, parent_feat=values.get("parent-feat")), warnings

    page_ref = PageRef(
        is_primary=True,
        route=values.get("route", ""),
        page_object=values.get("page-object", ""),
        owners=split_id_list(values.get("owners")),
        purpose=values.get("purpose", ""),
        functionalities=[],
    )
    entity = ParsedEntity(
        entity_id=entity_id,
        type="DocumentedFeature",
        title=title,
        purpose=values.get("purpose"),
        surface_type=values.get("surface_type"),
        owners=split_id_list(values.get("owners")),
        user_stories=split_id_list(values.get("user_stories")),
        functionalities=split_id_list(values.get("functionalities")),
        external_dependencies=split_id_list(values.get("external_dependencies")),
        feature_dependencies=split_id_list(values.get("feature_dependencies")),
        stub_reason=values.get("stub-reason"),
        deprecation_reason=values.get("deprecation_reason"),
        superseded_by=values.get("superseded_by"),
        wizard_steps=split_id_list(values.get("wizard-steps"), sep=" · "),
        notes=extract_bullets(raw_values.get("notes", [])),
        pages=[page_ref],
    )
    return PageObjectResult(page_ref=page_ref, entity=entity, parent_feat=None), warnings
