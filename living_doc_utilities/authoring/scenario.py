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
Gherkin scenario parsing: a scenario's title, its `@AC:<id>[/<param>:<value>]` tags, its line, its steps,
its rule and the backgrounds that run before it. The human-readable `# AC:` comment above a scenario is
documentation only; only the machine-readable `@AC:` Cucumber tag links a scenario to an acceptance criterion.
"""

import os
import re
from dataclasses import dataclass, field
from typing import Optional

from living_doc_utilities.authoring.ac_grammar import is_valid_ac_id, is_valid_variant_name
from living_doc_utilities.authoring.accounting import located
from living_doc_utilities.authoring.framing import (
    BACKGROUND,
    GHERKIN_RULE,
    SCENARIO,
    FramedLine,
    Role,
    opening_value,
    sections,
)
from living_doc_utilities.authoring.normalize import SourceFormat, normalize_framed
from living_doc_utilities.contracts.codes import Code
from living_doc_utilities.contracts.common import DocType
from living_doc_utilities.contracts.envelope import ContractWarning
from living_doc_utilities.contracts.ui_tests import AcLink

_TAG_TOKEN_RE = re.compile(r"@\S+")
_AC_TAG_PREFIX = "@AC:"


@dataclass
class ParsedScenario:
    """One Gherkin scenario, without `scenario_id`/`source_ref` (collector-filled). `line` is its `Scenario:` line;
    `steps`, `background` (its file's) and `rule_background` (its rule's) are lines as written."""

    title: str
    tags: list[str] = field(default_factory=list)
    acceptance_criteria: list[AcLink] = field(default_factory=list)
    line: Optional[int] = None
    rule: Optional[str] = None
    rule_background: list[str] = field(default_factory=list)
    background: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)


def _parse_ac_tag(tag: str) -> AcLink | None:
    """Parses `@AC:<id>[/<param>:<value>]`; `None` when malformed. The canon closes the format: at most one
    parameter, `aspect` or the criterion's keyword name, whose value fills `aspect` (the name is not stored).
    A bare tag links the whole criterion, every declared value."""
    ac_id, *segments = tag[len(_AC_TAG_PREFIX) :].split("/")
    if not is_valid_ac_id(ac_id) or len(segments) > 1:
        return None
    if not segments:
        return AcLink(id=ac_id)
    param, sep, value = segments[0].partition(":")
    if not sep or not is_valid_variant_name(param) or not value or ":" in value:
        return None
    return AcLink(id=ac_id, aspect=value)


def _tags_to_ac_links(tags: list[tuple[str, int]]) -> tuple[list[AcLink], list[ContractWarning]]:
    """Each `@AC:` tag of `(tag, input line number)` pairs as a link; a malformed one is reported on its line,
    naming the criterion when the tag's id is valid."""
    links: list[AcLink] = []
    warnings: list[ContractWarning] = []
    for tag, number in tags:
        if not tag.startswith(_AC_TAG_PREFIX):
            continue
        link = _parse_ac_tag(tag)
        if link is None:
            ac_id = tag[len(_AC_TAG_PREFIX) :].split("/")[0]
            warnings.append(
                located(
                    Code.MALFORMED_AC,
                    "'@AC:' tag is malformed.",
                    f"tag={tag!r} line_no={number}",
                    number=number,
                    ac_id=ac_id if is_valid_ac_id(ac_id) else None,
                )
            )
            continue
        links.append(link)
    return links, warnings


def _trailing_tags(lines: list[FramedLine]) -> list[tuple[str, int]]:
    """The tags of the tag lines that close a block, as `(tag, input line number)` pairs: any other line in the
    block (a step, `Examples:`, a DocString) drops the tags above it, so a tag block links only the next scenario."""
    tags: list[tuple[str, int]] = []
    for framed in lines:
        if framed.role is Role.TAG:
            tags.extend((tag, framed.number) for tag in _TAG_TOKEN_RE.findall(framed.line.text))
        elif framed.role in (Role.TEXT, Role.CODE):
            tags = []
    return tags


def _block_lines(lines: list[FramedLine]) -> list[str]:
    """A block's lines as written: blank, comment and tag lines drop unless a DocString holds them, and every line
    loses the indentation the lines with text share. A DocString line keeps its trailing whitespace; any other line
    loses it."""
    kept = [
        framed.raw if framed.role is Role.CODE else framed.raw.rstrip()
        for framed in lines
        if framed.role in (Role.TEXT, Role.CODE)
    ]
    margin = os.path.commonprefix([line[: len(line) - len(line.lstrip())] for line in kept if line.strip()])
    return [line[len(margin) :] if line.startswith(margin) else line.lstrip() for line in kept]


def parse_scenarios(text: str, entity_type: DocType) -> tuple[list[ParsedScenario], list[ContractWarning]]:
    """Parses every `Scenario:`/`Scenario Outline:` in a `.feature` file's Gherkin body."""
    _, frame = normalize_framed(text, SourceFormat.SCENARIO_FILE, entity_type)
    warnings: list[ContractWarning] = []
    scenarios: list[ParsedScenario] = []
    pending_tags: list[tuple[str, int]] = []
    background: list[str] = []
    rule: Optional[str] = None
    rule_background: list[str] = []

    for section in sections(frame):
        if section.name == SCENARIO:
            ac_links, ac_warnings = _tags_to_ac_links(pending_tags)
            warnings.extend(ac_warnings)
            scenarios.append(
                ParsedScenario(
                    title=opening_value(section.opener).strip(),
                    tags=[tag for tag, _ in pending_tags],
                    acceptance_criteria=ac_links,
                    line=section.opener.number,
                    rule=rule,
                    rule_background=list(rule_background),
                    steps=_block_lines(section.lines),
                )
            )
        elif section.name == GHERKIN_RULE:
            rule, rule_background = opening_value(section.opener).strip(), []
        elif section.name == BACKGROUND and rule is None:
            background = _block_lines(section.lines)
        elif section.name == BACKGROUND:
            rule_background = _block_lines(section.lines)
        pending_tags = _trailing_tags(section.lines)

    for scenario in scenarios:
        scenario.background = list(background)
    return scenarios, warnings
