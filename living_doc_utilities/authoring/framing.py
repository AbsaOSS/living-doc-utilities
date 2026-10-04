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
The framing pass: where a source's header starts and ends, and where each root-level section or key begins
and ends, decided once per input and by position. `normalize` rewrites by the frame and every parser reads
it, so no boundary is derived twice and no predicate reads a line's prose to find one.
"""

import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import NamedTuple, Optional

from living_doc_utilities.authoring.identity import _ENTITY_ID_RE, extract_living_doc_title

# --- the one indentation model: every frame reads a line through it ------------------------------------


class IndentedLine(NamedTuple):
    """One line with its comment marker already removed: `indent` is its leading-space count,
    `text` the rest with no surrounding whitespace, `raw` the line as given. A line's level is
    decided from `indent` - never from a stripped line, which has lost it."""

    indent: int
    text: str
    raw: str


def indented(content: str) -> IndentedLine:
    """`content` - a line after its comment marker and one following space are removed - as an `IndentedLine`."""
    text = content.lstrip()
    return IndentedLine(len(content) - len(text), text.rstrip(), content)


# Any bullet marker opening a list item, before (rule 1 rewrites the non-dash ones) or after normalisation.
_ITEM_MARKER_RE = re.compile(r"^[-–—*•+]\s")


class BulletItemTracker:
    """The open item of a bullet-list section. A line indented deeper than that item's marker is the
    item's text - wrapped text or a nested item - and never a key or an `AC:` header, whatever it
    reads like (a wrapped item may read `status: x`). Every other line closes the item and is read at
    face value, so an indented key outside a bullet item still counts. Every frame with a bullet
    section runs one."""

    def __init__(self) -> None:
        self._marker_indent: Optional[int] = None

    def continues_item(self, line: IndentedLine) -> bool:
        """True when `line` belongs to the open item; otherwise the item is closed and False."""
        if self._marker_indent is not None and line.text and line.indent > self._marker_indent:
            return True
        self._marker_indent = None
        return False

    def read(self, line: IndentedLine, in_bullet_section: bool) -> None:
        """Opens an item when `line` starts one inside a bullet-list section."""
        opens = in_bullet_section and _ITEM_MARKER_RE.match(line.text) is not None
        self._marker_indent = line.indent if opens else None


# --- the frame ------------------------------------------------------------------------------------------


class Role(Enum):
    """What a line is in its source's structure, decided by its position and its line syntax."""

    OUTSIDE = auto()  # not a line of the frame: passes through, and no parser reads it
    CODE = auto()  # a fenced code block's line: content of its section, never rewritten
    BLANK = auto()  # no text: layout, so it ends neither the open key nor its open item
    RULE = auto()  # a banner rule, the header comment's opening line, or its bare close
    TITLE = auto()  # the banner title: the first line after the opening rule, whatever it reads like
    HEADING = auto()  # opens a section: an issue body's `##` heading; a Gherkin `Feature:`, `Background:`, `Scenario:`
    CRITERION = auto()  # an acceptance criterion's header: opens its criterion block
    SUBHEADING = auto()  # any other Markdown heading: content of its section, never rewritten as a value
    KEY = auto()  # a header key's own line: opens that key's section
    TAG = auto()  # a Gherkin tag line
    COMMENT = auto()  # a Gherkin comment line
    TEXT = auto()  # any other line of the frame: content of its section, if it is in one


class FramedLine(NamedTuple):
    """One input line as the frame places it. `prefix` is its comment marker, kept verbatim; `line` the
    content after it. `section` is the slug or key of the root-level section it is in. `item_text` marks a line
    deeper than an open bullet item's marker, and `criterion` a line of an acceptance-criterion block.
    `number` is its 1-based line in the input, which every warning about the line names."""

    raw: str
    prefix: str
    line: IndentedLine
    role: Role
    section: Optional[str] = None
    item_text: bool = False
    criterion: bool = False
    number: int = 0

    @property
    def rendered(self) -> str:
        """The line as written out: its marker, then its content."""
        return self.prefix + self.line.raw


