#
# Copyright 2024 ABSA Group Limited
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

"""Tests for BaseActionInputs, the shared GitHub Action input validation and reporting base class."""

import pytest

from living_doc_utilities.inputs.action_inputs import BaseActionInputs


class TestActionInputs(BaseActionInputs):
    """Minimal concrete BaseActionInputs subclass used to exercise the base class's shared behaviour."""

    def _validate(self) -> int:
        return 0

    def _print_effective_configuration(self) -> None:
        pass


@pytest.fixture
def action_inputs():
    return TestActionInputs()


def test_get_github_token(mocker, action_inputs):
    """The GitHub token getter reads the GITHUB_TOKEN action input."""
    mock_get_action_input = mocker.patch(
        "living_doc_utilities.inputs.action_inputs.get_action_input",
        return_value="mock_token",
    )
    token = action_inputs.get_github_token()
    assert token == "mock_token"
    mock_get_action_input.assert_called_once_with("GITHUB_TOKEN")


def test_validate_user_configuration_success(action_inputs):
    """`validate_user_configuration` returns True when the subclass's `_validate` hook reports no errors."""
    assert action_inputs.validate_user_configuration() is True


def test_validate_user_configuration_failure(mocker, action_inputs):
    """`validate_user_configuration` returns False when the subclass's `_validate` hook reports an error count."""
    mock_validate = mocker.patch.object(TestActionInputs, "_validate", return_value=1)
    assert action_inputs.validate_user_configuration() is False
    mock_validate.assert_called_once()


def test_print_effective_configuration(mocker, action_inputs):
    """Printing the effective configuration reports the GitHub token status and delegates to the subclass hook."""
    mock_get_action_input = mocker.patch(
        "living_doc_utilities.inputs.action_inputs.get_action_input",
        return_value="mock_token",
    )
    mock_print_config = mocker.patch.object(TestActionInputs, "_print_effective_configuration")
    action_inputs.print_effective_configuration()
    mock_get_action_input.assert_called_once_with("GITHUB_TOKEN")
    mock_print_config.assert_called_once()
