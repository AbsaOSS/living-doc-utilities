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
The one normalisation layer over the five authoring source formats: rewrites non-canonical
dashes, bullet markers, case, version form and whitespace per format, never touching fenced
or inline code, Gherkin step text, TypeScript, or free prose. It runs in three phases around
`framing`: rule 6 on each line, then the frame, then every other rule by the frame's sections.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple, Optional

from living_doc_utilities.authoring.framing import (
    _AC_HEADER_FULL_RE,
    Frame,
    FramedLine,
    IndentedLine,
    Role,
    frame_feature_header,
    frame_issue_body,
    frame_page_object,
    frame_scenario_file,
    indented,
    names_an_entity,
    opening_value,
    opens_criterion,
)
from living_doc_utilities.authoring.identity import _ENTITY_ID_RE
from living_doc_utilities.contracts.common import DocType

# Rule names for the seven authoring rules (plus 5b); doubles as normalisation_cases.yaml's `rule` column.
RULE_BULLET_MARKER = "bullet_marker"
RULE_AC_HEADER_SEPARATOR = "ac_header_separator"
RULE_STATE_CASING = "state_casing"
RULE_VERSION_FORM = "version_form"
RULE_ENTITY_NAME_DASH = "entity_name_dash"
RULE_TITLE_ID_SEPARATOR = "title_id_separator"
RULE_WHITESPACE = "whitespace"
RULE_INLINE_AC_DESCRIPTION = "inline_ac_description"


class SourceFormat(str, Enum):
    """The five authoring surfaces `normalize` understands."""

    ISSUE_BODY = "issue_body"
    FEATURE_HEADER = "feature_header"
    SCENARIO_FILE = "scenario_file"
    PAGE_OBJECT = "page_object"
    HTML_MARKDOWN = "html_markdown"


class Change(NamedTuple):
    """One rewritten line: `line` is its 1-based position in `NormalizedSource.lines`
    (or 1 for a title, which has no line structure of its own)."""

    line: int
    rule: str
    before: str
    after: str


# Which of an entity type's sections are bullet-list sections; data only, nothing else branches on entity type.
TYPE_PROFILES: dict[DocType, frozenset[str]] = {
    "DocumentedUserStory": frozenset({"business_value", "preconditions", "not_in_scope", "notes"}),
    "DocumentedFeature": frozenset({"notes"}),
    "DocumentedFunctionality": frozenset({"rationale", "preconditions", "not_in_scope", "notes"}),
}

# The PageObject header keys whose value is a bullet list, whatever entity type `normalize` is given;
# `page_object.py::_BULLET_KEYS` is this same set, under the name the parser uses.
PO_BULLET_KEYS: frozenset[str] = frozenset({"notes"})


@dataclass
class NormalizedSource:
    """`normalize`'s result: the full reconstructed text (same shape as the input, only
    content-role lines rewritten) plus the list of changes that produced it."""

    lines: list[str]
    changes: list[Change]

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


# --- low-level, position-driven token reshaping: reshape by position only; validation lives in ac_grammar.py ---

# Canonical "- " bullet line; shared by ac_grammar (an AC block's own bullets) and `issue_body.py::extract_bullets`.
_BULLET_RE = re.compile(r"^-\s?(?P<text>.*)$")

_BULLET_START_RE = re.compile(r"^(?P<indent>\s*)(?P<marker>[–—*•+])(?P<sp>\s)(?P<rest>.*)$")
# A dash separates header segments only with whitespace on a side, else it's a hyphen inside a token (e.g. "in-review").
_DASH_SEP_CAP_RE = re.compile(r"(\s*[-–—]\s+|\s+[-–—]\s*)")
_VERSION_RESHAPE_RE = re.compile(r"^[vV]?(\d+)(?:\.(\d+))?(?:\.(\d+))?$")
_REMOVAL_PLANNED_CLAUSE_RE = re.compile(r"^removal[ \t]+planned[ \t]+(\S+)$", re.IGNORECASE)
_AC_TRAIL_DESC_RE = re.compile(r"^\s*[-–—]\s*(?P<desc>.+)$")


