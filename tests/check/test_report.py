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

"""The check's report: one line per finding, the GitHub Actions annotations, the job summary and the verdict."""

import re

from living_doc_utilities.check import report
from living_doc_utilities.check.engine import Finding
from living_doc_utilities.check.hints import FIX_HINTS, MISSING_TAG_HINT
from living_doc_utilities.policy import DEFAULT_FAIL_CODES

_MALFORMED = Finding(
    "func-008.feature",
    16,
    "MALFORMED_AC",
    "Acceptance criterion failed validation: state: Input should be 'planned', 'in_review', 'active' or 'deprecated'",
)
_DROPPED = Finding("func-008.feature", 17, "AUTHORING_WARNING", "Line of a dropped acceptance criterion is not read.")


def _missing_ids(count):
    return [Finding(f"f{index:02}.feature", 1, "MISSING_ENTITY_ID", "No header.") for index in range(count)]


def _commands(text):
    """The lines GitHub Actions reads as workflow commands: those after the `stop-commands` block."""
    lines = text.splitlines()
    token = re.fullmatch(r"::stop-commands::(?P<token>\w+)", lines[0]).group("token")
    return lines[lines.index(f"::{token}::") + 1 :]


def test_a_line_is_path_line_code_message_and_fix_hint():
    """A finding prints as `<path>:<line>: <CODE> <message> Fix: <hint>`, its message closed as a sentence."""
    assert report.format_line(_MALFORMED) == (
        "func-008.feature:16: MALFORMED_AC Acceptance criterion failed validation: state: Input should be 'planned', "
        f"'in_review', 'active' or 'deprecated'. Fix: {FIX_HINTS['MALFORMED_AC']}"
    )


def test_a_line_never_spans_two_lines():
    """A carriage return or line feed in a path or message is escaped, so each finding stays one line."""
    finding = Finding("a\nb.feature", 3, "MISSING_ENTITY_ID", "x\r\n::warning::y")

    assert report.format_line(finding) == (
        "a\\nb.feature:3: MISSING_ENTITY_ID x\\r\\n::warning::y. Fix: " + FIX_HINTS["MISSING_ENTITY_ID"]
    )


def test_findings_fail_when_a_code_is_in_the_fail_list():
    """The verdict fails on a code in the fail list, and passes once the policy relaxes every code found."""
    assert report.fails([_MALFORMED, _DROPPED], DEFAULT_FAIL_CODES)
    assert not report.fails([_MALFORMED, _DROPPED], DEFAULT_FAIL_CODES - {"MALFORMED_AC", "AUTHORING_WARNING"})
    assert not report.fails([], DEFAULT_FAIL_CODES)


def test_the_github_report_shields_the_lines_from_workflow_commands():
    """The lines sit between `::stop-commands::<token>` and `::<token>::`, so authored text runs no command."""
    lines = report.github_report([_MALFORMED, _DROPPED], DEFAULT_FAIL_CODES).splitlines()

    token = re.fullmatch(r"::stop-commands::(?P<token>[0-9a-f]{32})", lines[0]).group("token")
    assert lines[1:4] == [report.format_line(_MALFORMED), report.format_line(_DROPPED), f"::{token}::"]


def test_each_github_report_uses_a_new_token():
    """The token that resumes workflow commands is random, so authored text can't guess and end the block."""
    first, second = (report.github_report([_DROPPED], DEFAULT_FAIL_CODES).splitlines()[0] for _ in range(2))

    assert first != second


def test_the_first_annotation_is_a_summary_then_one_per_finding():
    """The summary annotation comes first, at the level of the worst finding, then each finding on its line."""
    text = report.github_report([_MALFORMED, _DROPPED], DEFAULT_FAIL_CODES - {"AUTHORING_WARNING"})

    assert _commands(text) == [
        "::error title=Living-doc check::2 findings in 1 file: 1 fails, 1 warns. Annotations show 1 of 1 failures "
        "and 1 of 1 warnings; the job summary and the log list every finding.",
        "::error file=func-008.feature,line=16,title=MALFORMED_AC::Acceptance criterion failed validation: state: "
        "Input should be 'planned', 'in_review', 'active' or 'deprecated'. Fix: " + FIX_HINTS["MALFORMED_AC"],
        "::warning file=func-008.feature,line=17,title=AUTHORING_WARNING::Line of a dropped acceptance criterion is "
        "not read. Fix: " + FIX_HINTS["AUTHORING_WARNING"],
    ]


