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
emits. `ALL_CODES` maps every code name to its kind and emitting component.
"""

from enum import Enum
from typing import Optional


class CodeKind(str, Enum):
    """Whether a code is raised as a structured hard error, or only ever recorded in warnings[]."""

    ERROR = "error"
    WARNING = "warning"


class Emitter(str, Enum):
    """Which fleet component raises or emits a code."""

    # R5: raised only by `compat.py::check_input`, `io.py::read_artifact` and `io.py::write_artifact`.
    UTILITIES = "utilities"
    # living_doc_toolkit_core.input_validation: shared cross-input checks run before any transform command.
    TOOLKIT = "toolkit"
    TRANSFORM = "transform"
    COLLECTOR = "collector"
    GENERATOR = "generator"


class Code(Enum):
    """Every code, with its kind and emitting component."""

    kind: CodeKind
    emitter: Emitter

    def __new__(cls, kind: CodeKind, emitter: Emitter) -> "Code":
        member = object.__new__(cls)
        # Unique per member, 1-indexed (Enum aliases members whose values are equal; many codes share (kind, emitter)).
        member._value_ = len(cls.__members__) + 1
        member.kind = kind
        member.emitter = emitter
        return member

    # --- R5: the shared compatibility check (`compat.py::check_input`) ---
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
    # Hard by default; a warning only under a collector's opt-in partial mode (R13).
    SOURCE_UNAVAILABLE = CodeKind.ERROR, Emitter.COLLECTOR
    EMPTY_SOURCE = CodeKind.WARNING, Emitter.COLLECTOR
    MALFORMED_AC = CodeKind.WARNING, Emitter.COLLECTOR
    LEGACY_AC_STATE = CodeKind.WARNING, Emitter.COLLECTOR
    UNPARSED_AC_LINE = CodeKind.WARNING, Emitter.COLLECTOR
    UNKNOWN_SECTION = CodeKind.WARNING, Emitter.COLLECTOR
    MISSING_ENTITY_ID = CodeKind.WARNING, Emitter.COLLECTOR
    IGNORED_AUTHORED_KEY = CodeKind.WARNING, Emitter.COLLECTOR
    MALFORMED_STATUS = CodeKind.WARNING, Emitter.COLLECTOR
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


# The registry other repos' doc checks and this package's own helpers read from, keyed by name.
ALL_CODES: dict[str, Code] = dict(Code.__members__)


class ContractError(Exception):
    """A structured hard error: raised with a Code, a human-readable message, and optional context."""

    def __init__(self, code: Code, message: str, context: Optional[str] = None) -> None:
        self.code = code
        self.message = message
        self.context = context
        text = f"[{code.name}] {message}"
        if context:
            text += f" ({context})"
        super().__init__(text)
