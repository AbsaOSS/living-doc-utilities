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
The model of a project's living-doc policy file, one file for all of its living-doc gates, and the default list of
codes that fail the authored-input check.
"""

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, ConfigDict, field_validator

from living_doc_utilities.contracts.codes import Code

# The policy file's name, at the root of the repository it governs.
POLICY_FILE = "living-doc-policy.yaml"

# YAML's `<<` merge key, which may legitimately repeat in one mapping.
_MERGE_TAG = "tag:yaml.org,2002:merge"

# Every code the authoring parsers and checks raise, and the check's own: each one drops or misreads authored text.
DEFAULT_FAIL_CODES: frozenset[str] = frozenset(
    code.name
    for code in (
        Code.AUTHORING_ERROR,
        Code.AUTHORING_WARNING,
        Code.FEATURE_WITHOUT_FUNCTIONALITY,
        Code.HTML_CONTENT_DROPPED,
        Code.IGNORED_AUTHORED_KEY,
        Code.LEGACY_AC_STATE,
        Code.MALFORMED_AC,
        Code.MALFORMED_STATUS,
        Code.MISINDENTED_LINE,
        Code.MISSING_ENTITY_ID,
        Code.MISSING_REQUIRED_KEY,
        Code.MISSING_STATUS,
        Code.RELATION_MISMATCH,
        Code.RELATION_TYPE_MISMATCH,
        Code.STATUS_AC_MISMATCH,
        Code.UNKNOWN_SECTION,
        Code.UNPARSED_AC_LINE,
        Code.UNPARSED_BULLET_LINE,
        Code.UNRESOLVED_RELATION,
    )
)


class CheckPolicy(BaseModel):
    """The `check` section: `warn` names the default codes that only warn in this project."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    warn: tuple[str, ...] = ()

    @field_validator("warn", mode="before")
    @classmethod
    def _empty_warn_is_no_code(cls, codes: object) -> object:
        """`warn:` with no value, its items commented out, reads as YAML null: no code only warns."""
        return () if codes is None else codes

    @field_validator("warn")
    @classmethod
    def _check_warn_codes(cls, codes: tuple[str, ...]) -> tuple[str, ...]:
        unknown = sorted(set(codes) - DEFAULT_FAIL_CODES)
        if unknown:
            raise ValueError(f"not a code the check fails on: {', '.join(unknown)}")
        return codes

    @property
    def fail_codes(self) -> frozenset[str]:
        """The codes that fail the check: the default list, less the ones under `warn`."""
        return DEFAULT_FAIL_CODES - set(self.warn)


class Policy(BaseModel):
    """A project's policy file. Other gates add their own top-level sections, so an unknown one is left to them."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    # Frozen, so one default section can serve every policy.
    check: CheckPolicy = CheckPolicy()

    @field_validator("check", mode="before")
    @classmethod
    def _empty_check_is_default(cls, section: object) -> object:
        """`check:` with no value reads as YAML null: the default section."""
        return {} if section is None else section


def _duplicate_key(root: Optional[yaml.Node]) -> Optional[yaml.ScalarNode]:
    """A key written twice in one mapping of the document, of which YAML would silently keep only the last value.
    A `<<` merge key may repeat; an alias is visited once, so a recursive document ends."""
    pending, visited = [root], set()
    while pending:
        node = pending.pop()
        if node is None or id(node) in visited:
            continue
        visited.add(id(node))
        if isinstance(node, yaml.MappingNode):
            seen: set[tuple[str, str]] = set()
            for key, value in node.value:
                if isinstance(key, yaml.ScalarNode) and key.tag != _MERGE_TAG:
                    if (key.tag, key.value) in seen:
                        return key
                    seen.add((key.tag, key.value))
                pending.append(value)
        elif isinstance(node, yaml.SequenceNode):
            pending.extend(node.value)
    return None


def load_policy(path: str | os.PathLike[str]) -> Policy:
    """Reads the policy file at `path`; an empty file is the default policy.
    @raises OSError: when the file can't be read.
    @raises yaml.YAMLError: when it is not YAML, or writes a key twice in one mapping.
    @raises pydantic.ValidationError: when it doesn't match the model."""
    text = Path(path).read_text(encoding="utf-8")
    duplicate = _duplicate_key(yaml.compose(text, Loader=yaml.SafeLoader))
    if duplicate is not None:
        raise yaml.MarkedYAMLError(
            problem=f"found duplicate key {duplicate.value!r}", problem_mark=duplicate.start_mark
        )
    data = yaml.safe_load(text)
    return Policy.model_validate({} if data is None else data)
