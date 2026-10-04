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
GitHub issue-body parsing: `##` sections map 1:1 onto the shared entity fields, plus `###
AC:<id> (v<version> - <state>)` sub-headings parsed by `ac_grammar` alone. Also defines
`ParsedEntity`, the pre-`Entity` shape every parser in this package returns.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, Optional

from pydantic import ValidationError

from living_doc_utilities.authoring.ac_grammar import parse_frame_criteria
from living_doc_utilities.authoring.accounting import (
    duplicate_sections,
    nesting_github_reads_as_siblings,
    structural_warnings,
    unplaced_lines,
)
from living_doc_utilities.authoring.framing import Frame, IndentedLine, indented, sections
from living_doc_utilities.authoring.identity import derive_entity_id
from living_doc_utilities.authoring.normalize import (
    _BULLET_RE,
    ItemText,
    SourceFormat,
    normalize_framed,
    normalize_title,
)
from living_doc_utilities.contracts.codes import Code
from living_doc_utilities.contracts.common import AcceptanceCriterion, DocType, LifecycleState, StateOrigin
from living_doc_utilities.contracts.doc_entities import EntityContent
from living_doc_utilities.contracts.envelope import ContractWarning

# Glossary headings that map to no field - a documented drop; still warns IGNORED_AUTHORED_KEY, not silent.
IGNORED_AUTHORED_KEYS = {
    "Status": "Feature state is derived; use `stub-reason:` for an uninstrumented surface",
    "Deprecated At": "Feature has no deprecation date",
}


class ParsedEntity(EntityContent):
    """Every `Entity` field except `source_ref`, `tags` and `timestamps`: `EntityContent`'s
    authored fields plus identity. `state`/`state_origin` stay `None` until authored or
    derived; each parser sets only the subset of fields its format carries."""

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
    # A declared heading that maps to no field - `field_name` holds its `IGNORED_AUTHORED_KEYS` lookup key,
    # not a contract field (e.g. "## Status"/"## Deprecated At" on a Feature).
    IGNORED_AUTHORED = auto()
    IGNORED = auto()  # a declared key whose content is parsed elsewhere (feature_header's "acceptance_criteria:")


@dataclass(frozen=True)
class _SectionSpec:
    field_name: Optional[str]
    kind: _SectionKind


# Authored on every entity type, a Feature included; neither drives the state.
_DEPRECATION_SECTIONS = {
    "deprecation_reason": _SectionSpec("deprecation_reason", _SectionKind.SCALAR),
    "superseded_by": _SectionSpec("superseded_by", _SectionKind.SCALAR),
}

# Authored on a User Story and a Functionality only; a Feature has none.
_DEPRECATED_AT_SECTION = {"deprecated_at": _SectionSpec("deprecated_at", _SectionKind.SCALAR)}

# Entity-level human context; every entity type carries it, and nothing ever reads a note's text.
_NOTES_SECTION = {"notes": _SectionSpec("notes", _SectionKind.BULLETS)}

# heading slug (`framing.py::_slugify_section`) -> spec, per entity type.
_SECTIONS_BY_TYPE: dict[DocType, dict[str, _SectionSpec]] = {
    "DocumentedUserStory": {
        "description": _SectionSpec("narrative", _SectionKind.PROSE),
        "status": _SectionSpec("state", _SectionKind.SCALAR),
        "business_value": _SectionSpec("business_value", _SectionKind.BULLETS),
        "acceptance_criteria": _SectionSpec(None, _SectionKind.AC),
        "preconditions": _SectionSpec("preconditions", _SectionKind.BULLETS),
        "not_in_scope": _SectionSpec("not_in_scope", _SectionKind.BULLETS),
        **_NOTES_SECTION,
        **_DEPRECATED_AT_SECTION,
        **_DEPRECATION_SECTIONS,
    },
    "DocumentedFeature": {
        "description": _SectionSpec("purpose", _SectionKind.PROSE),
        "status": _SectionSpec("Status", _SectionKind.IGNORED_AUTHORED),
        "deprecated_at": _SectionSpec("Deprecated At", _SectionKind.IGNORED_AUTHORED),
        "surface_type": _SectionSpec("surface_type", _SectionKind.SCALAR),
        "owners": _SectionSpec("owners", _SectionKind.ID_LIST),
        "user_stories": _SectionSpec("user_stories", _SectionKind.ID_LIST),
        "functionalities": _SectionSpec("functionalities", _SectionKind.ID_LIST),
        "external_dependencies": _SectionSpec("external_dependencies", _SectionKind.ID_LIST),
        "feature_dependencies": _SectionSpec("feature_dependencies", _SectionKind.ID_LIST),
        **_NOTES_SECTION,
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
        **_NOTES_SECTION,
        **_DEPRECATED_AT_SECTION,
        **_DEPRECATION_SECTIONS,
    },
}