def _fix_bullet_marker(m: "re.Match[str]") -> str:
    """`m` is the caller's own `_BULLET_START_RE.match(...)` - callers already need it to
    decide whether to call this at all, so it is passed in rather than matched again here."""
    return f"{m.group('indent')}-{m.group('sp')}{m.group('rest')}"


def _reshape_version_form(token: str) -> str:
    m = _VERSION_RESHAPE_RE.match(token)
    if not m or m.group(2) is None:
        # No minor part (e.g. bare "v1" or "1"): left as-is, malformed-AC error is downstream's job.
        return token
    major, minor, patch = m.group(1), m.group(2), m.group(3) or "0"
    return f"v{major}.{minor}.{patch}"


# Also used by `ac_grammar.py::_slug_placeholder_name`, which folds a placeholder name the same way.
_WORD_SEP_RE = re.compile(r"[\s\-]+")


def _canonicalize_token_case(token: str) -> str:
    return _WORD_SEP_RE.sub("_", token.strip().lower())


_NBSP = chr(0xA0)  # kept out of string literals - formatters fold   escapes into a literal, invisible byte
_INDENT_WS_RE = re.compile("^[ \t" + _NBSP + "]*")


def _fix_indentation_whitespace(line: str, tab_stop: int = 1) -> str:
    """Rule 6 on `line`'s indent: a no-break space becomes one space, a tab moves to the next multiple of
    `tab_stop`. A header passes 1 (one space per tab); an issue body passes 4, the tab stop GitHub renders."""
    m = _INDENT_WS_RE.match(line)
    lead = m.group(0) if m else ""
    if not lead or ("\t" not in lead and _NBSP not in lead):
        return line
    new_lead = lead.replace(_NBSP, " ").expandtabs(tab_stop)
    return new_lead + line[len(lead) :]


class ItemText:
    """The lines under one bullet item whose `- ` sits at `marker`, as they add to that item's string.
    Wrapped text before any nested item is joined with a space, as a flat list always was. A nested
    `- ` item, and every line after it, is kept as extracted: on its own line, at its indent relative
    to `marker` (`"Parent.\\n  - Child."`), so the consumer of the field decides how to render it.
    Shared by `issue_body.py::extract_bullets` and the criterion grammar."""

    def __init__(self, marker: int) -> None:
        self.marker = marker
        # Marker indents of the open nested items, outermost first.
        self._open: list[int] = []
        # Indent of a dropped misindented line: every line deeper than it is dropped with it.
        self._dropped: Optional[int] = None

    def fragment(self, line: IndentedLine) -> Optional[str]:
        """What `line`, deeper than the marker, appends to the item's string; `None` when the line is
        dropped: a nested `- ` whose indent fits no open level, or a line deeper than such a `- `."""
        if self._dropped is not None:
            if line.indent > self._dropped:
                return None
            self._dropped = None
        if _BULLET_RE.match(line.text):
            closed = False
            while self._open and self._open[-1] > line.indent:
                self._open.pop()
                closed = True
            if not self._open or self._open[-1] != line.indent:
                if closed:
                    # Back out of a nested item, but not to the indent of any item still open.
                    self._dropped = line.indent
                    return None
                self._open.append(line.indent)
        elif not self._open:
            return f" {line.text}"
        return "\n" + " " * (line.indent - self.marker) + line.text


