# URLs and HTML

## Purpose

Anyone who renders links or reads Azure DevOps rich text reads this page. It defines which links survive, how HTML
is sanitised, and how HTML becomes the Markdown-like text the parsers read.

Read before: [Parsers](parsers.md) · Next: back to [Authoring](../authoring.md)

## Contents

- [URL policy](#url-policy)
- [HTML sanitising](#html-sanitising)
- [HTML to Markdown conversion](#html-to-markdown-conversion)
- [Example](#example)

## URL policy

One small policy decides which links survive into rendered documentation → `authoring/url_policy.py::safe_href`.

- Allowed schemes: `http`, `https`, `mailto` → `authoring/url_policy.py::ALLOWED_SCHEMES`
- `safe_href(href)` returns `href` unchanged when it is absolute and uses an allowed scheme; `http` and `https` also need a host → `authoring/url_policy.py::safe_href`

`safe_href` returns `None` for:

| Link | Example | Why |
|---|---|---|
| relative | `docs/page.md` | no scheme to vet |
| protocol-relative | `//host/page` | it inherits whatever scheme the page loaded over |
| hostless | `https:example` | an `http`/`https` link needs a host |
| any other scheme | `javascript:`, `data:`, `file:` | a risk, not a documentation link |

## HTML sanitising

- `sanitize_html_fragment(html)` cleans a fragment with [`nh3`](https://pypi.org/project/nh3/), an `ammonia`-based sanitiser → `authoring/url_policy.py::sanitize_html_fragment`
- It strips every `<img>` tag → `authoring/url_policy.py::sanitized_tag_allowlist`
- It passes every `href` through `safe_href`; a rejected `href` is dropped and the element's text kept → `authoring/url_policy.py::sanitize_html_fragment`
- nh3's default allow-list handles the rest: `<script>` and `<style>` with their content, event-handler attributes, tags outside its set.
- `nh3` needs the `html` extra and is imported inside the two functions that use it → `tests/authoring/test_isolation.py::test_nh3_is_imported_only_inside_a_function_that_needs_it`
  - Why: most consumers never touch HTML; importing a module or calling `safe_href` never needs the extra.
- Its only consumer today is `html_to_markdown`; a future PDF-generator text filter can reuse the same policy → `authoring/url_policy.py::sanitize_html_fragment`

## HTML to Markdown conversion

`convert_html_to_markdown(html)` returns `(text, warnings)` → `authoring/html_to_markdown.py::convert_html_to_markdown`.

- Its output goes through `normalize(text, SourceFormat.HTML_MARKDOWN, entity_type)` and then a parser, like any other format.
- It only turns markup into text; it never derives an entity id or a field.
- It never raises on malformed input; what it cannot render is dropped and counted.

Supported tags → `authoring/html_to_markdown.py::_SUPPORTED_TAGS`:

| Tag | Rendered as |
|---|---|
| `<h1>` to `<h6>` | a `#` to `######` heading |
| `<p>` | a paragraph |
| `<div>`, `<br>` | line grouping |
| `<ul>`, `<ol>`, `<li>` | `- ` bullets; the bullet grammar has no ordered list |
| `<table>`, `<thead>`, `<tbody>`, `<tfoot>`, `<tr>`, `<td>`, `<th>` | a GitHub-Flavored-Markdown table |
| `<a href="...">` | `[text](href)`, or only the text when `safe_href` rejected the link |
| `<code>` | inline code |

- Sanitising is delegated to `sanitize_html_fragment`, not reimplemented → `authoring/html_to_markdown.py::convert_html_to_markdown`
- Any other tag that survives sanitising, such as `<strong>`, is unwrapped: text kept, markup dropped → `authoring/html_to_markdown.py::_TreeBuilder`
- Every drop in one call folds into one `HTML_CONTENT_DROPPED` warning with per-kind counts in its context → `authoring/html_to_markdown.py::_build_warnings`
  - Why: a caller that processes many documents is not flooded with one warning per stripped tag.
- Scope: well-formed HTML. Quirks of the real Azure DevOps editor belong to the Azure DevOps collector, once samples exist.

Drop kinds counted in the warning context, e.g. `img_tag=1, script_tag=1` → `authoring/html_to_markdown.py::_DropCountingParser`:

| Kind | Counts |
|---|---|
| `script_tag` | a `<script>` element |
| `style_tag` | a `<style>` element |
| `event_handler_attribute` | an `on…` attribute |
| `img_tag` | an `<img>` element |
| `unsupported_tag` | a tag outside nh3's kept set |
| `unsafe_href` | a link `safe_href` rejects |
| `unknown_tag` | a kept tag this converter cannot render, unwrapped |

## Example

Needs the `html` extra ([Extras](../api.md#extras)).

```python
from living_doc_utilities.authoring.html_to_markdown import convert_html_to_markdown
from living_doc_utilities.authoring.url_policy import safe_href

html = '<h2>Description</h2><p>Sign in <a href="javascript:alert(1)">here</a>.</p><img src="x.png">'
text, warnings = convert_html_to_markdown(html)

assert text.splitlines()[0] == "## Description"
assert [warning.code for warning in warnings] == ["HTML_CONTENT_DROPPED"]
assert safe_href("https://example.com") == "https://example.com"
assert safe_href("//example.com") is None
```
