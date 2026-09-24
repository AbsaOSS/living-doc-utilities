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

import re
from typing import Any, Optional

from living_doc_utilities.authoring.ac_grammar import parse_acceptance_criteria
from living_doc_utilities.authoring.identity import derive_entity_id, extract_living_doc_title
from living_doc_utilities.authoring.issue_body import (
    _EXTRACTORS,
    ParsedEntity,
    _build_parsed_entity,
    _SectionKind,
    _SectionSpec,
)
from living_doc_utilities.authoring.normalize import _FEATURE_LINE_RE, SourceFormat, _split_comment_prefix, normalize
from living_doc_utilities.contracts.codes import Code
from living_doc_utilities.contracts.common import DocType
from living_doc_utilities.contracts.envelope import ContractWarning

_BANNER_RE = re.compile(r"^#\s*=+\s*$")
_AC_HEADER_LOOKALIKE_RE = re.compile(r"^AC:\S+\s*\(")
_GENERIC_KEY_RE = re.compile(r"^(?P<key>[a-zA-Z_][a-zA-Z0-9_]*):\s*(?P<val>.*)$")

_COMMON_KEYS = {
    "source": _SectionSpec("source", _SectionKind.SCALAR),
    "status": _SectionSpec("state", _SectionKind.SCALAR),
    "deprecated_at": _SectionSpec("deprecated_at", _SectionKind.SCALAR),
    "deprecation_reason": _SectionSpec("deprecation_reason", _SectionKind.SCALAR),
    "superseded_by": _SectionSpec("superseded_by", _SectionKind.SCALAR),
    "preconditions": _SectionSpec("preconditions", _SectionKind.BULLETS),
    "not_in_scope": _SectionSpec("not_in_scope", _SectionKind.BULLETS),
    "acceptance_criteria": _SectionSpec(None, _SectionKind.IGNORED),
}

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


def _strip_comment_prefix(line: str) -> str:
    return _split_comment_prefix(line)[1]


def _extract_header_block(lines: list[str]) -> list[str]:
    """The banner brackets the whole header block but also reappears right after the title
    line, so the block runs from the *first* banner to the *last*. Search is bounded to
    before `Feature:`, else the scenario body's own banner-shaped comments would extend it."""
    feature_idx = next((i for i, ln in enumerate(lines) if _FEATURE_LINE_RE.match(ln.strip())), len(lines))
    banner_indices = [i for i, ln in enumerate(lines[:feature_idx]) if _BANNER_RE.match(ln)]
    if len(banner_indices) < 2:
        return []
    return lines[banner_indices[0] + 1 : banner_indices[-1]]


def _parse_keys(header_lines: list[str], key_specs: dict[str, _SectionSpec]) -> tuple[dict[str, Any], list[str]]:
    key_re = re.compile(
        r"^(?P<key>" + "|".join(re.escape(k) for k in sorted(key_specs, key=len, reverse=True)) + r"):\s*(?P<val>.*)$"
    )
    raw_values: dict[str, list[str]] = {}
    current_key: Optional[str] = None
    unrecognised: list[str] = []
    # Once the first "AC:" header is seen, every following line belongs to that AC's own block until "====" closes it.
    in_ac_block = False

    for raw_line in header_lines:
        content = _strip_comment_prefix(raw_line)
        stripped = content.strip()
        if set(stripped) == {"="}:
            current_key = None
            in_ac_block = False
            continue
        if stripped == "":
            current_key = None
            continue
        if _AC_HEADER_LOOKALIKE_RE.match(stripped):
            current_key = None
            in_ac_block = True
            continue
        if in_ac_block:
            continue

        key_m = key_re.match(stripped)
        if key_m:
            key = key_m.group("key")
            if key_specs[key].kind == _SectionKind.IGNORED:
                current_key = None
                continue
            current_key = key
            raw_values[key] = [key_m.group("val")]
            continue

        generic_m = _GENERIC_KEY_RE.match(stripped)
        if generic_m and generic_m.group("key") not in key_specs:
            unrecognised.append(generic_m.group("key"))
            current_key = None
            continue

        if current_key is not None:
            raw_values[current_key].append(content.rstrip())

    values: dict[str, Any] = {}
    for key, spec in key_specs.items():
        if key not in raw_values or spec.field_name is None:
            continue
        values[spec.field_name] = _EXTRACTORS[spec.kind](raw_values[key])

    return values, unrecognised


def parse_feature_header(text: str, entity_type: DocType) -> tuple[Optional[ParsedEntity], list[ContractWarning]]:
    """Parses a User Story / Functionality `.feature` file's header block into a
    `ParsedEntity`. Returns `(None, [MISSING_ENTITY_ID])` when the `LIVING DOC — ...` title
    line is missing or carries no parseable id."""
    normalized = normalize(text, SourceFormat.FEATURE_HEADER, entity_type)
    header_lines = _extract_header_block(normalized.lines)

    title = extract_living_doc_title(header_lines) or extract_living_doc_title(normalized.lines)
    if title is None:
        return None, [
            ContractWarning(
                code=Code.MISSING_ENTITY_ID.name,
                message="Feature-header banner carries no 'LIVING DOC — ...' title line.",
                context="title=''",
            )
        ]

    entity_id, id_warnings = derive_entity_id(title)
    if entity_id is None:
        return None, id_warnings

    warnings: list[ContractWarning] = []
    key_specs = _KEYS_BY_TYPE[entity_type]
    fields, unrecognised = _parse_keys(header_lines, key_specs)
    for key in unrecognised:
        warnings.append(
            ContractWarning(
                code=Code.IGNORED_AUTHORED_KEY.name,
                message=f"'{key}:' is not a field this contract carries.",
                context=f"entity_id={entity_id!r}",
            )
        )

    header_text = "\n".join(header_lines)
    acceptance_criteria, ac_warnings = parse_acceptance_criteria(header_text, entity_id)
    warnings.extend(ac_warnings)

    parsed, build_warnings = _build_parsed_entity(entity_id, entity_type, title, acceptance_criteria, fields)
    warnings.extend(build_warnings)
    return parsed, warnings
