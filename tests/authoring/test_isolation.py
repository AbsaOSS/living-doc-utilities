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
Package-shape guarantees that are cheap to break silently:

- `ac_grammar.py` is the only module in `authoring/` that knows what a *valid*
  acceptance-criterion state or version looks like - `normalize.py` only reshapes
  tokens by position, never validates them (docs/contracts.md).
- `contracts` never imports from `authoring` (the dependency runs one way only).
- `authoring` is source-agnostic: nothing in it imports a GitHub- or Azure-DevOps-specific
  module (docs/authoring.md) - a parser only ever sees document text, never a tracker SDK.
- `nh3` (the optional `html` extra `url_policy.py`/`html_to_markdown.py` need) is imported
  only inside the functions that actually call it, never at module load time - so importing
  any `authoring` module never requires that extra to be installed.
"""

import ast
from pathlib import Path

AUTHORING_DIR = Path(__file__).resolve().parents[2] / "living_doc_utilities" / "authoring"
CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "living_doc_utilities" / "contracts"

_RE_CALL_NAMES = {"compile", "match", "fullmatch", "search", "sub", "subn", "split", "findall", "finditer"}

# A strong, narrow signal that a pattern enumerates the AC state vocabulary or
# validates the strict stored-version shape - not merely a generic dash/whitespace
# reshaping regex, which normalize.py is expected to contain plenty of.
_STATE_VOCAB_TELLS = ("in_review", "deprecated")
_STRICT_VERSION_TELL = r"\d+\.\d+\.\d+$"


def _regex_pattern_literals(source: str) -> list[str]:
    tree = ast.parse(source)
    literals: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
        if name not in _RE_CALL_NAMES or not node.args:
            continue
        first_arg = node.args[0]
        if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
            literals.append(first_arg.value)
    return literals


def test_no_module_other_than_ac_grammar_validates_ac_state_or_version():
    offenders = []
    for path in sorted(AUTHORING_DIR.glob("*.py")):
        if path.name == "ac_grammar.py":
            continue
        for pattern in _regex_pattern_literals(path.read_text(encoding="utf-8")):
            if all(tell in pattern for tell in _STATE_VOCAB_TELLS) or _STRICT_VERSION_TELL in pattern:
                offenders.append((path.name, pattern))

    assert offenders == [], (
        "only ac_grammar.py may define a regex validating the AC state vocabulary or "
        f"the strict version shape, but found: {offenders}"
    )


def test_ac_grammar_itself_owns_that_validation():
    # ac_grammar validates via contracts.common's own VERSION_PATTERN/LifecycleState,
    # not a second, hand-rolled copy - confirm those are in fact what it uses.
    from living_doc_utilities.authoring import ac_grammar

    assert ac_grammar._VERSION_RE.pattern == r"^\d+\.\d+\.\d+$"  # noqa: SLF001 - white-box check
    assert ac_grammar._VALID_STATES == {"planned", "in_review", "active", "deprecated"}


def test_contracts_imports_nothing_from_authoring():
    offenders = []
    for path in sorted(CONTRACTS_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            if any("authoring" in name for name in names):
                offenders.append((path.name, names))

    assert offenders == [], f"contracts must not import from authoring, but found: {offenders}"


def _imported_module_names(node: "ast.Import | ast.ImportFrom") -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    return [node.module or ""]


def test_authoring_imports_nothing_github_or_azure_devops_specific():
    offenders = []
    for path in sorted(AUTHORING_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            for name in _imported_module_names(node):
                lowered = name.lower()
                if "github" in lowered or "azure" in lowered:
                    offenders.append((path.name, name))

    assert offenders == [], f"authoring must stay source-agnostic, but found: {offenders}"


def _has_enclosing_function(tree: ast.AST, target: ast.AST) -> bool:
    """True when `target` is nested inside a `def`/`async def` somewhere under `tree`."""
    for candidate in ast.walk(tree):
        if not isinstance(candidate, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for descendant in ast.walk(candidate):
            if descendant is target:
                return True
    return False


def test_nh3_is_imported_only_inside_a_function_that_needs_it():
    offenders = []
    for path in sorted(AUTHORING_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            if "nh3" not in _imported_module_names(node):
                continue
            if not _has_enclosing_function(tree, node):
                offenders.append((path.name, node.lineno))

    assert offenders == [], f"'nh3' must only be imported inside a function, but found at module level: {offenders}"
