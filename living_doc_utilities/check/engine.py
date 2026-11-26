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
The check: each changed file's own findings, and every relation finding of the whole corpus, each placed on a file
and line. The caller reads the files; this module reads no file and no environment.
"""

from collections import Counter
from dataclasses import dataclass
from typing import Collection, Optional, Sequence

from living_doc_utilities.authoring.feature_header import parse_feature_header
from living_doc_utilities.authoring.issue_body import ParsedEntity
from living_doc_utilities.authoring.normalize import SourceFormat, normalize_framed
from living_doc_utilities.authoring.page_object import parse_page_object
from living_doc_utilities.authoring.relations import check_relations
from living_doc_utilities.authoring.required_keys import missing_required_keys, missing_required_tag
from living_doc_utilities.authoring.scenario import parse_scenarios
from living_doc_utilities.authoring.status import derive_statuses
from living_doc_utilities.contracts.codes import Code
from living_doc_utilities.contracts.common import DocType
from living_doc_utilities.contracts.envelope import ContractWarning

_FEATURE_WITHOUT_FUNCTIONALITY = Code.FEATURE_WITHOUT_FUNCTIONALITY.name


@dataclass(frozen=True)
class AuthoredFile:
    """One authored file of the corpus: its path as findings name it, the entity type the caller's configuration gives
    it, and its text. A Feature's file is a PageObject; a User Story's or Functionality's is a `.feature` file."""

    path: str
    entity_type: DocType
    text: str


@dataclass(frozen=True, order=True)
class Finding:
    """One finding: the file's path, its 1-based line, the code and the message."""

    path: str
    line: int
    code: str
    message: str


@dataclass
class _Parsed:
    """One parsed file: its entities, the line its header's title is on (1 without one), its warnings, and for a
    cross-reference PageObject the Feature its page belongs to."""

    path: str
    entities: list[ParsedEntity]
    title_line: int
    warnings: list[ContractWarning]
    parent_feat: Optional[str] = None


def _parse(file: AuthoredFile) -> _Parsed:
    """Reads one file with the parsers the collectors run for its entity type, then its missing required keys and,
    for a `.feature` file, its missing tag."""
    parent_feat = None
    if file.entity_type == "DocumentedFeature":
        source_format = SourceFormat.PAGE_OBJECT
        result, warnings = parse_page_object(file.text)
        entities = [] if result is None or result.entity is None else [result.entity]
        if result is not None and result.entity is None:
            parent_feat = result.parent_feat or ""
    else:
        source_format = SourceFormat.FEATURE_HEADER
        parsed, warnings = parse_feature_header(file.text, file.entity_type)
        warnings = warnings + parse_scenarios(file.text, file.entity_type)[1]
        entities = [] if parsed is None else [parsed]
    _, frame = normalize_framed(file.text, source_format, file.entity_type)
    warnings = warnings + missing_required_keys(frame, source_format, file.entity_type)
    if source_format == SourceFormat.FEATURE_HEADER:
        warnings = warnings + missing_required_tag(frame, file.entity_type)
    return _Parsed(file.path, entities, 1 if frame.title is None else frame.title.number, warnings, parent_feat)


def _unattached_page(parent_feat: str) -> ContractWarning:
    """A cross-reference page whose Feature is not in the corpus: the collector drops it with this warning."""
    return ContractWarning(
        code=Code.UNRESOLVED_RELATION.name,
        message="'parent-feat' points outside the collected entity set; the page is dropped.",
        context=f"target={parent_feat!r}",
    )


def _finding(parsed: _Parsed, warning: ContractWarning) -> Finding:
    """`warning` placed on its file: on its own line, else on the title line, then with its context, which names what
    the message leaves out, such as a relation's target."""
    if warning.line_no is not None:
        return Finding(parsed.path, warning.line_no, warning.code, warning.message)
    message = warning.message if not warning.context else f"{warning.message} ({warning.context})"
    return Finding(parsed.path, parsed.title_line, warning.code, message)


def check(files: Sequence[AuthoredFile], changed: Collection[str]) -> list[Finding]:
    """Checks a corpus, `files`, whose `changed` paths are under review; the findings come sorted by path and line.
    The changed files' own findings are reported, and every relation finding of the corpus: relations are taken to be
    sound before the change, so each one is the change's.
    @raises ValueError: when a path is given twice, or a changed path is not one of `files`."""
    counts = Counter(file.path for file in files)
    twice = sorted(path for path, count in counts.items() if count > 1)
    if twice:
        raise ValueError(f"files given twice: {', '.join(twice)}")
    unknown = sorted(set(changed) - counts.keys())
    if unknown:
        raise ValueError(f"changed paths that are not among the files: {', '.join(unknown)}")

    # The changed files first, so a relation finding on an id two files declare lands on the changed one.
    parsed = sorted((_parse(file) for file in files), key=lambda file: file.path not in changed)
    findings: list[Finding] = []
    for file in parsed:
        if file.path in changed:
            # A User Story's or Functionality's status is its own file's; a Feature's comes from the corpus, below.
            own = file.warnings + derive_statuses(file.entities)[1]
            findings.extend(
                _finding(file, warning) for warning in own if warning.code != _FEATURE_WITHOUT_FUNCTIONALITY
            )

    owners: dict[str, _Parsed] = {}
    for file in parsed:
        for entity in file.entities:
            owners.setdefault(entity.entity_id, file)
    entities = [entity for file in parsed for entity in file.entities]
    status_warnings = derive_statuses(entities)[1]
    relation_warnings = [warning for warning in status_warnings if warning.code == _FEATURE_WITHOUT_FUNCTIONALITY]
    # The parsed entities, not `derive_statuses`' result: it keeps one entity per id, so a second file's relations
    # would never be checked.
    relation_warnings.extend(check_relations(entities))
    findings.extend(_finding(owners[str(warning.entity_id)], warning) for warning in relation_warnings)

    features = {entity.entity_id for entity in entities if entity.type == "DocumentedFeature"}
    findings.extend(
        _finding(file, _unattached_page(file.parent_feat))
        for file in parsed
        if file.parent_feat is not None and file.parent_feat not in features
    )
    return sorted(findings)
