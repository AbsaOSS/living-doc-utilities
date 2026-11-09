#
# Copyright 2026 ABSA Group Limited
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

"""`path::symbol` anchors live in the code maps and resolve to real code, never a line number (DEVELOPER.md, "Writing
documentation", Anchors)."""

import ast
import os
import re
from pathlib import Path
from typing import Optional

import pytest

from tests.docs.pages import (
    ANCHOR_PATTERN,
    ANCHOR_RE,
    ANCHORED_PAGES,
    APPROVED_PAGES,
    CODE_MAPS,
    FILE_TYPES,
    REPO_ROOT,
    read_page,
    section,
    unfenced_lines,
)

PACKAGE_DIR = REPO_ROOT / "living_doc_utilities"

_LINE_NUMBER_RE = re.compile(
    rf"(?:\.(?:{FILE_TYPES})|Makefile|\.pylintrc|\.coveragerc)`?(?::L?\d+|#L\d+|,?\s+lines?\s+\d+(?:-\d+)?\b)"
)
_API_MODULE_RE = re.compile(r"^\| `(?P<module>[a-z_.]+)` \|")
_LIST_ITEM_RE = re.compile(r"^(?:[-*+]|\d{1,9}[.)])[ \t]")
# The pages and the code maps: every file whose anchors must resolve.
ANCHORED_FILES = sorted({*APPROVED_PAGES, *CODE_MAPS.values()})
# The components a rule may name instead of an anchor (DEVELOPER.md, "Writing documentation", Anchors).
COMPONENTS = ("toolkit", "collectors", "transforms", "generators")
_DESTINATION = rf"(?:`{ANCHOR_PATTERN}`|{ANCHOR_PATTERN}|\[[^\]]*\]\([^)\s]+\)|(?:{'|'.join(COMPONENTS)})\b)"
_TRAILING_DESTINATIONS_RE = re.compile(rf"→\s*{_DESTINATION}(?:\s*(?:,|\band\b)\s*{_DESTINATION})*\s*$")
_LEAD_IN_DESTINATION_RE = re.compile(rf"→\s*{_DESTINATION}")


def _resolve(path: str) -> Optional[Path]:
    """An anchor path, relative to the repository root or, with `living_doc_utilities/` left out, to the package;
    never a `..`-laden path that escapes the repository, however it resolves on disk."""
    repo_root = REPO_ROOT.resolve()
    for candidate in (REPO_ROOT / path, PACKAGE_DIR / path):
        resolved = candidate.resolve()
        if resolved.is_file() and resolved.is_relative_to(repo_root):
            return resolved
    return None


def _bound_name(node: ast.stmt) -> Optional[str]:
    """The single name `node` binds at its own nesting level, or `None` when it binds none."""
    if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
        return node.name
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        return node.targets[0].id
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id
    return None


def _first_undefined_part(body: list[ast.stmt], parts: list[str]) -> Optional[str]:
    """The first dotted `parts` segment with no definition nested at its position in `body`, so `Class.member`
    only resolves when `member` is defined inside `Class` - not merely present anywhere in the file."""
    for index, part in enumerate(parts):
        node = next((candidate for candidate in body if _bound_name(candidate) == part), None)
        if node is None:
            return ".".join(parts[index:])
        body = getattr(node, "body", [])
    return None


def _anchor_problem(path: str, symbol: str) -> Optional[str]:
    """Why `path::symbol` does not resolve, or `None` when it does."""
    resolved = _resolve(path)
    if resolved is None:
        return f"no file '{path}'"
    text = resolved.read_text(encoding="utf-8")
    if resolved.suffix == ".py":
        missing = _first_undefined_part(ast.parse(text).body, symbol.split("."))
        return f"'{path}' defines no {missing!r}" if missing else None
    return None if symbol in text else f"'{path}' does not contain {symbol!r}"


def anchors(text: str) -> list[tuple[str, str]]:
    """Every `path::symbol` of a page, ticked or not; a trailing `()` or pytest `[id]` is dropped from the symbol."""
    return [(anchor_m.group("path"), anchor_m.group("symbol")) for anchor_m in ANCHOR_RE.finditer(text)]


def _anchors(page: str) -> list[tuple[str, str]]:
    return anchors(read_page(page))


