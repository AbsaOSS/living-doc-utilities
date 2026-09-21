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

# GitHub action utils
# get_action_input


def test_get_input_with_hyphen(mocker):
    mock_getenv = mocker.patch("os.getenv", return_value="test_value")

    actual = get_action_input("test-input")

    mock_getenv.assert_called_with("INPUT_TEST_INPUT", default='')
    assert "test_value" == actual


def test_get_input_without_hyphen(mocker):
    mock_getenv = mocker.patch("os.getenv", return_value="another_test_value")

    actual = get_action_input("anotherinput")

    mock_getenv.assert_called_with("INPUT_ANOTHERINPUT", default='')
    assert "another_test_value" == actual


# set_action_output


def test_set_action_output_writes_to_the_github_output_path(mocker, monkeypatch):
    monkeypatch.setenv("GITHUB_OUTPUT", "the_output.txt")
    mock_open = mocker.patch("builtins.open", new_callable=mocker.mock_open)

    set_action_output("test-output", "test_value")

    mock_open.assert_called_with("the_output.txt", "a", encoding="utf-8", newline="\n")
    handle = mock_open()
    handle.write.assert_any_call("test-output=test_value\n")


def test_set_action_output_raises_when_github_output_is_not_set(monkeypatch):
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)

    with pytest.raises(KeyError):
        set_action_output("test-output", "test_value")


def test_set_action_output_ioerror(mocker, monkeypatch):
    # R13: no silent swallowing in shared code - an unwritable output file must fail the
    # Action step loudly, not log-and-continue as if the output had been written.
    monkeypatch.setenv("GITHUB_OUTPUT", "fail.txt")
    mock_open = mocker.patch("builtins.open", side_effect=IOError("disk full"))

    with pytest.raises(IOError, match="disk full"):
        set_action_output("fail-output", "fail-value")

    mock_open.assert_called_once_with("fail.txt", "a", encoding="utf-8", newline="\n")
