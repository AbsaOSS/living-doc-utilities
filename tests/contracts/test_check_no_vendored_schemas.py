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

"""`check_no_vendored_schemas` (R12 check 1) flags vendored schema filenames among a repository's tracked files."""

import subprocess
from pathlib import Path

import pytest

from living_doc_utilities.contracts import check_no_vendored_schemas as vendor_check

REPO_ROOT = Path(__file__).resolve().parents[2]
_requires_repo_git = pytest.mark.skipif(
    not (REPO_ROOT / ".git").exists(), reason="requires this package's own git checkout, absent from a git-less export"
)


# Git prefers these over `cwd` / `-C`, so one inherited from a git hook running `make qa` would hit the outer repo.
_GIT_LOCATION_VARS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_COMMON_DIR",
    "GIT_NAMESPACE",
    "GIT_CEILING_DIRECTORIES",
)


@pytest.fixture(autouse=True)
def _hermetic_git_env(monkeypatch):
    """Removes inherited git location variables so every git call here acts only on its own repository."""
    for name in _GIT_LOCATION_VARS:
        monkeypatch.delenv(name, raising=False)


def _git_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=tmp_path, check=True)
    return tmp_path


def _track(repo: Path, *relative_paths: str) -> None:
    for relative in relative_paths:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)


# ---------------------------------------------------------------------------
# find_vendored_schemas / main: planted files, retired names, tests/, --allow, clean tree.
# ---------------------------------------------------------------------------


def test_fails_on_a_planted_doc_entities_schema(tmp_path):
    """A committed file named like a doc-entities schema is reported as a vendored-schema offender."""
    repo = _git_repo(tmp_path)
    _track(repo, "pkg/doc-entities-v1.0.0-schema.json")

    offenders = vendor_check.find_vendored_schemas(repo)

    assert offenders == ["pkg/doc-entities-v1.0.0-schema.json"]


def test_fails_on_a_planted_retired_doc_issues_schema(tmp_path):
    """The filename check still flags a retired contract name, not only the six contracts live today."""
    repo = _git_repo(tmp_path)
    _track(repo, "pkg/doc-issues-v1.0.0-schema.json")

    offenders = vendor_check.find_vendored_schemas(repo)

    assert offenders == ["pkg/doc-issues-v1.0.0-schema.json"]


def test_fails_on_a_planted_audit_envelope_schema(tmp_path):
    """A committed file named like an audit-envelope schema is reported as a vendored-schema offender."""
    repo = _git_repo(tmp_path)
    _track(repo, "pkg/audit_envelope_v1.schema.json")

    offenders = vendor_check.find_vendored_schemas(repo)

    assert offenders == ["pkg/audit_envelope_v1.schema.json"]


def test_ignores_anything_under_a_tests_directory(tmp_path):
    """A schema-shaped filename committed under any tests directory is never reported as an offender."""
    repo = _git_repo(tmp_path)
    _track(repo, "tests/fixtures/doc-entities-v1.0.0-schema.json", "src/tests/nested-schema.json")

    offenders = vendor_check.find_vendored_schemas(repo)

    assert offenders == []


def test_passes_on_a_clean_tree(tmp_path):
    """A tree with no schema-shaped filenames reports no offenders."""
    repo = _git_repo(tmp_path)
    _track(repo, "pkg/__init__.py", "README.md")

    offenders = vendor_check.find_vendored_schemas(repo)

    assert offenders == []


def test_untracked_schema_file_is_not_flagged(tmp_path):
    """An untracked schema-shaped file is not reported, since only git-tracked files are checked."""
    repo = _git_repo(tmp_path)
    (repo / "scratch-schema.json").write_text("{}", encoding="utf-8")

    offenders = vendor_check.find_vendored_schemas(repo)

    assert offenders == []


def test_allow_excludes_a_named_directory(tmp_path):
    """Files under a directory passed to allow are excluded, while other vendored files are still reported."""
    repo = _git_repo(tmp_path)
    _track(repo, "generated/doc-entities-v1.0.0-schema.json", "pkg/vendored-schema.json")

    offenders = vendor_check.find_vendored_schemas(repo, allow=[Path("generated")])

    assert offenders == ["pkg/vendored-schema.json"]


def test_main_returns_nonzero_and_reports_offenders(tmp_path, capsys):
    """main() exits with a nonzero code and writes the offending filename to stderr."""
    repo = _git_repo(tmp_path)
    _track(repo, "pkg/doc-entities-v1.0.0-schema.json")

    exit_code = vendor_check.main(["--root", str(repo)])

    assert exit_code == 1
    assert "doc-entities-v1.0.0-schema.json" in capsys.readouterr().err


def test_main_returns_zero_on_a_clean_tree(tmp_path):
    """main() exits 0 when the tracked tree has no vendored schema files."""
    repo = _git_repo(tmp_path)
    _track(repo, "pkg/__init__.py")

    assert vendor_check.main(["--root", str(repo)]) == 0


# ---------------------------------------------------------------------------
# This package's own tree: passes only with its own schemas directory allowed.
# ---------------------------------------------------------------------------


@_requires_repo_git
def test_this_packages_own_tree_fails_without_allow():
    """Without --allow, this package's own committed contract schema files are reported as offenders."""
    offenders = vendor_check.find_vendored_schemas(REPO_ROOT)

    assert offenders, "expected the six committed contract schemas to be reported without --allow"
    assert all("living_doc_utilities/contracts/schemas" in offender for offender in offenders)


@_requires_repo_git
def test_this_packages_own_tree_passes_with_its_schemas_dir_allowed():
    """With its own schemas directory allowed, this package's tree reports no vendored-schema offenders."""
    offenders = vendor_check.find_vendored_schemas(REPO_ROOT, allow=[Path("living_doc_utilities/contracts/schemas")])

    assert offenders == []


def test_make_qa_runs_this_check_with_its_own_schemas_dir_allowed():
    """The Makefile's qa target runs this check with the package's own schemas directory allowed."""
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

    assert "living_doc_utilities.contracts.check_no_vendored_schemas" in makefile
    assert "--allow living_doc_utilities/contracts/schemas" in makefile
    assert "no-vendored-schemas" in makefile.split("qa:", 1)[1].split("\n", 1)[0]
