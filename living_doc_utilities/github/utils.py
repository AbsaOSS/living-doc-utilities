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

import logging
import os

logger = logging.getLogger(__name__)


def get_action_input(name: str, default: str = "") -> str:
    """
    Get the input value from the environment variables.

    @param name: The name of the input parameter.
    @param default: The default value to return if the environment variable is not set.
    @return: The value of the specified input parameter, or an empty string
    """
    return os.getenv(f'INPUT_{name.replace("-", "_").upper()}', default=default)


def set_action_output(name: str, value: str, default_output_path: str = "default_output.txt") -> None:
    """
    Write an action output to a file in the format expected by GitHub Actions.

    This function writes the output in a specific format that includes the name of the
    output and its value. The output is appended to the specified file.

    @param name: The name of the output parameter.
    @param value: The value of the output parameter.
    @param default_output_path: The default file path to which the output is written if the GITHUB_OUTPUT
    environment variable is not set.
    @return: None
    """
    output_file = os.getenv("GITHUB_OUTPUT", default_output_path)
    try:
        with open(output_file, "a", encoding="utf-8") as f:
            f.write(f"{name}={value}\n")
    except IOError as e:
        logger.error("Failed to write output to %s: %s", output_file, e)
