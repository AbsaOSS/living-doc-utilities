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
Regenerates docs/authoring.md's worked-examples table from normalisation_cases.yaml, so the table can never
drift from what the test suite proves. Only the region between the BEGIN/END GENERATED markers is rewritten;
a CI job re-runs this and diffs the whole file.
"""

from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CASES_FILE = _REPO_ROOT / "living_doc_utilities" / "authoring" / "normalisation_cases.yaml"
_DOC_FILE = _REPO_ROOT / "docs" / "authoring.md"

_BEGIN_MARKER = "<!-- BEGIN GENERATED: normalisation-examples -->"
_END_MARKER = "<!-- END GENERATED: normalisation-examples -->"

_TABLE_HEADER = "| ID | Rule | Format | Entity type | Before | After | Note |\n|---|---|---|---|---|---|---|"


def _load_cases() -> list[dict[str, Any]]:
    # PyYAML is a development dependency (make docs, the tests), so importing this module must not need it.
    import yaml  # pylint: disable=import-outside-toplevel

    with _CASES_FILE.open(encoding="utf-8") as handle:
        cases = yaml.safe_load(handle)
    if not isinstance(cases, list):
        raise ValueError(f"{_CASES_FILE} must contain a YAML list of cases")
    return cases


def _cell(text: str) -> str:
    """Renders a YAML field as one Markdown table cell: each line wrapped in its own code
    span and joined with `<br>`, `|` escaped. A literal `\\r` renders as the two-char escape
    `\\r`, since `.gitattributes` normalises checkouts to LF so a raw CR byte would never survive a commit."""
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
        case.get("note", "").strip().replace("|", "\\|"),
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
    # Explicit newline: text mode would write CRLF on Windows.
    _DOC_FILE.write_text(regenerate(), encoding="utf-8", newline="\n")
    doc = _DOC_FILE.relative_to(_REPO_ROOT).as_posix()
    cases = _CASES_FILE.relative_to(_REPO_ROOT).as_posix()
    print(f"Regenerated {doc} from {cases}")


if __name__ == "__main__":
    main()
