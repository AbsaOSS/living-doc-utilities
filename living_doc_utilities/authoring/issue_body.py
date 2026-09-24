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
every `Entity` field except `source_ref`, `tags` and `timestamps` (collector-filled, never
parser-filled - see docs/contracts.md's "Entity identity") and with `state`/`state_origin`
optional, since those are only settled once `status.derive_statuses` has run over the whole
collected set.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, Optional

from pydantic import ValidationError

from living_doc_utilities.authoring.ac_grammar import parse_acceptance_criteria
from living_doc_utilities.authoring.identity import derive_entity_id
from living_doc_utilities.authoring.normalize import (
    _BULLET_RE,
    _MD_HEADING_RE,
    SourceFormat,
    _slugify_section,
    compute_fence_flags,
    normalize,
    normalize_title,
)
from living_doc_utilities.contracts.codes import Code
from living_doc_utilities.contracts.common import AcceptanceCriterion, DocType, LifecycleState, StateOrigin
from living_doc_utilities.contracts.doc_entities import EntityContent
from living_doc_utilities.contracts.envelope import ContractWarning

# Glossary-defined headings that map to no model field, with the reason each is dropped
# rather than stored (docs/contracts.md, "State and `state_origin`"). A key found here
# still produces an `IGNORED_AUTHORED_KEY` warning - it is a documented drop, not a silent
# one. Every other glossary-defined issue-body heading maps to a real field instead (see
# tests/contracts/test_authored_field_set.py).
IGNORED_AUTHORED_KEYS = {
    "Status": "Feature state is derived; use `stub-reason:` for an uninstrumented surface",
}


class ParsedEntity(EntityContent):
    """Every `Entity` field except `source_ref`, `tags` and `timestamps`: `EntityContent`'s
    authored fields plus this entity's identity. `state` is `None` until authored (issue
    body / feature header) or derived (`status.derive_statuses`) fills it in; `state_origin`
    likewise. Built up field-by-field by whichever authoring-format parser produced it -
    a given parser only ever sets the subset of fields its format carries.
    """

    entity_id: str
    type: DocType
    title: str
    state: Optional[LifecycleState] = None
    state_origin: Optional[StateOrigin] = None


# --- section kinds -------------------------------------------------------------------


class _SectionKind(Enum):
    """What shape a section's raw lines take, and so how `_EXTRACTORS` turns them into a
    field value - or, for the sentinel members below, that they carry no field at all."""

    PROSE = auto()  # free-flowing paragraph, joined into one string
    SCALAR = auto()  # a single value, possibly wrapped across lines
    BULLETS = auto()  # a `- ...` list, one entry per bullet
    PROSE_BULLET = auto()  # a single `- ...` value (still one string field)
    ID_LIST = auto()  # a comma-separated list of ids/names, or "none"
    AC = auto()  # the "## Acceptance Criteria" heading itself - content parsed separately
    IGNORED_STATUS = auto()  # "## Status" on a Feature - not a real field
    IGNORED = auto()  # a declared key whose content is parsed elsewhere (feature_header's "acceptance_criteria:")


@dataclass(frozen=True)
class _SectionSpec:
    field_name: Optional[str]
    kind: _SectionKind


_DEPRECATION_SECTIONS = {
    "deprecated_at": _SectionSpec("deprecated_at", _SectionKind.SCALAR),
    "deprecation_reason": _SectionSpec("deprecation_reason", _SectionKind.SCALAR),
    "superseded_by": _SectionSpec("superseded_by", _SectionKind.SCALAR),
}

# heading slug (normalize.py's `_slugify_section`: lowercase, spaces/underscores -> "_") ->
# spec, per entity type. Mirrors tests/contracts/test_authored_field_set.py exactly.
_SECTIONS_BY_TYPE: dict[DocType, dict[str, _SectionSpec]] = {
    "DocumentedUserStory": {
        "description": _SectionSpec("narrative", _SectionKind.PROSE),
        "status": _SectionSpec("state", _SectionKind.SCALAR),
        "business_value": _SectionSpec("business_value", _SectionKind.BULLETS),
        "acceptance_criteria": _SectionSpec(None, _SectionKind.AC),
        "preconditions": _SectionSpec("preconditions", _SectionKind.BULLETS),
        "not_in_scope": _SectionSpec("not_in_scope", _SectionKind.BULLETS),
        **_DEPRECATION_SECTIONS,
    },
    "DocumentedFeature": {
        "description": _SectionSpec("purpose", _SectionKind.PROSE),
        "status": _SectionSpec(None, _SectionKind.IGNORED_STATUS),
        "surface_type": _SectionSpec("surface_type", _SectionKind.SCALAR),
        "owners": _SectionSpec("owners", _SectionKind.ID_LIST),
        "user_stories": _SectionSpec("user_stories", _SectionKind.ID_LIST),
        "functionalities": _SectionSpec("functionalities", _SectionKind.ID_LIST),
        "external_dependencies": _SectionSpec("external_dependencies", _SectionKind.ID_LIST),
        **_DEPRECATION_SECTIONS,
    },
    "DocumentedFunctionality": {
        "description": _SectionSpec("narrative", _SectionKind.PROSE),
        "status": _SectionSpec("state", _SectionKind.SCALAR),
        "parent_feature": _SectionSpec("parent", _SectionKind.SCALAR),
        "func_type": _SectionSpec("func_type", _SectionKind.SCALAR),
        "acceptance_criteria": _SectionSpec(None, _SectionKind.AC),
        "rationale": _SectionSpec("rationale", _SectionKind.PROSE_BULLET),
        "preconditions": _SectionSpec("preconditions", _SectionKind.BULLETS),
        "not_in_scope": _SectionSpec("not_in_scope", _SectionKind.BULLETS),
        **_DEPRECATION_SECTIONS,
    },
}


# --- markdown H2 section splitting -----------------------------------------------------


def _split_h2_sections(lines: list[str]) -> list[tuple[str, str, list[str]]]:
    """Every exactly-`##` heading outside a fenced code block, as `(slug, heading_text,
    content_lines)` - content runs up to (not including) the next such heading."""
    fence_flags = compute_fence_flags(lines)
    sections: list[tuple[str, str, list[str]]] = []
    current: Optional[list[str]] = None
    for line, fenced in zip(lines, fence_flags, strict=True):
        if not fenced:
            heading_m = _MD_HEADING_RE.match(line)
            if heading_m and len(heading_m.group("hashes")) == 2:
                current = []
                sections.append((_slugify_section(heading_m.group("text")), heading_m.group("text").strip(), current))
                continue
        if current is not None:
            current.append(line)
    return sections


# --- content extraction per section kind -----------------------------------------------


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


def split_id_list(value: Optional[str], sep: str = ",") -> list[str]:
    """Splits an already-joined `sep`-separated id/name list into its items, or `[]` for
    a blank or literal "none" value. Shared with page_object.py, whose header keys carry
    the same list shape already joined to one string (there with `sep=" · "` for
    wizard-steps)."""
    if not value or value.strip().lower() == "none":
        return []
    return [token.strip() for token in value.split(sep) if token.strip()]


def _extract_id_list(lines: list[str]) -> list[str]:
    return split_id_list(_extract_prose(lines))


_EXTRACTORS: dict[_SectionKind, Callable[[list[str]], Any]] = {
    _SectionKind.PROSE: _extract_prose,
    _SectionKind.SCALAR: _extract_prose,
    _SectionKind.BULLETS: extract_bullets,
    _SectionKind.PROSE_BULLET: _extract_prose_bullet,
    _SectionKind.ID_LIST: _extract_id_list,
}


def _build_parsed_entity(
    entity_id: str,
    entity_type: DocType,
    title: str,
    acceptance_criteria: list[AcceptanceCriterion],
    fields: dict[str, Any],
) -> tuple[ParsedEntity, list[ContractWarning]]:
    """Constructs a `ParsedEntity` from already-extracted field values, shared by
    `parse_issue_body` and `feature_header.parse_feature_header` - the two parsers that
    build one from free-form authored text. `state` is the only field that can fail the
    contract's own validation here (it narrows to `LifecycleState`, everything else is an
    unconstrained `str`/`list[str]`); an authored value the reader mistyped must become a
    warning, not an exception - every other unrecognised authored value in this contract
    does (docs/contracts.md, section 5), and pydantic validates eagerly on construction.
    """
    try:
        return (
            ParsedEntity(
                entity_id=entity_id, type=entity_type, title=title, acceptance_criteria=acceptance_criteria, **fields
            ),
            [],
        )
    except ValidationError as exc:
        warnings: list[ContractWarning] = []
        for error in exc.errors():
            field_path = ".".join(str(part) for part in error["loc"])
            fields.pop(field_path, None)
            warnings.append(
                ContractWarning(
                    code=Code.MALFORMED_STATUS.name,
                    message=f"Authored '{field_path}' value {error['input']!r} failed validation: {error['msg']}",
                    context=f"entity_id={entity_id!r}",
                )
            )
        parsed = ParsedEntity(
            entity_id=entity_id, type=entity_type, title=title, acceptance_criteria=acceptance_criteria, **fields
        )
        return parsed, warnings


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
                    code=Code.UNKNOWN_SECTION.name,
                    message=f"Unrecognised heading '## {heading_text}'.",
                    context=f"entity_id={entity_id!r}",
                )
            )
            continue
        if spec.kind == _SectionKind.AC:
            continue
        if spec.kind == _SectionKind.IGNORED_STATUS:
            warnings.append(
                ContractWarning(
                    code=Code.IGNORED_AUTHORED_KEY.name,
                    message=IGNORED_AUTHORED_KEYS["Status"],
                    context=f"entity_id={entity_id!r} heading='## {heading_text}'",
                )
            )
            continue
        assert spec.field_name is not None  # every other kind carries a field
        fields[spec.field_name] = _EXTRACTORS[spec.kind](content)

    acceptance_criteria, ac_warnings = parse_acceptance_criteria(normalized.text, entity_id)
    warnings.extend(ac_warnings)

    parsed, build_warnings = _build_parsed_entity(entity_id, entity_type, normalized_title, acceptance_criteria, fields)
    warnings.extend(build_warnings)
    return parsed, warnings