def _rewrite_ac_header_inner(inner: str) -> tuple[str, set[str]]:
    """Rules 2, 3 and 4 applied to an AC header's already-isolated paren content."""
    fired: set[str] = set()
    stripped = inner.strip()
    parts = _DASH_SEP_CAP_RE.split(stripped)
    segments = parts[0::2]
    seps = parts[1::2]

    for sep in seps:
        if sep != " - ":
            fired.add(RULE_AC_HEADER_SEPARATOR)

    if len(segments) == 1:
        seg0 = segments[0].strip()
        canon = _canonicalize_token_case(seg0)
        if canon != seg0:
            fired.add(RULE_STATE_CASING)
        return canon, fired

    norm_segments: list[str] = []
    last_index = len(segments) - 1
    for idx, seg in enumerate(segments):
        seg_stripped = seg.strip()
        if idx == last_index and idx > 0:
            rp_m = _REMOVAL_PLANNED_CLAUSE_RE.match(seg_stripped)
            if rp_m:
                version_raw = rp_m.group(1)
                rp_version = _reshape_version_form(version_raw)
                if rp_version != version_raw:
                    fired.add(RULE_VERSION_FORM)
                keyword_raw = seg_stripped[: rp_m.start(1)].rstrip()
                if keyword_raw != "removal planned":
                    fired.add(RULE_STATE_CASING)
                norm_segments.append(f"removal planned {rp_version}")
                continue
        if idx == 0:
            reshaped = _reshape_version_form(seg_stripped)
            if reshaped != seg_stripped:
                fired.add(RULE_VERSION_FORM)
            norm_segments.append(reshaped)
            continue
        canon = _canonicalize_token_case(seg_stripped)
        if canon != seg_stripped:
            fired.add(RULE_STATE_CASING)
        norm_segments.append(canon)

    return " - ".join(norm_segments), fired


def _rewrite_ac_header_content(
    m: "re.Match[str]", inline_description: bool, bullet_indent: str
) -> tuple[list[str], set[str]]:
    """Rewrites one AC header's content (no comment-wrapper prefix). Returns the
    produced content line(s) - two when rule 7 splits an inline description onto its
    own bullet - and the set of rules that fired."""
    ac_id, inner, trail = m.group("id"), m.group("inner"), m.group("trail")
    new_inner, fired = _rewrite_ac_header_inner(inner)

    trail_m = _AC_TRAIL_DESC_RE.match(trail)
    if not trail_m:
        return [f"AC:{ac_id} ({new_inner}){trail}"], fired

    desc_text = trail_m.group("desc").strip()
    fired = set(fired)
    fired.add(RULE_INLINE_AC_DESCRIPTION)

    if inline_description:
        return [f"AC:{ac_id} ({new_inner}) - {desc_text}"], fired

    return [f"AC:{ac_id} ({new_inner})", f"{bullet_indent}- {desc_text}"], fired


def _fired_if(changed: bool, rule: str) -> set[str]:
    """`{rule}` when `changed`, else the empty set - the single-rule `fired` shape most
    `_emit` call sites below build from a plain before/after comparison."""
    return {rule} if changed else set()


def _emit(out: list[FramedLine], changes: list[Change], fired: set[str], framed: FramedLine, content: str) -> None:
    """Emits `framed` with `content` after its marker, one `Change` per rule in `fired`; when no rule
    fired, `framed` goes out as it came in."""
    if not fired:
        out.append(framed)
        return
    rewritten = framed._replace(line=indented(content))
    out.append(rewritten)
    for rule in sorted(fired):
        changes.append(Change(len(out), rule, framed.raw, rewritten.rendered))


def _emit_description(out: list[FramedLine], changes: list[Change], header: FramedLine, content: str) -> None:
    """Emits the bullet rule 7 splits off a criterion header, in that header's section."""
    bullet = header._replace(raw="", line=indented(content), role=Role.TEXT)
    out.append(bullet)
    changes.append(Change(len(out), RULE_INLINE_AC_DESCRIPTION, "", bullet.rendered))


def _whitespace(framed: FramedLine) -> set[str]:
    """Rule 6, when phase 1 rewrote this line's indent."""
    return _fired_if(framed.rendered != framed.raw, RULE_WHITESPACE)


