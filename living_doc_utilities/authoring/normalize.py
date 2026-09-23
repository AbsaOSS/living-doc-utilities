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
The one normalisation layer over the five authoring source formats. Canon established in
AbsaOSS/living-doc's docs/guides/living-doc-glossary.md and docs/guides/living-doc-header-types.md
(PRs #25/#26). `normalize` rewrites non-canonical
dashes, bullet markers, case, version form and whitespace per format, and never touches
fenced or inline code, Gherkin step text, TypeScript, or free prose. `normalize_title`
applies the entity-name/title rules (5, 5b) shared by a GitHub issue title, a `.feature`
banner and a PageObject banner.

Type differences - which sections of an entity are bullet sections - are data, held
entirely in `TYPE_PROFILES`; nothing else in this module branches on entity type.

This module never validates or enumerates the acceptance-criterion state vocabulary or
the strict version shape - it only reshapes whatever token sits in a given structural
position. That vocabulary lives in exactly one place, `ac_grammar.py`.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple, Optional

from living_doc_utilities.authoring.identity import _ENTITY_ID_RE
from living_doc_utilities.contracts.common import DocType

# Rule names (authoring rules 1-7 plus 5b, per AbsaOSS/living-doc's docs/specs/issues/
# P35-UT1b1-prompt.md), used both as the `rule` field of a Change and as the `rule`
# column of normalisation_cases.yaml.
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


@dataclass(frozen=True)
class TypeProfile:
    """Which of an entity type's sections are bullet-list sections. The AC block itself
    is always bullet-eligible regardless of entity type, so it is not listed here."""

    bullet_sections: frozenset[str]


TYPE_PROFILES: dict[DocType, TypeProfile] = {
    "DocumentedUserStory": TypeProfile(bullet_sections=frozenset({"business_value", "preconditions", "not_in_scope"})),
    "DocumentedFeature": TypeProfile(bullet_sections=frozenset()),
    "DocumentedFunctionality": TypeProfile(bullet_sections=frozenset({"rationale", "preconditions", "not_in_scope"})),
}


@dataclass
class NormalizedSource:
    """`normalize`'s result: the full reconstructed text (same shape as the input, only
    content-role lines rewritten) plus the list of changes that produced it."""

    lines: list[str]
    changes: list[Change]

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


# --- low-level, position-driven token reshaping -----------------------------------
# None of the helpers below know what a *valid* acceptance-criterion state or version
# looks like - they only reshape whatever token a caller hands them, based on where it
# sits in the line. Validation lives in ac_grammar.py alone.

# A canonical "- " bullet line - shared by ac_grammar (an AC block's own bullets) and
# issue_body (extract_bullets), so imported by both rather than redefined.
_BULLET_RE = re.compile(r"^-\s?(?P<text>.*)$")

_BULLET_START_RE = re.compile(r"^(?P<indent>\s*)(?P<marker>[–—*•+])(?P<sp>\s)(?P<rest>.*)$")
# A dash separates header segments only when whitespace sits on at least one side -
# otherwise it is indistinguishable from a hyphen inside a state token (e.g. the
# "in-review" in "v1.0.0 - in-review"), which must stay intact for
# `_canonicalize_token_case` to fold into "in_review".
_DASH_SEP_CAP_RE = re.compile(r"(\s*[-–—]\s+|\s+[-–—]\s*)")
_VERSION_RESHAPE_RE = re.compile(r"^[vV]?(\d+)(?:\.(\d+))?(?:\.(\d+))?$")
_REMOVAL_PLANNED_CLAUSE_RE = re.compile(r"^removal[ \t]+planned[ \t]+(\S+)$", re.IGNORECASE)
_AC_HEADER_FULL_RE = re.compile(r"^(?P<lead>[#*]{0,3}\s*)AC:(?P<id>\S+)\s*\((?P<inner>[^)]*)\)(?P<trail>.*)$")
_AC_TRAIL_DESC_RE = re.compile(r"^\s*[-–—]\s*(?P<desc>.+)$")


def _fix_bullet_marker(line: str, m: "re.Match[str]") -> tuple[str, bool]:
    """`m` is the caller's own `_BULLET_START_RE.match(line)` - callers already need it to
    decide whether to call this at all, so it is passed in rather than matched again here."""
    new_line = f"{m.group('indent')}-{m.group('sp')}{m.group('rest')}"
    return new_line, new_line != line


def _reshape_version_form(token: str) -> tuple[str, bool]:
    m = _VERSION_RESHAPE_RE.match(token)
    if not m or m.group(2) is None:
        # No minor part - e.g. bare "v1" or "1": left as-is, no digit to infer a patch
        # from (a malformed-acceptance-criterion error downstream, not normalize's job).
        return token, False
    major, minor, patch = m.group(1), m.group(2), m.group(3) or "0"
    reshaped = f"v{major}.{minor}.{patch}"
    return reshaped, reshaped != token


# Shared with ac_grammar._slug_placeholder_name - both fold a token to lowercase
# snake_case, only the return shape (plain string vs. a (value, changed) pair) differs.
_WORD_SEP_RE = re.compile(r"[\s\-]+")


def _canonicalize_token_case(token: str) -> tuple[str, bool]:
    canon = _WORD_SEP_RE.sub("_", token.strip().lower())
    return canon, canon != token


_NBSP = chr(0xA0)  # kept out of string literals - formatters fold \u00A0 escapes into a literal, invisible byte
_INDENT_WS_RE = re.compile("^[ \t" + _NBSP + "]*")


def _fix_indentation_whitespace(line: str) -> tuple[str, bool]:
    m = _INDENT_WS_RE.match(line)
    lead = m.group(0) if m else ""
    if not lead or ("\t" not in lead and _NBSP not in lead):
        return line, False
    new_lead = lead.replace("\t", " ").replace(_NBSP, " ")
    new_line = new_lead + line[len(lead) :]
    return new_line, True


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
        canon, changed = _canonicalize_token_case(segments[0].strip())
        if changed:
            fired.add(RULE_STATE_CASING)
        return canon, fired

    norm_segments: list[str] = []
    last_index = len(segments) - 1
    for idx, seg in enumerate(segments):
        seg_stripped = seg.strip()
        if idx == last_index and idx > 0:
            rp_m = _REMOVAL_PLANNED_CLAUSE_RE.match(seg_stripped)
            if rp_m:
                rp_version, v_changed = _reshape_version_form(rp_m.group(1))
                if v_changed:
                    fired.add(RULE_VERSION_FORM)
                keyword_raw = seg_stripped[: rp_m.start(1)].rstrip()
                if keyword_raw != "removal planned":
                    fired.add(RULE_STATE_CASING)
                norm_segments.append(f"removal planned {rp_version}")
                continue
        if idx == 0:
            reshaped, v_changed = _reshape_version_form(seg_stripped)
            if v_changed:
                fired.add(RULE_VERSION_FORM)
            norm_segments.append(reshaped)
            continue
        canon, changed = _canonicalize_token_case(seg_stripped)
        if changed:
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


def _slugify_section(text: str) -> str:
    """Shared with issue_body._split_h2_sections, which slugifies the same way."""
    return re.sub(r"[\s_]+", "_", text.strip().lower())


def _emit(out_lines: list[str], changes: list[Change], fired: set, before: str, after: str) -> None:
    out_lines.append(after)
    for rule in sorted(fired):
        changes.append(Change(len(out_lines), rule, before, after))


# --- entity/title rules (5, 5b) -----------------------------------------------------
# _ENTITY_ID_RE itself lives in identity.py (entity-id derivation is that module's job);
# imported here rather than redefined, since normalize_title also needs to locate one.

_TITLE_SEP_AFTER_ID_RE = re.compile(r"^\s*([-–—:|·])\s*")
# An en/em dash is always the structural Feature-name/Functionality-name separator
# (English compound words use a plain hyphen, never an en/em dash), so it is rewritten
# regardless of spacing. A plain hyphen is only the same separator when whitespace sits
# on at least one side - unspaced, it is a hyphenated word like "Password-reset".
_TITLE_DASH_RE = re.compile(r"\s*[–—]\s*|\s*-\s+|\s+-\s*")
_TITLE_CANONICAL_SEP = " · "


def normalize_title(title: str) -> tuple[str, list[Change]]:
    """Rules 5 and 5b applied to an entity/title string - a GitHub issue title, a
    `.feature` banner's `LIVING DOC — <id> · <title>` text, or a PageObject
    banner's title line. Text before the entity id (e.g. a `LIVING DOC — ` prefix)
    is left untouched."""
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


# --- per-format handlers -------------------------------------------------------------

# A Gherkin `Feature:` declaration line - shared by feature_header (bounds its header-
# block banner search) and scenario (resets a pending tag block), so imported by both
# rather than redefined.
_FEATURE_LINE_RE = re.compile(r"^Feature:\s*.*$")

_MD_HEADING_RE = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<text>.*)$")
# CommonMark fence syntax (spec, "Fenced code blocks"): up to three literal leading
# spaces - a tab's larger indent disqualifies a fence marker, so this is " " not \s -
# and a backtick fence's info string may not itself contain a backtick (a tilde fence
# has no such restriction). Getting this wrong misclassifies which side of the fence
# an "AC:..." line falls on, the one thing this function exists to get right for both
# `_normalize_markdown` and `ac_grammar.py`.
_FENCE_OPEN_RE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
_FENCE_CLOSE_RE = re.compile(r"^ {0,3}(?P<fence>`+|~+)[ \t]*$")


