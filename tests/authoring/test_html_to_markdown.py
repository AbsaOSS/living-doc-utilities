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
`convert_html_to_markdown`: one test per supported construct (headings, paragraphs,
`<div>`/`<br>`, lists, tables, links, inline code), the hostile-input case that must fold
every drop - of whatever kind - into exactly one `HTML_CONTENT_DROPPED` warning, and two
cross-checks that its output really does reach the rest of the pipeline (`normalize` then
`issue_body`) in the same canonical form a hand-authored Markdown issue body would.
"""

import pytest

from living_doc_utilities.authoring.html_to_markdown import convert_html_to_markdown
from living_doc_utilities.authoring.issue_body import parse_issue_body
from living_doc_utilities.authoring.normalize import SourceFormat, normalize
from living_doc_utilities.authoring.status import derive_statuses
from tests.authoring.golden.helpers import load_expected, to_entity_dict


@pytest.mark.parametrize("level", [1, 2, 3, 4, 5, 6])
def test_heading_levels_produce_matching_hash_count(level):
    """An HTML heading of any level 1-6 converts to Markdown with the matching number of leading hash marks."""
    html = f"<h{level}>Title</h{level}>"

    text, warnings = convert_html_to_markdown(html)

    assert text == f"{'#' * level} Title"
    assert warnings == []


def test_paragraph_becomes_plain_text():
    """An HTML paragraph converts to its plain text content."""
    text, warnings = convert_html_to_markdown("<p>Some text</p>")

    assert text == "Some text"
    assert warnings == []


def test_div_with_br_splits_into_two_lines():
    """A `<div>` containing a `<br>` converts to two plain-text lines joined by a newline."""
    text, warnings = convert_html_to_markdown("<div>line one<br>line two</div>")

    assert text == "line one\nline two"
    assert warnings == []


def test_bare_div_becomes_plain_text():
    """A `<div>` with no line breaks converts to its plain text content."""
    text, warnings = convert_html_to_markdown("<div>text</div>")

    assert text == "text"
    assert warnings == []


@pytest.mark.parametrize("list_tag", ["ul", "ol"])
def test_list_renders_as_bullets_regardless_of_ordered_or_unordered(list_tag):
    """Both ordered and unordered HTML lists convert to the same plain bullet Markdown syntax."""
    html = f"<{list_tag}><li>a</li><li>b</li></{list_tag}>"

    text, warnings = convert_html_to_markdown(html)

    assert text == "- a\n- b"
    assert warnings == []


def test_table_renders_as_gfm_style_table():
    """An HTML table converts to a GitHub-Flavored-Markdown-style pipe table with a header separator row."""
    html = "<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>"

    text, warnings = convert_html_to_markdown(html)

    lines = text.split("\n")
    assert lines[0] == "A | B"
    assert lines[1] == "--- | ---"
    assert lines[2] == "1 | 2"
    assert len(lines) == 3
    assert warnings == []


def test_link_with_allowed_scheme_becomes_markdown_link():
    """A link with an allowed URL scheme converts to a Markdown link, preserving both text and href."""
    text, warnings = convert_html_to_markdown('<a href="https://example.com">click here</a>')

    assert text == "[click here](https://example.com)"
    assert warnings == []


def test_link_with_disallowed_scheme_keeps_text_and_warns():
    """A link with a disallowed URL scheme keeps its visible text but drops the href and warns."""
    text, warnings = convert_html_to_markdown('<a href="javascript:alert(1)">click</a>')

    assert text == "click"
    assert len(warnings) == 1
    assert warnings[0].code == "HTML_CONTENT_DROPPED"
    assert "unsafe_href=1" in warnings[0].context


def test_inline_code_becomes_backtick_span():
    """A `<code>` element converts to an inline backtick-delimited Markdown code span."""
    text, warnings = convert_html_to_markdown("<p>Use <code>foo()</code> here</p>")

    assert text == "Use `foo()` here"
    assert warnings == []


def test_hostile_input_folds_every_drop_kind_into_one_warning():
    """HTML mixing scripts, styles, event handlers, images and unsafe links is sanitized into a single warning."""
    hostile_html = (
        "<script>doEvil()</script>"
        "<style>.x { color: red; }</style>"
        '<div onclick="doEvil()">click me</div>'
        '<img src="x.png">'
        '<a href="javascript:alert(1)">bad link</a>'
    )

    text, warnings = convert_html_to_markdown(hostile_html)

    assert len(warnings) == 1
    warning = warnings[0]
    assert warning.code == "HTML_CONTENT_DROPPED"
    for expected_count in ("script_tag=1", "style_tag=1", "event_handler_attribute=1", "img_tag=1", "unsafe_href=1"):
        assert expected_count in warning.context

    assert "click me" in text
    assert "bad link" in text
    assert "<script" not in text
    assert "<style" not in text
    assert "onclick" not in text
    assert "<img" not in text
    assert "javascript:" not in text


def test_tag_outside_the_sanitizer_allowlist_is_counted_not_silently_dropped():
    """An HTML tag outside the sanitizer's allowlist is stripped and counted in a warning, not silently discarded."""
    text, warnings = convert_html_to_markdown('<p>keep</p><iframe src="https://evil.example">hijacked</iframe>')

    assert "keep" in text
    assert len(warnings) == 1
    assert "unsupported_tag=1" in warnings[0].context