@pytest.mark.parametrize("page", ANCHORED_FILES)
def test_every_anchor_resolves(page):
    """Each `path::symbol` on a page or in a code map names an existing file that defines, or contains, the symbol."""
    problems = [
        f"{page}: `{path}::{symbol}`: {problem}"
        for path, symbol in _anchors(page)
        if (problem := _anchor_problem(path, symbol)) is not None
    ]
    assert problems == []


@pytest.mark.parametrize("page", ANCHORED_FILES)
def test_no_anchor_uses_a_line_number(page):
    """No page or code map points at code by line number (`io.py:42`, `#L42`, prose "file.py lines 12-34"); line
    numbers drift."""
    assert _LINE_NUMBER_RE.findall(read_page(page)) == []


def page_anchor_problems(page: str, text: str) -> list[str]:
    """Each `path::symbol` on a page that may carry none; the page's code map holds them."""
    return [
        f"{page}: `{path}::{symbol}` belongs in the page's code map, not on the page" for path, symbol in anchors(text)
    ]


@pytest.mark.parametrize("page", sorted(page for page in APPROVED_PAGES if page not in ANCHORED_PAGES))
def test_a_page_carries_no_anchor(page):
    """A page states facts in plain words; its code map, not the page, says where the code realises them."""
    assert page_anchor_problems(page, read_page(page)) == []


def test_planted_anchor_on_a_page_is_reported():
    """A `path::symbol` left on a page fails, naming the page and the anchor."""
    assert page_anchor_problems("docs/x.md", "- a fact → `contracts/io.py::read_artifact`\n") == [
        "docs/x.md: `contracts/io.py::read_artifact` belongs in the page's code map, not on the page"
    ]


def code_map_entry(page: str, code_map: str, text: str) -> list[str]:
    """The lines of the `###` under the code map's `## Code map` that opens with a link to `page`; empty when there
    is none."""
    link = os.path.relpath(REPO_ROOT / page, (REPO_ROOT / code_map).parent)
    entries: list[list[str]] = []
    for line in section(text, "Code map"):
        if line.startswith("### "):
            entries.append([])
        elif entries and (entries[-1] or line.strip()):
            entries[-1].append(line)
    return next((lines for lines in entries if lines and f"]({link})" in lines[0]), [])


def code_map_problems(page: str, code_map: str, text: str) -> list[str]:
    """`page` has its `###` in its code map, opening with a link to the page and carrying anchors to check."""
    lines = code_map_entry(page, code_map, text)
    if not lines:
        return [f"{code_map}: no '###' under '## Code map' opens with a link to {page}"]
    if not anchors("\n".join(lines)):
        return [f"{code_map}: the code map of {page} carries no anchor"]
    return []


def test_every_depth_two_and_three_page_has_a_code_map():
    """Each depth-2 and depth-3 page is paired with a code map, and has its `###` there."""
    assert sorted(page for page, depth in APPROVED_PAGES.items() if depth > 1) == sorted(CODE_MAPS)
    problems = [
        problem
        for page, code_map in CODE_MAPS.items()
        for problem in code_map_problems(page, code_map, read_page(code_map))
    ]
    assert problems == []


def test_planted_page_without_its_code_map_entry_is_reported():
    """A page whose code map has no `###` opening with a link to it, or one that carries no anchor, fails."""
    other = "## Code map\n\n### Other\n\nWhat realises [other.md](other.md):\n\n- a fact → `contracts/io.py::x`\n"
    bare = "## Code map\n\n### X\n\nWhat realises each fact of [x.md](x.md):\n\n- a fact → toolkit\n"
    assert code_map_problems("docs/x.md", "docs/CONTEXT.md", other) == [
        "docs/CONTEXT.md: no '###' under '## Code map' opens with a link to docs/x.md"
    ]
    assert code_map_problems("docs/x.md", "docs/CONTEXT.md", bare) == [
        "docs/CONTEXT.md: the code map of docs/x.md carries no anchor"
    ]


def test_anchor_resolution_rejects_a_missing_file_and_a_missing_symbol():
    """A planted wrong path or wrong symbol is reported; a dotted member is checked part by part."""
    assert _anchor_problem("contracts/io.py", "read_artifact") is None
    assert _anchor_problem("contracts/doc_entities.py", "Entity._check_state_origin") is None
    assert _anchor_problem("contracts/nowhere.py", "x") == "no file 'contracts/nowhere.py'"
    assert _anchor_problem("contracts/io.py", "read_everything") == "'contracts/io.py' defines no 'read_everything'"
    assert _anchor_problem("Makefile", "no-such-target") == "'Makefile' does not contain 'no-such-target'"