def compute_fence_flags(lines: list[str]) -> list[bool]:
    """True for a line that opens, closes or lies inside a fenced code block. A fence
    opens with 3+ backticks or 3+ tildes and is only closed by a line consisting of that
    same character repeated at least as many times - so a `~~~` fence is recognised, and
    a shorter or differently-charactered run nested inside a longer fence does not close
    it early. The one fence-tracking rule shared by `_normalize_markdown` (which must
    never touch fenced content) and `ac_grammar.py` (which must never parse an `AC:...`
    example quoted inside one).
    """
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


def _normalize_markdown(lines: list[str], profile: TypeProfile, changes: list[Change]) -> list[str]:
    out_lines: list[str] = []
    current_section: Optional[str] = None
    in_ac_block = False
    fence_flags = compute_fence_flags(lines)

    for line_idx, raw in enumerate(lines):
        if fence_flags[line_idx]:
            out_lines.append(raw)
            continue

        stripped = raw.strip()
        if stripped == "":
            # A blank line does not end an AC block: issue-body headings are
            # conventionally followed by one blank line before their own bullets.
            # Only a new heading (handled below) ends one.
            out_lines.append(raw)
            continue

        # An AC header is recognised on any line - a "### AC:..." sub-heading (the
        # issue-body convention) or a bare "AC:..." line (e.g. a snippet quoted
        # without its enclosing heading) - never only inside a markdown heading.
        header_full_m = _AC_HEADER_FULL_RE.match(raw)
        if header_full_m:
            lead = header_full_m.group("lead")
            new_lines, fired = _rewrite_ac_header_content(header_full_m, inline_description=False, bullet_indent="")
            in_ac_block = True
            if not fired:
                out_lines.append(raw)
                continue
            _emit(out_lines, changes, fired, raw, f"{lead}{new_lines[0]}")
            for extra in new_lines[1:]:
                _emit(out_lines, changes, {RULE_INLINE_AC_DESCRIPTION}, "", extra)
            continue

        heading_m = _MD_HEADING_RE.match(raw)
        if heading_m:
            current_section = _slugify_section(heading_m.group("text"))
            in_ac_block = False
            out_lines.append(raw)
            continue

        if current_section == "status":
            canon, changed = _canonicalize_token_case(stripped)
            if changed:
                _emit(out_lines, changes, {RULE_STATE_CASING}, raw, canon)
            else:
                out_lines.append(raw)
            continue

        if in_ac_block or (current_section is not None and current_section in profile.bullet_sections):
            bullet_m = _BULLET_START_RE.match(raw)
            if bullet_m:
                new_line, changed = _fix_bullet_marker(raw, bullet_m)
                if changed:
                    _emit(out_lines, changes, {RULE_BULLET_MARKER}, raw, new_line)
                else:
                    out_lines.append(raw)
                continue

        out_lines.append(raw)

    return out_lines


