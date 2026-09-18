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
The single registry of every error/warning code the Living Documentation fleet raises or
emits (docs/contracts.md, section 5 - "This section is the single source of truth for
every code below; nothing elsewhere redefines one"). `ALL_CODES` is read both by this
package's own helpers (compat.py raises INVALID_CONTRACT_ID, CONTRACT_MISMATCH,
SCHEMA_VALIDATION_FAILED) and by other repos' documentation checks, so every code any
component in the fleet can produce has exactly one entry here, with its kind and its
emitting component.
"""

from enum import Enum, auto
from typing import Optional


class CodeKind(str, Enum):
    """Whether a code is raised as a structured hard error, or only ever recorded in an
    artifact's warnings[] array (docs/contracts.md, section 5)."""

    ERROR = "error"
    WARNING = "warning"


class Emitter(str, Enum):
    """Which fleet component raises or emits a code."""

    # This package's own compat.check_input / io.read_artifact / io.write_artifact (R5) -
    # the only place these three codes are ever raised, regardless of which component
    # (collector, transform or generator) called through to them.
    UTILITIES = "utilities"
    # living_doc_toolkit_core.input_validation - the shared, cross-input checks a transform
    # command runs before any transform (docs/contracts.md, "Shared input validation").
    TOOLKIT = "toolkit"
    TRANSFORM = "transform"
    COLLECTOR = "collector"
    GENERATOR = "generator"


class Code(Enum):
    """Every code from docs/contracts.md section 5.

    Members use auto() rather than a (kind, emitter) tuple as their value: many codes share
    the same kind and emitter (e.g. most collector warnings), and Enum treats two members
    with an equal value as aliases of one another rather than distinct members - a (kind,
    emitter) value would have silently collapsed this registry to one member per unique
    combination. kind/emitter are looked up from _CODE_INFO instead, keyed by the member
    itself, which stays unique by construction.
    """

    # --- R5: the shared compatibility check (contracts.compat.check_input) ---
    INVALID_CONTRACT_ID = auto()
    CONTRACT_MISMATCH = auto()
    SCHEMA_VALIDATION_FAILED = auto()

    # --- Shared input validation (toolkit) ---
    MISSING_INPUT = auto()
    UNKNOWN_PRODUCER = auto()
    PROJECT_MISMATCH = auto()
    MULTIPLE_DOCUMENTATION_SOURCES = auto()
    MIXED_DOCUMENTATION_SOURCES = auto()
    DUPLICATE_ENTITY_ID = auto()
    DUPLICATE_AC_ID = auto()

    # --- Transform-time hard error and transform warnings (R11) ---
    FIELD_LOSS = auto()
    PLANNED_AC_HAS_TESTS = auto()
    IN_REVIEW_AC_HAS_TESTS = auto()
    STALE_AC_REF = auto()

    # --- Collectors (R13, and the authoring/parsing rules) ---
    INVALID_CONFIGURATION = auto()
    # Hard by default; a warning only under a collector's opt-in partial mode (R13) - kept
    # as ERROR here since that is the default disposition.
    SOURCE_UNAVAILABLE = auto()
    EMPTY_SOURCE = auto()
    MALFORMED_AC = auto()
    LEGACY_AC_STATE = auto()
    UNPARSED_AC_LINE = auto()
    UNKNOWN_SECTION = auto()
    MISSING_ENTITY_ID = auto()
    IGNORED_AUTHORED_KEY = auto()
    MISSING_STATUS = auto()
    STATUS_AC_MISMATCH = auto()
    ORPHAN_FEATURE = auto()
    RELATION_MISMATCH = auto()
    UNRESOLVED_RELATION = auto()
    RELATION_TYPE_MISMATCH = auto()
    NO_SOURCE_URL = auto()
    HTML_CONTENT_DROPPED = auto()
    DUPLICATE_AC_SOURCE = auto()
    EXCLUDED_STATE = auto()

    # --- Generators ---
    TEMPLATE_KEY_MISSING = auto()
    URL_FETCH_REFUSED = auto()

    @property
    def kind(self) -> CodeKind:
        return _CODE_INFO[self][0]

    @property
    def emitter(self) -> Emitter:
        return _CODE_INFO[self][1]