def test_anchor_resolution_rejects_a_member_that_belongs_to_a_different_class():
    """`Class.member` only resolves when `member` is nested in `Class`, not merely present elsewhere in the file."""
    assert _anchor_problem("contracts/doc_entities.py", "PageRef._check_state_origin") == (
        "'contracts/doc_entities.py' defines no '_check_state_origin'"
    )


def test_anchor_resolution_rejects_a_path_that_escapes_the_repository(tmp_path):
    """A `..`-laden path that exists on disk is still rejected when it resolves outside the repository."""
    outside = tmp_path / "escaped.py"
    outside.write_text("ESCAPED = 1\n", encoding="utf-8")
    escaping = os.path.relpath(outside, REPO_ROOT)
    assert _anchor_problem(escaping, "ESCAPED") == f"no file '{escaping}'"


def test_a_line_number_anchor_is_found():
    """A planted `io.py:42` or `#L42` pointer is caught."""
    assert _LINE_NUMBER_RE.findall("see `io.py:42` and [read](io.py#L42)") == [".py:42", ".py#L42"]


@pytest.mark.parametrize(
    "text",
    [
        "`io.py` lines 12-34",
        "io.py, line 42",
        "io.py:L42",
        "`requirements.txt:3`",
        "[pin](requirements.txt#L3)",
        "[qa](Makefile#L12)",
        "`.pylintrc:10`",
    ],
)
def test_every_line_number_form_is_found(text):
    """A line number after a ticked file, after a comma, as `:L42`, or into a non-Python file is caught too."""
    assert len(_LINE_NUMBER_RE.findall(text)) == 1


def test_an_anchor_into_a_non_python_file_is_no_line_number():
    """`test.yml::3.14` and `Makefile::qa` name a text, not a line."""
    assert _LINE_NUMBER_RE.findall("`.github/workflows/test.yml::3.14` and `Makefile::qa`") == []


@pytest.mark.parametrize(
    "text, found",
    [
        ("→ `contracts/io.py::read_artifacts()`", ("contracts/io.py", "read_artifacts")),
        ("→ contracts/io.py::read_artifacts", ("contracts/io.py", "read_artifacts")),
        ("→ `tests/docs/test_x.py::test_no_such_case[param]`", ("tests/docs/test_x.py", "test_no_such_case")),
        ("→ `.coveragerc::fail_under`", (".coveragerc", "fail_under")),
    ],
    ids=["call-parentheses", "unticked", "pytest-id", "dotfile"],
)
def test_every_anchor_form_is_found_so_a_wrong_one_is_reported(text, found):
    """An anchor with `()`, a pytest id, no ticks, or into a dotfile is still read, so its resolution is checked."""
    assert anchors(text) == [found]
    assert _anchor_problem(*found) is not None


def test_a_placeholder_is_no_anchor():
    """The rule's own placeholders, `path::symbol` and `tests/<path>.py::test_name`, are not read as anchors."""
    assert anchors("`path::symbol`, `tests/<path>.py::test_name`") == []


def unplaced_list_items(page: str, text: str) -> list[str]:
    """Top-level list items that do not end in `→` and their destinations - anchors, links or components - and
    whose lead-in carries none either. A lead-in covers only the list right after it, not one past a table.
    `Contents` is routing, not facts."""
    problems: list[str] = []
    chapter, lead_in, previous = "", "", "blank"
    for line in unfenced_lines(text):
        stripped = line.strip()
        if not stripped:
            previous = "blank"
            continue
        if stripped.startswith("#"):
            chapter = stripped.lstrip("#").strip() if stripped.startswith("## ") else chapter
            lead_in, previous = "", "blank"
            continue
        if stripped.startswith("|"):
            lead_in, previous = "", "blank"  # a table ends the reach of the lead-in above it
            continue
        if line.startswith((" ", "\t")):
            continue  # a sub-item (`Why:`, detail)
        if _LIST_ITEM_RE.match(line) is None:
            lead_in = f"{lead_in} {stripped}" if previous == "text" else stripped
            previous = "text"
            continue
        previous = "item"
        if chapter == "Contents":
            continue
        if _TRAILING_DESTINATIONS_RE.search(stripped) or _LEAD_IN_DESTINATION_RE.search(lead_in):
            continue
        problems.append(f"{page}: '{stripped[:80]}' ends in no anchor, component or link, and its lead-in none either")
    return problems


