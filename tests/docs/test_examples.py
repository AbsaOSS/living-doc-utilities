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

_MODEL_MARKER_RE = re.compile(r"^<!-- example: (?P<path>[\w./]+)\.py::(?P<model>\w+) -->$")


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
        module_path = marker_m.group("path")
        module_name = module_path.replace("/", ".")
        if not module_name.startswith("living_doc_utilities."):
            module_name = f"living_doc_utilities.{module_name}"
        model = getattr(importlib.import_module(module_name), marker_m.group("model"))
        model.model_validate(payload)


def test_the_pages_carry_examples():
    """The example check has something to run: there are Python examples and at least one model-checked JSON one."""
    assert len(_examples("python")) >= 5
    assert any(_MODEL_MARKER_RE.match(param.values[0].line_above) for param in _examples("json"))