_CODE_INFO: dict[Code, tuple[CodeKind, Emitter]] = {
    Code.INVALID_CONTRACT_ID: (CodeKind.ERROR, Emitter.UTILITIES),
    Code.CONTRACT_MISMATCH: (CodeKind.ERROR, Emitter.UTILITIES),
    Code.SCHEMA_VALIDATION_FAILED: (CodeKind.ERROR, Emitter.UTILITIES),
    Code.MISSING_INPUT: (CodeKind.ERROR, Emitter.TOOLKIT),
    Code.UNKNOWN_PRODUCER: (CodeKind.ERROR, Emitter.TOOLKIT),
    Code.PROJECT_MISMATCH: (CodeKind.ERROR, Emitter.TOOLKIT),
    Code.MULTIPLE_DOCUMENTATION_SOURCES: (CodeKind.ERROR, Emitter.TOOLKIT),
    Code.MIXED_DOCUMENTATION_SOURCES: (CodeKind.ERROR, Emitter.TOOLKIT),
    Code.DUPLICATE_ENTITY_ID: (CodeKind.ERROR, Emitter.TOOLKIT),
    Code.DUPLICATE_AC_ID: (CodeKind.ERROR, Emitter.TOOLKIT),
    Code.FIELD_LOSS: (CodeKind.ERROR, Emitter.TRANSFORM),
    Code.PLANNED_AC_HAS_TESTS: (CodeKind.WARNING, Emitter.TRANSFORM),
    Code.IN_REVIEW_AC_HAS_TESTS: (CodeKind.WARNING, Emitter.TRANSFORM),
    Code.STALE_AC_REF: (CodeKind.WARNING, Emitter.TRANSFORM),
    Code.INVALID_CONFIGURATION: (CodeKind.ERROR, Emitter.COLLECTOR),
    Code.SOURCE_UNAVAILABLE: (CodeKind.ERROR, Emitter.COLLECTOR),
    Code.EMPTY_SOURCE: (CodeKind.WARNING, Emitter.COLLECTOR),
    Code.MALFORMED_AC: (CodeKind.WARNING, Emitter.COLLECTOR),
    Code.LEGACY_AC_STATE: (CodeKind.WARNING, Emitter.COLLECTOR),
    Code.UNPARSED_AC_LINE: (CodeKind.WARNING, Emitter.COLLECTOR),
    Code.UNKNOWN_SECTION: (CodeKind.WARNING, Emitter.COLLECTOR),
    Code.MISSING_ENTITY_ID: (CodeKind.WARNING, Emitter.COLLECTOR),
    Code.IGNORED_AUTHORED_KEY: (CodeKind.WARNING, Emitter.COLLECTOR),
    Code.MISSING_STATUS: (CodeKind.WARNING, Emitter.COLLECTOR),
    Code.STATUS_AC_MISMATCH: (CodeKind.WARNING, Emitter.COLLECTOR),
    Code.ORPHAN_FEATURE: (CodeKind.WARNING, Emitter.COLLECTOR),
    Code.RELATION_MISMATCH: (CodeKind.WARNING, Emitter.COLLECTOR),
    Code.UNRESOLVED_RELATION: (CodeKind.WARNING, Emitter.COLLECTOR),
    Code.RELATION_TYPE_MISMATCH: (CodeKind.WARNING, Emitter.COLLECTOR),
    Code.NO_SOURCE_URL: (CodeKind.WARNING, Emitter.COLLECTOR),
    Code.HTML_CONTENT_DROPPED: (CodeKind.WARNING, Emitter.COLLECTOR),
    Code.DUPLICATE_AC_SOURCE: (CodeKind.WARNING, Emitter.COLLECTOR),
    Code.EXCLUDED_STATE: (CodeKind.WARNING, Emitter.COLLECTOR),
    Code.TEMPLATE_KEY_MISSING: (CodeKind.ERROR, Emitter.GENERATOR),
    Code.URL_FETCH_REFUSED: (CodeKind.WARNING, Emitter.GENERATOR),
}

if _CODE_INFO.keys() != set(Code):
    raise ValueError("every Code member must have exactly one _CODE_INFO entry")

# The registry other repos' documentation checks and this package's own helpers read from -
# every code, keyed by its name, e.g. ALL_CODES["CONTRACT_MISMATCH"].kind.
ALL_CODES: dict[str, Code] = {code.name: code for code in Code}


class ContractError(Exception):
    """A structured hard error (docs/contracts.md, section 5): "Hard errors are raised as
    structured errors with a code, a message and context." Every ContractError this package
    raises carries its Code, a human-readable message, and optional context.
    """

    def __init__(self, code: Code, message: str, context: Optional[str] = None) -> None:
        self.code = code
        self.message = message
        self.context = context
        text = f"[{code.name}] {message}"
        if context:
            text += f" ({context})"
        super().__init__(text)
