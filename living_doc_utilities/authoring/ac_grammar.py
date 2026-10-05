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
The one acceptance-criterion header and extension grammar. Parses only the canonical form
`normalize` produces - no dash/case/version tolerance here, that's normalize's job. The only
module that knows the AC state vocabulary and strict version shape; elsewhere they're opaque tokens.
"""

import re
from dataclasses import dataclass, field
from typing import Optional

from pydantic import ValidationError

from living_doc_utilities.authoring.accounting import report
from living_doc_utilities.authoring.framing import (
    CriterionBlock,
    Frame,
    IndentedLine,
    Role,
    criterion_blocks,
    indented,
)
from living_doc_utilities.authoring.normalize import (
    _BULLET_RE,
    _WORD_SEP_RE,
    ItemText,
    compute_fence_flags,
)
from living_doc_utilities.contracts.codes import Code
from living_doc_utilities.contracts.common import (
    AC_ID_PATTERN,
    PLACEHOLDER_NAME_PATTERN,
    VERSION_PATTERN,
    AcceptanceCriterion,
)
from living_doc_utilities.contracts.envelope import ContractWarning

# The only place that still recognises this literal string; everywhere else it's simply not a valid state.
_LEGACY_DESCOPED_STATE = "descoped"

_VERSION_RE = re.compile(VERSION_PATTERN)
_AC_ID_RE = re.compile(AC_ID_PATTERN)
_PLACEHOLDER_NAME_RE = re.compile(PLACEHOLDER_NAME_PATTERN)

# Strips a comment-block leader (feature-header "#", issue-body "###", PageObject "*") and one following space;
# the rest of the indent is kept, since a block line's level is read from it.
_COMMENT_LEADER_RE = re.compile(r"^[#*]+ ?")

_AC_HEADER_RE = re.compile(r"^AC:(?P<id>\S*)\s*\((?P<inner>.*)\)\s*$")
_AC_PREFIX_RE = re.compile(r"^AC:")
# The input line a warning's context names.
_LINE_NO_RE = re.compile(r"\bline_no=(\d+)")

# Hard AC-block boundary like a fresh "AC:" header; else the last AC absorbs the banner and the scenario body.
_SECTION_BANNER_RE = re.compile(r"^=+$")

# Hard AC-block boundary on the raw line (a stripped "#" prefix would blur with "##"); at most 3 leading spaces.
_MD_SECTION_HEADING_RE = re.compile(r"^ {0,3}#{2,6}\s+\S")

_REMOVAL_PLANNED_RE = re.compile(r"^removal planned (?P<version>\S+)$")
_SUBLIST_KEY_RE = re.compile(r"^(?P<key>preconditions|not_in_scope):\s*$")
# Any other bare list key, e.g. `notes:`, which the canon allows at entity level only, never on a criterion.
_UNKNOWN_SUBLIST_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*:\s*$")
_ASPECT_RE = re.compile(r"^Aspect:\s*(?P<values>.+)$")
_RATIONALE_RE = re.compile(r"^Rationale:\s*(?P<text>.+)$")
_PLACEHOLDER_BULLET_RE = re.compile(r"^(?P<name>.+?):\s*(?P<values>.+)$")
_LEGACY_DESCOPED_REASON_RE = re.compile(r"^descoped_reason:\s*(?P<text>.+)$")
_LEGACY_DISCARD_RE = re.compile(r"^(?:descoped_at|future_release):\s*.+$")


def _strip_leading_v(token: str) -> Optional[str]:
    """Strips the canonical lowercase 'v' prefix `normalize.py::_reshape_version_form` emits once a minor part
    exists. `None` means the token isn't in that canonical form - caller reports MALFORMED_AC."""
    return token[1:] if token[:1] == "v" else None


def _slug_placeholder_name(name: str) -> str:
    return _WORD_SEP_RE.sub("_", name.strip().lower())


def _parse_header_inner(inner: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Maps an AC header's already-canonical paren content to (state, version,
    removal_planned). A None state means the shape couldn't be mapped; caller reports MALFORMED_AC."""
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


