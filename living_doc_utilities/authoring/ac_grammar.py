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
The one acceptance-criterion header and extension grammar (living-doc's docs/guides/
living-doc-glossary.md, "Acceptance Criterion (AC)"). Parses only the canonical form
`normalize` produces - no dash, case or version-form tolerance lives here, that is
normalize's job entirely. This is the only module that knows the acceptance-criterion
state vocabulary and the strict version shape; every other module in this package
treats those as opaque tokens to reshape, never to validate.
"""

import re
from dataclasses import dataclass, field
from typing import Optional

from pydantic import ValidationError

from living_doc_utilities.authoring.normalize import _BULLET_RE, _WORD_SEP_RE, compute_fence_flags
from living_doc_utilities.contracts.codes import Code
from living_doc_utilities.contracts.common import (
    AC_ID_PATTERN,
    PLACEHOLDER_NAME_PATTERN,
    VERSION_PATTERN,
    AcceptanceCriterion,
)
from living_doc_utilities.contracts.envelope import ContractWarning

# The only place in the codebase that still recognises this literal string (docs/
# contracts.md's AC grammar section) - everywhere else it is simply not a valid state.
_LEGACY_DESCOPED_STATE = "descoped"

_VERSION_RE = re.compile(VERSION_PATTERN)
_AC_ID_RE = re.compile(AC_ID_PATTERN)
_PLACEHOLDER_NAME_RE = re.compile(PLACEHOLDER_NAME_PATTERN)

# Strips a comment-block leader (feature-header "#", issue-body "###", PageObject "*")
# that survives in normalize's reconstructed text; a purely mechanical unwrap, not a
# dash/case tolerance - the grammar below still accepts only the canonical inner form.
_COMMENT_LEADER_RE = re.compile(r"^[#*]+\s*")

_AC_HEADER_RE = re.compile(r"^AC:(?P<id>\S*)\s*\((?P<inner>.*)\)\s*$")
_AC_PREFIX_RE = re.compile(r"^AC:")

# The "# ====...====" rule that opens and closes a feature-header entity block (living-
# doc's docs/guides/living-doc-header-types.md, every worked header example). Once
# comment-leaders are stripped this is a line of nothing but "=" - a hard boundary for
# an AC's block, the same way a fresh "AC:" header already is. Without it, the last AC in
# a complete `.feature` file would otherwise absorb the closing banner, the `Feature:`
# declaration and the entire scenario body into its own block.
_SECTION_BANNER_RE = re.compile(r"^=+$")

# An issue-body Markdown section heading ("## Preconditions", "## Not In Scope", ...) -
# another hard boundary for an AC's block, the same way a fresh "AC:" header or a
# feature-header "====" banner already is. Checked against the *raw* line, never the
# comment-leader-stripped one: `_COMMENT_LEADER_RE` would strip a heading's own "##"
# indistinguishably from a feature-header block's single-"#" comment prefix, so the
# minimum of two "#" here is what keeps this from firing on every feature-header/
# scenario-file AC-block line (those never use a doubled leader). The " {0,3}" mirrors
# `_FENCE_OPEN_RE`/`_FENCE_CLOSE_RE` in normalize.py (CommonMark: at most three leading
# spaces before a construct still counts as "unindented") - four or more is an indented
# code block, never a heading, so it must not terminate the AC block early.
_MD_SECTION_HEADING_RE = re.compile(r"^ {0,3}#{2,6}\s+\S")

_REMOVAL_PLANNED_RE = re.compile(r"^removal planned (?P<version>\S+)$")
_SUBLIST_KEY_RE = re.compile(r"^(?P<key>preconditions|not_in_scope):\s*$")
_ASPECT_RE = re.compile(r"^Aspect:\s*(?P<values>.+)$")
_RATIONALE_RE = re.compile(r"^Rationale:\s*(?P<text>.+)$")
_PLACEHOLDER_BULLET_RE = re.compile(r"^(?P<name>.+?):\s*(?P<values>.+)$")
_LEGACY_DESCOPED_REASON_RE = re.compile(r"^descoped_reason:\s*(?P<text>.+)$")
_LEGACY_DISCARD_RE = re.compile(r"^(?:descoped_at|future_release):\s*.+$")


def _strip_leading_v(token: str) -> Optional[str]:
    """Strips the canonical lowercase 'v' prefix `normalize`'s `_reshape_version_form`
    always emits. `None` means the token is not in that canonical form (e.g. an
    uppercase 'V' or a bare digit string) - the caller reports that as MALFORMED_AC
    rather than tolerating a version form this module does not own.
    """
    return token[1:] if token[:1] == "v" else None


def _slug_placeholder_name(name: str) -> str:
    return _WORD_SEP_RE.sub("_", name.strip().lower())


def _parse_header_inner(inner: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Maps an AC header's already-canonical paren content to (state, version,
    removal_planned). A None state means the shape could not be mapped at all; the
    caller reports that as MALFORMED_AC rather than guessing.
    """
    if inner == "":
        return None, None, None
    segments = inner.split(" - ")
    if len(segments) == 1:
        return segments[0], None, None
    if len(segments) == 2:
        version_raw, state = segments
        version = _strip_leading_v(version_raw)
        if version is None:
            return None, None, None
        return state, version, None
    if len(segments) == 3:
        version_raw, state, removal_clause = segments
        removal_m = _REMOVAL_PLANNED_RE.match(removal_clause)
        if removal_m is None:
            return None, None, None
        version = _strip_leading_v(version_raw)
        removal_version = _strip_leading_v(removal_m.group("version"))
        if version is None or removal_version is None:
            return None, None, None
        return state, version, removal_version
    return None, None, None