def test_tag_with_no_markdown_form_is_unwrapped_and_counted_as_unknown_tag():
    """A sanitizer-allowed tag this converter can't render (e.g. `<strong>`) keeps its text and counts unknown_tag."""
    text, warnings = convert_html_to_markdown("<p>before <strong>bold</strong> after</p>")

    assert text == "before bold after"
    assert len(warnings) == 1
    assert "unknown_tag=1" in warnings[0].context


def test_en_dash_bullet_in_div_is_normalized_to_a_plain_bullet():
    """An en-dash-prefixed bullet from a converted div is normalized to a plain hyphen bullet once normalize runs."""
    html = "<h2>Business Value</h2><div>&ndash; Registered customers can reach their account area.</div>"

    text, warnings = convert_html_to_markdown(html)
    assert warnings == []

    normalized = normalize(text, SourceFormat.HTML_MARKDOWN, "DocumentedUserStory")

    assert "- Registered customers can reach their account area." in normalized.text
    assert "– Registered customers can reach their account area." not in normalized.text


def test_en_dash_bullet_reaches_issue_body_in_canonical_form():
    """An en-dash bullet converted from HTML reaches the parsed issue body as a canonical plain-bullet value."""
    html = "<h2>Business Value</h2><div>&ndash; Registered customers can reach their account area.</div>"

    text, warnings = convert_html_to_markdown(html)
    assert warnings == []

    normalized = normalize(text, SourceFormat.HTML_MARKDOWN, "DocumentedUserStory")
    entity, entity_warnings = parse_issue_body(normalized.text, "US-001 · Sample", "DocumentedUserStory")

    assert entity_warnings == []
    assert entity.business_value == ["Registered customers can reach their account area."]


_US_001_HTML = (
    "<h2>Description</h2>"
    "<p>As a registered customer, I can sign in with my email and password, "
    "so that I can reach my account area.</p>"
    "<h2>Status</h2>"
    "<p>active</p>"
    "<h2>Business Value</h2>"
    "<ul><li>Registered customers can reach their account area, "
    "so returning users convert without friction.</li></ul>"
    "<h2>Not In Scope</h2>"
    "<ul><li>Social-identity (OAuth) sign-in &mdash; tracked separately as US-002.</li></ul>"
    "<h2>Acceptance Criteria</h2>"
    "<h3>AC:US-001-01 (v1.0.0 - active)</h3>"
    "<ul><li>A customer who submits valid credentials lands on the account dashboard.</li></ul>"
    "<h3>AC:US-001-02 (v1.0.0 - active)</h3>"
    "<ul><li>An inline error is shown when the customer submits invalid credentials, "
    "without leaving the login screen.</li></ul>"
    "<h3>AC:US-001-03 (v1.1.0 - planned)</h3>"
    "<ul><li>A customer who forgot the password can request a reset link from the login screen.</li></ul>"
    "<h3>AC:US-001-04 (v1.0.0 - deprecated - removal planned v2.0.0)</h3>"
    '<ul><li>A "Remember me" choice keeps the customer signed in across browser restarts.</li></ul>'
)


def test_golden_us_001_rewritten_as_simple_html_matches_the_markdown_golden_fixture():
    """An HTML rewrite of the US-001 fixture, converted and parsed, matches the hand-authored Markdown golden."""
    text, html_warnings = convert_html_to_markdown(_US_001_HTML)
    assert html_warnings == []

    normalized = normalize(text, SourceFormat.HTML_MARKDOWN, "DocumentedUserStory")
    parsed, parse_warnings = parse_issue_body(normalized.text, "US-001 · Customer Login", "DocumentedUserStory")
    assert parse_warnings == []

    derived, derive_warnings = derive_statuses([parsed])
    assert derive_warnings == []

    assert to_entity_dict(derived[0]) == load_expected("us-001-customer-login.json")