@dataclass
class _SubList:
    """An open `preconditions:` / `not_in_scope:` list. Its first item sets `item_level`: items
    deeper than the key end the list where the indent returns to the key's, and items at the
    key's own indent (the flat layout) keep it open for every later bullet, in line order."""

    key: str
    key_indent: int
    item_level: Optional[int] = None

    def is_nested(self) -> bool:
        return self.item_level is not None and self.item_level > self.key_indent

    def closed_by(self, line: IndentedLine) -> bool:
        return self.is_nested() and line.indent <= self.key_indent

    def misplaces(self, line: IndentedLine) -> bool:
        """True when `line` sits between the key and its items' level: it fits no level."""
        return self.item_level is not None and self.key_indent < line.indent < self.item_level


class _ExtensionReader:
    """Reads one criterion block's lines into `_Extensions` by indent. The block's content level is
    its first bullet's indent. A line deeper than the open item's `- ` is that item's text (`ItemText`);
    any other line is read at its level, and a line that fits no level is `MISINDENTED_LINE`."""

    def __init__(self, is_legacy_descoped: bool, context: str) -> None:
        self.result = _Extensions()
        self.warnings: list[ContractWarning] = []
        self._is_legacy_descoped = is_legacy_descoped
        self._context = context
        # The input line being read, which every warning names.
        self._number = 0
        self._content_level: Optional[int] = None
        self._sublist: Optional[_SubList] = None
        # Indent of an unknown bare key (e.g. `notes:`) or of a dropped misindented line, with the code
        # that every line deeper than it is reported with.
        self._skip: Optional[tuple[int, Code]] = None
        # The open bullet item: its marker's indent, and its text when it fills a text field.
        self._item_indent: Optional[int] = None
        self._item_text: Optional[ItemText] = None
        # Field a wrapped line is appended to; only the first physical line carries "-".
        self._continuation: Optional[str] = None

    def _warn(self, code: Code, line: IndentedLine) -> None:
        if code == Code.MISINDENTED_LINE:
            message = f"Acceptance-criterion block line at indent {line.indent} fits no level and was dropped."
        else:
            message = "Acceptance-criterion block line could not be assigned to any known field."
        self.warnings.append(
            ContractWarning(
                code=code.name, message=message, context=f"{self._context} line_no={self._number} line={line.text!r}"
            )
        )

    def _skip_deeper_than(self, line: IndentedLine, code: Code) -> None:
        """Reports `line` with `code`, and every later line deeper than it with the same code."""
        self._warn(code, line)
        self._skip = (line.indent, code)
        self._open_item(None, None)

    def _open_item(self, continuation: Optional[str], item: Optional[IndentedLine]) -> None:
        """Ends the open item; `item`, when given, opens the next one, whose text fills `continuation`."""
        self._continuation = continuation
        self._item_indent = item.indent if item is not None else None
        self._item_text = ItemText(item.indent) if item is not None and continuation is not None else None

    def _append(self, fragment: str) -> None:
        assert self._continuation is not None
        current = getattr(self.result, self._continuation)
        if isinstance(current, list):
            current[-1] = f"{current[-1]}{fragment}".strip()
        else:
            setattr(self.result, self._continuation, f"{current}{fragment}".strip())

    def read(self, line: IndentedLine, following: Optional[IndentedLine], number: int = 0) -> None:
        """Reads one non-blank block line, input line `number`; `following` is the next non-blank one, if any."""
        self._number = number
        if self._skip is not None:
            if line.indent > self._skip[0]:
                self._warn(self._skip[1], line)
                return
            self._skip = None

        if self._item_indent is not None and line.indent > self._item_indent:
            self._read_item_text(line)
            return

        if self._sublist is not None and self._sublist.closed_by(line):
            self._sublist = None
            self._open_item(None, None)
        below_content = self._content_level is not None and line.indent < self._content_level
        if below_content or (self._sublist is not None and self._sublist.misplaces(line)):
            self._skip_deeper_than(line, Code.MISINDENTED_LINE)
            return

        sublist_m = _SUBLIST_KEY_RE.match(line.text)
        if sublist_m:
            self._sublist = _SubList(sublist_m.group("key"), line.indent)
            self._open_item(None, None)
            return
        # A bare key with nothing deeper under it may be the end of a wrapped line ("…shows the" / "following:").
        if _UNKNOWN_SUBLIST_KEY_RE.match(line.text) and following is not None and following.indent > line.indent:
            # An open sub-list stays open: a key deeper than its items is already the open item's text, and one
            # shallower was closed by `closed_by` or dropped by `misplaces`, so a key reaching here sits at the
            # items' own level and the list goes on after the reported lines.
            self._skip_deeper_than(line, Code.UNPARSED_AC_LINE)
            return

        bullet_m = _BULLET_RE.match(line.text)
        if bullet_m:
            self._read_bullet(line, bullet_m.group("text").strip())
        elif self._continuation is None:
            self._warn(Code.UNPARSED_AC_LINE, line)
        else:
            self._append(f" {line.text}")

    def _read_item_text(self, line: IndentedLine) -> None:
        """A line deeper than the open item's `- `: wrapped text, or a nested item kept as extracted."""
        if self._item_text is None:
            self._warn(Code.UNPARSED_AC_LINE, line)
            return
        fragment = self._item_text.fragment(line)
        if fragment is None:
            self._warn(Code.MISINDENTED_LINE, line)
        else:
            self._append(fragment)

    def _read_bullet(self, line: IndentedLine, text: str) -> None:
        if self._content_level is None:
            self._content_level = line.indent

        if self._sublist is not None:
            if self._sublist.item_level is None:
                self._sublist.item_level = line.indent
            getattr(self.result, self._sublist.key).append(text)
            self._open_item(self._sublist.key, line)
            return

        if self.result.description is None:
            self.result.description = text
            self._open_item("description", line)
            return

        self._open_item(self._read_criterion_field(line, text), line)

    def _read_criterion_field(self, line: IndentedLine, text: str) -> Optional[str]:
        """Fills the field a criterion-level bullet names; returns the field its wrapped text continues."""
        result = self.result
        if self._is_legacy_descoped:
            legacy_reason_m = _LEGACY_DESCOPED_REASON_RE.match(text)
            if legacy_reason_m:
                result.rationale = legacy_reason_m.group("text").strip()
                return "rationale"
            if _LEGACY_DISCARD_RE.match(text):
                # descoped_at / future_release have no home in the model; silently dropped (legacy conversion only).
                return None

        aspect_m = _ASPECT_RE.match(text)
        if aspect_m:
            result.aspect = [v.strip() for v in aspect_m.group("values").split(",")]
            return None

        rationale_m = _RATIONALE_RE.match(text)
        if rationale_m:
            result.rationale = rationale_m.group("text").strip()
            return "rationale"

        placeholder_m = _PLACEHOLDER_BULLET_RE.match(text)
        if placeholder_m:
            name = _slug_placeholder_name(placeholder_m.group("name"))
            if _PLACEHOLDER_NAME_RE.match(name):
                result.placeholder_values[name] = [v.strip() for v in placeholder_m.group("values").split(",")]
                return None

        self._warn(Code.UNPARSED_AC_LINE, line)
        return None


