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
docs/contracts.md, R10: "All structural validation goes through one shared helper that
selects the validator class with jsonschema.validators.validator_for(schema). No call site
hardcodes a validator class." The day a schema starts using a 2020-12-only keyword, a
hardcoded Draft-07 validator would not fail - it would silently ignore the keyword and pass
files it should have rejected.
"""

from typing import Any

import jsonschema
from jsonschema.exceptions import ValidationError


def validate(payload: Any, schema: dict[str, Any]) -> list[ValidationError]:
    """
    Structurally validates `payload` against `schema`, selecting the validator class from
    the schema's own declared dialect (R1/R10) rather than a hardcoded draft.

    @param payload: the parsed JSON document to check.
    @param schema: the JSON Schema to validate against.
    @return: every validation error found, in the validator's own iteration order; an empty
        list when `payload` is valid.
    """
    validator_cls = jsonschema.validators.validator_for(schema)
    validator_cls.check_schema(schema)
    validator = validator_cls(schema)
    return list(validator.iter_errors(payload))