# The structural problems a frame reports - never a missing required key, which is checked above the parser.
NO_FRAME = "no_frame"  # no banner rule, or no header comment, was found
UNTERMINATED_FRAME = "unterminated_frame"  # the frame opened and never closed
KEY_OUTSIDE_FRAME = "key_outside_frame"  # a `.feature` key line between the header's end and `Feature:`
LINE_WITHOUT_MARKER = "line_without_marker"  # a line with text inside the frame that lacks the comment marker
CRITERION_HEADER_AS_TEXT = "criterion_header_as_text"  # an `AC:` line in a criterion block read as text, not a header
LINE_AFTER_CLOSE = "line_after_close"  # a ` * ` line between a PageObject comment's early close and its real end


class Problem(NamedTuple):
    """One structural problem: `kind` is one of the constants above, `line` the 1-based input line it names."""

    kind: str
    line: int


@dataclass
class Frame:
    """The framing pass's one result: every line of the input, placed, plus the structural problems found.
    `normalize` rewrites by it, and the parser of the same format reads it."""

    lines: list[FramedLine]
    problems: list[Problem] = field(default_factory=list)

    @property
    def title(self) -> Optional[FramedLine]:
        """The banner's title line, when the frame has one."""
        return next((framed for framed in self.lines if framed.role is Role.TITLE), None)


def names_an_entity(frame: Frame) -> bool:
    """Whether the frame found a header that names an entity: a title line, found by position, whose
    `LIVING DOC — …` text carries an entity id. Only then is there a header - and only then does a parser read an
    entity from it, and `normalize` rewrite it."""
    if frame.title is None:
        return False
    title = extract_living_doc_title([frame.title.line.raw])
    return title is not None and _ENTITY_ID_RE.search(title) is not None


class Section(NamedTuple):
    """One root-level section: its `name` (a heading's slug, a key), the line that opens it, and the lines in it."""

    name: str
    opener: FramedLine
    lines: list[FramedLine]


def sections(frame: Frame) -> list[Section]:
    """Each root-level section in order. A parser reads its sections here and never finds a boundary itself."""
    result: list[Section] = []
    for framed in frame.lines:
        if framed.role in (Role.HEADING, Role.KEY) and framed.section is not None:
            result.append(Section(framed.section, framed, []))
        elif result and framed.section == result[-1].name:
            result[-1].lines.append(framed)
    return result


def opening_value(opener: FramedLine) -> str:
    """The value on a section's opening line: what follows the key's (or the Gherkin keyword's) colon."""
    return opener.line.text.split(":", 1)[1].lstrip()


class CriterionBlock(NamedTuple):
    """One acceptance criterion as the frame bounds it: its header line and the lines of its block."""

    header: FramedLine
    lines: list[FramedLine]


def opens_criterion(framed: FramedLine) -> bool:
    """Whether `framed` is a criterion's header: a `CRITERION` line, or an issue body's `## AC:` heading."""
    return framed.role is Role.CRITERION or (framed.role is Role.HEADING and framed.criterion)


def criterion_blocks(frame: Frame) -> list[CriterionBlock]:
    """Each criterion block in order. The frame alone decides where one starts and ends, so the grammar reads
    exactly these lines and finds no boundary itself. A line outside the frame - a blank line without its
    comment marker, a reported line without one - neither belongs to a block nor ends it."""
    blocks: list[CriterionBlock] = []
    open_block: Optional[CriterionBlock] = None
    for framed in frame.lines:
        if framed.role is Role.OUTSIDE:
            continue
        if opens_criterion(framed):
            open_block = CriterionBlock(framed, [])
            blocks.append(open_block)
        elif open_block is not None and framed.criterion:
            open_block.lines.append(framed)
        else:
            open_block = None
    return blocks


def _placed(
    framed: FramedLine, role: Role, section: Optional[str] = None, item_text: bool = False, criterion: bool = False
) -> FramedLine:
    return framed._replace(role=role, section=section, item_text=item_text, criterion=criterion)


def _title(lines: list[FramedLine], opening: int, stop: int, rule_re: "re.Pattern[str]") -> Optional[int]:
    """The banner title's index: the first line with text after the `opening` rule, unless a rule comes first.
    Found by position alone, so no line's prose - a note quoting `LIVING DOC — …` - is ever taken for it."""
    for index in range(opening + 1, stop):
        if lines[index].role is Role.OUTSIDE or not lines[index].line.text:
            continue
        return None if rule_re.match(lines[index].line.text) else index
    return None


