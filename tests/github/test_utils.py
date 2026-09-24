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

import pytest

from living_doc_utilities.github.utils import get_action_input, set_action_output

# get_action_input


def test_get_input_with_hyphen(monkeypatch):
    monkeypatch.setenv("INPUT_TEST_INPUT", "test_value")

    actual = get_action_input("test-input")

    assert actual == "test_value"


def test_get_input_without_hyphen(monkeypatch):
    monkeypatch.setenv("INPUT_ANOTHERINPUT", "another_test_value")

    actual = get_action_input("anotherinput")

    assert actual == "another_test_value"


# set_action_output


def test_set_action_output_writes_to_the_github_output_path(tmp_path, monkeypatch):
    output_file = tmp_path / "the_output.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))

    set_action_output("test-output", "test_value")

    assert output_file.read_text(encoding="utf-8") == "test-output=test_value\n"


def test_set_action_output_raises_when_github_output_is_not_set(monkeypatch):
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)

    with pytest.raises(KeyError):
        set_action_output("test-output", "test_value")


def test_set_action_output_ioerror(tmp_path, monkeypatch):
    # R13: no silent swallowing in shared code - an unwritable output file must fail the
    # Action step loudly, not log-and-continue as if the output had been written.
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "missing-dir" / "fail.txt"))

    with pytest.raises(OSError):
        set_action_output("fail-output", "fail-value")
