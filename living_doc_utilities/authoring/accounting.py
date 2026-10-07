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
Line accounting: every authored line a parser does not read is reported, so no line is lost without a code.
A line that breaks the header format is `AUTHORING_ERROR`; any other unread line no more specific code covers
is `AUTHORING_WARNING`. Both are warnings - a parser never stops - and each names its input line and its text.
"""

from typing import Optional

from living_doc_utilities.authoring.framing import (
    CRITERION_HEADER_AS_TEXT,
    CRITERION_OUTSIDE_KEY,
    KEY_OUTSIDE_FRAME,
    LINE_AFTER_CLOSE,
    LINE_WITHOUT_MARKER,
    NO_FRAME,
    UNTERMINATED_FRAME,
    Frame,
    FramedLine,
    Role,
    Section,
    indented,
    opening_value,
)
from living_doc_utilities.contracts.codes import Code
from living_doc_utilities.contracts.envelope import ContractWarning

_PROBLEMS = {
    UNTERMINATED_FRAME: (
        Code.AUTHORING_ERROR,
        "The header is never closed: it is read up to its last comment line; close it with a rule.",
    ),
    KEY_OUTSIDE_FRAME: (Code.AUTHORING_ERROR, "A header key outside the header is not read."),
    LINE_WITHOUT_MARKER: (Code.AUTHORING_ERROR, "A line inside the header without its comment marker is not read."),
    LINE_AFTER_CLOSE: (
        Code.AUTHORING_ERROR,
        "A header line after a '*/' that closed the comment early is not read; the header's real end comes later.",
    ),
    CRITERION_HEADER_AS_TEXT: (
        Code.AUTHORING_WARNING,
        "An 'AC:' line inside a criterion is read as text: it is not at the criteria's indent, or it continues an item.",
    ),
    CRITERION_OUTSIDE_KEY: (
        Code.AUTHORING_ERROR,
        "An 'AC:' header outside 'acceptance_criteria:' is no criterion: write it under that key.",
    ),
}
# A PageObject comment with no `*/` is no valid TypeScript, and nothing in it is read.
UNCLOSED_COMMENT = "The header comment is never closed with '*/': nothing in it is read."


def line_context(entity_id: str, number: int, text: str) -> str:
    """A line warning's context: the entity, the line's 1-based input number and the whole line as written."""
    return f"entity_id={entity_id!r} line_no={number} line={text.strip()!r}"


def located(
    code: Code,
    message: str,
    context: str,
    entity_id: str = "",
    number: Optional[int] = None,
    ac_id: Optional[str] = None,
) -> ContractWarning:
    """A warning naming where it belongs, from what its emitter knows (`DEC-77`): an empty `entity_id` and a missing
    line `number` are not known, so their fields stay unset. `ac_id` is passed only when valid; `context` keeps
    its free text."""
    return ContractWarning(
        code=code.name,
        message=message,
        context=context,
        entity_id=entity_id or None,
        ac_id=ac_id,
        line_no=number or None,
    )


def report(
    code: Code, message: str, entity_id: str, framed: FramedLine, ac_id: Optional[str] = None
) -> ContractWarning:
    """One warning about one input line; `ac_id`, when given, is the valid id of the criterion the line is in."""
    return located(code, message, line_context(entity_id, framed.number, framed.raw), entity_id, framed.number, ac_id)


def missing_title(frame: Frame, banner: str, no_header: str = "") -> ContractWarning:
    """`MISSING_ENTITY_ID` for a banner with no title line: it names the opening rule, or line 1 with no banner.
    With no header found at all, `no_header`, when given, says so instead."""
    number = next((framed.number for framed in frame.lines if framed.role is Role.RULE), 1)
    found_none = any(problem.kind == NO_FRAME for problem in frame.problems)
    message = no_header if found_none and no_header else f"{banner} banner carries no 'LIVING DOC — ...' title line."
    return located(Code.MISSING_ENTITY_ID, message, f"title='' line_no={number}", number=number)


def at_title(warnings: list[ContractWarning], frame: Frame) -> list[ContractWarning]:
    """Title warnings, each naming the title's input line."""
    if frame.title is None:
        return warnings
    number = frame.title.number
    return [
        warning.model_copy(update={"context": f"{warning.context} line_no={number}", "line_no": number})
        for warning in warnings
    ]


def structural_warnings(
    frame: Frame, entity_id: str, unclosed: str = "", criterion_ids: Optional[dict[int, str]] = None
) -> list[ContractWarning]:
    """The frame's structural problems, each reported on the line it names. `unclosed`, when given, replaces the
    message for a header that never closes, for a format that reads nothing of it. `criterion_ids` maps each line of
    a criterion block to its valid id (`ac_grammar.criterion_ids`): a problem on such a line names the criterion."""
    raw_by_number = {framed.number: framed.raw for framed in frame.lines}
    ids = criterion_ids or {}
    warnings = []
    for problem in frame.problems:
        if problem.kind in _PROBLEMS:
            code, message = _PROBLEMS[problem.kind]
            if problem.kind == UNTERMINATED_FRAME and unclosed:
                message = unclosed
            context = line_context(entity_id, problem.line, raw_by_number.get(problem.line, ""))
            warnings.append(located(code, message, context, entity_id, problem.line, ids.get(problem.line)))
    return warnings