_FH_KEY_LIST_RE = re.compile(r"^(?P<key>[a-zA-Z_]+):\s*$")
_FH_KEY_SCALAR_RE = re.compile(r"^(?P<key>[a-zA-Z_]+):(?P<sep>\s+)(?P<val>.*)$")


# Shared with feature_header._strip_comment_prefix, which only needs the second half of
# the split this function returns.
_COMMENT_PREFIX_RE = re.compile(r"^#\s?")


def _split_comment_prefix(raw: str) -> tuple[str, str]:
    """Strips the feature-header comment marker: a leading '#' plus at most one
    following whitespace character. Returns (prefix, content) so callers can reattach
    the exact prefix that was removed."""
    m = _COMMENT_PREFIX_RE.match(raw)
    prefix = m.group(0) if m else ""
    return prefix, raw[len(prefix) :]


def _normalize_feature_header(lines: list[str], profile: TypeProfile, changes: list[Change]) -> list[str]:
    out_lines: list[str] = []
    current_section: Optional[str] = None
    in_ac_block = False
    seen_title = False

    for raw in lines:
        if not raw.startswith("#"):
            out_lines.append(raw)
            continue

        prefix, content = _split_comment_prefix(raw)
        stripped = content.strip()

        if stripped == "":
            # A blank line does not end an AC block, mirroring `_normalize_markdown`:
            # issue-body-style headings are conventionally followed by one blank line
            # before their own bullets.
            out_lines.append(raw)
            continue

        if set(stripped) == {"="}:
            out_lines.append(raw)
            in_ac_block = False
            continue

        if not seen_title and "LIVING DOC" in content:
            seen_title = True
            new_content, title_changes = normalize_title(content)
            fired = {c.rule for c in title_changes}
            if fired:
                _emit(out_lines, changes, fired, raw, prefix + new_content)
            else:
                out_lines.append(raw)
            continue

        header_full_m = _AC_HEADER_FULL_RE.match(stripped)
        if header_full_m and header_full_m.group("lead").strip() == "":
            new_lines, fired = _rewrite_ac_header_content(header_full_m, inline_description=False, bullet_indent="  ")
            in_ac_block = True
            if not fired:
                out_lines.append(raw)
                continue
            _emit(out_lines, changes, fired, raw, f"#   {new_lines[0]}")
            for extra in new_lines[1:]:
                # `extra` already carries the "  " `bullet_indent` passed above; prefixing
                # it with the same "#   " used for the AC header line (not one more "  ")
                # keeps the canonical five spaces between "#" and "-", not seven.
                _emit(out_lines, changes, {RULE_INLINE_AC_DESCRIPTION}, "", f"#   {extra}")
            continue

        list_key_m = _FH_KEY_LIST_RE.match(stripped)
        if list_key_m:
            current_section = list_key_m.group("key")
            in_ac_block = False
            out_lines.append(raw)
            continue

        scalar_m = _FH_KEY_SCALAR_RE.match(stripped)
        if scalar_m:
            current_section = None
            in_ac_block = False
            if scalar_m.group("key") == "status":
                val = scalar_m.group("val")
                canon, changed = _canonicalize_token_case(val.strip())
                if changed:
                    _emit(out_lines, changes, {RULE_STATE_CASING}, raw, raw.replace(val, canon, 1))
                    continue
            out_lines.append(raw)
            continue

        if in_ac_block or (current_section is not None and current_section in profile.bullet_sections):
            bullet_m = _BULLET_START_RE.match(content)
            if bullet_m:
                new_content, changed = _fix_bullet_marker(content, bullet_m)
                if changed:
                    _emit(out_lines, changes, {RULE_BULLET_MARKER}, raw, prefix + new_content)
                else:
                    out_lines.append(raw)
                continue

        out_lines.append(raw)

    return out_lines


