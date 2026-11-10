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

import pytest

from tests.docs.pages import (
    _CODE_SPAN_RE,
    APPROVED_PAGES,
    REPO_BLOB_URL,
    REPO_ROOT,
    _link_targets,
    check_contents_links,
    check_no_orphans,
    check_page_list,
    check_purpose_then_contents,
    headings,
    read_page,
    tracked_markdown,
    unfenced_lines,
)

_GOOD_PAGE = """# Title

## Purpose

This page is what the page is for.

## Contents

- [Facts](#facts)

## Facts

- a fact
"""


def test_page_list_matches_the_tracked_pages():
    """Every tracked page is approved, every approved page is tracked, and its path gives its depth."""
    assert check_page_list(tracked_markdown(), APPROVED_PAGES) == []


def test_planted_page_list_violations_are_reported_naming_the_page():
    """An unapproved page, an approved page git does not track, and a wrong depth each fail."""
    approved = {"README.md": 1, "docs/api.md": 2, "docs/gone.md": 2, "CONTRIBUTING.md": 2}
    listed = {"README.md", "docs/api.md", "CONTRIBUTING.md", "CHANGELOG.md"}
    assert check_page_list(listed, approved) == [
        "CHANGELOG.md: unapproved page; add it to APPROVED_PAGES",
        "docs/gone.md: approved but not tracked",
        "CONTRIBUTING.md: listed at depth 2, but its path gives 1",
    ]


def test_a_code_map_and_the_documents_under_test_fixtures_are_no_pages():
    """A `CONTEXT.md` beside the pages and an authored document under `tests/fixtures/` are not pages."""
    listed = tracked_markdown()
    assert "docs/contracts/CONTEXT.md" not in listed
    assert "tests/fixtures/golden/gh-issues/us-001-customer-login.md" not in listed


def test_depth_one_is_exactly_the_three_root_pages():
    """Depth 1 is `README.md`, `DEVELOPER.md` and `CONTRIBUTING.md`, and neither solo page has child pages."""
    solo = ["CONTRIBUTING.md", "DEVELOPER.md"]
    assert sorted(page for page, depth in APPROVED_PAGES.items() if depth == 1) == sorted(["README.md", *solo])
    assert [page for page in solo if (REPO_ROOT / "docs" / page.removesuffix(".md")).exists()] == []


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


def _relative_links(readme: str) -> list[str]:
    """The targets of `readme`'s links that are neither absolute nor a fragment, every link form read as the orphan
    check reads it: outside fenced code blocks, HTML comments and code spans."""
    prose = _CODE_SPAN_RE.sub("", "\n".join(unfenced_lines(readme)))
    return [target for target in _link_targets(prose) if not target.startswith(("#", "https://", "http://", "mailto:"))]


def test_readme_links_work_on_pypi():
    """README.md is the PyPI long description, so it links repository files absolutely; relative links 404 there."""
    relative = _relative_links(read_page("README.md"))
    assert relative == [], f"README.md: use {REPO_BLOB_URL}<path> for these links: {relative}"


@pytest.mark.parametrize(
    "readme, relative",
    [
        ("See [the API][r].\n\n[r]: docs/api.md\n", ["docs/api.md"]),
        ('See [the API](docs/api.md "t").\n', ["docs/api.md"]),
        ("`[the API](docs/api.md)`\n\n```text\n[the API](docs/api.md)\n```\n", []),
    ],
    ids=["reference-style", "titled", "code-span-and-fence"],
)
def test_a_relative_readme_link_is_found_in_every_markdown_link_form(readme, relative):
    """A relative reference-style or titled link breaks on PyPI as an inline one does; a link in code renders none."""
    assert _relative_links(readme) == relative


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
    page = _GOOD_PAGE.replace("## Purpose\n\nThis page is what the page is for.\n\n", "")
    assert check_purpose_then_contents("docs/x.md", page) == [
        "docs/x.md: the page must open with '# <title>', '## Purpose', '## Contents'; "
        "found ['# Title', '## Contents', '## Facts']"
    ]


def test_planted_wrong_order_is_reported_naming_the_page():
    """`Contents` before `Purpose` fails."""
    page = "# Title\n\n## Contents\n\n- [Purpose](#purpose)\n\n## Purpose\n\nText.\n"
    assert check_purpose_then_contents("docs/x.md", page) == [
        "docs/x.md: the page must open with '# <title>', '## Purpose', '## Contents'; "
        "found ['# Title', '## Contents', '## Purpose']"
    ]


