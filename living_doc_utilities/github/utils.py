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
This module contains utility functions for GitHub Actions.
"""

import os


def get_action_input(name: str, default: str = "") -> str:
    """
    Get the input value from the environment variables.

    @param name: The name of the input parameter.
    @param default: The default value to return if the environment variable is not set.
    @return: The value of the specified input parameter, or an empty string
    """
    return os.getenv(f'INPUT_{name.replace("-", "_").upper()}', default=default)


def set_action_output(name: str, value: str) -> None:
    """
    Write an action output to a file in the format expected by GitHub Actions.

    This function writes the output in a specific format that includes the name of the
    output and its value. The output is appended to the specified file.

    @param name: The name of the output parameter.
    @param value: The value of the output parameter.
    @return: None
    @raises KeyError: GITHUB_OUTPUT is not set.
    @raises OSError: the output file cannot be written (R13: no silent swallowing).
    """
    output_file = os.environ["GITHUB_OUTPUT"]
    # Explicit newline: text mode would append CRLF on Windows.
    with open(output_file, "a", encoding="utf-8", newline="\n") as f:
        f.write(f"{name}={value}\n")