def unplaced_lines(
    frame: Frame,
    entity_id: str,
    criteria_section: str = "acceptance_criteria",
    skip_intro: bool = False,
    criterion_ids: Optional[dict[int, str]] = None,
) -> list[ContractWarning]:
    """Every line with text that no field reads: one in no section (before the first key or `##` heading, or
    after a rule), one in the criteria section outside every criterion, and a code block inside a criterion,
    which names the criterion by `criterion_ids` (`ac_grammar.criterion_ids`) when its id is valid.
    An HTML comment renders as nothing, so it holds no authored content; `skip_intro` spares the prose a
    cross-reference header may open with. A line a structural problem already names is left to that warning."""
    ids = criterion_ids or {}
    warnings: list[ContractWarning] = []
    seen_section = False
    in_html_comment = False
    named = {problem.line for problem in frame.problems}
    for framed in frame.lines:
        text = framed.line.text
        if in_html_comment or text.startswith("<!--"):
            in_html_comment = "-->" not in text
            continue
        if framed.number in named:
            continue
        if framed.role in (Role.HEADING, Role.KEY):
            seen_section = True
            continue
        if not text or framed.role not in (Role.TEXT, Role.CODE, Role.SUBHEADING):
            continue
        if framed.criterion:
            if framed.role is Role.CODE:
                warnings.append(
                    report(
                        Code.AUTHORING_WARNING,
                        "A code block inside an acceptance criterion is not read.",
                        entity_id,
                        framed,
                        ids.get(framed.number),
                    )
                )
            continue
        if framed.section is None and not (skip_intro and not seen_section):
            warnings.append(
                report(Code.AUTHORING_WARNING, "Line belongs to no section and was not read.", entity_id, framed)
            )
        elif framed.section == criteria_section and not framed.item_text:
            warnings.append(
                report(
                    Code.AUTHORING_WARNING,
                    "Line is outside every acceptance criterion and was not read.",
                    entity_id,
                    framed,
                )
            )
    return warnings


def scalar_lines(section: Section, single_value: bool, entity_id: str) -> tuple[list[str], list[ContractWarning]]:
    """A scalar key's value lines and what its other lines cost. A deeper line continues the value - unless the
    key takes a single value, when it is an `AUTHORING_ERROR` and not read; a part after a blank line continues
    the value and is reported once, on its first line. A line not deeper than the key fits no level and is not read."""
    values = [opening_value(section.opener)]
    warnings: list[ContractWarning] = []
    key = section.name
    after_blank = False
    for framed in section.lines:
        if not framed.line.text:
            after_blank = True
            continue
        if framed.line.indent <= section.opener.line.indent:
            warnings.append(
                report(
                    Code.AUTHORING_WARNING, f"Line under '{key}:' fits no level and was not read.", entity_id, framed
                )
            )
        elif single_value:
            warnings.append(
                report(
                    Code.AUTHORING_ERROR, f"'{key}:' takes a single value; this line was not read.", entity_id, framed
                )
            )
        else:
            if after_blank:
                # The first line after the blank one carries the warning: the part is reported once, not per line.
                after_blank = False
                warnings.append(
                    report(
                        Code.AUTHORING_WARNING,
                        f"'{key}:' value continues after a blank line; it was read as part of it.",
                        entity_id,
                        framed,
                    )
                )
            values.append(framed.line.raw.rstrip())
    return values, warnings


def first_occurrences(
    frame: Frame, entity_id: str, criterion_ids: Optional[dict[int, str]] = None
) -> tuple[Frame, list[ContractWarning]]:
    """A key or `##` heading written twice: only its first occurrence is read. A later one runs to the next key,
    heading or rule, so a `.feature` header's criteria under it are its too; each of its lines is reported and
    leaves the frame, so no field, criterion or other check reads it. A line of such a criterion names it by
    `criterion_ids` (`ac_grammar.criterion_ids` over this frame) when its id is valid."""
    ids = criterion_ids or {}
    seen: set[str] = set()
    repeated: Optional[str] = None
    lines: list[FramedLine] = []
    warnings: list[ContractWarning] = []
    for framed in frame.lines:
        # An issue body's `## AC:` heading is a criterion, not a section that can repeat.
        if framed.role in (Role.HEADING, Role.KEY) and framed.section is not None and not framed.criterion:
            repeated = framed.section if framed.section in seen else None
            seen.add(framed.section)
        elif framed.role in (Role.RULE, Role.TITLE):
            repeated = None
        if repeated is None or framed.role is Role.OUTSIDE:
            lines.append(framed)
            continue
        # A line rule 7 split off an input line carries no `raw` of its own; that input line is reported once.
        if framed.line.text and framed.raw:
            message = f"'{repeated}' appears earlier; only the first one is read, so this line is not."
            warnings.append(report(Code.AUTHORING_WARNING, message, entity_id, framed, ids.get(framed.number)))
        lines.append(framed._replace(role=Role.OUTSIDE, section=None, item_text=False, criterion=False))
    return Frame(lines, frame.problems), warnings


def nesting_github_reads_as_siblings(lines: list[FramedLine], entity_id: str, field_name: str) -> list[ContractWarning]:
    """An issue-body `- ` one space deeper than its parent's: the parser nests it, but GitHub renders a sibling
    (`D19`). Reported, so the author decides."""
    warnings: list[ContractWarning] = []
    markers: list[int] = []
    for framed in lines:
        line = indented(framed.line.raw)
        if not line.text.startswith("- "):
            continue
        while markers and markers[-1] >= line.indent:
            markers.pop()
        if markers and line.indent - markers[-1] == 1:
            warnings.append(
                report(
                    Code.AUTHORING_WARNING,
                    f"'{field_name}' item one space deeper than its parent: read as nested, GitHub shows a sibling.",
                    entity_id,
                    framed,
                )
            )
        markers.append(line.indent)
    return warnings