# --- the issue body: `##` sections --------------------------------------------------------------------

# CommonMark: a heading may be indented by up to three spaces.
_MD_HEADING_RE = re.compile(r"^ {0,3}(?P<hashes>#{1,6})\s+(?P<text>.*)$")
# A criterion header in an issue body, with or without a Markdown heading or emphasis in front of it.
_AC_HEADER_FULL_RE = re.compile(r"^(?P<lead>[#*]{0,3}\s*)AC:(?P<id>\S+)\s*\((?P<inner>[^)]*)\)(?P<trail>.*)$")


def _slugify_section(text: str) -> str:
    """A heading's text as its section's name: lowercase, every run of spaces and underscores one `_`."""
    return re.sub(r"[\s_]+", "_", text.strip().lower())


def frame_issue_body(lines: list[FramedLine], bullet_sections: frozenset[str]) -> Frame:
    """Places an issue body's lines. Each `##` heading outside a fence opens the section its slug names; text
    before the first belongs to none. A criterion block runs from an `AC:` header to the next heading. In a
    bullet section and in a criterion block, a line deeper than the open item's marker is that item's text,
    across blank lines as a Markdown list item is. An `AC:` line there is no criterion: in a bullet field it is
    the item's text (`D20`); in a criterion block it is reported too."""
    placed: list[FramedLine] = []
    problems: list[Problem] = []
    section: Optional[str] = None
    criterion = False
    items = BulletItemTracker()
    for framed in lines:
        if framed.role is Role.CODE or not framed.line.text:
            role = Role.CODE if framed.role is Role.CODE else Role.BLANK
            placed.append(_placed(framed, role, section, criterion=criterion))
            continue
        tracks_items = criterion or section in bullet_sections
        if tracks_items and items.continues_item(framed.line):
            if criterion and _AC_HEADER_FULL_RE.match(framed.line.raw):
                problems.append(Problem(CRITERION_HEADER_AS_TEXT, framed.number))
            placed.append(_placed(framed, Role.TEXT, section, item_text=True, criterion=criterion))
            continue
        heading_m = _MD_HEADING_RE.match(framed.line.raw)
        role = Role.TEXT if heading_m is None else Role.SUBHEADING
        if heading_m is not None and len(heading_m.group("hashes")) == 2:
            role, section = Role.HEADING, _slugify_section(heading_m.group("text"))
        if _AC_HEADER_FULL_RE.match(framed.line.raw):
            criterion = True
            role = Role.CRITERION if role is not Role.HEADING else role
        elif heading_m is not None:
            criterion = False
        if tracks_items or criterion:
            items.read(framed.line, True)
        placed.append(_placed(framed, role, section, criterion=criterion))
    return Frame(placed, problems)


# --- the headers: key sections inside a banner --------------------------------------------------------------


