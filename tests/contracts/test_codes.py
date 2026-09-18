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
Tests for the docs/contracts.md, section 5 code registry (codes.py): every code is
present exactly once, with the right kind/emitter, and ContractError carries them faithfully.
"""

import pytest

from living_doc_utilities.contracts.codes import ALL_CODES, Code, CodeKind, ContractError, Emitter

# docs/contracts.md, section 5: a representative sample spanning every emitter/kind
# combination, so a regression in _CODE_INFO's mapping (not just a missing entry) is caught.
_KNOWN_CODES = [
    ("INVALID_CONTRACT_ID", CodeKind.ERROR, Emitter.UTILITIES),
    ("CONTRACT_MISMATCH", CodeKind.ERROR, Emitter.UTILITIES),
    ("SCHEMA_VALIDATION_FAILED", CodeKind.ERROR, Emitter.UTILITIES),
    ("FIELD_LOSS", CodeKind.ERROR, Emitter.TRANSFORM),
    ("EMPTY_SOURCE", CodeKind.WARNING, Emitter.COLLECTOR),
    ("TEMPLATE_KEY_MISSING", CodeKind.ERROR, Emitter.GENERATOR),
    ("MISSING_INPUT", CodeKind.ERROR, Emitter.TOOLKIT),
    ("STALE_AC_REF", CodeKind.WARNING, Emitter.TRANSFORM),
    ("URL_FETCH_REFUSED", CodeKind.WARNING, Emitter.GENERATOR),
]

# The three codes compat.py is the only place that ever raises (docs/contracts.md, R5).
_COMPAT_RAISED_CODES = ["INVALID_CONTRACT_ID", "CONTRACT_MISMATCH", "SCHEMA_VALIDATION_FAILED"]


def test_all_codes_has_exactly_35_entries():
    # Canary: docs/contracts.md, section 5 currently enumerates exactly 35 codes. A change
    # to this count means a code was added/removed there without a matching Code member.
    assert len(ALL_CODES) == 35


@pytest.mark.parametrize("name, kind, emitter", _KNOWN_CODES)
def test_all_codes_contains_known_codes_with_expected_kind_and_emitter(name, kind, emitter):
    assert name in ALL_CODES
    code = ALL_CODES[name]
    assert code.kind == kind
    assert code.emitter == emitter


def test_all_codes_keys_match_their_own_member_name():
    for name, code in ALL_CODES.items():
        assert code.name == name


@pytest.mark.parametrize("name", _COMPAT_RAISED_CODES)
def test_compat_raised_codes_are_registered_as_errors_emitted_by_utilities(name):
    code = ALL_CODES[name]
    assert code.kind == CodeKind.ERROR
    assert code.emitter == Emitter.UTILITIES


def test_every_code_member_is_a_distinct_object():
    # Guards against the Enum-aliasing bug class: two members sharing a value collapse into
    # one (docs/contracts.md, section 5 - "Members use auto() rather than a (kind, emitter)
    # tuple as their value" precisely to avoid this).
    assert len(set(Code)) == len(list(Code)) == 35


def test_every_code_has_a_kind_and_an_emitter():
    for code in Code:
        assert isinstance(code.kind, CodeKind)
        assert isinstance(code.emitter, Emitter)


def test_code_kind_is_a_str_enum_with_the_documented_values():
    assert CodeKind.ERROR == "error"
    assert CodeKind.WARNING == "warning"


def test_emitter_is_a_str_enum_with_the_documented_values():
    assert Emitter.UTILITIES == "utilities"
    assert Emitter.TOOLKIT == "toolkit"
    assert Emitter.TRANSFORM == "transform"
    assert Emitter.COLLECTOR == "collector"
    assert Emitter.GENERATOR == "generator"


def test_contract_error_carries_code_message_and_context():
    error = ContractError(Code.CONTRACT_MISMATCH, "expected one of ['doc-entities']", context="US-001")

    assert error.code == Code.CONTRACT_MISMATCH
    assert error.message == "expected one of ['doc-entities']"
    assert error.context == "US-001"


def test_contract_error_str_without_context_omits_the_parenthetical():
    error = ContractError(Code.INVALID_CONTRACT_ID, "schema_version is missing or not a string")

    assert error.context is None
    assert str(error) == "[INVALID_CONTRACT_ID] schema_version is missing or not a string"


def test_contract_error_str_with_context_appends_the_parenthetical():
    error = ContractError(Code.SCHEMA_VALIDATION_FAILED, "boom", context="doc-entities-v1.0.0")

    assert str(error) == "[SCHEMA_VALIDATION_FAILED] boom (doc-entities-v1.0.0)"


def test_contract_error_is_an_exception():
    with pytest.raises(ContractError):
        raise ContractError(Code.MISSING_INPUT, "no input configured")
