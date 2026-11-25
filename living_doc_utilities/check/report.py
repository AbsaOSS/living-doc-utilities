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
The check's report as text a caller prints or writes: one line per finding, the GitHub Actions annotations, the job
summary, and whether the findings fail.
"""

import re
import secrets
from typing import Collection, Iterable, Sequence

from living_doc_utilities.check.engine import Finding
from living_doc_utilities.check.hints import FIX_HINTS

_TITLE = "Living-doc check"

# GitHub Actions shows at most this many annotations of each level per step, and drops the rest without notice.
_ANNOTATIONS_PER_LEVEL = 10

# Every ASCII punctuation character, which a backslash makes literal in Markdown.
_MARKDOWN_PUNCTUATION_RE = re.compile(r"([!-/:-@\[-`{-~])")


def _one_line(text: str) -> str:
    """`text` with each carriage return and line feed escaped, so it can never start a line of its own."""
    return text.replace("\r", "\\r").replace("\n", "\\n")


def _with_hint(finding: Finding) -> str:
    """The finding's message, closed as a sentence, then its fix hint."""
    message = finding.message if finding.message.endswith((".", "!", "?")) else f"{finding.message}."
    hint = FIX_HINTS.get(finding.code)
    return f"{message} Fix: {hint}" if hint else message


def _data(text: str) -> str:
    """An annotation's message, escaped as GitHub's workflow-command syntax requires."""
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _property(text: str) -> str:
    """An annotation property's value, escaped as GitHub's workflow-command syntax requires."""
    return _data(text).replace(":", "%3A").replace(",", "%2C")


def _cell(text: str) -> str:
    """A job-summary table cell that shows `text` as written: no Markdown, no HTML, one line."""
    return _MARKDOWN_PUNCTUATION_RE.sub(r"\\\1", re.sub(r"[\r\n]", " ", text))


def _count(number: int, noun: str) -> str:
    return f"{number} {noun}" if number == 1 else f"{number} {noun}s"


def _tally(failures: int, warnings: int) -> str:
    """`<n> fail(s), <n> warn(s)`, each verb agreeing with its number."""
    return f"{failures} {'fails' if failures == 1 else 'fail'}, {warnings} {'warns' if warnings == 1 else 'warn'}"


def format_line(finding: Finding) -> str:
    """`<path>:<line>: <CODE> <message> Fix: <hint>`, on one line."""
    return _one_line(f"{finding.path}:{finding.line}: {finding.code} {_with_hint(finding)}")


def fails(findings: Iterable[Finding], fail_codes: Collection[str]) -> bool:
    """Whether the findings fail the check: one of their codes is in the fail list."""
    return any(finding.code in fail_codes for finding in findings)


def github_report(findings: Sequence[Finding], fail_codes: Collection[str]) -> str:
    """The text to print in GitHub Actions, `""` without findings: the lines, in a block that runs no workflow command;
    then a summary annotation at the level of the worst finding; then one annotation per finding while the step's
    limit for its level lasts. The caller writes `job_summary` too, which the summary annotation points to."""
    if not findings:
        return ""
    failures = [finding for finding in findings if finding.code in fail_codes]
    warnings = [finding for finding in findings if finding.code not in fail_codes]
    summary_level = "error" if failures else "warning"
    room = {level: _ANNOTATIONS_PER_LEVEL - (level == summary_level) for level in ("error", "warning")}
    shown = {"error": failures[: room["error"]], "warning": warnings[: room["warning"]]}
    summary = (
        f"{_count(len(findings), 'finding')} in {_count(len({finding.path for finding in findings}), 'file')}: "
        f"{_tally(len(failures), len(warnings))}. Annotations show {len(shown['error'])} of {len(failures)} failures "
        f"and {len(shown['warning'])} of {len(warnings)} warnings; the job summary and the log list every finding."
    )

    token = secrets.token_hex(16)
    lines = [f"::stop-commands::{token}", *(format_line(finding) for finding in findings), f"::{token}::"]
    lines.append(f"::{summary_level} title={_TITLE}::{_data(summary)}")
    for level, level_findings in shown.items():
        lines.extend(
            f"::{level} file={_property(finding.path)},line={finding.line},title={_property(finding.code)}::"
            f"{_data(_with_hint(finding))}"
            for finding in level_findings
        )
    return "\n".join(lines) + "\n"


def job_summary(findings: Sequence[Finding], fail_codes: Collection[str]) -> str:
    """A Markdown table of every finding for the job summary page, `""` without findings."""
    if not findings:
        return ""
    failures = sum(finding.code in fail_codes for finding in findings)
    rows = [
        f"## {_TITLE}",
        "",
        f"{_count(len(findings), 'finding')}: {_tally(failures, len(findings) - failures)}.",
        "",
        "| File | Line | Level | Code | Message |",
        "|---|---|---|---|---|",
    ]
    rows.extend(
        f"| {_cell(finding.path)} | {finding.line} | {'fail' if finding.code in fail_codes else 'warn'} | "
        f"{_cell(finding.code)} | {_cell(_with_hint(finding))} |"
        for finding in findings
    )
    return "\n".join(rows) + "\n"
