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

"""The page-structure rules: `Purpose` then `Contents`, `Contents` links, no orphan page (DEVELOPER.md)."""

import re

import pytest

from tests.docs.pages import (
    APPROVED_PAGES,
    REPO_BLOB_URL,
    REPO_ROOT,
    check_contents_links,
    check_no_orphans,
    check_purpose_then_contents,
    headings,
    page_depth,
    read_page,
)

_GOOD_PAGE = """# Title

## Purpose

Who reads this page, and what they get.

## Contents

- [Facts](#facts)

## Facts

- a fact
"""


def test_page_list_matches_the_docs_tree():
    """Every Markdown page under `docs/` is approved, every approved page exists, and its path gives its depth."""
    on_disk = {path.relative_to(REPO_ROOT).as_posix() for path in (REPO_ROOT / "docs").rglob("*.md")}
    approved_docs = {page for page in APPROVED_PAGES if page.startswith("docs/")}
    assert on_disk - approved_docs == set(), "unapproved page(s); add them to APPROVED_PAGES"
    assert approved_docs - on_disk == set(), "approved page(s) missing from docs/"
    for page, depth in APPROVED_PAGES.items():
        assert (REPO_ROOT / page).is_file(), f"{page}: approved but missing"
        assert page_depth(page) == depth, f"{page}: listed at depth {depth}, but its path gives {page_depth(page)}"


def test_depth_one_is_exactly_the_three_root_pages():
    """Depth 1 is `README.md`, `DEVELOPER.md` and `CONTRIBUTING.md`, and neither solo page has child pages."""
    assert sorted(page for page, depth in APPROVED_PAGES.items() if depth == 1) == [
        "CONTRIBUTING.md",
        "DEVELOPER.md",
        "README.md",
    ]
    assert not (REPO_ROOT / "docs" / "DEVELOPER").exists() and not (REPO_ROOT / "docs" / "CONTRIBUTING").exists()


def test_every_depth_three_page_sits_under_an_approved_hub():
    """A depth-3 page `docs/<topic>/<page>.md` has its hub `docs/<topic>.md` in the approved list."""
    for page, depth in APPROVED_PAGES.items():
        if depth == 3:
            hub = f"docs/{page.split('/')[1]}.md"
            assert hub in APPROVED_PAGES, f"{page}: its hub {hub} is not an approved page"


@pytest.mark.parametrize("page", sorted(APPROVED_PAGES))
def test_page_opens_with_purpose_then_contents(page):
    """The page's first `##` heading is `Purpose` and its second is `Contents`."""
    assert check_purpose_then_contents(page, read_page(page)) == []


@pytest.mark.parametrize("page", sorted(APPROVED_PAGES))
def test_contents_links_every_chapter_and_nothing_else(page):
    """Every `Contents` link resolves to a `##` chapter of the same page, and every chapter is listed."""
    assert check_contents_links(page, read_page(page)) == []


def test_no_page_is_an_orphan():
    """Every approved page is linked from its hub or from `README.md`."""
    assert check_no_orphans({page: read_page(page) for page in APPROVED_PAGES}) == []


def test_readme_links_work_on_pypi():
    """README.md is the PyPI long description, so it links repository files absolutely; relative links 404 there."""
    targets = re.findall(r"\]\(([^)\s]+)\)", read_page("README.md"))
    relative = [target for target in targets if not target.startswith(("#", "https://", "http://", "mailto:"))]
    assert relative == [], f"README.md: use {REPO_BLOB_URL}<path> for these links: {relative}"


def test_an_absolute_repository_link_counts_as_a_link_into_the_tree():
    """A README link by `REPO_BLOB_URL` puts a hub into the tree, exactly as a relative link does."""
    pages = {"README.md": f"[Hub]({REPO_BLOB_URL}docs/topic.md#principle)", "docs/topic.md": ""}
    assert check_no_orphans(pages) == []


def test_a_backtick_in_a_backtick_fence_info_string_does_not_open_a_fence():
    """A backtick in a backtick-fence info string leaves the following heading visible to the parser."""
    page = "# Title\n\n```bad`info\n## Actually A Heading\n```\n"
    assert headings(page, 2) == ["Actually A Heading"]


def test_a_well_formed_page_passes_every_check():
    """The synthetic page the planted-violation tests start from is itself clean."""
    assert check_purpose_then_contents("docs/x.md", _GOOD_PAGE) == []
    assert check_contents_links("docs/x.md", _GOOD_PAGE) == []


def test_planted_missing_purpose_is_reported_naming_the_page():
    """A page without `## Purpose` fails, and the message names the page."""
    page = _GOOD_PAGE.replace("## Purpose\n\nWho reads this page, and what they get.\n\n", "")
    assert check_purpose_then_contents("docs/x.md", page) == [
        "docs/x.md: the first two '##' headings must be 'Purpose', 'Contents'; found ['Contents', 'Facts']"
    ]


def test_planted_wrong_order_is_reported_naming_the_page():
    """`Contents` before `Purpose` fails."""
    page = "# Title\n\n## Contents\n\n- [Purpose](#purpose)\n\n## Purpose\n\nText.\n"
    assert check_purpose_then_contents("docs/x.md", page) == [
        "docs/x.md: the first two '##' headings must be 'Purpose', 'Contents'; found ['Contents', 'Purpose']"
    ]


def test_planted_dead_contents_link_is_reported_naming_the_page():
    """A `Contents` link to a chapter the page does not have fails, as does the chapter it leaves out."""
    page = _GOOD_PAGE.replace("- [Facts](#facts)", "- [Facts](#fact-list)")
    assert check_contents_links("docs/x.md", page) == [
        "docs/x.md: 'Contents' links to '#fact-list', which is no '##' chapter of the page",
        "docs/x.md: chapter '## Facts' is missing from 'Contents'",
    ]


def test_planted_contents_line_that_is_not_a_chapter_link_is_reported():
    """`Contents` holds only chapter links; prose or an outside link fails."""
    page = _GOOD_PAGE.replace("- [Facts](#facts)", "- [Facts](#facts)\n- [Elsewhere](other.md)")
    assert check_contents_links("docs/x.md", page) == [
        "docs/x.md: 'Contents' may hold only '- [title](#chapter)' lines; found '- [Elsewhere](other.md)'"
    ]


def test_planted_orphan_page_is_reported_naming_the_page():
    """A depth-3 page linked neither from its hub nor from `README.md` fails."""
    pages = {
        "README.md": "[Hub](docs/topic.md)",
        "docs/topic.md": "[A](topic/a.md)",
        "docs/topic/a.md": "",
        "docs/topic/b.md": "",
    }
    assert check_no_orphans(pages) == ["docs/topic/b.md: orphan page; link it from README.md or docs/topic.md"]


def test_a_page_linked_only_from_a_sibling_is_still_an_orphan():
    """A link from another depth-3 page does not count; only the hub or `README.md` puts a page in the tree."""
    pages = {
        "README.md": "[Hub](docs/topic.md)",
        "docs/topic.md": "",
        "docs/topic/a.md": "[B](b.md)",
        "docs/topic/b.md": "",
    }
    assert check_no_orphans(pages) == [
        "docs/topic/a.md: orphan page; link it from README.md or docs/topic.md",
        "docs/topic/b.md: orphan page; link it from README.md or docs/topic.md",
    ]
