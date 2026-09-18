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
GitHub issue-body parsing (living-doc's docs/examples/README.md, "GitHub issue-body layout
(canonical)"): `##` sections mapped 1:1 onto the shared entity fields, plus `###
AC:<id> (v<version> - <state>)` sub-headings parsed by `ac_grammar` alone.

Also defines `ParsedEntity`, the pre-`Entity` shape every parser in this package returns:
every `Entity` field except `source_ref` (collector-filled, never parser-filled - see
docs/contracts.md's "Entity identity") and with `state`/`state_origin` optional, since
those are only settled once `status.derive_statuses` has run over the whole collected set.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from living_doc_utilities.authoring.ac_grammar import parse_acceptance_criteria
from living_doc_utilities.authoring.identity import derive_entity_id
from living_doc_utilities.authoring.normalize import SourceFormat, compute_fence_flags, normalize, normalize_title
from living_doc_utilities.contracts.common import AcceptanceCriterion, DocType
from living_doc_utilities.contracts.doc_entities import PageRef
from living_doc_utilities.contracts.envelope import ContractWarning

UNKNOWN_SECTION = "UNKNOWN_SECTION"
IGNORED_AUTHORED_KEY = "IGNORED_AUTHORED_KEY"

# Glossary-defined headings that map to no model field, with the reason each is dropped
# rather than stored (docs/contracts.md, "State and `state_origin`"). A key found here
# still produces an `IGNORED_AUTHORED_KEY` warning - it is a documented drop, not a silent
# one. Every other glossary-defined issue-body heading maps to a real field instead (see
# tests/contracts/test_authored_field_set.py).
IGNORED_AUTHORED_KEYS = {
    "Status": "Feature state is derived; use `stub-reason:` for an uninstrumented surface",
}


@dataclass
class ParsedEntity:
    """Every `Entity` field except `source_ref`. `state` is `None` until authored (issue
    body / feature header) or derived (`status.derive_statuses`) fills it in; `state_origin`
    likewise. Built up field-by-field by whichever authoring-format parser produced it -
    a given parser only ever sets the subset of fields its format carries.
    """

    entity_id: str
    type: DocType
    title: str
    narrative: Optional[str] = None
    purpose: Optional[str] = None
    source: Optional[str] = None
    state: Optional[str] = None
    state_origin: Optional[str] = None
    business_value: list[str] = field(default_factory=list)
    acceptance_criteria: list[AcceptanceCriterion] = field(default_factory=list)
    preconditions: list[str] = field(default_factory=list)
    not_in_scope: list[str] = field(default_factory=list)
    deprecated_at: Optional[str] = None
    deprecation_reason: Optional[str] = None
    superseded_by: Optional[str] = None
    surface_type: Optional[str] = None
    owners: list[str] = field(default_factory=list)
    user_stories: list[str] = field(default_factory=list)
    functionalities: list[str] = field(default_factory=list)
    external_dependencies: list[str] = field(default_factory=list)
    stub_reason: Optional[str] = None
    wizard_steps: list[str] = field(default_factory=list)
    pages: list[PageRef] = field(default_factory=list)
    parent: Optional[str] = None
    func_type: Optional[str] = None
    rationale: Optional[str] = None


# --- section kinds -------------------------------------------------------------------

_KIND_PROSE = "prose"  # free-flowing paragraph, joined into one string
_KIND_SCALAR = "scalar"  # a single value, possibly wrapped across lines
_KIND_BULLETS = "bullets"  # a `- ...` list, one entry per bullet
_KIND_PROSE_BULLET = "prose_bullet"  # a single `- ...` value (still one string field)
_KIND_ID_LIST = "id_list"  # a comma-separated list of ids/names, or "none"
_KIND_AC = "ac"  # the "## Acceptance Criteria" heading itself - content parsed separately
_KIND_IGNORED_STATUS = "ignored_status"  # "## Status" on a Feature - not a real field


@dataclass(frozen=True)
class _SectionSpec:
    field_name: Optional[str]
    kind: str


_DEPRECATION_SECTIONS = {
    "deprecated_at": _SectionSpec("deprecated_at", _KIND_SCALAR),
    "deprecation_reason": _SectionSpec("deprecation_reason", _KIND_SCALAR),
    "superseded_by": _SectionSpec("superseded_by", _KIND_SCALAR),
}

# heading slug (normalize.py's `_slugify_section`: lowercase, spaces/underscores -> "_") ->
# spec, per entity type. Mirrors tests/contracts/test_authored_field_set.py exactly.
_SECTIONS_BY_TYPE: dict[DocType, dict[str, _SectionSpec]] = {
    "DocumentedUserStory": {
        "description": _SectionSpec("narrative", _KIND_PROSE),
        "status": _SectionSpec("state", _KIND_SCALAR),
        "business_value": _SectionSpec("business_value", _KIND_BULLETS),
        "acceptance_criteria": _SectionSpec(None, _KIND_AC),
        "preconditions": _SectionSpec("preconditions", _KIND_BULLETS),
        "not_in_scope": _SectionSpec("not_in_scope", _KIND_BULLETS),
        **_DEPRECATION_SECTIONS,
    },
    "DocumentedFeature": {
        "description": _SectionSpec("purpose", _KIND_PROSE),
        "status": _SectionSpec(None, _KIND_IGNORED_STATUS),
        "surface_type": _SectionSpec("surface_type", _KIND_SCALAR),
        "owners": _SectionSpec("owners", _KIND_ID_LIST),
        "user_stories": _SectionSpec("user_stories", _KIND_ID_LIST),
        "functionalities": _SectionSpec("functionalities", _KIND_ID_LIST),
        "external_dependencies": _SectionSpec("external_dependencies", _KIND_ID_LIST),
        **_DEPRECATION_SECTIONS,
    },
    "DocumentedFunctionality": {
        "description": _SectionSpec("narrative", _KIND_PROSE),
        "status": _SectionSpec("state", _KIND_SCALAR),
        "parent_feature": _SectionSpec("parent", _KIND_SCALAR),
        "func_type": _SectionSpec("func_type", _KIND_SCALAR),
        "acceptance_criteria": _SectionSpec(None, _KIND_AC),
        "rationale": _SectionSpec("rationale", _KIND_PROSE_BULLET),
        "preconditions": _SectionSpec("preconditions", _KIND_BULLETS),
        "not_in_scope": _SectionSpec("not_in_scope", _KIND_BULLETS),
        **_DEPRECATION_SECTIONS,
    },
}


# --- markdown H2 section splitting -----------------------------------------------------

_HEADING_RE = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<text>.*)$")


def _slugify(text: str) -> str:
    return re.sub(r"[\s_]+", "_", text.strip().lower())


def _split_h2_sections(lines: list[str]) -> list[tuple[str, str, list[str]]]:
    """Every exactly-`##` heading outside a fenced code block, as `(slug, heading_text,
    content_lines)` - content runs up to (not including) the next such heading."""
    fence_flags = compute_fence_flags(lines)
    sections: list[tuple[str, str, list[str]]] = []
    current: Optional[list[str]] = None
    for line, fenced in zip(lines, fence_flags, strict=True):
        if not fenced:
            heading_m = _HEADING_RE.match(line)
            if heading_m and len(heading_m.group("hashes")) == 2:
                current = []
                sections.append((_slugify(heading_m.group("text")), heading_m.group("text").strip(), current))
                continue
        if current is not None:
            current.append(line)
    return sections


# --- content extraction per section kind -----------------------------------------------

_BULLET_RE = re.compile(r"^-\s?(?P<text>.*)$")


def extract_bullets(lines: list[str]) -> list[str]:
    """Extracts a `- ...` list's items from already-normalised `lines`, joining a
    following non-bullet line onto the previous item as its hard-wrap continuation.
    Shared by every authoring-format parser that carries a bullet section (issue-body
    `##` sections here, feature-header `key:` sections in `feature_header.py`) - the one
    place this join rule is implemented."""
    items: list[str] = []
    for raw in lines:
        stripped = raw.strip()
        if not stripped:
            continue
        bullet_m = _BULLET_RE.match(stripped)
        if bullet_m:
            items.append(bullet_m.group("text").strip())
        elif items:
            items[-1] = f"{items[-1]} {stripped}".strip()
    return items


def _extract_prose(lines: list[str]) -> Optional[str]:
    parts = [ln.strip() for ln in lines if ln.strip()]
    return " ".join(parts) if parts else None


def _extract_prose_bullet(lines: list[str]) -> Optional[str]:
    items = extract_bullets(lines)
    return " ".join(items) if items else None


def _extract_id_list(lines: list[str]) -> list[str]:
    joined = _extract_prose(lines)
    if not joined or joined.strip().lower() == "none":
        return []
    return [token.strip() for token in joined.split(",") if token.strip()]


_EXTRACTORS = {
    _KIND_PROSE: _extract_prose,
    _KIND_SCALAR: _extract_prose,
    _KIND_BULLETS: extract_bullets,
    _KIND_PROSE_BULLET: _extract_prose_bullet,
    _KIND_ID_LIST: _extract_id_list,
}


def parse_issue_body(
    text: str, title: str, entity_type: DocType
) -> tuple[Optional[ParsedEntity], list[ContractWarning]]:
    """Parses a GitHub issue body into a `ParsedEntity`. `title` is the issue title (e.g.
    `US-001 · Customer Login`); its entity-id prefix becomes `entity_id`, and (normalised)
    it becomes `title`. Returns `(None, [MISSING_ENTITY_ID])` when the title has no
    parseable id - nothing else about the body is inspected in that case.
    """
    normalized_title, _title_changes = normalize_title(title)
    entity_id, id_warnings = derive_entity_id(normalized_title)
    if entity_id is None:
        return None, id_warnings

    warnings: list[ContractWarning] = []
    normalized = normalize(text, SourceFormat.ISSUE_BODY, entity_type)
    spec_map = _SECTIONS_BY_TYPE[entity_type]

    fields: dict[str, Any] = {}
    for slug, heading_text, content in _split_h2_sections(normalized.lines):
        spec = spec_map.get(slug)
        if spec is None:
            warnings.append(
                ContractWarning(
                    code=UNKNOWN_SECTION,
                    message=f"Unrecognised heading '## {heading_text}'.",
                    context=f"entity_id={entity_id!r}",
                )
            )
            continue
        if spec.kind == _KIND_AC:
            continue
        if spec.kind == _KIND_IGNORED_STATUS:
            warnings.append(
                ContractWarning(
                    code=IGNORED_AUTHORED_KEY,
                    message=IGNORED_AUTHORED_KEYS["Status"],
                    context=f"entity_id={entity_id!r} heading='## {heading_text}'",
                )
            )
            continue
        assert spec.field_name is not None  # every other kind carries a field
        fields[spec.field_name] = _EXTRACTORS[spec.kind](content)

    acceptance_criteria, ac_warnings = parse_acceptance_criteria(normalized.text, entity_id)
    warnings.extend(ac_warnings)

    parsed = ParsedEntity(
        entity_id=entity_id,
        type=entity_type,
        title=normalized_title,
        acceptance_criteria=acceptance_criteria,
        **fields,
    )
    return parsed, warnings
