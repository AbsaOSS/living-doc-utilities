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
Gherkin scenario parsing: a scenario's title and its `@AC:<id>[/<param>:<value>...]` tags. The
human-readable `# AC:` comment above a scenario is documentation only; only the
machine-readable `@AC:` Cucumber tag links a scenario to an acceptance criterion.
"""

import re
from dataclasses import dataclass, field

from living_doc_utilities.authoring.ac_grammar import is_valid_ac_id
from living_doc_utilities.authoring.framing import SCENARIO, Role, opening_value
from living_doc_utilities.authoring.normalize import SourceFormat, normalize_framed
from living_doc_utilities.contracts.codes import Code
from living_doc_utilities.contracts.common import DocType
from living_doc_utilities.contracts.envelope import ContractWarning
from living_doc_utilities.contracts.ui_tests import AcLink

_TAG_TOKEN_RE = re.compile(r"@\S+")
_AC_TAG_PREFIX = "@AC:"
_ASPECT_PARAM = "aspect"


@dataclass
class ParsedScenario:
    """One Gherkin scenario, without `scenario_id`/`source_ref` (collector-filled)."""

    title: str
    tags: list[str] = field(default_factory=list)
    acceptance_criteria: list[AcLink] = field(default_factory=list)


def _parse_ac_tag(tag: str) -> AcLink | None:
    """Parses `@AC:<id>[/<param>:<value>...]`; `None` when malformed. Only `aspect` is stored; the canon
    keeps the format open, and other parameters are accepted but have no field on `AcLink`."""
    ac_id, *segments = tag[len(_AC_TAG_PREFIX) :].split("/")
    if not is_valid_ac_id(ac_id):
        return None
    aspect: str | None = None
    for segment in segments:
        param, sep, value = segment.partition(":")
        if not sep or not param or not value:
            return None
        if param == _ASPECT_PARAM:
            if aspect is not None or ":" in value:
                return None
            aspect = value
    return AcLink(id=ac_id, aspect=aspect)


def _tags_to_ac_links(tags: list[str]) -> tuple[list[AcLink], list[ContractWarning]]:
    links: list[AcLink] = []
    warnings: list[ContractWarning] = []
    for tag in tags:
        if not tag.startswith(_AC_TAG_PREFIX):
            continue
        link = _parse_ac_tag(tag)
        if link is None:
            warnings.append(
                ContractWarning(code=Code.MALFORMED_AC.name, message="'@AC:' tag is malformed.", context=f"tag={tag!r}")
            )
            continue
        links.append(link)
    return links, warnings


def parse_scenarios(text: str, entity_type: DocType) -> tuple[list[ParsedScenario], list[ContractWarning]]:
    """Parses every `Scenario:`/`Scenario Outline:` in a `.feature` file's Gherkin body."""
    _, frame = normalize_framed(text, SourceFormat.SCENARIO_FILE, entity_type)
    warnings: list[ContractWarning] = []
    scenarios: list[ParsedScenario] = []
    pending_tags: list[str] = []

    for framed in frame.lines:
        if framed.role in (Role.BLANK, Role.COMMENT):
            continue
        if framed.role is Role.TAG:
            pending_tags.extend(_TAG_TOKEN_RE.findall(framed.line.text))
            continue
        if framed.role is not Role.HEADING or framed.section != SCENARIO:
            # `Feature:`, `Background:` or any other construct (Rule:, a step, Examples:, ...) drops pending tags.
            pending_tags = []
            continue

        ac_links, ac_warnings = _tags_to_ac_links(pending_tags)
        warnings.extend(ac_warnings)
        scenarios.append(
            ParsedScenario(title=opening_value(framed).strip(), tags=pending_tags, acceptance_criteria=ac_links)
        )
        pending_tags = []

    return scenarios, warnings
