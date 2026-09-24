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

"""
The approved documentation pages and the checks the page rules need (DEVELOPER.md, "Writing documentation").
Each check takes page text and returns one message per problem, each naming the page, so a test can also
plant a violation in a synthetic page and see it reported.
"""

import re
from pathlib import Path, PurePosixPath
from typing import NamedTuple

REPO_ROOT = Path(__file__).resolve().parents[2]

# README.md is also the PyPI long description, so it links repository files by this absolute prefix; the link
# check remaps it onto the checked-out files (.github/workflows/link-check.yml).
REPO_BLOB_URL = "https://github.com/AbsaOSS/living-doc-utilities/blob/master/"

# Every shipped page and its depth; a new page is added here and linked from its hub.
APPROVED_PAGES: dict[str, int] = {
    "README.md": 1,
    "DEVELOPER.md": 1,
    "CONTRIBUTING.md": 1,
    "docs/api.md": 2,
    "docs/contracts.md": 2,
    "docs/authoring.md": 2,
    "docs/contracts/entities-and-state.md": 3,
    "docs/contracts/schema-rules.md": 3,
    "docs/contracts/artifact-rules.md": 3,
    "docs/contracts/pipeline-rules.md": 3,
    "docs/contracts/component-checks.md": 3,
    "docs/contracts/rendering.md": 3,
    "docs/contracts/errors.md": 3,
    "docs/authoring/normalisation.md": 3,
    "docs/authoring/ac-grammar.md": 3,
    "docs/authoring/parsers.md": 3,
    "docs/authoring/urls-and-html.md": 3,
}

_FENCE_RE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
_FENCE_CLOSE_RE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})\s*$")
_HEADING_RE = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<text>.*?)\s*#*\s*$")
_LIST_LINK_RE = re.compile(r"^[-*]\s+\[[^\]]*\]\((?P<target>[^)\s]*)\)\s*$")
_LINK_TARGET_RE = re.compile(r"\]\((?P<target>[^)\s]+)\)")


class CodeBlock(NamedTuple):
    """One fenced block: its info string (e.g. `python`), its code, and the non-blank line right above it."""

    info: str
    code: str
    line_above: str


def _closes(line: str, fence: str) -> bool:
    """Whether `line` closes a block opened with `fence`: the same character, at least as many times."""
    close_m = _FENCE_CLOSE_RE.match(line)
    return close_m is not None and close_m.group("fence")[0] == fence[0] and len(close_m.group("fence")) >= len(fence)


def read_page(page: str) -> str:
    """The text of an approved page, read from the repository."""
    return (REPO_ROOT / page).read_text(encoding="utf-8")


def unfenced_lines(text: str) -> list[str]:
    """The page's lines outside fenced code blocks, so a `#` comment in a code block is never a heading."""
    lines: list[str] = []
    fence: str | None = None
    for line in text.splitlines():
        fence_m = _FENCE_RE.match(line)
        if fence is None and fence_m:
            fence = fence_m.group("fence")
            continue
        if fence is not None:
            if _closes(line, fence):
                fence = None
            continue
        lines.append(line)
    return lines


def code_blocks(text: str) -> list[CodeBlock]:
    """Every fenced block of the page, in order."""
    blocks: list[CodeBlock] = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        fence_m = _FENCE_RE.match(lines[index])
        if fence_m is None:
            index += 1
            continue
        fence = fence_m.group("fence")
        above = next((line.strip() for line in reversed(lines[:index]) if line.strip()), "")
        body: list[str] = []
        index += 1
        while index < len(lines) and not _closes(lines[index], fence):
            body.append(lines[index])
            index += 1
        blocks.append(CodeBlock(fence_m.group("info").strip(), "\n".join(body) + "\n", above))
        index += 1
    return blocks


def headings(text: str, level: int) -> list[str]:
    """The text of every heading of exactly `level` (2 for `##`) outside fenced blocks."""
    found = []
    for line in unfenced_lines(text):
        heading_m = _HEADING_RE.match(line)
        if heading_m and len(heading_m.group("hashes")) == level:
            found.append(heading_m.group("text"))
    return found