def _criterion_header(framed: FramedLine, text: str) -> Optional["re.Match[str]"]:
    """`text` read as a criterion header: only on the line the frame placed as one."""
    return _AC_HEADER_FULL_RE.match(text) if opens_criterion(framed) else None


def _rewrite_bullet(content: str) -> tuple[str, set[str]]:
    """Rule 1 on `content` when it opens a list item; `content` unchanged otherwise."""
    bullet_m = _BULLET_START_RE.match(content)
    if bullet_m is None:
        return content, set()
    marked = _fix_bullet_marker(bullet_m)
    return marked, _fired_if(marked != content, RULE_BULLET_MARKER)


# --- entity/title rules (5, 5b): _ENTITY_ID_RE lives in identity.py, imported here not redefined ---

_TITLE_SEP_AFTER_ID_RE = re.compile(r"^\s*([-–—:|·])\s*")
# An en/em dash always separates; a plain hyphen only when whitespace flanks it (else e.g. "Password-reset").
_TITLE_DASH_RE = re.compile(r"\s*[–—]\s*|\s*-\s+|\s+-\s*")
_TITLE_CANONICAL_SEP = " · "


def normalize_title(title: str) -> tuple[str, list[Change]]:
    """Rules 5 and 5b applied to an entity/title string (an issue title, a `.feature` or
    PageObject banner). Text before the entity id is left untouched."""
    changes: list[Change] = []
    id_m = _ENTITY_ID_RE.search(title)
    if not id_m:
        return title, changes

    head, rest = title[: id_m.end()], title[id_m.end() :]

    sep_m = _TITLE_SEP_AFTER_ID_RE.match(rest)
    if sep_m:
        matched = sep_m.group(0)
        if matched != _TITLE_CANONICAL_SEP:
            changes.append(Change(1, RULE_TITLE_ID_SEPARATOR, matched, _TITLE_CANONICAL_SEP))
        remainder = rest[sep_m.end() :]
        tail = _TITLE_DASH_RE.sub(lambda dm: _record_title_dash(dm, changes), remainder)
        rest = _TITLE_CANONICAL_SEP + tail
    else:
        rest = _TITLE_DASH_RE.sub(lambda dm: _record_title_dash(dm, changes), rest)

    return head + rest, changes


def _record_title_dash(dm: "re.Match[str]", changes: list[Change]) -> str:
    original = dm.group(0)
    if original != " - ":
        changes.append(Change(1, RULE_ENTITY_NAME_DASH, original, " - "))
    return " - "


def _emit_title(out: list[FramedLine], changes: list[Change], framed: FramedLine) -> None:
    """Rules 5 and 5b on the banner's title line, which the frame found by position. The line is rewritten
    only when it carries the banner's marker: a header with no title has some other line there, such as
    an `AC:` header whose criterion id would read as an entity id."""
    content = framed.line.raw
    fired = _whitespace(framed)
    if "LIVING DOC" in content:
        content, title_changes = normalize_title(content)
        fired |= {c.rule for c in title_changes}
    _emit(out, changes, fired, framed, content)


# --- phase 1: each line's marker split off, and rule 6 on the indent after it ---------------------------------

# CommonMark fence rule: <=3 leading spaces, no backtick in a backtick fence's info string; else "AC:" lines misfile.
_FENCE_OPEN_RE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
_FENCE_CLOSE_RE = re.compile(r"^ {0,3}(?P<fence>`+|~+)[ \t]*$")