def test_planted_heading_before_purpose_is_reported():
    """A `###` section between the title and `## Purpose` means the page does not open with its Purpose."""
    page = _GOOD_PAGE.replace("## Purpose", "Intro.\n\n### Quick start\n\nText.\n\n## Purpose")
    assert check_purpose_then_contents("docs/x.md", page) == [
        "docs/x.md: the page must open with '# <title>', '## Purpose', '## Contents'; "
        "found ['# Title', '### Quick start', '## Purpose']"
    ]


def test_planted_missing_title_is_reported():
    """A page that starts at `## Purpose`, with no `#` title, fails."""
    page = _GOOD_PAGE.replace("# Title\n\n", "")
    assert check_purpose_then_contents("docs/x.md", page) == [
        "docs/x.md: the page must open with '# <title>', '## Purpose', '## Contents'; "
        "found ['## Purpose', '## Contents', '## Facts']"
    ]


def test_badges_and_a_comment_between_title_and_purpose_are_allowed():
    """Badge lines and an HTML comment are no heading, so the page still opens with its Purpose."""
    page = _GOOD_PAGE.replace(
        "## Purpose", "![Status](https://img.shields.io/badge/x-y-blue)\n\n<!-- ## Draft -->\n\n## Purpose"
    )
    assert check_purpose_then_contents("docs/x.md", page) == []


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


def test_a_second_chapter_with_the_same_title_needs_its_own_contents_entry():
    """GitHub gives a repeated `## Facts` the fragment `#facts-1`; `Contents` must link that too, not just `#facts`."""
    page = "# Title\n\n## Purpose\n\nText.\n\n## Contents\n\n- [Facts](#facts)\n\n## Facts\n\n- a\n\n## Facts\n\n- b\n"
    assert check_contents_links("docs/x.md", page) == ["docs/x.md: chapter '## Facts' is missing from 'Contents'"]


def test_a_literal_heading_matching_a_generated_suffix_still_gets_its_own_fragment():
    """A literal `## Facts-1` chapter collides with the suffix GitHub already gave the second `## Facts`, so it
    becomes `#facts-1-1`, and that fragment - not the already-used `#facts-1` - is what `Contents` must link."""
    page = (
        "# Title\n\n## Purpose\n\nText.\n\n## Contents\n\n"
        "- [Facts](#facts)\n- [Facts](#facts-1)\n- [Facts-1](#facts-1-1)\n\n"
        "## Facts\n\n- a\n\n## Facts\n\n- b\n\n## Facts-1\n\n- c\n"
    )
    assert check_contents_links("docs/x.md", page) == []


def test_fragments_are_numbered_in_page_order_including_purpose_and_contents():
    """`## Purpose` claims `#purpose` before any chapter is numbered, so a later chapter that also slugs to
    `purpose` is `#purpose-1`, matching GitHub's page-wide numbering, not a fresh `#purpose`."""
    page = "# Title\n\n## Purpose\n\nText.\n\n## Contents\n\n- [Purpose!](#purpose-1)\n\n## Purpose!\n\nText.\n"
    assert check_contents_links("docs/x.md", page) == []


def test_a_subsection_takes_part_in_the_fragment_numbering():
    """GitHub numbers repeated fragments across every heading level: after a `### Usage`, the chapter `## Usage` is
    `#usage-1`, and `#usage` lands on the subsection."""
    page = (
        "# Title\n\n## Purpose\n\nText.\n\n## Contents\n\n- [Activation](#activation)\n- [Usage](#usage)\n\n"
        "## Activation\n\n### Usage\n\nText.\n\n## Usage\n\nText.\n"
    )
    assert check_contents_links("docs/x.md", page) == [
        "docs/x.md: 'Contents' links to '#usage', which is no '##' chapter of the page",
        "docs/x.md: chapter '## Usage' is missing from 'Contents'",
    ]
    assert check_contents_links("docs/x.md", page.replace("](#usage)", "](#usage-1)")) == []