@dataclass
class _Extensions:
    description: Optional[str] = None
    aspect: list[str] = field(default_factory=list)
    preconditions: list[str] = field(default_factory=list)
    not_in_scope: list[str] = field(default_factory=list)
    rationale: Optional[str] = None
    placeholder_values: dict[str, list[str]] = field(default_factory=dict)


def _parse_extensions(
    block_lines: list[str], is_legacy_descoped: bool, context: str
) -> tuple[_Extensions, list[ContractWarning]]:
    result = _Extensions()
    warnings: list[ContractWarning] = []
    pending_sublist_key: Optional[str] = None
    seen_description = False
    # Field a following non-bullet line's hard-wrapped text is appended to (the last entry
    # if it is a list): only the first physical line of a wrapped description, rationale or
    # sub-list item carries the "-" bullet marker.
    continuation: Optional[str] = None

    def _unparsed(raw_line: str) -> None:
        warnings.append(
            ContractWarning(
                code=Code.UNPARSED_AC_LINE.name,
                message="Acceptance-criterion block line could not be assigned to any known field.",
                context=f"{context} line={raw_line.strip()!r}",
            )
        )

    for raw_line in block_lines:
        stripped = raw_line.strip()
        if stripped == "":
            continue

        sublist_m = _SUBLIST_KEY_RE.match(stripped)
        if sublist_m:
            pending_sublist_key = sublist_m.group("key")
            continuation = None
            continue

        bullet_m = _BULLET_RE.match(stripped)
        if not bullet_m:
            if continuation is None:
                _unparsed(raw_line)
            else:
                current = getattr(result, continuation)
                if isinstance(current, list):
                    current[-1] = f"{current[-1]} {stripped}".strip()
                else:
                    setattr(result, continuation, f"{current} {stripped}".strip())
            continue

        text = bullet_m.group("text").strip()

        if pending_sublist_key is not None:
            getattr(result, pending_sublist_key).append(text)
            continuation = pending_sublist_key
            continue

        if not seen_description:
            result.description = text
            seen_description = True
            continuation = "description"
            continue

        if is_legacy_descoped:
            legacy_reason_m = _LEGACY_DESCOPED_REASON_RE.match(text)
            if legacy_reason_m:
                result.rationale = legacy_reason_m.group("text").strip()
                continuation = "rationale"
                continue
            if _LEGACY_DISCARD_RE.match(text):
                # descoped_at / future_release: no home in the canon model (there is no
                # descoped state any more), silently dropped as part of the one legacy
                # conversion path.
                continuation = None
                continue

        aspect_m = _ASPECT_RE.match(text)
        if aspect_m:
            result.aspect = [v.strip() for v in aspect_m.group("values").split(",")]
            continuation = None
            continue

        rationale_m = _RATIONALE_RE.match(text)
        if rationale_m:
            result.rationale = rationale_m.group("text").strip()
            continuation = "rationale"
            continue

        placeholder_m = _PLACEHOLDER_BULLET_RE.match(text)
        if placeholder_m:
            name = _slug_placeholder_name(placeholder_m.group("name"))
            if _PLACEHOLDER_NAME_RE.match(name):
                result.placeholder_values[name] = [v.strip() for v in placeholder_m.group("values").split(",")]
                continuation = None
                continue

        _unparsed(raw_line)
        continuation = None

    return result, warnings


