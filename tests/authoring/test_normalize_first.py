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

"""Package-shape guarantees: the parsers import `ac_grammar`, and the retired criteria-table layout leaves no trace."""

import ast
from pathlib import Path

LIVING_DOC_UTILITIES_DIR = Path(__file__).resolve().parents[2] / "living_doc_utilities"
AUTHORING_DIR = LIVING_DOC_UTILITIES_DIR / "authoring"


def _imported_module_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_feature_header_issue_body_and_scenario_import_ac_grammar():
    """feature_header.py, issue_body.py, and scenario.py each import ac_grammar rather than reimplementing it."""
    for module_name in ("feature_header.py", "issue_body.py", "scenario.py"):
        imports = _imported_module_names(AUTHORING_DIR / module_name)
        assert any("ac_grammar" in name for name in imports), f"{module_name} does not import ac_grammar"


def test_criteria_id_table_layout_has_no_trace_left():
    """The retired `Criteria ID | State | Version | Description` table layout appears nowhere in the package."""
    offenders = []
    for path in LIVING_DOC_UTILITIES_DIR.rglob("*.py"):
        if "Criteria ID" in path.read_text(encoding="utf-8"):
            offenders.append(str(path))
    assert offenders == []
