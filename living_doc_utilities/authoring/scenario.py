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
Gherkin scenario parsing: a scenario's title and its `@AC:<id>[/aspect:<value>]` tags
(living-doc's docs/guides/living-doc-glossary.md, "Scenario traceability"). The
human-readable `# AC:` comment above a scenario is documentation only - it is never parsed
as a tag; only the machine-readable `@AC:` Cucumber tag links a scenario to an acceptance
criterion.
"""

import re
from dataclasses import dataclass, field

from living_doc_utilities.authoring.ac_grammar import is_valid_ac_id
from living_doc_utilities.authoring.normalize import SourceFormat, normalize
from living_doc_utilities.contracts.codes import Code
from living_doc_utilities.contracts.common import DocType
from living_doc_utilities.contracts.envelope import ContractWarning
from living_doc_utilities.contracts.ui_tests import AcLink

_TAG_TOKEN_RE = re.compile(r"@\S+")
_SCENARIO_RE = re.compile(r"^Scenario(?:\s+Outline)?:\s*(?P<title>.*)$")
_FEATURE_RE = re.compile(r"^Feature:\s*.*$")
_BACKGROUND_RE = re.compile(r"^Background:\s*.*$")
_AC_TAG_RE = re.compile(r"^@AC:(?P<id>[^/\s]*)(?:/aspect:(?P<aspect>\S+))?$")


@dataclass
class ParsedScenario:
    """One Gherkin scenario, without `scenario_id`/`source_ref` (collector-filled)."""

    title: str
    tags: list[str] = field(default_factory=list)
    acceptance_criteria: list[AcLink] = field(default_factory=list)


def _tags_to_ac_links(tags: list[str]) -> tuple[list[AcLink], list[ContractWarning]]:
    links: list[AcLink] = []
    warnings: list[ContractWarning] = []
    for tag in tags:
        if not tag.startswith("@AC:"):
            continue
        tag_m = _AC_TAG_RE.match(tag)
        ac_id = tag_m.group("id") if tag_m else ""
        if tag_m is None or not is_valid_ac_id(ac_id):
            warnings.append(
                ContractWarning(code=Code.MALFORMED_AC.name, message="'@AC:' tag is malformed.", context=f"tag={tag!r}")
            )
            continue
        links.append(AcLink(id=ac_id, aspect=tag_m.group("aspect")))
    return links, warnings


def parse_scenarios(text: str, entity_type: DocType) -> tuple[list[ParsedScenario], list[ContractWarning]]:
    """Parses every `Scenario:`/`Scenario Outline:` in a `.feature` file's Gherkin body."""
    normalized = normalize(text, SourceFormat.SCENARIO_FILE, entity_type)
    warnings: list[ContractWarning] = []
    scenarios: list[ParsedScenario] = []
    pending_tags: list[str] = []

    for line in normalized.lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if _FEATURE_RE.match(stripped) or _BACKGROUND_RE.match(stripped):
            pending_tags = []
            continue
        if stripped.startswith("@"):
            pending_tags.extend(_TAG_TOKEN_RE.findall(stripped))
            continue

        scenario_m = _SCENARIO_RE.match(stripped)
        if scenario_m is None:
            # Any other construct (`Rule:`, a step, an `Examples:` table, ...) invalidates
            # a pending tag block - it only ever links the *next* `Scenario:`/`Scenario
            # Outline:` line, never one further down past something else.
            pending_tags = []
            continue

        ac_links, ac_warnings = _tags_to_ac_links(pending_tags)
        warnings.extend(ac_warnings)
        scenarios.append(
            ParsedScenario(title=scenario_m.group("title").strip(), tags=pending_tags, acceptance_criteria=ac_links)
        )
        pending_tags = []

    return scenarios, warnings