# --- content extraction per section kind -----------------------------------------------


@dataclass
class _BulletList:
    items: list[str]
    # Lines whose indent fits no level of the list, dropped (the lines deeper than such a line with it), each with
    # its position in the list's lines.
    misindented: list[tuple[int, IndentedLine]]


def _read_bullets(lines: list[str]) -> _BulletList:
    """The one reading of a bullet list's already-normalised `lines`, by indent. The first `- `
    sets the item level. At that level a `- ` opens the next item and an unmarked line is joined
    onto the open item (the flat layout). A deeper line is the open item's own text (`ItemText`).
    A line shallower than the item level fits no level. Text before the first `- ` is skipped
    here; `unparsed_bullet_warning` reports it."""
    result = _BulletList([], [])
    item_level: Optional[int] = None
    item_text: Optional[ItemText] = None
    dropped: Optional[int] = None
    for index, line in enumerate(map(indented, lines)):
        if not line.text:
            continue
        if dropped is not None and line.indent > dropped:
            result.misindented.append((index, line))
            continue
        dropped = None
        bullet_m = _BULLET_RE.match(line.text)
        if item_level is None or item_text is None:
            if bullet_m:
                item_level = line.indent
                item_text = ItemText(line.indent)
                result.items.append(bullet_m.group("text").strip())
            continue
        if line.indent > item_level:
            fragment = item_text.fragment(line)
            if fragment is None:
                result.misindented.append((index, line))
            else:
                result.items[-1] = f"{result.items[-1]}{fragment}".strip()
        elif line.indent < item_level:
            result.misindented.append((index, line))
            dropped = line.indent
        elif bullet_m:
            item_text = ItemText(line.indent)
            result.items.append(bullet_m.group("text").strip())
        else:
            result.items[-1] = f"{result.items[-1]} {line.text}".strip()
    return result


def extract_bullets(lines: list[str]) -> list[str]:
    """Extracts a `- ...` list's items from already-normalised `lines`, one string per top-level
    item: a wrapped line is joined on, a nested item is kept inside its parent's string as
    extracted. Shared by every parser with a bullet section - the one place this rule lives."""
    return _read_bullets(lines).items


def _line_no(numbers: Optional[list[int]], index: int) -> str:
    """` line_no=<n>` for the line at `index` of a field's lines, when their input numbers are known."""
    return f" line_no={numbers[index]}" if numbers is not None else ""


def unparsed_bullet_warning(
    entity_id: str, field_name: str, lines: list[str], numbers: Optional[list[int]] = None
) -> list[ContractWarning]:
    """`[UNPARSED_BULLET_LINE]` when a bullet-list field's already-normalised `lines` hold text
    before its first `- ` bullet, else `[]`: `extract_bullets` has no item to join that text onto,
    so it drops it. Shared by every parser with a bullet field - the one place this warning is built.
    `field_name` is the contract field, never the authored key or heading; `numbers` are the lines' input
    numbers, and the warning names the first dropped one."""
    dropped: list[str] = []
    first: Optional[int] = None
    for index, raw in enumerate(lines):
        stripped = raw.strip()
        if not stripped:
            continue
        if _BULLET_RE.match(stripped):
            break
        first = index if first is None else first
        dropped.append(stripped)
    if first is None:
        return []
    return [
        ContractWarning(
            code=Code.UNPARSED_BULLET_LINE.name,
            message=f"'{field_name}' text outside a '- ' bullet was dropped: {' '.join(dropped)!r}.",
            context=f"entity_id={entity_id!r} field={field_name!r}{_line_no(numbers, first)}",
        )
    ]


def bullet_field_warnings(
    entity_id: str, field_name: str, lines: list[str], numbers: Optional[list[int]] = None
) -> list[ContractWarning]:
    """Every warning for text a bullet-list field's `lines` lose: `UNPARSED_BULLET_LINE` for text
    before the first bullet, then one `MISINDENTED_LINE` per line whose indent fits no level.
    Shared by every parser with a bullet field; `field_name` is the contract field, and `numbers` the
    lines' input numbers, which each warning names."""
    warnings = unparsed_bullet_warning(entity_id, field_name, lines, numbers)
    for index, line in _read_bullets(lines).misindented:
        warnings.append(
            ContractWarning(
                code=Code.MISINDENTED_LINE.name,
                message=f"'{field_name}' line at indent {line.indent} fits no level of its list and was dropped.",
                context=f"entity_id={entity_id!r} field={field_name!r}{_line_no(numbers, index)} line={line.text!r}",
            )
        )
    return warnings


# Both bullet kinds are read by `extract_bullets`, so both can drop text before the first bullet.
BULLET_KINDS = frozenset({_SectionKind.BULLETS, _SectionKind.PROSE_BULLET})


def _extract_prose(lines: list[str]) -> Optional[str]:
    parts = [ln.strip() for ln in lines if ln.strip()]
    return " ".join(parts) if parts else None


