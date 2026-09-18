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
Regenerates docs/authoring.md's worked-examples table from normalisation_cases.yaml (that
file is normalize's own test data - see its header comment - so the table shown to a human
reader can never drift from what the test suite actually proves). Run as
`python -m living_doc_utilities.authoring.docs_export`, or `make docs`.

Only the region between the `BEGIN GENERATED` / `END GENERATED` markers is rewritten;
everything else in docs/authoring.md is hand-maintained prose. A CI job re-runs this and
diffs the result against what is committed, so a case added to the YAML without regenerating
the doc fails the build rather than silently drifting.
"""

from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CASES_FILE = _REPO_ROOT / "living_doc_utilities" / "authoring" / "normalisation_cases.yaml"
_DOC_FILE = _REPO_ROOT / "docs" / "authoring.md"

_BEGIN_MARKER = "<!-- BEGIN GENERATED: normalisation-examples -->"
_END_MARKER = "<!-- END GENERATED: normalisation-examples -->"

_TABLE_HEADER = "| ID | Rule | Format | Entity type | Before | After | Note |\n|---|---|---|---|---|---|---|"


def _load_cases() -> list[dict[str, Any]]:
    with _CASES_FILE.open(encoding="utf-8") as handle:
        cases = yaml.safe_load(handle)
    if not isinstance(cases, list):
        raise ValueError(f"{_CASES_FILE} must contain a YAML list of cases")
    return cases


def _cell(text: str) -> str:
    """Renders a (possibly multi-line) YAML field as one Markdown table cell: each physical
    line wrapped in its own code span (so a leading `#`/`-`/`*` reads as literal text, not
    as Markdown structure) and joined with `<br>`, with `|` escaped so it can't be mistaken
    for a column separator. A literal `\\r` (a CRLF-rule case's raw content) is rendered as
    the visible two-character escape `\\r`, never as a raw carriage-return byte - this
    repo's `.gitattributes` normalises every text file to LF on checkout, so a raw `\\r`
    byte here would never survive a commit and would make this table's regeneration
    non-reproducible."""
    lines = text.rstrip("\n").split("\n")
    escaped = []
    for line in lines:
        line = line.replace("\r", "\\r").replace("|", "\\|")
        escaped.append(f"`{line}`" if line and "`" not in line else line)
    return "<br>".join(escaped)


def _row(case: dict[str, Any]) -> str:
    cells = [
        case["id"],
        case["rule"],
        case["format"],
        case["entity_type"],
        _cell(case["input"]),
        _cell(case["expected"]),
        case.get("note", "").strip(),
    ]
    return "| " + " | ".join(str(cell) for cell in cells) + " |"


def render_table(cases: list[dict[str, Any]]) -> str:
    return "\n".join([_TABLE_HEADER] + [_row(case) for case in cases])


def _splice(doc_text: str, table: str) -> str:
    begin_idx = doc_text.index(_BEGIN_MARKER) + len(_BEGIN_MARKER)
    end_idx = doc_text.index(_END_MARKER)
    if begin_idx >= end_idx:
        raise ValueError(f"{_DOC_FILE}: malformed generated-table markers")
    return doc_text[:begin_idx] + "\n" + table + "\n" + doc_text[end_idx:]


def regenerate() -> str:
    """Returns the fully regenerated docs/authoring.md content, without writing it."""
    cases = _load_cases()
    table = render_table(cases)
    doc_text = _DOC_FILE.read_text(encoding="utf-8")
    return _splice(doc_text, table)


def main() -> None:
    _DOC_FILE.write_text(regenerate(), encoding="utf-8")
    print(f"Regenerated {_DOC_FILE.relative_to(_REPO_ROOT)} from {_CASES_FILE.relative_to(_REPO_ROOT)}")


if __name__ == "__main__":
    main()