_SCENARIO_AC_COMMENT_RE = re.compile(r"^(?P<lead>\s*#\s?)(?P<content>AC:\S+\s*\(.*)$")


def _normalize_scenario_file(lines: list[str], changes: list[Change]) -> list[str]:
    """Only `# AC:` comment lines are content; Gherkin steps (including `*`-style
    steps), tags, section banners and everything else pass through untouched."""
    out_lines: list[str] = []
    for raw in lines:
        m = _SCENARIO_AC_COMMENT_RE.match(raw)
        if not m:
            out_lines.append(raw)
            continue

        content = m.group("content")
        header_full_m = _AC_HEADER_FULL_RE.match(content)
        if not header_full_m or header_full_m.group("lead") != "":
            out_lines.append(raw)
            continue

        new_lines, fired = _rewrite_ac_header_content(header_full_m, inline_description=True, bullet_indent="")
        if not fired:
            out_lines.append(raw)
            continue
        _emit(out_lines, changes, fired, raw, m.group("lead") + new_lines[0])

    return out_lines


# Shared with page_object._content_lines. The optional trailing char is a literal space,
# not \s: a tab or NBSP there must fall into `content`, where _fix_indentation_whitespace
# can still rewrite it - absorbing it into `lead` here would let it slip through unfixed.
_PO_LINE_RE = re.compile(r"^(?P<lead>\s*\*[ ]?)(?P<content>.*)$")


