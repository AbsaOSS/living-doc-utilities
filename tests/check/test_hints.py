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

"""Every code the check fails on by default has exactly one one-line fix hint."""

from living_doc_utilities.check.hints import FIX_HINTS
from living_doc_utilities.policy import DEFAULT_FAIL_CODES


def test_every_default_fail_code_has_a_fix_hint_and_nothing_else_does():
    """`FIX_HINTS` covers the default fail list exactly."""
    assert set(FIX_HINTS) == DEFAULT_FAIL_CODES


def test_every_fix_hint_is_one_sentence_on_one_line():
    """Each hint is one non-empty line ending in a full stop, so it reads after a message on the same line."""
    for code, hint in FIX_HINTS.items():
        assert hint.strip() == hint and "\n" not in hint and hint.endswith("."), code