@pytest.mark.parametrize("code_map", sorted(set(CODE_MAPS.values())))
def test_every_code_map_item_says_where_it_is_realised(code_map):
    """Each item of a `## Code map` ends in `→` and an anchor, a component or a link."""
    lines = section(read_page(code_map), "Code map")
    assert unplaced_list_items(code_map, "\n".join(["## Code map", *lines])) == []


def test_an_unplaced_list_item_is_reported_and_a_lead_in_anchor_covers_its_items():
    """A bare fact fails, as does a trailing arrow with no destination; an anchored lead-in covers its items."""
    bare = "## Facts\n\n- a fact with no home\n"
    dangling_arrow = "## Facts\n\n- a fact with a dangling arrow →\n"
    covered = "## Facts\n\nThe cases → `contracts/io.py::read_artifact`:\n\n- a fact with no home\n"
    assert unplaced_list_items("docs/x.md", bare) == [
        "docs/x.md: '- a fact with no home' ends in no anchor, component or link, and its lead-in none either"
    ]
    assert unplaced_list_items("docs/x.md", dangling_arrow) == [
        "docs/x.md: '- a fact with a dangling arrow →' ends in no anchor, component or link, and its lead-in none "
        "either"
    ]
    assert unplaced_list_items("docs/x.md", covered) == []


@pytest.mark.parametrize(
    "item",
    [
        "- a fact → somewhere",
        "- collect → normalize → generate is deterministic",
        "- the flow `a → b` is fixed",
        "- see [x](y.md) for a fact with no home",
        "- a fact → `contracts/io.py::read_artifact` and more text",
    ],
)
def test_an_item_that_does_not_end_in_a_destination_is_reported(item):
    """An arrow mid-sentence, an arrow to no destination, or a link mid-sentence does not say where it is realised."""
    assert len(unplaced_list_items("docs/x.md", f"## Facts\n\n{item}\n")) == 1


@pytest.mark.parametrize(
    "item",
    [
        "- a fact → `contracts/io.py::read_artifact`",
        "- a fact → toolkit",
        "- a fact → [Errors](contracts/errors.md#codes), [Rendering](contracts/rendering.md#coverage)",
        "- a fact → `contracts/io.py::read_artifact` and `contracts/io.py::write_artifact`",
    ],
)
def test_an_item_that_ends_in_destinations_passes(item):
    """An anchor, a component, or several links or anchors joined by `,` or `and` end an item."""
    assert unplaced_list_items("docs/x.md", f"## Facts\n\n{item}\n") == []


def test_a_lead_in_does_not_cover_a_list_after_a_table():
    """A lead-in's `→` covers the list right after it; past a table, each item needs its own destination."""
    page = "## Facts\n\nThe rows → `contracts/io.py::run`:\n\n| a | b |\n|---|---|\n\n- a fact with no home\n"
    assert unplaced_list_items("docs/x.md", page) == [
        "docs/x.md: '- a fact with no home' ends in no anchor, component or link, and its lead-in none either"
    ]


@pytest.mark.parametrize("item", ["+ a fact with no home", "1) a fact with no home", "-\ta fact with no home"])
def test_every_list_marker_is_read_as_a_list_item(item):
    """`+`, `1)` and a tab after the marker start a list item on GitHub, so the item is checked."""
    assert len(unplaced_list_items("docs/x.md", f"## Facts\n\n{item}\n")) == 1


def test_api_page_lists_every_module():
    """`docs/api.md`'s module table names every module of the package, and no module that does not exist."""
    modules = {
        ".".join(path.relative_to(PACKAGE_DIR).with_suffix("").parts)
        for path in PACKAGE_DIR.rglob("*.py")
        if path.name != "__init__.py"
    }
    listed = {
        module_m.group("module")
        for line in section(read_page("docs/api.md"), "Modules")
        if (module_m := _API_MODULE_RE.match(line))
    }
    assert listed == modules
