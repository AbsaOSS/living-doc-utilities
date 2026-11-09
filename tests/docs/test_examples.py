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

"""Every documentation example runs: `python` executes, `json` parses and validates its marked model."""

import importlib
import json
import re

import pytest

from tests.docs.pages import APPROVED_PAGES, code_blocks, read_page

_MODEL_MARKER_RE = re.compile(r"^<!-- example: (?P<module>[\w.]+)\.(?P<model>[A-Z]\w*) -->$")


def _examples(info: str) -> list:
    return [
        pytest.param(block, id=f"{page}#{index}")
        for page in sorted(APPROVED_PAGES)
        for index, block in enumerate(code_blocks(read_page(page)))
        if block.info == info
    ]


@pytest.mark.parametrize("block", _examples("python"))
def test_python_example_runs(block, tmp_path, monkeypatch):
    """The block runs in a fresh namespace, in a temporary working directory, with the inputs an action has."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("INPUT_GITHUB_TOKEN", "doc-example-token")
    exec(compile(block.code, "<doc example>", "exec"), {"__name__": "doc_example"})  # pylint: disable=exec-used


@pytest.mark.parametrize("block", _examples("json"))
def test_json_example_parses_and_validates(block):
    """The block parses as JSON and, when marked with a model, validates as that model."""
    payload = json.loads(block.code)
    marker_m = _MODEL_MARKER_RE.match(block.line_above)
    if marker_m:
        module_name = marker_m.group("module")
        if not module_name.startswith("living_doc_utilities."):
            module_name = f"living_doc_utilities.{module_name}"
        model = getattr(importlib.import_module(module_name), marker_m.group("model"))
        model.model_validate(payload)


_ANY_MARKER_RE = re.compile(r"^<!--\s*example\s*:", re.I)


def malformed_markers(page: str, text: str) -> list[str]:
    """Each example marker, in any spacing or case, that is not `<!-- example: module.Model -->` right above a `json`
    block: it would leave a block unvalidated."""
    lines = [line.strip() for line in text.splitlines()]
    problems: list[str] = []
    for index, line in enumerate(lines):
        if not _ANY_MARKER_RE.match(line):
            continue
        below = next((later for later in lines[index + 1 :] if later), "")
        if not _MODEL_MARKER_RE.match(line):
            problems.append(f"{page}: {line!r} is no '<!-- example: module.Model -->' marker")
        elif below != "```json":
            problems.append(f"{page}: {line!r} is not right above a 'json' block")
    return problems


@pytest.mark.parametrize("page", sorted(APPROVED_PAGES))
def test_every_example_marker_names_a_module_and_a_model(page):
    """A marker in another form matches nothing, so its `json` block would only be parsed; it fails instead."""
    assert malformed_markers(page, read_page(page)) == []


@pytest.mark.parametrize(
    "marker",
    [
        "<!-- example: contracts/envelope.py::Metadata -->",
        "<!-- example: contracts.envelope.metadata -->",
        "<!--example: contracts.envelope.Metadata-->",
        "<!-- Example: contracts.envelope.Metadata -->",
    ],
    ids=["path-and-symbol", "lowercase-model", "no-spaces", "capitalised"],
)
def test_planted_malformed_example_marker_is_reported(marker):
    """The old `path::Model` form, a lowercase model name, other spacing and other case are each reported."""
    assert malformed_markers("docs/x.md", f"{marker}\n```json\n{{}}\n```\n") == [
        f"docs/x.md: {marker!r} is no '<!-- example: module.Model -->' marker"
    ]


def test_planted_example_marker_above_a_block_that_is_not_json_is_reported():
    """Only a `json` block is validated, so a marker above any other block would check nothing."""
    marker = "<!-- example: contracts.envelope.Metadata -->"
    assert malformed_markers("docs/x.md", f"{marker}\n```python\npass\n```\n") == [
        f"docs/x.md: {marker!r} is not right above a 'json' block"
    ]


def test_a_well_formed_example_marker_above_a_json_block_passes():
    """The form the pages use, right above a `json` block, is no problem."""
    assert malformed_markers("docs/x.md", "<!-- example: contracts.envelope.Metadata -->\n```json\n{}\n```\n") == []


def test_the_pages_carry_examples():
    """The example check has something to run: there are Python examples and at least one model-checked JSON one."""
    assert len(_examples("python")) >= 5
    assert any(_MODEL_MARKER_RE.match(param.values[0].line_above) for param in _examples("json"))
