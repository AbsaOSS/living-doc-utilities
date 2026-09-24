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
Runs every row of `normalisation_cases.yaml` - normalize's only test data - and checks
that every rule and every SourceFormat is covered at least once.
"""

from pathlib import Path

import pytest
import yaml

from living_doc_utilities.authoring.normalize import (
    RULE_AC_HEADER_SEPARATOR,
    RULE_BULLET_MARKER,
    RULE_ENTITY_NAME_DASH,
    RULE_INLINE_AC_DESCRIPTION,
    RULE_STATE_CASING,
    RULE_TITLE_ID_SEPARATOR,
    RULE_VERSION_FORM,
    RULE_WHITESPACE,
    SourceFormat,
    normalize,
)

CASES_PATH = (
    Path(__file__).resolve().parents[2] / "living_doc_utilities" / "authoring" / "normalisation_cases.yaml"
)

ALL_RULES = frozenset(
    {
        RULE_BULLET_MARKER,
        RULE_AC_HEADER_SEPARATOR,
        RULE_STATE_CASING,
        RULE_VERSION_FORM,
        RULE_ENTITY_NAME_DASH,
        RULE_TITLE_ID_SEPARATOR,
        RULE_WHITESPACE,
        RULE_INLINE_AC_DESCRIPTION,
    }
)
ALL_FORMATS = frozenset(fmt.value for fmt in SourceFormat)


def _load_cases() -> list[dict]:
    with open(CASES_PATH, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


CASES = _load_cases()


def test_cases_file_is_not_empty():
    """`normalisation_cases.yaml` loads at least one case."""
    assert len(CASES) > 0


def test_cases_file_covers_every_rule():
    """Every normalization rule is exercised by at least one case in `normalisation_cases.yaml`."""
    covered = {case["rule"] for case in CASES if case["rule"] != "none"}
    assert covered == ALL_RULES


def test_cases_file_covers_every_source_format():
    """Every `SourceFormat` is exercised by at least one case in `normalisation_cases.yaml`."""
    covered = {case["format"] for case in CASES}
    assert covered == ALL_FORMATS


def test_case_ids_are_unique():
    """Every case in `normalisation_cases.yaml` has a unique `id`."""
    ids = [case["id"] for case in CASES]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_normalisation_case(case):
    """Each `normalisation_cases.yaml` row's input normalizes to its expected output, firing its declared rule."""
    fmt = SourceFormat(case["format"])
    result = normalize(case["input"], fmt, case["entity_type"])

    assert result.text == case["expected"], case.get("note", "")

    if case["rule"] == "none":
        assert result.changes == [], "a 'none' case must produce no changes at all"
    else:
        fired_rules = {change.rule for change in result.changes}
        assert case["rule"] in fired_rules, f"expected rule {case['rule']!r} to fire, got {fired_rules!r}"
