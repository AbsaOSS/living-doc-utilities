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
`.feature`-file header parsing for a User Story or a Functionality: the `# key: value` /
`# key:` + bulleted-list comment block between two `# ===...===` banners, plus its
`AC:<id> (v<version> - <state>)` blocks, parsed by `ac_grammar` alone.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from living_doc_utilities.authoring.ac_grammar import parse_frame_criteria
from living_doc_utilities.authoring.accounting import (
    at_title,
    first_occurrences,
    missing_title,
    scalar_lines,
    structural_warnings,
    unplaced_lines,
)
from living_doc_utilities.authoring.framing import Frame, opening_value, sections
from living_doc_utilities.authoring.identity import derive_entity_id, extract_living_doc_title
from living_doc_utilities.authoring.issue_body import (
    _EXTRACTORS,
    BULLET_KINDS,
    ParsedEntity,
    _build_parsed_entity,
    _SectionKind,
    _SectionSpec,
    bullet_field_warnings,
)
from living_doc_utilities.authoring.normalize import SourceFormat, normalize_framed
from living_doc_utilities.contracts.codes import Code
from living_doc_utilities.contracts.common import DocType
from living_doc_utilities.contracts.envelope import ContractWarning

_COMMON_KEYS = {
    "source": _SectionSpec("source", _SectionKind.SCALAR),
    "status": _SectionSpec("state", _SectionKind.SCALAR),
    "deprecated_at": _SectionSpec("deprecated_at", _SectionKind.SCALAR),
    "deprecation_reason": _SectionSpec("deprecation_reason", _SectionKind.SCALAR),
    "superseded_by": _SectionSpec("superseded_by", _SectionKind.SCALAR),
    "preconditions": _SectionSpec("preconditions", _SectionKind.BULLETS),
    "not_in_scope": _SectionSpec("not_in_scope", _SectionKind.BULLETS),
    "notes": _SectionSpec("notes", _SectionKind.BULLETS),
    "acceptance_criteria": _SectionSpec(None, _SectionKind.IGNORED),
}

# Scalar keys whose value is one token - a state, a date, an id, a URL: a further line is an AUTHORING_ERROR and
# is not read. `deprecation_reason` is text, and may wrap.
_SINGLE_VALUE_KEYS = frozenset({"source", "status", "deprecated_at", "superseded_by", "parent", "func_type"})

_KEYS_BY_TYPE: dict[DocType, dict[str, _SectionSpec]] = {
    "DocumentedUserStory": {
        **_COMMON_KEYS,
        "business_value": _SectionSpec("business_value", _SectionKind.BULLETS),
    },
    "DocumentedFunctionality": {
        **_COMMON_KEYS,
        "parent": _SectionSpec("parent", _SectionKind.SCALAR),
        "func_type": _SectionSpec("func_type", _SectionKind.SCALAR),
        "rationale": _SectionSpec("rationale", _SectionKind.PROSE_BULLET),
    },
}


@dataclass
class _ParsedKeys:
    """`_read_keys`' result: each field's value, each present key's raw lines (the key's own line first, so the
    caller can report text a bullet field drops) and their input line numbers, each field's key line, the
    unrecognised keys with their lines, and the warnings for lines no field reads."""

    values: dict[str, Any] = field(default_factory=dict)
    raw_values: dict[str, list[str]] = field(default_factory=dict)
    numbers: dict[str, list[int]] = field(default_factory=dict)
    field_lines: dict[str, int] = field(default_factory=dict)
    unrecognised: list[tuple[str, int]] = field(default_factory=list)
    warnings: list[ContractWarning] = field(default_factory=list)


def _read_keys(frame: Frame, key_specs: dict[str, _SectionSpec], entity_id: str) -> _ParsedKeys:
    """Each key section of the frame, looked up in `key_specs`; a key written twice has left the frame already
    (`accounting.first_occurrences`). A scalar key's further lines are read by its value's type
    (`accounting.scalar_lines`)."""
    result = _ParsedKeys()
    for section in sections(frame):
        spec = key_specs.get(section.name)
        if spec is None:
            result.unrecognised.append((section.name, section.opener.number))
            continue
        if spec.field_name is not None:
            result.field_lines[spec.field_name] = section.opener.number
        if spec.kind == _SectionKind.SCALAR:
            lines, warnings = scalar_lines(section, section.name in _SINGLE_VALUE_KEYS, entity_id)
            result.raw_values[section.name] = lines
            result.warnings.extend(warnings)
        elif spec.kind != _SectionKind.IGNORED:
            result.raw_values[section.name] = [opening_value(section.opener)] + [
                framed.line.raw.rstrip() for framed in section.lines
            ]
            result.numbers[section.name] = [section.opener.number] + [framed.number for framed in section.lines]

    for key, spec in key_specs.items():
        if key not in result.raw_values or spec.field_name is None:
            continue
        result.values[spec.field_name] = _EXTRACTORS[spec.kind](result.raw_values[key])

    return result


def parse_feature_header(text: str, entity_type: DocType) -> tuple[Optional[ParsedEntity], list[ContractWarning]]:
    """Parses a User Story / Functionality `.feature` file's header block into a
    `ParsedEntity`. Returns `(None, [MISSING_ENTITY_ID])` when the `LIVING DOC — ...` title
    line is missing or carries no parseable id."""
    _, frame = normalize_framed(text, SourceFormat.FEATURE_HEADER, entity_type)
    title = None if frame.title is None else extract_living_doc_title([frame.title.line.raw])
    if title is None:
        no_header = "No living-doc header found: no '# ===' rule above 'Feature:'."
        return None, [missing_title(frame, "Feature-header", no_header), *structural_warnings(frame, "")]

    entity_id, id_warnings = derive_entity_id(title)
    if entity_id is None:
        return None, at_title(id_warnings, frame)

    warnings: list[ContractWarning] = structural_warnings(frame, entity_id)
    frame, repeated = first_occurrences(frame, entity_id)
    warnings.extend(repeated)
    key_specs = _KEYS_BY_TYPE[entity_type]
    keys = _read_keys(frame, key_specs, entity_id)
    warnings.extend(keys.warnings)
    warnings.extend(unplaced_lines(frame, entity_id))
    for key, number in keys.unrecognised:
        warnings.append(
            ContractWarning(
                code=Code.IGNORED_AUTHORED_KEY.name,
                message=f"'{key}:' is not a field this contract carries.",
                context=f"entity_id={entity_id!r} line_no={number}",
            )
        )
    for key, spec in key_specs.items():
        if spec.kind in BULLET_KINDS and key in keys.raw_values:
            assert spec.field_name is not None  # every bullet kind carries a field
            warnings.extend(bullet_field_warnings(entity_id, spec.field_name, keys.raw_values[key], keys.numbers[key]))

    acceptance_criteria, ac_warnings = parse_frame_criteria(frame, entity_id)
    warnings.extend(ac_warnings)

    parsed, build_warnings = _build_parsed_entity(
        entity_id, entity_type, title, acceptance_criteria, keys.values, keys.field_lines
    )
    warnings.extend(build_warnings)
    return parsed, warnings
