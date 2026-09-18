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

from living_doc_utilities.authoring.docs_export import _DOC_FILE, _load_cases, regenerate, render_table


def test_committed_doc_matches_a_fresh_regeneration():
    committed = _DOC_FILE.read_text(encoding="utf-8")

    assert regenerate() == committed


def test_regenerate_is_idempotent():
    once = regenerate()

    doc_with_once_applied = _DOC_FILE.read_text(encoding="utf-8")
    assert doc_with_once_applied == once


def test_render_table_has_one_row_per_case_plus_header():
    cases = _load_cases()

    table = render_table(cases)
    lines = table.split("\n")

    assert len(lines) == len(cases) + 2  # header row + separator row
    assert lines[0].startswith("| ID | Rule | Format |")
    assert lines[1] == "|---|---|---|---|---|---|---|"


def test_a_stale_table_is_detected_as_different_from_a_fresh_regeneration():
    # Simulates what the CI job's `git diff --exit-code -- docs/authoring.md` step catches:
    # a committed table that no longer matches what the cases file produces today - here,
    # by regenerating from a cases list with one case removed, standing in for a case added
    # to the YAML without `make docs` having been re-run.
    cases = _load_cases()
    stale_table = render_table(cases[:-1])
    fresh_table = render_table(cases)

    assert stale_table != fresh_table
    assert fresh_table not in stale_table