def test_failure_annotations_stop_at_the_per_step_limit():
    """With 12 failures, the summary and 9 failures fill the step's 10 error annotations; the summary says so."""
    commands = _commands(report.github_report(_missing_ids(12), DEFAULT_FAIL_CODES))

    assert commands[0].startswith("::error title=Living-doc check::12 findings in 12 files: 12 fail, 0 warn. ")
    assert "Annotations show 9 of 12 failures and 0 of 0 warnings" in commands[0]
    assert [command.split(" ", 1)[0] for command in commands] == ["::error"] * 10


def test_with_only_warnings_the_summary_is_a_warning():
    """When nothing fails, the summary is a warning and takes one of the step's 10 warning annotations."""
    commands = _commands(report.github_report(_missing_ids(11), DEFAULT_FAIL_CODES - {"MISSING_ENTITY_ID"}))

    assert commands[0].startswith("::warning title=Living-doc check::11 findings in 11 files: 0 fail, 11 warn. ")
    assert [command.split(" ", 1)[0] for command in commands] == ["::warning"] * 10


def test_without_findings_there_is_nothing_to_report():
    """No finding gives an empty GitHub report and an empty job summary."""
    assert report.github_report([], DEFAULT_FAIL_CODES) == ""
    assert report.job_summary([], DEFAULT_FAIL_CODES) == ""


def test_annotation_values_are_escaped():
    """A finding's path and message escape what GitHub would read as its own annotation syntax."""
    finding = Finding("a:b,c%.feature", 1, "MISSING_ENTITY_ID", "50% done\nnext")

    (summary, annotation) = _commands(report.github_report([finding], DEFAULT_FAIL_CODES))

    assert annotation.startswith("::error file=a%3Ab%2Cc%25.feature,line=1,title=MISSING_ENTITY_ID::50%25 done%0Anext.")
    assert summary.startswith("::error title=Living-doc check::1 finding in 1 file: 1 fails, 0 warn.")


def test_the_job_summary_lists_every_finding():
    """The job summary is a table of every finding, also those the annotation limit leaves out."""
    rows = [line for line in report.job_summary(_missing_ids(12), DEFAULT_FAIL_CODES).splitlines() if line[:3] == "| f"]

    assert len(rows) == 12
    assert rows[0].startswith("| f00\\.feature | 1 | fail | MISSING\\_ENTITY\\_ID | No header\\. Fix\\: ")


def test_a_job_summary_cell_shows_authored_text_literally():
    """A cell escapes Markdown and HTML, so authored text shows as written and never as markup or a link."""
    finding = Finding("x.feature", 2, "MALFORMED_AC", "AC:<id> | [x](y) *z*\nnext")

    (row,) = [line for line in report.job_summary([finding], DEFAULT_FAIL_CODES).splitlines() if line[:3] == "| x"]

    assert "AC\\:\\<id\\> \\| \\[x\\]\\(y\\) \\*z\\* next\\." in row


def test_a_missing_tag_gets_the_tag_hint_and_a_missing_key_the_key_hint():
    """`MISSING_REQUIRED_KEY` covers a header key and a feature-level tag; each is fixed in its own place."""
    tag = Finding("f.feature", 14, "MISSING_REQUIRED_KEY", "Required tag '@US_ID:' is missing.")
    key = Finding("f.feature", 2, "MISSING_REQUIRED_KEY", "Required key 'status:' is missing.")

    assert report.format_line(tag).endswith(f"is missing. Fix: {MISSING_TAG_HINT}")
    assert report.format_line(key).endswith(f"is missing. Fix: {FIX_HINTS['MISSING_REQUIRED_KEY']}")