def test_a_commented_out_heading_is_not_a_chapter():
    """A `##` line inside a multi-line HTML comment renders as nothing, so `Contents` need not link it."""
    page = _GOOD_PAGE + "\n<!--\n## Old\n\nRetired text.\n-->\n"
    assert check_contents_links("docs/x.md", page) == []


def test_a_comment_marker_inside_a_code_span_is_text():
    """`` `<!--` `` and a later `` `-->` `` are code on GitHub, not a comment, so the headings between them stay."""
    page = _GOOD_PAGE.replace("This page is", "Write `<!--` to open one. This page is") + (
        "\n## More\n\nClose it with `-->`.\n"
    )
    assert check_purpose_then_contents("docs/x.md", page) == []
    assert check_contents_links("docs/x.md", page) == ["docs/x.md: chapter '## More' is missing from 'Contents'"]


def test_emphasis_in_a_heading_is_dropped_from_its_fragment():
    """`## **Branch Naming**` is `#branch-naming` on GitHub, so `Contents` links it by that fragment."""
    page = (
        "# Title\n\n## Purpose\n\nText.\n\n## Contents\n\n- [Branch Naming](#branch-naming)\n\n## **Branch Naming**\n"
    )
    assert check_contents_links("docs/x.md", page) == []


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


def test_a_link_inside_a_fenced_code_block_does_not_count_as_navigation():
    """A repository-shaped link inside an illustrative code example is not a real link into the tree."""
    pages = {"README.md": "```text\n[Hub](docs/topic.md)\n```\n", "docs/topic.md": ""}
    assert check_no_orphans(pages) == ["docs/topic.md: orphan page; link it from README.md"]


@pytest.mark.parametrize(
    "readme",
    ["<!-- [Hub](docs/topic.md) -->\n", "`[Hub](docs/topic.md)`\n"],
    ids=["html-comment", "code-span"],
)
def test_a_commented_out_or_code_span_link_does_not_count_as_navigation(readme):
    """GitHub renders no link inside an HTML comment or a code span, so the page stays an orphan."""
    assert check_no_orphans({"README.md": readme, "docs/topic.md": ""}) == [
        "docs/topic.md: orphan page; link it from README.md"
    ]


def test_a_code_span_wrapped_across_lines_leaves_a_later_link_alone():
    """A code span may cross a line break; its backticks pair with each other, not with a later one."""
    readme = "Run `make\nqa` first, then read the [hub](docs/topic.md) and `x`.\n"
    assert check_no_orphans({"README.md": readme, "docs/topic.md": ""}) == []


def test_a_run_indented_four_spaces_does_not_close_an_indented_top_level_fence():
    """A closing fence takes at most three spaces, whatever the opener's own indentation; four or more are code."""
    page = "  ```text\n     ```\n## Not a heading\n  ```\n\n## Next\n"
    assert headings(page, 2) == ["Next"]


def test_a_fence_inside_an_html_comment_hides_nothing():
    """A fence in a commented-out block opens no code block, so the headings after the comment are still read."""
    page = "# T\n\n<!--\n```python\nraise SystemExit\n-->\n\n## Visible\n"
    assert headings(page, 2) == ["Visible"]


@pytest.mark.parametrize(
    "readme",
    [
        '[Hub](docs/topic.md "Topic hub")\n',
        "[Hub](docs/topic.md 'Topic hub')\n",
        "[Hub](<docs/topic.md>)\n",
        "[Hub][hub]\n\n[hub]: docs/topic.md\n",
        "[Hub][HUB]\n\n[hub]: docs/topic.md 'Topic hub'\n",
        "[hub][]\n\n[hub]: docs/topic.md\n",
        "[hub]\n\n[hub]: docs/topic.md\n",
    ],
    ids=["double-quoted-title", "single-quoted-title", "angle-brackets", "full", "any-case", "collapsed", "shortcut"],
)
def test_every_markdown_link_form_counts_as_navigation(readme):
    """A titled, bracketed or reference-style link renders as a link on GitHub, so it puts the page in the tree."""
    assert check_no_orphans({"README.md": readme, "docs/topic.md": ""}) == []


def test_a_reference_definition_nothing_uses_does_not_count_as_navigation():
    """A definition alone renders nothing, so the page it names stays an orphan."""
    assert check_no_orphans({"README.md": "[hub]: docs/topic.md\n", "docs/topic.md": ""}) == [
        "docs/topic.md: orphan page; link it from README.md"
    ]
