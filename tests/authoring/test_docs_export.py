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
`docs_export.regenerate()` is what `make docs` writes and what the CI "Authoring Docs
Regeneration Check" job diffs against the committed file (.github/workflows/test.yml). These
tests prove both halves: the committed table really is what the generator produces from
`normalisation_cases.yaml` today (so the CI job is green), and the generator actually
notices when the cases file and the committed table disagree (so the CI job would catch a
stale table, not just a missing one).
"""

import pytest

from living_doc_utilities.authoring import docs_export
from living_doc_utilities.authoring.docs_export import (
    _CASES_FILE,
    _DOC_FILE,
    _load_cases,
    _row,
    regenerate,
    render_table,
)


def test_committed_doc_matches_a_fresh_regeneration():
    """The committed docs/authoring.md is exactly what `regenerate()` produces from the cases file today."""
    committed = _DOC_FILE.read_text(encoding="utf-8")

    assert regenerate() == committed


def test_regenerate_is_idempotent():
    """Calling `regenerate()` does not itself change what the next `regenerate()` call produces."""
    once = regenerate()

    doc_with_once_applied = _DOC_FILE.read_text(encoding="utf-8")
    assert doc_with_once_applied == once


def test_render_table_has_one_row_per_case_plus_header():
    """The rendered table has exactly one row per case, plus a header row and a separator row."""
    cases = _load_cases()

    table = render_table(cases)
    lines = table.split("\n")

    assert len(lines) == len(cases) + 2  # header row + separator row
    assert lines[0].startswith("| ID | Rule | Format |")
    assert lines[1] == "|---|---|---|---|---|---|---|"


def test_a_stale_table_is_detected_as_different_from_a_fresh_regeneration():
    """A table regenerated from a shorter case list differs from one regenerated from the full case list."""
    # Simulates what the CI job's `git diff --exit-code -- docs/authoring.md` step catches:
    # a committed table that no longer matches what the cases file produces today - here,
    # by regenerating from a cases list with one case removed, standing in for a case added
    # to the YAML without `make docs` having been re-run.
    cases = _load_cases()
    stale_table = render_table(cases[:-1])
    fresh_table = render_table(cases)

    assert stale_table != fresh_table
    assert fresh_table not in stale_table


def test_a_pipe_in_the_note_field_is_escaped_so_it_cannot_split_the_row():
    """A literal `|` inside a case's `note` field is escaped so it cannot be mistaken for a table delimiter."""
    case = {
        "id": "case-x",
        "rule": "rule-x",
        "format": "format-x",
        "entity_type": "entity-x",
        "input": "in",
        "expected": "out",
        "note": "| aspect: this looks like a table cell |",
    }

    row = _row(case)

    assert "\\|" in row
    assert row.replace("\\|", "").count("|") == 8  # 7 cells => 8 delimiters, none from the note


@pytest.fixture
def crlf_checkout(tmp_path, mocker):
    """Wire `docs_export` to a CRLF, nested-path copy of the doc and cases file, as autocrlf checkouts leave them."""
    # The doc and the cases file as a Windows autocrlf checkout can leave them (CRLF), in nested folders so a
    # path separator shows up in what `main()` prints, wired into `main()` in place of the real files.
    (tmp_path / "docs").mkdir()
    (tmp_path / "pkg").mkdir()
    doc, cases = tmp_path / "docs" / "authoring.md", tmp_path / "pkg" / "cases.yaml"
    for target, source in ((doc, _DOC_FILE), (cases, _CASES_FILE)):
        target.write_bytes(source.read_text(encoding="utf-8").encode("utf-8").replace(b"\n", b"\r\n"))
    mocker.patch.object(docs_export, "_REPO_ROOT", tmp_path)
    mocker.patch.object(docs_export, "_DOC_FILE", doc)
    mocker.patch.object(docs_export, "_CASES_FILE", cases)
    return doc


def test_main_writes_lf_line_endings_on_every_os_and_from_any_checkout(crlf_checkout):
    """`main()` writes the regenerated doc with LF line endings only, regardless of OS or the checkout's own."""
    # Text mode would turn each newline into CRLF on Windows.
    docs_export.main()

    written = crlf_checkout.read_bytes()
    assert b"\r" not in written
    assert written == _DOC_FILE.read_text(encoding="utf-8").encode("utf-8")


def test_main_prints_forward_slash_paths_on_every_os(crlf_checkout, capsys):
    """`main()` prints the doc and cases paths with forward slashes, regardless of OS."""
    docs_export.main()

    assert capsys.readouterr().out == "Regenerated docs/authoring.md from pkg/cases.yaml\n"