def _extract_prose_bullet(lines: list[str]) -> Optional[str]:
    items = extract_bullets(lines)
    return " ".join(items) if items else None


def split_id_list(value: Optional[str], sep: str = ",") -> list[str]:
    """Splits an already-joined `sep`-separated id/name list into its items, or `[]` for
    blank or "none". Shared with page_object.py (there with `sep=" · "` for wizard-steps)."""
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
    field_lines: Optional[dict[str, int]] = None,
) -> tuple[ParsedEntity, list[ContractWarning]]:
    """Constructs a `ParsedEntity` from already-extracted field values; shared by
    `parse_issue_body` and `feature_header.py::parse_feature_header`. An authored `state` value
    the reader mistyped becomes a warning, not an exception - pydantic validates eagerly. `field_lines`
    maps a field to the input line its key or heading is on, which the warning names."""
    lines = field_lines or {}
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
            line_no = f" line_no={lines[field_path]}" if field_path in lines else ""
            warnings.append(
                ContractWarning(
                    code=Code.MALFORMED_STATUS.name,
                    message=f"Authored '{field_path}' value {error['input']!r} failed validation: {error['msg']}",
                    context=f"entity_id={entity_id!r}{line_no}",
                )
            )
        parsed = ParsedEntity(
            entity_id=entity_id, type=entity_type, title=title, acceptance_criteria=acceptance_criteria, **fields
        )
        return parsed, warnings


def _read_sections(
    frame: Frame, spec_map: dict[str, _SectionSpec], entity_id: str
) -> tuple[dict[str, Any], dict[str, int], list[ContractWarning]]:
    """Each `##` section of the frame, looked up by its slug in `spec_map`: the field values, each field's
    heading line, and a warning for each heading that maps to no field and each line no field reads."""
    fields: dict[str, Any] = {}
    field_lines: dict[str, int] = {}
    found = sections(frame)
    warnings: list[ContractWarning] = duplicate_sections(found, entity_id)
    for section in found:
        heading_text = section.opener.line.text.lstrip("# ").strip()
        content = [framed.rendered for framed in section.lines]
        numbers = [framed.number for framed in section.lines]
        at = f"line_no={section.opener.number}"
        spec = spec_map.get(section.name)
        if spec is None:
            warnings.append(
                ContractWarning(
                    code=Code.UNKNOWN_SECTION.name,
                    message=f"Unrecognised heading '## {heading_text}'.",
                    context=f"entity_id={entity_id!r} {at}",
                )
            )
            continue
        if spec.kind == _SectionKind.AC:
            continue
        if spec.kind == _SectionKind.IGNORED_AUTHORED:
            assert spec.field_name is not None  # holds the IGNORED_AUTHORED_KEYS lookup key
            warnings.append(
                ContractWarning(
                    code=Code.IGNORED_AUTHORED_KEY.name,
                    message=IGNORED_AUTHORED_KEYS[spec.field_name],
                    context=f"entity_id={entity_id!r} {at} heading='## {heading_text}'",
                )
            )
            continue
        assert spec.field_name is not None  # every other kind carries a field
        fields[spec.field_name] = _EXTRACTORS[spec.kind](content)
        field_lines[spec.field_name] = section.opener.number
        if spec.kind in BULLET_KINDS:
            warnings.extend(bullet_field_warnings(entity_id, spec.field_name, content, numbers))
            warnings.extend(nesting_github_reads_as_siblings(section.lines, entity_id, spec.field_name))
    warnings.extend(unplaced_lines(frame, entity_id))
    return fields, field_lines, warnings


def parse_issue_body(
    text: str, title: str, entity_type: DocType
) -> tuple[Optional[ParsedEntity], list[ContractWarning]]:
    """Parses a GitHub issue body into a `ParsedEntity`. `title`'s entity-id prefix becomes
    `entity_id`; returns `(None, [MISSING_ENTITY_ID])` when the title has no parseable id."""
    normalized_title, _title_changes = normalize_title(title)
    entity_id, id_warnings = derive_entity_id(normalized_title)
    if entity_id is None:
        return None, id_warnings

    _, frame = normalize_framed(text, SourceFormat.ISSUE_BODY, entity_type)
    fields, field_lines, warnings = _read_sections(frame, _SECTIONS_BY_TYPE[entity_type], entity_id)
    warnings.extend(structural_warnings(frame, entity_id))

    # The frame bounds every criterion: an item's own text is never one, whatever it reads like (`D20`).
    acceptance_criteria, ac_warnings = parse_frame_criteria(frame, entity_id)
    warnings.extend(ac_warnings)

    parsed, build_warnings = _build_parsed_entity(
        entity_id, entity_type, normalized_title, acceptance_criteria, fields, field_lines
    )
    warnings.extend(build_warnings)
    return parsed, warnings
