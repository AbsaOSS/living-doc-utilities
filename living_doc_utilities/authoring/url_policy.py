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
The one policy for which links survive into rendered documentation: an absolute
`http`/`https`/`mailto` link is kept, everything else is dropped. Shared by
`html_to_markdown.py` and any future consumer needing the same vetted href/image logic.
"""

from typing import Optional
from urllib.parse import urlsplit

# The only schemes a kept link may use; mailto for contact links, other schemes (javascript:, data:, ...) are risks.
ALLOWED_SCHEMES = {"http", "https", "mailto"}


def safe_href(href: str) -> Optional[str]:
    """Returns `href` unchanged when it's an absolute link using one of `ALLOWED_SCHEMES`;
    `None` for a relative or protocol-relative (`//host/...`) link, or any other scheme."""
    scheme = urlsplit(href).scheme
    if scheme.lower() not in ALLOWED_SCHEMES:
        return None
    return href


def sanitized_tag_allowlist() -> frozenset[str]:
    """The exact set of tags `sanitize_html_fragment` keeps - nh3's default allow-list, minus
    `img`. Shared with `html_to_markdown.py::_DropCountingParser` so its drop counts match nh3's
    actual policy, not a second copy that can drift."""
    import nh3  # pylint: disable=import-outside-toplevel

    return frozenset(nh3.ALLOWED_TAGS - {"img"})


def sanitize_html_fragment(html: str) -> str:
    """Strips `<img>` tags and any `href` `safe_href` rejects, keeping nh3's default
    allow-list of formatting tags and dropping the rest (`<script>`/`<style>` and content,
    event-handler attributes, unrecognised tags). Imports `nh3` lazily."""
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