def compute_fence_flags(lines: list[str]) -> list[bool]:
    """True for a line that opens, closes or lies inside a fenced code block, per
    CommonMark fence-closing rules. Shared by `normalize`'s first phase and `ac_grammar.py`
    so neither parses an `AC:...` example quoted inside a fence."""
    flags: list[bool] = []
    fence_char: Optional[str] = None
    fence_len = 0
    for line in lines:
        if fence_char is None:
            m = _FENCE_OPEN_RE.match(line)
            if m is None or (m.group("fence")[0] == "`" and "`" in m.group("info")):
                flags.append(False)
            else:
                fence_char = m.group("fence")[0]
                fence_len = len(m.group("fence"))
                flags.append(True)
            continue

        m = _FENCE_CLOSE_RE.match(line)
        if m and m.group("fence")[0] == fence_char and len(m.group("fence")) >= fence_len:
            fence_char = None
            fence_len = 0
        flags.append(True)
    return flags


# A `.feature` header line's comment marker: '#' and at most one following space. A literal space, as in
# `_PO_LINE_RE`, so a tab or NBSP stays in the content's indent for rule 6 to rewrite.
_COMMENT_PREFIX_RE = re.compile(r"^# ?")
# A PageObject header line: its ` * ` marker, then the content; the trailing char is a literal space likewise.
_PO_LINE_RE = re.compile(r"^(?P<lead>\s*\*[ ]?)(?P<content>.*)$")


def _prepared(raw: str, prefix: str, role: Role, number: int, tab_stop: int = 0) -> FramedLine:
    """`raw` split after its `prefix`, with rule 6 at `tab_stop` on the rest when it has text (0: rule 6 off).
    A tab right after a bare marker becomes the marker's own space, as the rewritten line reads (`#\\tx` is
    `# x`): every reader of the normalised text, the criterion grammar included, sees the indent the frame saw."""
    content = raw[len(prefix) :]
    if tab_stop and content.strip():
        content = _fix_indentation_whitespace(content, tab_stop)
        if prefix and not prefix.endswith(" ") and content.startswith(" "):
            prefix, content = prefix + " ", content[1:]
    return FramedLine(raw, prefix, indented(content), role, number=number)


def _prepare(lines: list[str], fmt: SourceFormat) -> list[FramedLine]:
    """Phase 1, line-local and context-free: each line's comment marker split off and rule 6 applied to the
    indent after it, so every placement the frame makes reads an indent already in spaces. A whitespace-only
    line, a fenced code block's line, a line that is no comment of the header format and a scenario file
    stay as written; `TEXT` and `OUTSIDE` are placeholders the frame replaces."""
    numbered = list(enumerate(lines, start=1))
    if fmt in (SourceFormat.ISSUE_BODY, SourceFormat.HTML_MARKDOWN):
        fenced = compute_fence_flags(lines)
        return [
            _prepared(raw, "", Role.CODE, number) if code else _prepared(raw, "", Role.TEXT, number, tab_stop=4)
            for (number, raw), code in zip(numbered, fenced, strict=True)
        ]
    if fmt == SourceFormat.FEATURE_HEADER:
        marker_re = _COMMENT_PREFIX_RE
    elif fmt == SourceFormat.PAGE_OBJECT:
        marker_re = _PO_LINE_RE
    else:
        return [_prepared(raw, "", Role.TEXT, number) for number, raw in numbered]
    prepared = []
    for number, raw in numbered:
        marker = marker_re.match(raw)
        if marker is None:
            prepared.append(_prepared(raw, "", Role.OUTSIDE, number))
        else:
            prefix = marker.group("lead") if fmt == SourceFormat.PAGE_OBJECT else marker.group(0)
            prepared.append(_prepared(raw, prefix, Role.TEXT, number, tab_stop=1))
    return prepared


# --- phase 3: every other rule, per line, by the section the frame put it in -------------------------------


