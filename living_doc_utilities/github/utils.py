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
    """Gets `name`'s value from the `INPUT_<NAME>` env var, or `default` if unset."""
    return os.getenv(f'INPUT_{name.replace("-", "_").upper()}', default=default)


def set_action_output(name: str, value: str) -> None:
    """Writes one `name=value` action output line to $GITHUB_OUTPUT, appended.

    @raises KeyError: GITHUB_OUTPUT is not set.
    @raises OSError: the output file cannot be written (R13: no silent swallowing).
    """
    output_file = os.environ["GITHUB_OUTPUT"]
    # Explicit newline: text mode would append CRLF on Windows.
    with open(output_file, "a", encoding="utf-8", newline="\n") as f:
        f.write(f"{name}={value}\n")
