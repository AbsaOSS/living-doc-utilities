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
Converts an Azure DevOps rich-text HTML fragment into the canonical Markdown-like text this
package's other parsers understand (docs/authoring.md, "HTML-to-Markdown conversion").
`convert_html_to_markdown`'s output is meant to be run through
`normalize(text, SourceFormat.HTML_MARKDOWN, entity_type)` and then `issue_body` (or
whichever parser fits the entity), exactly like any other source format - this module only
turns markup into text, it never derives an entity id or a field.

Handles headings, paragraphs, `<div>`/`<br>`, lists, tables, links and inline code. Two
passes run over the input: one (`_DropCountingParser`) counts, on the *original* markup,
every construct this pipeline drops - a `<script>`/`<style>` tag, an event-handler
attribute, an `<img>` tag, a link `url_policy.safe_href` rejects, or any other tag
`url_policy.sanitized_tag_allowlist()` won't keep (an `<iframe>`, a `<form>`, ...), counted
as `unsupported_tag` - and a second sanitises the input with `url_policy.sanitize_html_fragment`
(the same vetted policy a future PDF-generator text filter will reuse, and the same
allow-list the first pass counts against, so the two passes can't drift apart) before
walking the result into Markdown, counting any remaining tag this converter has no Markdown
form for as `unknown_tag`. Every drop, of whichever kind, is folded into one
`HTML_CONTENT_DROPPED` warning carrying the per-kind counts - never one warning per drop.

Handling the specific quirks of a real Azure DevOps rich-text editor's HTML output is out of
scope for this PR - that is a later Azure-DevOps-collector task's job, once real editor
samples are available. This covers the well-formed-HTML case.
"""

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Optional

from living_doc_utilities.authoring.url_policy import safe_href, sanitize_html_fragment, sanitized_tag_allowlist
from living_doc_utilities.contracts.envelope import ContractWarning

HTML_CONTENT_DROPPED = "HTML_CONTENT_DROPPED"

_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
_LIST_TAGS = {"ul", "ol"}
_TABLE_SECTION_TAGS = {"thead", "tbody", "tfoot"}
_CELL_TAGS = {"td", "th"}

# Every tag this converter has a Markdown rendering for. Anything else surviving
# `sanitize_html_fragment` (nh3 allows plenty of formatting tags this converter simply has
# no opinion on yet, e.g. `<strong>`) is unwrapped - its text kept, its markup dropped and
# counted as `unknown_tag`.
_SUPPORTED_TAGS = (
    _HEADING_TAGS | _LIST_TAGS | _TABLE_SECTION_TAGS | _CELL_TAGS | {"p", "div", "br", "li", "table", "tr", "a", "code"}
)

_WHITESPACE_RE = re.compile(r"[ \t\r\n]+")


def _is_event_handler_attribute(name: str) -> bool:
    return name.lower().startswith("on")


@dataclass
class _Elem:
    """One kept element of the Markdown-relevant tree: a tag, its (already-sanitised)
    attributes, and its children (nested `_Elem` instances and/or literal text)."""

    tag: str
    attrs: dict
    children: list = field(default_factory=list)


class _DropCountingParser(HTMLParser):
    """Counts, over the *original* input, every construct the pipeline is about to drop -
    kept as its own pass so the counts reflect the input exactly once, independent of how
    `sanitize_html_fragment` restructures its output."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.counts: dict[str, int] = {}
        self._tag_allowlist = sanitized_tag_allowlist()

    def _count(self, key: str) -> None:
        self.counts[key] = self.counts.get(key, 0) + 1

    def _handle(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        for name, _value in attrs:
            if _is_event_handler_attribute(name):
                self._count("event_handler_attribute")
        if tag == "script":
            self._count("script_tag")
        elif tag == "style":
            self._count("style_tag")
        elif tag == "img":
            self._count("img_tag")
        elif tag not in self._tag_allowlist:
            # Anything else `sanitize_html_fragment` won't keep - an `<iframe>`, `<form>`,
            # `<svg>`, ... - derived from the same allow-list it actually sanitises against,
            # not a second, hand-maintained copy that can drift from it.
            self._count("unsupported_tag")
        if tag == "a":
            href = dict(attrs).get("href")
            if href is not None and safe_href(href) is None:
                self._count("unsafe_href")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        self._handle(tag, attrs)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        self._handle(tag, attrs)


class _TreeBuilder(HTMLParser):
    """Builds a `_Elem` tree from already-sanitised HTML. Any tag outside
    `_SUPPORTED_TAGS` is unwrapped rather than dropped with its content - only
    `sanitize_html_fragment` decides what loses its content entirely (`<script>`,
    `<style>`); this pass only decides what this converter can render as Markdown."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Elem(tag="root", attrs={})
        self._stack = [self.root]
        self.counts: dict[str, int] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        if tag not in _SUPPORTED_TAGS:
            self.counts["unknown_tag"] = self.counts.get("unknown_tag", 0) + 1
            return
        elem = _Elem(tag=tag, attrs=dict(attrs))
        self._stack[-1].children.append(elem)
        if tag != "br":
            self._stack.append(elem)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag == "br" or tag not in _SUPPORTED_TAGS:
            return
        if len(self._stack) > 1 and self._stack[-1].tag == tag:
            self._stack.pop()

    def handle_data(self, data: str) -> None:
        self._stack[-1].children.append(data)


def _inline_text(items: list) -> str:
    parts = []
    for item in items:
        if isinstance(item, str):
            parts.append(item)
        elif item.tag == "a":
            text = _inline_text(item.children)
            href = item.attrs.get("href")
            parts.append(f"[{text}]({href})" if href else text)
        elif item.tag == "code":
            parts.append(f"`{_inline_text(item.children)}`")
        elif item.tag == "br":
            parts.append(" ")
        else:
            parts.append(_inline_text(item.children))
    return _WHITESPACE_RE.sub(" ", "".join(parts)).strip()


def _render_list(list_elem: _Elem, out: list[str]) -> None:
    for item in list_elem.children:
        if isinstance(item, _Elem) and item.tag == "li":
            out.append(f"- {_inline_text(item.children)}")
    out.append("")


def _table_rows(table_elem: _Elem) -> list[_Elem]:
    rows: list[_Elem] = []
    for child in table_elem.children:
        if not isinstance(child, _Elem):
            continue
        if child.tag == "tr":
            rows.append(child)
        elif child.tag in _TABLE_SECTION_TAGS:
            rows.extend(_table_rows(child))
    return rows


def _render_table(table_elem: _Elem, out: list[str]) -> None:
    rows = _table_rows(table_elem)
    for index, row in enumerate(rows):
        cells = [c for c in row.children if isinstance(c, _Elem) and c.tag in _CELL_TAGS]
        out.append(" | ".join(_inline_text(cell.children) for cell in cells))
        if index == 0:
            out.append(" | ".join("---" for _ in cells))
    out.append("")


def _walk_block(elem: _Elem, out: list[str]) -> None:
    buffer: list = []

    def flush() -> None:
        if buffer:
            text = _inline_text(buffer)
            if text:
                out.append(text)
            buffer.clear()

    for child in elem.children:
        if isinstance(child, str):
            buffer.append(child)
            continue
        if child.tag in _HEADING_TAGS:
            flush()
            level = int(child.tag[1])
            out.append(f"{'#' * level} {_inline_text(child.children)}")
            out.append("")
        elif child.tag == "p":
            flush()
            out.append(_inline_text(child.children))
            out.append("")
        elif child.tag == "div":
            flush()
            _walk_block(child, out)
        elif child.tag == "br":
            flush()
        elif child.tag in _LIST_TAGS:
            flush()
            _render_list(child, out)
        elif child.tag == "table":
            flush()
            _render_table(child, out)
        else:  # "a" / "code" - inline content at block level
            buffer.append(child)
    flush()


def _build_warnings(counts: dict[str, int]) -> list[ContractWarning]:
    if not counts:
        return []
    summary = ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))
    return [
        ContractWarning(
            code=HTML_CONTENT_DROPPED,
            message=f"HTML-to-Markdown conversion dropped disallowed or unsupported content: {summary}.",
            context=summary,
        )
    ]


def convert_html_to_markdown(html: str) -> tuple[str, list[ContractWarning]]:
    """Converts an Azure DevOps rich-text HTML fragment into Markdown-like text. Never
    raises on malformed input, matching every other parser in this package - a construct
    it cannot render is simply dropped and counted, never fatal.
    """
    drop_scan = _DropCountingParser()
    drop_scan.feed(html)
    drop_scan.close()

    sanitized = sanitize_html_fragment(html)

    builder = _TreeBuilder()
    builder.feed(sanitized)
    builder.close()

    counts = dict(drop_scan.counts)
    for key, value in builder.counts.items():
        counts[key] = counts.get(key, 0) + value

    lines: list[str] = []
    _walk_block(builder.root, lines)
    while lines and lines[-1] == "":
        lines.pop()
    while lines and lines[0] == "":
        lines.pop(0)

    return "\n".join(lines), _build_warnings(counts)