def _parse_extensions(
    block_lines: list[tuple[str, int]], is_legacy_descoped: bool, context: str
) -> tuple[_Extensions, list[ContractWarning]]:
    """Reads a block's `(line, input line number)` pairs; an empty block reads as no extension at all (`D22`)."""
    reader = _ExtensionReader(is_legacy_descoped, context)
    lines = [(line, number) for line, number in ((indented(raw), number) for raw, number in block_lines) if line.text]
    followers = [*(line for line, _ in lines[1:]), None][: len(lines)]
    for (line, number), following in zip(lines, followers, strict=True):
        reader.read(line, following, number)
    return reader.result, reader.warnings


def _malformed_header(entity_id: str, raw_header_line: str, number: int) -> ContractWarning:
    return ContractWarning(
        code=Code.MALFORMED_AC.name,
        message="Acceptance-criterion header is malformed.",
        context=f"entity={entity_id!r} line_no={number} header={raw_header_line.strip()!r}",
    )


def _build_ac(
    entity_id: str, raw_id: str, raw_inner: str, block_lines: list[tuple[str, int]], raw_header_line: str, number: int
) -> tuple[Optional[AcceptanceCriterion], list[ContractWarning]]:
    """One criterion from its header's id and paren content and its block's `(line, number)` pairs; `number` is
    the header's input line, named by every warning about the criterion as a whole."""
    context = f"entity={entity_id!r} line_no={number} header={raw_header_line.strip()!r}"
    # A warning about one block line names that line's own number instead.
    block_context = f"entity={entity_id!r} header={raw_header_line.strip()!r}"
    warnings: list[ContractWarning] = []

    id_valid = bool(raw_id) and _AC_ID_RE.match(raw_id) is not None
    state, version, removal_planned = _parse_header_inner(raw_inner.strip())

    if not id_valid or state is None:
        warnings.append(_malformed_header(entity_id, raw_header_line, number))
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

    extensions, ext_warnings = _parse_extensions(block_lines, is_legacy_descoped, block_context)
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
        # A criterion with no `- ` line under its header has no description: said in words, not the model's.
        missing_description = field_path == "description" and extensions.description is None
        message = (
            "Acceptance criterion has no description line."
            if missing_description
            else f"Acceptance criterion failed validation: {detail}"
        )
        warnings.append(ContractWarning(code=Code.MALFORMED_AC.name, message=message, context=context))
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
    """Parses every `AC:<id> (...)` block in already-normalised `text` into
    `AcceptanceCriterion` instances plus warnings. `entity_id` is carried into warning
    context only - it never checks that an id belongs to it (that lives on `Entity`)."""
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
            warnings.append(_malformed_header(entity_id, raw_lines[index], index + 1))
            index += 1
            continue

        # A blank line is skipped, not a terminator (issue-body AC headings get one blank line before bullets).
        block: list[tuple[str, int]] = []
        # Marker indent of the block's open bullet item: a deeper line is its text, even one reading "AC:...".
        item_indent: Optional[int] = None
        cursor = index + 1
        while cursor < line_count:
            if fence_flags[cursor]:
                cursor += 1
                continue
            candidate = indented(cleaned_lines[cursor])
            is_item_text = item_indent is not None and candidate.indent > item_indent
            if not is_item_text and (_AC_PREFIX_RE.match(candidate.text) or _SECTION_BANNER_RE.match(candidate.text)):
                break
            if _MD_SECTION_HEADING_RE.match(raw_lines[cursor]):
                break
            if candidate.text != "":
                block.append((cleaned_lines[cursor], cursor + 1))
                if _BULLET_RE.match(candidate.text):
                    item_indent = candidate.indent
            cursor += 1

        acceptance_criterion, ac_warnings = _build_ac(
            entity_id, header_m.group("id"), header_m.group("inner"), block, raw_lines[index], index + 1
        )
        if acceptance_criterion is not None:
            results.append(acceptance_criterion)
        warnings.extend(ac_warnings)
        index = cursor

    return results, warnings