def _rewrite_markdown(lines: list[FramedLine], profile: frozenset[str], changes: list[Change]) -> list[FramedLine]:
    out: list[FramedLine] = []
    for framed in lines:
        if framed.role in (Role.CODE, Role.BLANK):
            out.append(framed)
            continue
        line, ws_fired = framed.line.raw, _whitespace(framed)

        # Recognised on any line, not only under a markdown heading (e.g. a bare "AC:..." snippet).
        header_m = _criterion_header(framed, line)
        if header_m:
            new_lines, fired = _rewrite_ac_header_content(header_m, inline_description=False, bullet_indent="")
            _emit(out, changes, fired | ws_fired, framed, f"{header_m.group('lead')}{new_lines[0]}")
            for extra in new_lines[1:]:
                _emit_description(out, changes, framed, extra)
            continue

        if framed.role in (Role.HEADING, Role.SUBHEADING):
            _emit(out, changes, ws_fired, framed, line)
        elif framed.section == "status":
            stripped = line.strip()
            canon = _canonicalize_token_case(stripped)
            if canon != stripped:
                _emit(out, changes, {RULE_STATE_CASING}, framed, canon)
            else:
                _emit(out, changes, ws_fired, framed, line)
        elif framed.criterion or framed.section in profile:
            marked, fired = _rewrite_bullet(line)
            _emit(out, changes, ws_fired | fired, framed, marked)
        else:
            _emit(out, changes, ws_fired, framed, line)
    return out


def _as_written(framed: FramedLine) -> FramedLine:
    """`framed` exactly as the input wrote it: a line outside the header, which `normalize` never rewrites."""
    return framed._replace(prefix="", line=indented(framed.raw))


def _rewrite_feature_header(
    lines: list[FramedLine], profile: frozenset[str], changes: list[Change]
) -> list[FramedLine]:
    out: list[FramedLine] = []
    for framed in lines:
        if framed.role is Role.OUTSIDE:
            out.append(_as_written(framed))
            continue
        content, ws_fired = framed.line.raw, _whitespace(framed)
        if framed.role is Role.TITLE:
            _emit_title(out, changes, framed)
            continue

        header_m = _criterion_header(framed, framed.line.text)
        if header_m and header_m.group("lead") == "":
            new_lines, fired = _rewrite_ac_header_content(header_m, inline_description=False, bullet_indent="  ")
            # The header keeps the author's indent: its criterion's items are read relative to it.
            indent = " " * framed.line.indent
            _emit(out, changes, fired | ws_fired, framed, indent + new_lines[0])
            for extra in new_lines[1:]:
                # `extra` already carries the two-space bullet_indent, so a split description sits one level deeper.
                _emit_description(out, changes, framed, indent + extra)
            continue

        fired = set(ws_fired)
        if framed.role is Role.KEY and framed.section == "status":
            value = opening_value(framed)
            canon = _canonicalize_token_case(value)
            fired |= _fired_if(canon != value, RULE_STATE_CASING)
            content = content.replace(value, canon, 1)
        elif framed.role is Role.TEXT and (framed.criterion or framed.section in profile):
            content, bullet_fired = _rewrite_bullet(content)
            fired |= bullet_fired
        _emit(out, changes, fired, framed, content)
    return out


_SCENARIO_AC_COMMENT_RE = re.compile(r"^(?P<lead>\s*#\s?)(?P<content>AC:\S+\s*\(.*)$")


def _rewrite_scenario_file(lines: list[FramedLine], changes: list[Change]) -> list[FramedLine]:
    """Only `# AC:` comment lines are content; Gherkin steps (including `*`-style
    steps), tags, section banners and everything else pass through untouched."""
    out: list[FramedLine] = []
    for framed in lines:
        m = _SCENARIO_AC_COMMENT_RE.match(framed.raw) if framed.role is Role.COMMENT else None
        if m is None:
            out.append(framed)
            continue
        header_m = _AC_HEADER_FULL_RE.match(m.group("content"))
        if header_m is None or header_m.group("lead") != "":
            out.append(framed)
            continue
        new_lines, fired = _rewrite_ac_header_content(header_m, inline_description=True, bullet_indent="")
        _emit(out, changes, fired, framed, m.group("lead") + new_lines[0])
    return out