def _build_ac(
    entity_id: str, raw_id: str, raw_inner: str, block_lines: list[str], raw_header_line: str
) -> tuple[Optional[AcceptanceCriterion], list[ContractWarning]]:
    context = f"entity={entity_id!r} header={raw_header_line.strip()!r}"
    warnings: list[ContractWarning] = []

    id_valid = bool(raw_id) and _AC_ID_RE.match(raw_id) is not None
    state, version, removal_planned = _parse_header_inner(raw_inner.strip())

    if not id_valid or state is None:
        warnings.append(
            ContractWarning(
                code=Code.MALFORMED_AC.name, message="Acceptance-criterion header is malformed.", context=context
            )
        )
        return None, warnings

    is_legacy_descoped = state == _LEGACY_DESCOPED_STATE
    if is_legacy_descoped:
        legacy_shape_valid = removal_planned is None and version is not None and _VERSION_RE.match(version) is not None
        if not legacy_shape_valid:
            warnings.append(
                ContractWarning(
                    code=Code.MALFORMED_AC.name,
                    message="Legacy 'descoped' acceptance criterion requires the strict versioned form "
                    "'vX.Y.Z - descoped'.",
                    context=context,
                )
            )
            return None, warnings
        warnings.append(
            ContractWarning(
                code=Code.LEGACY_AC_STATE.name,
                message="Legacy 'descoped' state converted to a version-less 'planned' acceptance criterion.",
                context=context,
            )
        )
        state = "planned"
        version = None
        removal_planned = None

    extensions, ext_warnings = _parse_extensions(block_lines, is_legacy_descoped, context)
    warnings.extend(ext_warnings)

    try:
        acceptance_criterion = AcceptanceCriterion(
            id=raw_id,
            state=state,  # type: ignore[arg-type]
            version=version,
            removal_planned=removal_planned,
            description=extensions.description,  # type: ignore[arg-type]
            aspect=extensions.aspect,
            preconditions=extensions.preconditions,
            not_in_scope=extensions.not_in_scope,
            rationale=extensions.rationale,
            placeholder_values=extensions.placeholder_values,
        )
    except ValidationError as exc:
        first = exc.errors()[0]
        field_path = ".".join(str(part) for part in first["loc"])
        detail = f"{field_path}: {first['msg']}" if field_path else first["msg"]
        warnings.append(
            ContractWarning(
                code=Code.MALFORMED_AC.name,
                message=f"Acceptance criterion failed validation: {detail}",
                context=context,
            )
        )
        return None, warnings

    return acceptance_criterion, warnings


def is_valid_ac_id(candidate: str) -> bool:
    """Whether `candidate` matches the AC id shape (`AC_ID_PATTERN`) - the one place every
    other module should check this (e.g. a scenario's `@AC:<id>` tag), instead of
    re-deriving the pattern itself."""
    return _AC_ID_RE.match(candidate) is not None


def parse_acceptance_criteria(
    text: str, entity_id: str = ""
) -> tuple[list[AcceptanceCriterion], list[ContractWarning]]:
    """Parses every `AC:<id> (...)` block found in already-normalised `text` into
    `AcceptanceCriterion` instances plus a `list[ContractWarning]`. `entity_id` is
    carried into warning context only; this function never checks that an id belongs
    to it (that cross-field check lives on `Entity`).
    """
    raw_lines = text.splitlines()
    cleaned_lines = [_COMMENT_LEADER_RE.sub("", line) for line in raw_lines]
    fence_flags = compute_fence_flags(raw_lines)

    results: list[AcceptanceCriterion] = []
    warnings: list[ContractWarning] = []

    index = 0
    line_count = len(raw_lines)
    while index < line_count:
        if fence_flags[index]:
            index += 1
            continue

        stripped_line = cleaned_lines[index].strip()
        if not _AC_PREFIX_RE.match(stripped_line):
            index += 1
            continue

        header_m = _AC_HEADER_RE.match(stripped_line)
        if header_m is None:
            warnings.append(
                ContractWarning(
                    code=Code.MALFORMED_AC.name,
                    message="Acceptance-criterion header is malformed.",
                    context=f"entity={entity_id!r} header={raw_lines[index].strip()!r}",
                )
            )
            index += 1
            continue

        # A blank line is skipped, not a terminator: issue-body AC headings are
        # conventionally followed by one blank line before their own bullets. Only the
        # next "AC:"-prefixed line (or end of input) ends this one's block.
        block: list[str] = []
        cursor = index + 1
        while cursor < line_count:
            if fence_flags[cursor]:
                cursor += 1
                continue
            candidate = cleaned_lines[cursor].strip()
            if _AC_PREFIX_RE.match(candidate) or _SECTION_BANNER_RE.match(candidate):
                break
            if _MD_SECTION_HEADING_RE.match(raw_lines[cursor]):
                break
            if candidate != "":
                block.append(cleaned_lines[cursor])
            cursor += 1

        acceptance_criterion, ac_warnings = _build_ac(
            entity_id, header_m.group("id"), header_m.group("inner"), block, raw_lines[index]
        )
        if acceptance_criterion is not None:
            results.append(acceptance_criterion)
        warnings.extend(ac_warnings)
        index = cursor

    return results, warnings
