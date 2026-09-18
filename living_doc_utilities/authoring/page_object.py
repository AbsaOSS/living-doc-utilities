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
PageObject header parsing for a Feature (living-doc's docs/guides/living-doc-header-types.md,
"Feature in a PageObject File"). A PageObject carries no status - only `stub-reason:`, the
"documented but not yet instrumented" marker. A full header describes the whole Feature
plus its own page; a cross-reference header (`parent-feat:` present) only describes its own
page, scoped to an already-described Feature.
"""

import re
from dataclasses import dataclass
from typing import Optional

from living_doc_utilities.authoring.identity import MISSING_ENTITY_ID, derive_entity_id
from living_doc_utilities.authoring.issue_body import IGNORED_AUTHORED_KEY, ParsedEntity
from living_doc_utilities.authoring.normalize import SourceFormat, normalize
from living_doc_utilities.contracts.doc_entities import PageRef
from living_doc_utilities.contracts.envelope import ContractWarning

_LINE_RE = re.compile(r"^\s*\*\s?(?P<content>.*)$")
_BANNER_CONTENT_RE = re.compile(r"^=+\s*(\*/)?\s*$")
_LIVING_DOC_TITLE_RE = re.compile(r"LIVING DOC\s*—\s*(?P<title>.+?)\s*$")
_GENERIC_KEY_RE = re.compile(r"^(?P<key>[a-zA-Z][a-zA-Z0-9_-]*)\s*:\s*(?P<val>.*)$")

# A glossary-defined key that maps to no model field, with the reason it is dropped rather
# than stored (docs/contracts.md, "State and `state_origin`") - a documented drop, not a
# silent one. Every other PageObject header key maps to a real field instead (see
# tests/contracts/test_authored_field_set.py).
IGNORED_AUTHORED_KEYS = {
    "status": "Feature state is derived; use `stub-reason:` for an uninstrumented surface",
}

# Required + optional keys of a full header, and of a cross-reference header (living-doc's
# header-types.md tables). `status` is recognised - only to be reported as ignored.
_FULL_HEADER_KEYS = {
    "surface_type",
    "route",
    "owners",
    "purpose",
    "user_stories",
    "functionalities",
    "external_dependencies",
    "page-object",
    "wizard-steps",
    "stub-reason",
    "status",
}
_CROSS_REFERENCE_KEYS = {
    "parent-feat",
    "route",
    "owners",
    "purpose",
    "page-object",
    "functionalities",
    "status",
}


@dataclass
class PageObjectResult:
    """One PageObject file's parse result. `entity` is only populated for a full header
    (it describes the whole Feature); a cross-reference header instead carries `parent_feat`,
    the id of the Feature its `page_ref` belongs to - the collector is responsible for
    appending `page_ref` onto that already-parsed Feature's `pages` list.
    """

    page_ref: PageRef
    entity: Optional[ParsedEntity] = None
    parent_feat: Optional[str] = None


def _content_lines(lines: list[str]) -> list[str]:
    contents = []
    for raw in lines:
        line_m = _LINE_RE.match(raw)
        if line_m:
            contents.append(line_m.group("content").rstrip())
    return contents


def _extract_title(contents: list[str]) -> Optional[str]:
    for content in contents:
        title_m = _LIVING_DOC_TITLE_RE.search(content)
        if title_m:
            title = title_m.group("title").strip()
            # Strip an optional "[cross-reference]" suffix - `parent-feat:` is the
            # authoritative format signal, this is just cosmetic on the title line.
            return re.sub(r"\s*\[cross-reference]\s*$", "", title)
    return None


def _parse_keys(contents: list[str], known_keys: set[str]) -> tuple[dict[str, str], list[str]]:
    key_re = re.compile(
        r"^(?P<key>"
        + "|".join(re.escape(k) for k in sorted(known_keys, key=len, reverse=True))
        + r")\s*:\s*(?P<val>.*)$"
    )
    values: dict[str, str] = {}
    current_key: Optional[str] = None
    unrecognised: list[str] = []

    for content in contents:
        stripped = content.strip()
        if stripped == "" or _BANNER_CONTENT_RE.match(stripped) or "LIVING DOC" in content:
            current_key = None
            continue

        key_m = key_re.match(stripped)
        if key_m:
            current_key = key_m.group("key")
            values[current_key] = key_m.group("val").strip()
            continue

        generic_m = _GENERIC_KEY_RE.match(stripped)
        if generic_m and generic_m.group("key") not in known_keys:
            unrecognised.append(generic_m.group("key"))
            current_key = None
            continue

        if current_key is not None:
            values[current_key] = f"{values[current_key]} {stripped}".strip()

    return values, unrecognised


def _split_list(value: Optional[str], sep: str = ",") -> list[str]:
    if not value or value.strip().lower() == "none":
        return []
    return [token.strip() for token in value.split(sep) if token.strip()]


def parse_page_object(text: str) -> tuple[Optional[PageObjectResult], list[ContractWarning]]:
    """Parses one PageObject file's living-doc header. Returns `(None, [MISSING_ENTITY_ID])`
    when the banner carries no parseable title/id.
    """
    normalized = normalize(text, SourceFormat.PAGE_OBJECT, "DocumentedFeature")
    contents = _content_lines(normalized.lines)

    title = _extract_title(contents)
    if title is None:
        return None, [
            ContractWarning(
                code=MISSING_ENTITY_ID,
                message="PageObject banner carries no 'LIVING DOC — ...' title line.",
                context="title=''",
            )
        ]

    entity_id, id_warnings = derive_entity_id(title)
    if entity_id is None:
        return None, id_warnings

    is_cross_reference = False
    for content in contents:
        generic_m = _GENERIC_KEY_RE.match(content.strip())
        if generic_m and generic_m.group("key") == "parent-feat":
            is_cross_reference = True
            break
    known_keys = _CROSS_REFERENCE_KEYS if is_cross_reference else _FULL_HEADER_KEYS
    values, unrecognised = _parse_keys(contents, known_keys)

    warnings: list[ContractWarning] = []
    for key in unrecognised:
        warnings.append(
            ContractWarning(
                code=IGNORED_AUTHORED_KEY,
                message=f"'{key}:' is not a field this contract carries.",
                context=f"entity_id={entity_id!r}",
            )
        )
    if "status" in values:
        warnings.append(
            ContractWarning(
                code=IGNORED_AUTHORED_KEY,
                message=IGNORED_AUTHORED_KEYS["status"],
                context=f"entity_id={entity_id!r} key='status:'",
            )
        )

    if is_cross_reference:
        page_ref = PageRef(
            is_primary=False,
            route=values.get("route", ""),
            page_object=values.get("page-object", ""),
            owners=[],
            purpose=values.get("purpose", ""),
            functionalities=_split_list(values.get("functionalities")),
        )
        return PageObjectResult(page_ref=page_ref, entity=None, parent_feat=values.get("parent-feat")), warnings

    page_ref = PageRef(
        is_primary=True,
        route=values.get("route", ""),
        page_object=values.get("page-object", ""),
        owners=_split_list(values.get("owners")),
        purpose=values.get("purpose", ""),
        functionalities=[],
    )
    entity = ParsedEntity(
        entity_id=entity_id,
        type="DocumentedFeature",
        title=title,
        purpose=values.get("purpose"),
        surface_type=values.get("surface_type"),
        owners=_split_list(values.get("owners")),
        user_stories=_split_list(values.get("user_stories")),
        functionalities=_split_list(values.get("functionalities")),
        external_dependencies=_split_list(values.get("external_dependencies")),
        stub_reason=values.get("stub-reason"),
        wizard_steps=_split_list(values.get("wizard-steps"), sep=" · "),
        pages=[page_ref],
    )
    return PageObjectResult(page_ref=page_ref, entity=entity, parent_feat=None), warnings