def _rewrite_page_object(lines: list[FramedLine], changes: list[Change]) -> list[FramedLine]:
    """A PageObject header carries no AC blocks and no states, so its title line (rules 5/5b), generic
    indentation whitespace (rule 6) and the bullet markers of a `PO_BULLET_KEYS` list (rule 1) are all
    that is ever rewritten; every other ` * key: value` metadata line passes through untouched."""
    out: list[FramedLine] = []
    for framed in lines:
        if framed.role is Role.OUTSIDE:
            out.append(_as_written(framed))
            continue
        if framed.role is Role.TITLE:
            _emit_title(out, changes, framed)
            continue
        content, fired = framed.line.raw, _whitespace(framed)
        if framed.role is Role.TEXT and framed.section in PO_BULLET_KEYS:
            content, bullet_fired = _rewrite_bullet(content)
            fired |= bullet_fired
        _emit(out, changes, fired, framed, content)
    return out


def _split_lines_lf(text: str) -> tuple[list[str], list[int]]:
    """Rule 6 (line endings): splits on '\\n', stripping a trailing '\\r' from CRLF
    lines. Returns (lines, indices of lines that had CRLF), 0-based against `lines`."""
    raw = text.split("\n")
    lines: list[str] = []
    crlf_indices: list[int] = []
    for idx, raw_line in enumerate(raw):
        if raw_line.endswith("\r"):
            lines.append(raw_line[:-1])
            crlf_indices.append(idx)
        else:
            lines.append(raw_line)
    return lines, crlf_indices


def normalize(text: str, fmt: SourceFormat, entity_type: DocType) -> NormalizedSource:
    """Rewrites `text` (one format's worth of authoring input) to the canonical form,
    without ever touching code, Gherkin step text, or free prose. `entity_type` selects
    a `TYPE_PROFILES` entry; this function itself never branches on it."""
    return normalize_framed(text, fmt, entity_type)[0]


def normalize_framed(text: str, fmt: SourceFormat, entity_type: DocType) -> tuple[NormalizedSource, Frame]:
    """`normalize`, plus the frame its rules were applied by, holding the rewritten lines. Every parser reads
    its sections here instead of finding a boundary itself; `Frame.problems` are its structural diagnostics."""
    profile = TYPE_PROFILES[entity_type]
    lines, crlf_indices = _split_lines_lf(text)
    changes: list[Change] = []

    if fmt in (SourceFormat.ISSUE_BODY, SourceFormat.HTML_MARKDOWN):
        frame = frame_issue_body(_prepare(lines, fmt), profile)
        rewritten = _rewrite_markdown(frame.lines, profile, changes)
    elif fmt == SourceFormat.FEATURE_HEADER:
        frame = frame_feature_header(_prepare(lines, fmt), profile)
        rewritten = (
            _rewrite_feature_header(frame.lines, profile, changes)
            if names_an_entity(frame)
            else [_as_written(framed) for framed in frame.lines]
        )
    elif fmt == SourceFormat.SCENARIO_FILE:
        frame = frame_scenario_file(_prepare(lines, fmt))
        rewritten = _rewrite_scenario_file(frame.lines, changes)
    elif fmt == SourceFormat.PAGE_OBJECT:
        frame = frame_page_object(_prepare(lines, fmt), PO_BULLET_KEYS)
        rewritten = (
            _rewrite_page_object(frame.lines, changes)
            if names_an_entity(frame)
            else [_as_written(framed) for framed in frame.lines]
        )
    else:
        raise ValueError(f"unknown SourceFormat: {fmt!r}")

    # Recorded against the input line's 1-based position; the rule name/text is what matters, not exact position.
    for idx in crlf_indices:
        changes.append(Change(idx + 1, RULE_WHITESPACE, lines[idx] + "\r", lines[idx]))

    normalized = NormalizedSource(lines=[framed.rendered for framed in rewritten], changes=changes)
    return normalized, Frame(rewritten, frame.problems)