def parse_frame_criteria(frame: Frame, entity_id: str) -> tuple[list[AcceptanceCriterion], list[ContractWarning]]:
    """Every criterion the frame bounds, read by this grammar. The frame alone decides where a block starts and
    ends (`framing.criterion_blocks`), so nothing here looks for a boundary. A fenced code line in a block is
    not read; `parse_acceptance_criteria` is the same grammar over bare text, which finds its own blocks."""
    results: list[AcceptanceCriterion] = []
    warnings: list[ContractWarning] = []
    for block in criterion_blocks(frame):
        header_m = _AC_HEADER_RE.match(_COMMENT_LEADER_RE.sub("", block.header.rendered).strip())
        if header_m is None:
            warnings.append(_malformed_header(entity_id, block.header.rendered, block.header.number))
            warnings.extend(_dropped_lines(frame, block, entity_id, []))
            continue
        lines = [
            (_COMMENT_LEADER_RE.sub("", framed.rendered), framed.number)
            for framed in block.lines
            if framed.role is not Role.CODE
        ]
        acceptance_criterion, ac_warnings = _build_ac(
            entity_id,
            header_m.group("id"),
            header_m.group("inner"),
            lines,
            block.header.rendered,
            block.header.number,
        )
        warnings.extend(ac_warnings)
        if acceptance_criterion is None:
            warnings.extend(_dropped_lines(frame, block, entity_id, ac_warnings))
        else:
            results.append(acceptance_criterion)
    return results, warnings


def _dropped_lines(
    frame: Frame, block: CriterionBlock, entity_id: str, named: list[ContractWarning]
) -> list[ContractWarning]:
    """Each line of a dropped criterion's block that no other warning names: one warning per line, so none of its
    lines is lost unnamed. A code line is reported as a code block already, and a structural problem by the frame."""
    numbers = {problem.line for problem in frame.problems}
    numbers |= {int(m.group(1)) for warning in named if (m := _LINE_NO_RE.search(warning.context or ""))}
    return [
        report(Code.AUTHORING_WARNING, "Line of a dropped acceptance criterion is not read.", entity_id, framed)
        for framed in block.lines
        if framed.line.text and framed.role is not Role.CODE and framed.number not in numbers
    ]
