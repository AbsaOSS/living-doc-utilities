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

"""Tests for the GitHub Action input and output helper functions."""

import pytest

from living_doc_utilities.github.utils import get_action_input, set_action_output


def test_get_input_with_hyphen(monkeypatch):
    """An input name with a hyphen is read from the INPUT_ variable with the hyphen turned into an underscore."""
    monkeypatch.setenv("INPUT_TEST_INPUT", "test_value")

    actual = get_action_input("test-input")

    assert actual == "test_value"


def test_get_input_without_hyphen(monkeypatch):
    """An input name without a hyphen is read from its INPUT_ environment variable unchanged."""
    monkeypatch.setenv("INPUT_ANOTHERINPUT", "another_test_value")

    actual = get_action_input("anotherinput")

    assert actual == "another_test_value"


def test_get_input_falls_back_to_the_default_when_the_variable_is_unset(monkeypatch):
    """An unset INPUT_ variable yields an empty string, or the caller's `default` when one is given."""
    monkeypatch.delenv("INPUT_MISSING_INPUT", raising=False)

    assert get_action_input("missing-input") == ""
    assert get_action_input("missing-input", "fallback") == "fallback"


def test_set_action_output_appends_one_name_value_line_per_output(tmp_path, monkeypatch):
    """Each output is appended to the GITHUB_OUTPUT file as its own name=value line, earlier lines kept."""
    output_file = tmp_path / "the_output.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))

    set_action_output("first-output", "one")
    set_action_output("second-output", "two")

    assert output_file.read_bytes() == b"first-output=one\nsecond-output=two\n"


def test_set_action_output_raises_when_github_output_is_not_set(monkeypatch):
    """`set_action_output` raises `KeyError` when the GITHUB_OUTPUT environment variable is unset."""
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)

    with pytest.raises(KeyError):
        set_action_output("test-output", "test_value")


def test_set_action_output_ioerror(tmp_path, monkeypatch):
    """An unwritable GITHUB_OUTPUT path raises OSError instead of silently swallowing the write failure."""
    # R13: an unwritable output file must fail the step loudly, not log-and-continue.
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "missing-dir" / "fail.txt"))

    with pytest.raises(OSError):
        set_action_output("fail-output", "fail-value")
