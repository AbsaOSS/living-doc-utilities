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

from enum import Enum
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
    """Every code from docs/contracts.md section 5, with its kind and emitting component."""

    kind: CodeKind
    emitter: Emitter

    def __new__(cls, kind: CodeKind, emitter: Emitter) -> "Code":
        member = object.__new__(cls)
        # Unique per member: Enum aliases members whose values are equal, and many codes share (kind, emitter).
        member._value_ = len(cls.__members__)
        member.kind = kind
        member.emitter = emitter
        return member

    # --- R5: the shared compatibility check (contracts.compat.check_input) ---
    INVALID_CONTRACT_ID = CodeKind.ERROR, Emitter.UTILITIES
    CONTRACT_MISMATCH = CodeKind.ERROR, Emitter.UTILITIES
    SCHEMA_VALIDATION_FAILED = CodeKind.ERROR, Emitter.UTILITIES

    # --- Shared input validation (toolkit) ---
    MISSING_INPUT = CodeKind.ERROR, Emitter.TOOLKIT
    UNKNOWN_PRODUCER = CodeKind.ERROR, Emitter.TOOLKIT
    PROJECT_MISMATCH = CodeKind.ERROR, Emitter.TOOLKIT
    MULTIPLE_DOCUMENTATION_SOURCES = CodeKind.ERROR, Emitter.TOOLKIT
    MIXED_DOCUMENTATION_SOURCES = CodeKind.ERROR, Emitter.TOOLKIT
    DUPLICATE_ENTITY_ID = CodeKind.ERROR, Emitter.TOOLKIT
    DUPLICATE_AC_ID = CodeKind.ERROR, Emitter.TOOLKIT

    # --- Transform-time hard error and transform warnings (R11) ---
    FIELD_LOSS = CodeKind.ERROR, Emitter.TRANSFORM
    PLANNED_AC_HAS_TESTS = CodeKind.WARNING, Emitter.TRANSFORM
    IN_REVIEW_AC_HAS_TESTS = CodeKind.WARNING, Emitter.TRANSFORM
    STALE_AC_REF = CodeKind.WARNING, Emitter.TRANSFORM

    # --- Collectors (R13, and the authoring/parsing rules) ---
    INVALID_CONFIGURATION = CodeKind.ERROR, Emitter.COLLECTOR
    # Hard by default; a warning only under a collector's opt-in partial mode (R13) - kept
    # as ERROR here since that is the default disposition.
    SOURCE_UNAVAILABLE = CodeKind.ERROR, Emitter.COLLECTOR
    EMPTY_SOURCE = CodeKind.WARNING, Emitter.COLLECTOR
    MALFORMED_AC = CodeKind.WARNING, Emitter.COLLECTOR
    LEGACY_AC_STATE = CodeKind.WARNING, Emitter.COLLECTOR
    UNPARSED_AC_LINE = CodeKind.WARNING, Emitter.COLLECTOR
    UNKNOWN_SECTION = CodeKind.WARNING, Emitter.COLLECTOR
    MISSING_ENTITY_ID = CodeKind.WARNING, Emitter.COLLECTOR
    IGNORED_AUTHORED_KEY = CodeKind.WARNING, Emitter.COLLECTOR
    MISSING_STATUS = CodeKind.WARNING, Emitter.COLLECTOR
    STATUS_AC_MISMATCH = CodeKind.WARNING, Emitter.COLLECTOR
    ORPHAN_FEATURE = CodeKind.WARNING, Emitter.COLLECTOR
    RELATION_MISMATCH = CodeKind.WARNING, Emitter.COLLECTOR
    UNRESOLVED_RELATION = CodeKind.WARNING, Emitter.COLLECTOR
    RELATION_TYPE_MISMATCH = CodeKind.WARNING, Emitter.COLLECTOR
    NO_SOURCE_URL = CodeKind.WARNING, Emitter.COLLECTOR
    HTML_CONTENT_DROPPED = CodeKind.WARNING, Emitter.COLLECTOR
    DUPLICATE_AC_SOURCE = CodeKind.WARNING, Emitter.COLLECTOR
    EXCLUDED_STATE = CodeKind.WARNING, Emitter.COLLECTOR

    # --- Generators ---
    TEMPLATE_KEY_MISSING = CodeKind.ERROR, Emitter.GENERATOR
    URL_FETCH_REFUSED = CodeKind.WARNING, Emitter.GENERATOR


# The registry other repos' documentation checks and this package's own helpers read from -
# every code, keyed by its name, e.g. ALL_CODES["CONTRACT_MISMATCH"].kind.
ALL_CODES: dict[str, Code] = dict(Code.__members__)


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