class _HeaderWalk:
    """Places a header's body lines one by one: which key's section each is in, and whether it is an open
    bullet item's text. A rule ends the open key, a key line opens the next, and a blank line ends nothing."""

    def __init__(self, bullet_sections: frozenset[str]) -> None:
        self._bullet_sections = bullet_sections
        self._items = BulletItemTracker()
        self._section: Optional[str] = None
        self.criterion = False
        # The key level: the indent of the header's first key. A key-shaped line deeper than it is content.
        self._key_level: Optional[int] = None
        # The criterion level: the indent of the header's first `AC:` line. An `AC:` line elsewhere is text.
        self._criterion_level: Optional[int] = None
        self.problems: list[Problem] = []

    def is_key_level(self, line: IndentedLine) -> bool:
        """Whether a key-shaped line sits at the key level. Before the first key, a criterion block's own
        `preconditions:` is never taken for one."""
        if self._key_level is None:
            return not self.criterion
        return line.indent <= self._key_level

    def is_criterion_level(self, line: IndentedLine) -> bool:
        """Whether an `AC:` line sits where the header's criteria start: the first one sets the level."""
        if self._criterion_level is None:
            self._criterion_level = line.indent
        return line.indent == self._criterion_level

    def _close(self, framed: FramedLine, criterion: bool) -> None:
        self._items.continues_item(framed.line)
        self._section, self.criterion = None, criterion

    def title(self, framed: FramedLine) -> FramedLine:
        self._close(framed, False)
        return _placed(framed, Role.TITLE)

    def rule(self, framed: FramedLine) -> FramedLine:
        self._close(framed, False)
        return _placed(framed, Role.RULE)

    def blank(self, framed: FramedLine) -> FramedLine:
        """A blank line is layout: it ends neither the open key nor its open item, as in a Markdown list."""
        return _placed(framed, Role.BLANK, self._section, criterion=self.criterion)

    def item_text(self, framed: FramedLine) -> Optional[FramedLine]:
        """The line placed as the open item's text, or `None` when it closes the item instead."""
        if not self._items.continues_item(framed.line):
            return None
        return _placed(framed, Role.TEXT, self._section, item_text=True, criterion=self.criterion)

    def criterion_header(self, framed: FramedLine) -> FramedLine:
        """An `AC:` header: its criterion block holds every line up to the next header, key or rule."""
        self._section, self.criterion = None, True
        self._items.read(framed.line, False)
        return _placed(framed, Role.CRITERION, criterion=True)

    def key(self, framed: FramedLine, key: str) -> FramedLine:
        """A key line: it opens its key's section, ends a criterion block, and the first one sets the key level."""
        if self._key_level is None:
            self._key_level = framed.line.indent
        self._section, self.criterion = key, False
        self._items.read(framed.line, False)
        return _placed(framed, Role.KEY, key)

    def text(self, framed: FramedLine) -> FramedLine:
        self._items.read(framed.line, self.criterion or self._section in self._bullet_sections)
        return _placed(framed, Role.TEXT, self._section, criterion=self.criterion)


# --- the `.feature` header: `# key:` sections between `# ===` rules ------------------------------------

# Gherkin's `Feature:` line: a `.feature` header's rules are only looked for above it.
_FEATURE_LINE_RE = re.compile(r"^Feature:\s*.*$")
_FH_RULE_RE = re.compile(r"^#\s*=+\s*$")
_RULE_TEXT_RE = re.compile(r"^=+$")
_FH_KEY_RE = re.compile(r"^(?P<key>[a-zA-Z_][a-zA-Z0-9_]*):")
# A `.feature` criterion header: any line starting `AC:`; the grammar reports one that is malformed.
_AC_PREFIX_RE = re.compile(r"^AC:")


def frame_feature_header(lines: list[FramedLine], bullet_sections: frozenset[str]) -> Frame:
    """Places a `.feature` file's lines. The frame runs from the first `# ===` rule above `Feature:` to the last;
    its title is the first line after the opening rule. Inside it every line with text is a header line: a
    `key:` line at the key level opens that key's section, and an `AC:` header at the criterion level opens a
    criterion block that runs to the next `AC:` header, key or rule. Neither is read on an open bullet item's
    text. A blank line without `#` is no header line and closes nothing, as a blank line in a Markdown list does
    not. With no rule at all there is no header; nothing outside the frame is read."""
    end = next((i for i, framed in enumerate(lines) if _FEATURE_LINE_RE.match(framed.raw.strip())), len(lines))
    rules = [i for i in range(end) if _FH_RULE_RE.match(lines[i].raw)]
    problems: list[Problem] = []
    if not rules:
        # No header: its start was not found, so no line of the file is a header line.
        problems.append(Problem(NO_FRAME, 1))
        start, stop, title = 1, 0, None
    elif len(rules) == 1:
        # Never closed: the header is still read, up to its last comment line before any other line, and reported.
        problems.append(Problem(UNTERMINATED_FRAME, rules[0] + 1))
        start, stop = rules[0], _last_comment_line(lines, rules[0], end)
        title = _title(lines, start, stop + 1, _RULE_TEXT_RE)
    else:
        start, stop = rules[0], rules[-1]
        title = _title(lines, start, stop, _RULE_TEXT_RE)

    walk = _HeaderWalk(bullet_sections)
    placed: list[FramedLine] = []
    for index, framed in enumerate(lines):
        # Phase 1 marked each comment line `TEXT`; only those are header lines. A line between the rules with text
        # and no `#` breaks the format: it is not read, and the frame reports it.
        in_frame = start <= index <= stop and framed.role is not Role.OUTSIDE
        if rules and start <= index <= stop and not in_frame and framed.line.text:
            problems.append(Problem(LINE_WITHOUT_MARKER, framed.number))
        if index == title:
            placed.append(walk.title(framed))
        elif in_frame:
            placed.append(_place_header_line(walk, framed))
        else:
            # A key between the header's end and `Feature:` is out of place. Above the opening rule the header has not
            # started, so a comment there is no header line: Gherkin's own `# language:` sits on line 1.
            if rules and stop < index < end and framed.role is not Role.OUTSIDE and _FH_KEY_RE.match(framed.line.text):
                problems.append(Problem(KEY_OUTSIDE_FRAME, framed.number))
            placed.append(_placed(framed, Role.OUTSIDE))
    return Frame(placed, problems + walk.problems)


