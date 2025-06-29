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


def test_set_output_default(mocker):
    mocker.patch("os.getenv", return_value="default_output.txt")
    mock_open = mocker.patch("builtins.open", new_callable=mocker.mock_open)

    set_action_output("test-output", "test_value")

    mock_open.assert_called_with("default_output.txt", "a", encoding="utf-8")
    handle = mock_open()
    handle.write.assert_any_call("test-output=test_value\n")


def test_set_output_custom_path(mocker):
    mocker.patch("os.getenv", return_value="custom_output.txt")
    mock_open = mocker.patch("builtins.open", new_callable=mocker.mock_open)

    set_action_output("custom-output", "custom_value", "default_output.txt")

    mock_open.assert_called_with("custom_output.txt", "a", encoding="utf-8")
    handle = mock_open()
    handle.write.assert_any_call("custom-output=custom_value\n")


def test_set_action_output_ioerror(mocker):
    mocker.patch("os.getenv", return_value="fail.txt")
    mock_open = mocker.patch("builtins.open", side_effect=IOError("disk full"))
    mock_logger = mocker.patch("living_doc_utilities.github.utils.logger.error")

    set_action_output("fail-output", "fail-value", "fail.txt")

    mock_open.assert_called_once_with("fail.txt", "a", encoding="utf-8")
    mock_logger.assert_called_once()
    args = mock_logger.call_args[0]
    assert args[0] == "Failed to write output to %s: %s"
    assert args[1] == "fail.txt"
    assert isinstance(args[2], IOError)
    assert "disk full" in str(args[2])
