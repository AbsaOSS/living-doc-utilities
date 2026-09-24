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

"""`validation.py::validate` (R10) selects its validator class from the schema's own dialect, never a hardcoded one."""

import jsonschema

from living_doc_utilities.contracts.validation import validate

_DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"


def test_validate_returns_empty_list_for_a_valid_payload():
    """A payload that satisfies the schema yields an empty error list, not None or a falsy sentinel."""
    schema = {"$schema": _DRAFT_2020_12, "type": "object", "required": ["name"], "properties": {"name": {"type": "string"}}}

    errors = validate({"name": "US-001"}, schema)

    assert errors == []


def test_validate_returns_every_error_for_an_invalid_payload():
    """An invalid payload yields its jsonschema ValidationError objects, not a boolean or a summary."""
    schema = {"$schema": _DRAFT_2020_12, "type": "object", "required": ["name"], "properties": {"name": {"type": "string"}}}

    errors = validate({"name": 123}, schema)

    assert len(errors) == 1
    assert isinstance(errors[0], jsonschema.exceptions.ValidationError)


def test_validate_enforces_a_2020_12_only_keyword_prefixitems():
    """validate picks its validator class from the schema's own $schema dialect, not a hardcoded draft."""
    # A hardcoded Draft-07 validator would silently ignore prefixItems (2020-12), not reject a violating instance.
    schema = {
        "$schema": _DRAFT_2020_12,
        "type": "array",
        "prefixItems": [{"type": "string"}, {"type": "integer"}],
    }

    assert validate(["US-001", 1], schema) == []

    errors = validate([1, "US-001"], schema)

    assert len(errors) == 2
    assert all("is not of type" in error.message for error in errors)
