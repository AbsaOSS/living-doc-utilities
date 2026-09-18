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
The one URL policy for which links survive into rendered documentation
(docs/authoring.md, "URL policy"): `safe_href` keeps an absolute `http`/`https`/`mailto`
link and rejects everything else, and `sanitize_html_fragment` applies that same policy
(plus a broad, conservative tag/attribute allow-list) to an entire HTML fragment.
"""

import pytest

from living_doc_utilities.authoring.url_policy import ALLOWED_SCHEMES, safe_href, sanitize_html_fragment


def test_allowed_schemes_is_exactly_http_https_mailto():
    assert ALLOWED_SCHEMES == {"http", "https", "mailto"}


@pytest.mark.parametrize(
    ("href", "expected"),
    [
        ("http://example.com", "http://example.com"),
        ("https://example.com/path?q=1", "https://example.com/path?q=1"),
        ("mailto:person@example.com", "mailto:person@example.com"),
        ("javascript:alert(1)", None),
        ("data:text/html,<script>alert(1)</script>", None),
        ("file:///etc/passwd", None),
        ("/login", None),
        ("path/to/page", None),
        ("//evil.example/x", None),
    ],
)
def test_safe_href(href, expected):
    assert safe_href(href) == expected


def test_sanitize_html_fragment_drops_img_tag_entirely():
    result = sanitize_html_fragment('<img src="x.png">')

    assert "<img" not in result


def test_sanitize_html_fragment_keeps_a_safe_links_href():
    result = sanitize_html_fragment('<a href="https://example.com">text</a>')

    assert 'href="https://example.com"' in result
    assert "<a" in result
    assert "text" in result


def test_sanitize_html_fragment_drops_unsafe_href_but_keeps_text():
    result = sanitize_html_fragment('<a href="javascript:alert(1)">text</a>')

    assert "javascript:" not in result
    assert "text" in result


def test_sanitize_html_fragment_drops_script_tag_and_its_content():
    result = sanitize_html_fragment("<script>alert(1)</script>safe")

    assert result == "safe"


def test_sanitize_html_fragment_drops_event_handler_attribute():
    result = sanitize_html_fragment('<b onclick="x()">bold</b>')

    assert "onclick" not in result
    assert "bold" in result