def _last_comment_line(lines: list[FramedLine], opening: int, end: int) -> int:
    """The index of an unclosed header's last line: the last comment line after its `opening` rule before the first
    line with text that is no comment (a tag, `Feature:`), or before `end`. A blank line is layout, so it ends nothing.
    """
    last = opening
    for index in range(opening + 1, end):
        if lines[index].role is not Role.OUTSIDE:
            last = index
        elif lines[index].line.text:
            break
    return last


def _place_header_line(walk: _HeaderWalk, framed: FramedLine) -> FramedLine:
    """A `.feature` header body line. A rule ends a criterion block wherever it sits, but deeper than a key's
    open item it is that item's text. An `AC:` line is a criterion header only at the criterion level and never
    on an item's text; inside a criterion block, one that is not is reported."""
    text = framed.line.text
    if not text:
        return walk.blank(framed)
    is_rule = _RULE_TEXT_RE.match(text) is not None
    looks_like_header = _AC_PREFIX_RE.match(text) is not None
    continued = None if is_rule and walk.criterion else walk.item_text(framed)
    if continued is not None:
        if looks_like_header and continued.criterion:
            walk.problems.append(Problem(CRITERION_HEADER_AS_TEXT, framed.number))
        return continued
    if is_rule:
        return walk.rule(framed)
    if looks_like_header:
        if walk.is_criterion_level(framed.line):
            return walk.criterion_header(framed)
        if walk.criterion:
            walk.problems.append(Problem(CRITERION_HEADER_AS_TEXT, framed.number))
        return walk.text(framed)
    # A key at the key level opens its section, and ends a criterion block; a deeper key-shaped line is content.
    key_m = _FH_KEY_RE.match(text) if walk.is_key_level(framed.line) else None
    return walk.text(framed) if key_m is None else walk.key(framed, key_m.group("key"))


# --- the PageObject header: the leading `/* ... */` comment ---------------------------------------------

_COMMENT_OPEN_RE = re.compile(r"^\s*/\*")
# The header comment's close: the first line that ends in `*/` - never a `*/` inside a value, which leaves the
# frame open. What the line carries before the `*/` is still header text, unless it is a rule: `=== */`, ` */`.
_COMMENT_CLOSE_RE = re.compile(r"\*/\s*$")
_PO_RULE_CONTENT_RE = re.compile(r"^=+\s*(\*?/)?\s*$")
_PO_BARE_CLOSE_CONTENT_RE = re.compile(r"^\*?/$")
_PO_KEY_RE = re.compile(r"^(?P<key>[a-zA-Z][a-zA-Z0-9_-]*)\s*:")


def without_comment_close(text: str) -> str:
    """`text` without the comment's closing `*/` at its end. On the header's last line the close belongs to the
    comment, not to a value written there; no other header line ends in `*/`, as the frame ends at the first one."""
    return _COMMENT_CLOSE_RE.sub("", text).rstrip()