def _normalize_page_object(lines: list[str], changes: list[Change]) -> list[str]:
    """A PageObject header carries no bullet sections, AC blocks or states - only its
    title line (rules 5/5b) and generic indentation whitespace (rule 6) are ever
    rewritten; every ` * key: value` metadata line passes through untouched."""
    out_lines: list[str] = []
    seen_title = False
    for raw in lines:
        m = _PO_LINE_RE.match(raw)
        if not m:
            out_lines.append(raw)
            continue

        content = m.group("content")
        prefix = m.group("lead")

        if not seen_title and "LIVING DOC" in content:
            seen_title = True
            new_content, title_changes = normalize_title(content)
            fired = {c.rule for c in title_changes}
            if fired:
                _emit(out_lines, changes, fired, raw, prefix + new_content)
            else:
                out_lines.append(raw)
            continue

        new_content, changed = _fix_indentation_whitespace(content)
        if changed:
            _emit(out_lines, changes, {RULE_WHITESPACE}, raw, prefix + new_content)
        else:
            out_lines.append(raw)

    return out_lines


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
    profile = TYPE_PROFILES[entity_type]
    lines, crlf_indices = _split_lines_lf(text)
    changes: list[Change] = []

    if fmt in (SourceFormat.ISSUE_BODY, SourceFormat.HTML_MARKDOWN):
        out_lines = _normalize_markdown(lines, profile, changes)
    elif fmt == SourceFormat.FEATURE_HEADER:
        out_lines = _normalize_feature_header(lines, profile, changes)
    elif fmt == SourceFormat.SCENARIO_FILE:
        out_lines = _normalize_scenario_file(lines, changes)
    elif fmt == SourceFormat.PAGE_OBJECT:
        out_lines = _normalize_page_object(lines, changes)
    else:
        raise ValueError(f"unknown SourceFormat: {fmt!r}")

    # Best-effort: recorded against the *input* line's 1-based position, independent of
    # any line rule 7 inserted - the rule name and before/after text are what matters.
    for idx in crlf_indices:
        changes.append(Change(idx + 1, RULE_WHITESPACE, lines[idx] + "\r", lines[idx]))

    return NormalizedSource(lines=out_lines, changes=changes)
