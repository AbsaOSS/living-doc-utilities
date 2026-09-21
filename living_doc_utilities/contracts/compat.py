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
docs/contracts.md, R5: the three-step compatibility check every consumer runs before
trusting an input file - deciding purely from the file itself (its schema_version and its
structure), never from who produced it. metadata.producer.version is audit information
only and is never read here.
"""

import re
from importlib.metadata import version as _installed_version
from typing import Any, Optional, Union

from jsonschema.exceptions import ValidationError, best_match

from living_doc_utilities.contracts import schema_export
from living_doc_utilities.contracts.codes import Code, ContractError
from living_doc_utilities.contracts.envelope import CONTRACT_ID_PATTERN
from living_doc_utilities.contracts.validation import validate

_CONTRACT_ID_RE = re.compile(CONTRACT_ID_PATTERN)

_PACKAGE_NAME = "living-doc-utilities"


def installed_utilities_version() -> str:
    """This installed package's own version (R5 step 3, R6 metadata.producer.utilities_version)."""
    return _installed_version(_PACKAGE_NAME)


def _safe_get(payload: Any, *keys: str) -> Optional[Any]:
    value: Any = payload
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def schema_validation_error(errors: list[ValidationError], payload: Any) -> ContractError:
    """
    Builds the R5 step-3 SCHEMA_VALIDATION_FAILED error: names the failing path, the file's
    own metadata.producer.utilities_version and this installed package's own version and,
    only when the two differ, appends the pin-alignment hint. Shared by check_input's own
    read-time check and io.write_artifact's pre-write validation, so both paths report a
    version skew identically.

    @param errors: the jsonschema validation errors found (must be non-empty).
    @param payload: the payload that failed validation, read for its producer version.
    @return: the ContractError to raise.
    """
    worst = best_match(errors)
    path = worst.json_path if worst is not None else "$"
    detail = worst.message if worst is not None else "schema validation failed"

    producer_version = _safe_get(payload, "metadata", "producer", "utilities_version")
    own_version = installed_utilities_version()
    message = (
        f"{path}: {detail} (file written by utilities {producer_version!r}, " f"this is utilities {own_version!r})"
    )
    if producer_version is not None and producer_version != own_version:
        message += "; the components run different utilities versions — align the pins"
    return ContractError(Code.SCHEMA_VALIDATION_FAILED, message)


def check_input(payload: Any, expected: Union[str, set[str]]) -> str:
    """
    Runs R5's three checks, in order, deciding purely from `payload` itself:

    1. schema_version is present and parses against "<contract-name>-v<major>.<minor>.<patch>".
    2. the parsed contract name is in the caller's expected set.
    3. structural validation against that contract's bundled schema.

    @param payload: the parsed JSON of a candidate contract artifact.
    @param expected: a single contract name (e.g. "doc-entities") or a set of acceptable
        ones (e.g. {"doc-entities", "doc-source"}).
    @return: the payload's own contract id (e.g. "doc-entities-v1.0.0") on success.
    @raises ContractError: INVALID_CONTRACT_ID, CONTRACT_MISMATCH or SCHEMA_VALIDATION_FAILED.
    """
    expected_names = {expected} if isinstance(expected, str) else set(expected)

    schema_version = payload.get("schema_version") if isinstance(payload, dict) else None
    if not isinstance(schema_version, str):
        raise ContractError(Code.INVALID_CONTRACT_ID, "schema_version is missing or not a string")

    match = _CONTRACT_ID_RE.match(schema_version)
    if match is None:
        raise ContractError(
            Code.INVALID_CONTRACT_ID,
            f"schema_version {schema_version!r} does not match '<contract-name>-v<major>.<minor>.<patch>'",
        )
    contract_name = match.group(1)

    if contract_name not in expected_names:
        raise ContractError(
            Code.CONTRACT_MISMATCH,
            f"expected one of {sorted(expected_names)!r}, got {contract_name!r}",
        )

    schema = schema_export.load_schema(schema_version)
    errors = validate(payload, schema)
    if errors:
        raise schema_validation_error(errors, payload)

    return schema_version
