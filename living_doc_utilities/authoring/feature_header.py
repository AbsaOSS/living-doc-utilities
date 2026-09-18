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
`.feature`-file header parsing for a User Story or a Functionality (living-doc's
docs/guides/living-doc-header-types.md, sections 1 and 3): the `# key: value` / `# key:` +
bulleted-list comment block between the two `# ===...===` banner lines, plus its
`AC:<id> (v<version> - <state>)` blocks, parsed by `ac_grammar` alone. The Gherkin body
below the header (scenarios, `@AC:` tags) is `scenario.py`'s job, not this module's.
"""

import re
from typing import Any, Optional

from living_doc_utilities.authoring.ac_grammar import parse_acceptance_criteria
from living_doc_utilities.authoring.identity import MISSING_ENTITY_ID, derive_entity_id
from living_doc_utilities.authoring.issue_body import IGNORED_AUTHORED_KEY, ParsedEntity
from living_doc_utilities.authoring.normalize import SourceFormat, normalize
from living_doc_utilities.contracts.common import DocType
from living_doc_utilities.contracts.envelope import ContractWarning

_BANNER_RE = re.compile(r"^#\s*=+\s*$")
_LIVING_DOC_TITLE_RE = re.compile(r"LIVING DOC\s*—\s*(?P<title>.+?)\s*$")
_COMMENT_PREFIX_RE = re.compile(r"^#\s?")
_AC_HEADER_LOOKALIKE_RE = re.compile(r"^AC:\S+\s*\(")
_BULLET_RE = re.compile(r"^-\s?(?P<text>.*)$")
_GENERIC_KEY_RE = re.compile(r"^(?P<key>[a-zA-Z_][a-zA-Z0-9_]*):\s*(?P<val>.*)$")

_KIND_SCALAR = "scalar"
_KIND_BULLETS = "bullets"
_KIND_PROSE_BULLET = "prose_bullet"
_KIND_IGNORED = "ignored"


class _KeySpec:
    __slots__ = ("field_name", "kind")

    def __init__(self, field_name: Optional[str], kind: str) -> None:
        self.field_name = field_name
        self.kind = kind


_COMMON_KEYS = {
    "source": _KeySpec("source", _KIND_SCALAR),
    "status": _KeySpec("state", _KIND_SCALAR),
    "deprecated_at": _KeySpec("deprecated_at", _KIND_SCALAR),
    "deprecation_reason": _KeySpec("deprecation_reason", _KIND_SCALAR),
    "superseded_by": _KeySpec("superseded_by", _KIND_SCALAR),
    "preconditions": _KeySpec("preconditions", _KIND_BULLETS),
    "not_in_scope": _KeySpec("not_in_scope", _KIND_BULLETS),
    "acceptance_criteria": _KeySpec(None, _KIND_IGNORED),
}

_KEYS_BY_TYPE: dict[DocType, dict[str, _KeySpec]] = {
    "DocumentedUserStory": {
        **_COMMON_KEYS,
        "business_value": _KeySpec("business_value", _KIND_BULLETS),
    },
    "DocumentedFunctionality": {
        **_COMMON_KEYS,
        "parent": _KeySpec("parent", _KIND_SCALAR),
        "func_type": _KeySpec("func_type", _KIND_SCALAR),
        "rationale": _KeySpec("rationale", _KIND_PROSE_BULLET),
    },
}


def _strip_comment_prefix(line: str) -> str:
    return _COMMENT_PREFIX_RE.sub("", line, count=1)


def _extract_bullets(lines: list[str]) -> list[str]:
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


def _extract_header_block(lines: list[str]) -> list[str]:
    """The banner (`# ===...===`) brackets the whole header block, but also appears a
    second time right after the title line (framing it on its own) - so the block runs
    from the *first* banner to the *last*, not the first two."""
    banner_indices = [i for i, ln in enumerate(lines) if _BANNER_RE.match(ln)]
    if len(banner_indices) < 2:
        return []
    return lines[banner_indices[0] + 1 : banner_indices[-1]]


def _extract_title(lines: list[str]) -> Optional[str]:
    for line in lines:
        title_m = _LIVING_DOC_TITLE_RE.search(line)
        if title_m:
            return title_m.group("title").strip()
    return None


def _parse_keys(header_lines: list[str], key_specs: dict[str, _KeySpec]) -> tuple[dict[str, Any], list[str]]:
    key_re = re.compile(
        r"^(?P<key>" + "|".join(re.escape(k) for k in sorted(key_specs, key=len, reverse=True)) + r"):\s*(?P<val>.*)$"
    )
    raw_values: dict[str, list[str]] = {}
    current_key: Optional[str] = None
    unrecognised: list[str] = []

    for raw_line in header_lines:
        content = _strip_comment_prefix(raw_line)
        stripped = content.strip()
        if stripped == "" or _AC_HEADER_LOOKALIKE_RE.match(stripped) or set(stripped) == {"="}:
            current_key = None
            continue

        key_m = key_re.match(stripped)
        if key_m:
            key = key_m.group("key")
            if key_specs[key].kind == _KIND_IGNORED:
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
        content_lines = raw_values[key]
        if spec.kind == _KIND_BULLETS:
            values[spec.field_name] = _extract_bullets(content_lines)
        elif spec.kind == _KIND_PROSE_BULLET:
            bullets = _extract_bullets(content_lines)
            values[spec.field_name] = " ".join(bullets) if bullets else None
        else:  # _KIND_SCALAR
            parts = [ln.strip() for ln in content_lines if ln.strip()]
            values[spec.field_name] = " ".join(parts) if parts else None

    return values, unrecognised


def parse_feature_header(text: str, entity_type: DocType) -> tuple[Optional[ParsedEntity], list[ContractWarning]]:
    """Parses a User Story / Functionality `.feature` file's header block into a
    `ParsedEntity`. Returns `(None, [MISSING_ENTITY_ID])` when the `LIVING DOC — ...` title
    line is missing or carries no parseable id.
    """
    normalized = normalize(text, SourceFormat.FEATURE_HEADER, entity_type)
    header_lines = _extract_header_block(normalized.lines)

    title = _extract_title(header_lines) or _extract_title(normalized.lines)
    if title is None:
        return None, [
            ContractWarning(
                code=MISSING_ENTITY_ID,
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
                code=IGNORED_AUTHORED_KEY,
                message=f"'{key}:' is not a field this contract carries.",
                context=f"entity_id={entity_id!r}",
            )
        )

    header_text = "\n".join(header_lines)
    acceptance_criteria, ac_warnings = parse_acceptance_criteria(header_text, entity_id)
    warnings.extend(ac_warnings)

    parsed = ParsedEntity(
        entity_id=entity_id,
        type=entity_type,
        title=title,
        acceptance_criteria=acceptance_criteria,
        **fields,
    )
    return parsed, warnings
