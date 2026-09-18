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
The one policy for which links survive into rendered documentation (docs/authoring.md,
"URL policy"): an absolute `http`/`https`/`mailto` link is kept, everything else - a
relative link, a protocol-relative `//host/...` link, or any other scheme - is not. This
module has no consumer inside this PR other than its own tests and `html_to_markdown.py`;
it exists so a future PDF-generator text filter and `html_to_markdown` both import the same
vetted logic instead of each hand-rolling their own href/image allow-listing.

`nh3` (the HTML sanitizer `sanitize_html_fragment` uses) is imported inside that function
alone, so importing this module - or calling `safe_href`, which has no such dependency -
never requires the optional `html` extra. Only calling `sanitize_html_fragment` does.
"""

from typing import Optional
from urllib.parse import urlsplit

# The only schemes a kept link may use. `mailto` is included because an authored document
# legitimately links a contact address; every other scheme (`javascript:`, `data:`,
# `file:`, `ftp:`, ...) is a rendering or scripting risk this policy has no need to weigh
# case-by-case.
ALLOWED_SCHEMES = {"http", "https", "mailto"}


def safe_href(href: str) -> Optional[str]:
    """Returns `href` unchanged when it is an absolute link using one of `ALLOWED_SCHEMES`.
    Returns `None` for a relative link (no scheme), a protocol-relative link
    (`//host/...` - inherits whatever scheme the embedding page was loaded over, so it
    carries no scheme of its own to vet), or a link using any other scheme.
    """
    if href.startswith("//"):
        return None
    scheme = urlsplit(href).scheme
    if scheme.lower() not in ALLOWED_SCHEMES:
        return None
    return href


def sanitized_tag_allowlist() -> frozenset[str]:
    """The exact set of tags `sanitize_html_fragment` keeps - nh3's own default allow-list,
    minus `img` (stripped separately, see `sanitize_html_fragment`). Shared with
    `html_to_markdown._DropCountingParser` so its drop counts reflect the same policy nh3
    actually applies, rather than a second, hand-maintained copy that can drift from it.
    Imports `nh3` lazily, same as `sanitize_html_fragment`.
    """
    import nh3  # pylint: disable=import-outside-toplevel

    return frozenset(nh3.ALLOWED_TAGS - {"img"})


def sanitize_html_fragment(html: str) -> str:
    """Strips `<img>` tags entirely and drops any `href` attribute `safe_href` rejects,
    keeping the rest of a broad, conservative set of formatting tags (nh3's own default
    allow-list) and dropping everything else - `<script>`/`<style>` tags and their content,
    event-handler attributes (`onclick` and similar), and any tag nh3 does not recognise as
    safe formatting markup. Imports `nh3` lazily so importing this module never requires
    the optional `html` extra unless this specific function is called.
    """
    import nh3  # pylint: disable=import-outside-toplevel

    def _attribute_filter(_tag: str, attribute: str, value: str) -> Optional[str]:
        if attribute == "href":
            return safe_href(value)
        return value

    return nh3.clean(
        html,
        tags=sanitized_tag_allowlist(),
        attribute_filter=_attribute_filter,
        link_rel=None,
    )