def slug(heading: str) -> str:
    """The fragment GitHub gives a heading: emphasis and code markers dropped, lowercased, punctuation removed,
    each space a hyphen."""
    rendered = heading.replace("`", "").replace("**", "").lower()
    kept = "".join(char for char in rendered if char.isalnum() or char in " -_")
    return kept.replace(" ", "-")


def section(text: str, title: str) -> list[str]:
    """The lines under the `## <title>` heading, up to the next `##` heading."""
    body: list[str] = []
    inside = False
    for line in unfenced_lines(text):
        heading_m = _HEADING_RE.match(line)
        if heading_m and len(heading_m.group("hashes")) == 2:
            inside = heading_m.group("text") == title
            continue
        if inside:
            body.append(line)
    return body


def check_purpose_then_contents(page: str, text: str) -> list[str]:
    """The first `##` heading is `Purpose` and the second is `Contents`."""
    chapters = headings(text, 2)
    if chapters[:2] == ["Purpose", "Contents"]:
        return []
    return [f"{page}: the first two '##' headings must be 'Purpose', 'Contents'; found {chapters[:2]!r}"]


def check_contents_links(page: str, text: str) -> list[str]:
    """`Contents` links to every other `##` chapter of the page, and to nothing else."""
    chapters = {slug(title): title for title in headings(text, 2) if title not in ("Purpose", "Contents")}
    problems: list[str] = []
    linked: set[str] = set()
    for line in section(text, "Contents"):
        if not line.strip():
            continue
        link_m = _LIST_LINK_RE.match(line.strip())
        if link_m is None or not link_m.group("target").startswith("#"):
            problems.append(f"{page}: 'Contents' may hold only '- [title](#chapter)' lines; found {line.strip()!r}")
            continue
        fragment = link_m.group("target")[1:]
        if fragment not in chapters:
            problems.append(f"{page}: 'Contents' links to '#{fragment}', which is no '##' chapter of the page")
        linked.add(fragment)
    for fragment, title in chapters.items():
        if fragment not in linked:
            problems.append(f"{page}: chapter '## {title}' is missing from 'Contents'")
    return problems


def _resolved_links(page: str, text: str) -> set[str]:
    """Every link of the page into the repository, relative or by `REPO_BLOB_URL`, as a repository path without its
    fragment."""
    base = PurePosixPath(page).parent
    resolved: set[str] = set()
    for link_m in _LINK_TARGET_RE.finditer(text):
        target = link_m.group("target").split("#", 1)[0]
        target_base = base
        if target.startswith(REPO_BLOB_URL):
            target, target_base = target[len(REPO_BLOB_URL) :], PurePosixPath(".")
        if not target or "://" in target or target.startswith("mailto:"):
            continue
        parts: list[str] = []
        for part in (target_base / target).parts:
            if part == "..":
                if parts:
                    parts.pop()
            elif part != ".":
                parts.append(part)
        resolved.add("/".join(parts))
    return resolved


def expected_parents(page: str) -> set[str]:
    """The pages allowed to link `page` into the tree: its hub for a depth-3 page, and `README.md`."""
    parts = PurePosixPath(page).parts
    if len(parts) == 3:
        return {f"docs/{parts[1]}.md", "README.md"}
    return {"README.md"}


def check_no_orphans(pages: dict[str, str]) -> list[str]:
    """Every page except `README.md` is linked from its hub or from `README.md`."""
    links = {page: _resolved_links(page, text) for page, text in pages.items()}
    problems = []
    for page in pages:
        if page == "README.md":
            continue
        if not any(page in links.get(parent, set()) for parent in expected_parents(page)):
            parents = " or ".join(sorted(expected_parents(page)))
            problems.append(f"{page}: orphan page; link it from {parents}")
    return problems


def page_depth(page: str) -> int:
    """The depth a page's path gives it: 1 at the root, 2 in `docs/`, 3 in `docs/<topic>/`."""
    return len(PurePosixPath(page).parts)
