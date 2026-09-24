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

"""`path::symbol` anchors in the documentation pages point at code that exists, never at a line number, and
`docs/api.md` lists every module (DEVELOPER.md, "Writing documentation", Anchors)."""

import re
from pathlib import Path
from typing import Optional

import pytest

from tests.docs.pages import APPROVED_PAGES, REPO_ROOT, read_page, section, unfenced_lines

PACKAGE_DIR = REPO_ROOT / "living_doc_utilities"

_ANCHOR_RE = re.compile(
    r"`(?P<path>(?:[\w.-]+/)*[\w.-]+\.(?:py|md|yml|yaml|toml|sh|txt|json)|Makefile)::(?P<symbol>[\w.-]+)`"
)
_LINE_NUMBER_RE = re.compile(r"\.(?:py|md|yml|yaml|toml|sh)(?::\d+|#L\d+)")
_API_MODULE_RE = re.compile(r"^\| `(?P<module>[a-z_.]+)` \|")
_LIST_ITEM_RE = re.compile(r"^(?:[-*]|\d+\.) ")


def _resolve(path: str) -> Optional[Path]:
    """An anchor path, relative to the repository root or, with `living_doc_utilities/` left out, to the package."""
    for candidate in (REPO_ROOT / path, PACKAGE_DIR / path):
        if candidate.is_file():
            return candidate
    return None


def _defines(source: str, name: str) -> bool:
    """Whether Python `source` defines `name`: a class, a function, or an assignment at any indentation."""
    pattern = rf"^\s*(?:(?:async\s+)?def|class)\s+{re.escape(name)}\b|^\s*{re.escape(name)}\s*[:=]"
    return re.search(pattern, source, re.MULTILINE) is not None


def _anchor_problem(path: str, symbol: str) -> Optional[str]:
    """Why `path::symbol` does not resolve, or `None` when it does."""
    resolved = _resolve(path)
    if resolved is None:
        return f"no file '{path}'"
    text = resolved.read_text(encoding="utf-8")
    if resolved.suffix == ".py":
        missing = [part for part in symbol.split(".") if not _defines(text, part)]
        return f"'{path}' defines no {'.'.join(missing)!r}" if missing else None
    return None if symbol in text else f"'{path}' does not contain {symbol!r}"


def _anchors(page: str) -> list[tuple[str, str]]:
    return [(anchor_m.group("path"), anchor_m.group("symbol")) for anchor_m in _ANCHOR_RE.finditer(read_page(page))]


@pytest.mark.parametrize("page", sorted(APPROVED_PAGES))
def test_every_anchor_resolves(page):
    """Each `path::symbol` on the page names an existing file that defines, or contains, the symbol."""
    problems = [
        f"{page}: `{path}::{symbol}`: {problem}"
        for path, symbol in _anchors(page)
        if (problem := _anchor_problem(path, symbol)) is not None
    ]
    assert problems == []


@pytest.mark.parametrize("page", sorted(APPROVED_PAGES))
def test_no_anchor_uses_a_line_number(page):
    """No page points at code by line number (`io.py:42`, `#L42`); line numbers drift."""
    assert _LINE_NUMBER_RE.findall(read_page(page)) == []


def test_the_detail_pages_carry_anchors():
    """The anchor check has something to check: every depth-2 and depth-3 page carries anchors."""
    assert [page for page, depth in APPROVED_PAGES.items() if depth > 1 and not _anchors(page)] == []


def test_anchor_resolution_rejects_a_missing_file_and_a_missing_symbol():
    """A planted wrong path or wrong symbol is reported; a dotted member is checked part by part."""
    assert _anchor_problem("contracts/io.py", "read_artifact") is None
    assert _anchor_problem("contracts/doc_entities.py", "Entity._check_state_origin") is None
    assert _anchor_problem("contracts/nowhere.py", "x") == "no file 'contracts/nowhere.py'"
    assert _anchor_problem("contracts/io.py", "read_everything") == "'contracts/io.py' defines no 'read_everything'"
    assert _anchor_problem("Makefile", "no-such-target") == "'Makefile' does not contain 'no-such-target'"


def unplaced_list_items(page: str, text: str) -> list[str]:
    """Top-level list items that say nowhere where they are realised: no `→` (an anchor, a component or a link), no
    anchor, no link, and no lead-in line that carries an anchor. `Contents` and `Pages` are routing, not facts."""
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
        if line.startswith(" ") or stripped.startswith("|"):
            continue  # a sub-item (`Why:`, detail) or a table row
        if _LIST_ITEM_RE.match(line) is None:
            lead_in = f"{lead_in} {stripped}" if previous == "text" else stripped
            previous = "text"
            continue
        previous = "item"
        if chapter in ("Contents", "Pages"):
            continue
        if "→" in stripped or "](" in stripped or _ANCHOR_RE.search(stripped) or "→" in lead_in:
            continue
        problems.append(f"{page}: '{stripped[:80]}' names no anchor, component or link, and its lead-in none either")
    return problems


@pytest.mark.parametrize("page", sorted(page for page, depth in APPROVED_PAGES.items() if depth > 1))
def test_every_list_item_says_where_it_is_realised(page):
    """Each fact or decision on a depth-2 or depth-3 page ends in `→` and an anchor, a component, or a link;
    an item under a lead-in that carries an anchor inherits it."""
    assert unplaced_list_items(page, read_page(page)) == []


def test_an_unplaced_list_item_is_reported_and_a_lead_in_anchor_covers_its_items():
    """A bare fact fails; the same fact under an anchored lead-in passes."""
    bare = "## Facts\n\n- a fact with no home\n"
    covered = "## Facts\n\nThe cases → `contracts/io.py::read_artifact`:\n\n- a fact with no home\n"
    assert unplaced_list_items("docs/x.md", bare) == [
        "docs/x.md: '- a fact with no home' names no anchor, component or link, and its lead-in none either"
    ]
    assert unplaced_list_items("docs/x.md", covered) == []


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