def frame_page_object(lines: list[FramedLine], bullet_keys: frozenset[str]) -> Frame:
    """Places a PageObject file's lines. The frame is the file's first `/* ... */` comment, from its opening
    line to the first line that ends in `*/`; its title is the first line after the opening one. Inside it
    every ` * ` line is a header line: a `key:` line opens that key's section, a `===` rule ends it, and a blank
    ` *` line ends nothing. Everything else, a later JSDoc block included, is outside."""
    opening = next((i for i, framed in enumerate(lines) if _COMMENT_OPEN_RE.match(framed.raw)), None)
    close = None
    if opening is not None:
        close = next((i for i in range(opening, len(lines)) if _COMMENT_CLOSE_RE.search(lines[i].raw)), None)
    if opening is None or close is None:
        problem = Problem(NO_FRAME, 1) if opening is None else Problem(UNTERMINATED_FRAME, opening + 1)
        return Frame([_placed(framed, Role.OUTSIDE) for framed in lines], [problem])

    title = _title(lines, opening, close + 1, _PO_RULE_CONTENT_RE)
    walk = _HeaderWalk(bullet_keys)
    placed: list[FramedLine] = []
    problems = [
        Problem(LINE_WITHOUT_MARKER, lines[index].number)
        for index in range(opening + 1, close)
        if lines[index].role is Role.OUTSIDE and lines[index].line.text
    ]
    # A value ending in `*/` closed the comment early when a later ` * ` line, before any code, closes it again: the
    # header's real end is there, and each line up to it is reported. With no later close the header ends here.
    after = _star_lines_after(lines, close)
    ends = [index for index, framed in enumerate(after) if _COMMENT_CLOSE_RE.search(framed.raw)]
    if ends:
        problems += [Problem(LINE_AFTER_CLOSE, framed.number) for framed in after[: ends[-1] + 1] if framed.line.text]
    for index, framed in enumerate(lines):
        # Phase 1 marked each ` * ` line `TEXT`; only those are header lines, the close line's text included.
        closes = index == close and (
            framed.role is Role.OUTSIDE or _PO_BARE_CLOSE_CONTENT_RE.match(framed.line.text) is not None
        )
        if index == opening or closes:
            placed.append(walk.rule(framed))
        elif not opening < index <= close or framed.role is Role.OUTSIDE:
            placed.append(_placed(framed, Role.OUTSIDE))
        elif index == title:
            placed.append(walk.title(framed))
        else:
            placed.append(_place_page_object_line(walk, framed))
    return Frame(placed, problems)


def _star_lines_after(lines: list[FramedLine], close: int) -> list[FramedLine]:
    """The ` * ` lines after the comment's close, up to the first line of code; a blank line between them ends
    nothing."""
    found: list[FramedLine] = []
    for framed in lines[close + 1 :]:
        if framed.role is not Role.OUTSIDE:
            found.append(framed)
        elif framed.line.text:
            break
    return found


def _place_page_object_line(walk: _HeaderWalk, framed: FramedLine) -> FramedLine:
    """A PageObject header body line: an open item's text is placed first, so a deeper `===` stays its text."""
    if not framed.line.text:
        return walk.blank(framed)
    continued = walk.item_text(framed)
    if continued is not None:
        return continued
    if _PO_RULE_CONTENT_RE.match(framed.line.text):
        return walk.rule(framed)
    key_m = _PO_KEY_RE.match(framed.line.text) if walk.is_key_level(framed.line) else None
    return walk.text(framed) if key_m is None else walk.key(framed, key_m.group("key"))


# --- the scenario file: Gherkin's keyword lines ----------------------------------------------------------

FEATURE = "Feature"
BACKGROUND = "Background"
SCENARIO = "Scenario"
_GHERKIN_SECTION_RES = (
    (FEATURE, _FEATURE_LINE_RE),
    (BACKGROUND, re.compile(r"^Background:\s*.*$")),
    (SCENARIO, re.compile(r"^Scenario(?:\s+Outline)?:\s*.*$")),
)


def frame_scenario_file(lines: list[FramedLine]) -> Frame:
    """Places a `.feature` file's Gherkin body. `Feature:`, `Background:` and each `Scenario:` or `Scenario
    Outline:` line opens a section named by its keyword; a tag line, a comment line and a blank line are
    marked as such, and every other line is its section's text."""
    placed: list[FramedLine] = []
    section: Optional[str] = None
    for framed in lines:
        text = framed.line.text
        keyword = next((name for name, keyword_re in _GHERKIN_SECTION_RES if keyword_re.match(text)), None)
        if keyword is not None:
            section, role = keyword, Role.HEADING
        elif not text:
            role = Role.BLANK
        elif text.startswith("#"):
            role = Role.COMMENT
        elif text.startswith("@"):
            role = Role.TAG
        else:
            role = Role.TEXT
        placed.append(_placed(framed, role, section))
    return Frame(placed)
