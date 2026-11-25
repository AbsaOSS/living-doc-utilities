# Check

## Purpose

This page defines the authored-input check: what it reports, its report, the policy file and the required keys. A
caller, such as `living-doc-collector-gh`'s `doc-check` mode, runs it in a pull request.

Read before: [Authoring](authoring.md) · Next: [Errors and warnings](contracts/errors.md)

## Contents

- [Principle](#principle)
- [What it reports](#what-it-reports)
- [Report](#report)
- [Policy file](#policy-file)
- [Required keys](#required-keys)
- [Example](#example)

## Principle

The check runs the collectors' parsers over a corpus before a merge, so a broken header fails on its line.
The parsers stay lenient; the check runs above them.
It is a library: the caller reads the files, prints the report and sets the exit code.

## What it reports

- The caller gives every authored file of the corpus, each with its path, entity type and text, and the changed paths
- The entity type picks the parser: a User Story or Functionality is a `.feature` file, header and scenarios; a Feature is a PageObject
- Each changed file's own findings are reported; an unchanged file's are not
- Every relation finding of the corpus is reported, on the title line of the file that declares its entity
  - Why: relations are taken to be sound before the change, so a broken one is the change's.
- A cross-reference PageObject whose `parent-feat:` names no Feature of the corpus gets `UNRESOLVED_RELATION`, as the collector reports it
- `FEATURE_WITHOUT_FUNCTIONALITY` is a relation finding; `MISSING_STATUS` and `STATUS_AC_MISMATCH` are per file
- A finding with no line of its own sits on the title line, and shows its context, such as a relation's target
- A changed path that is not one of the files, or a path given twice, raises `ValueError`

## Report

- One line per finding: `<path>:<line>: <CODE> <message> Fix: <hint>`; a line break in it is escaped
- Every code of the default fail list has a one-line fix hint
- The findings fail when one of their codes is in the fail list
- The GitHub Actions report, which the caller prints:
  1. the lines, between `::stop-commands::<token>` and `::<token>::`, so authored text runs no workflow command
  2. a summary annotation: the findings, files, failures and warnings, and how many the annotations show
  3. one `::error` or `::warning` annotation per finding, on its line
- In GitHub Actions the caller prints the GitHub report as it is, from the start of a line, and no finding line outside it
  - Why: outside the block, a path that starts with `::` would run as a workflow command.
- GitHub shows at most 10 annotations of a level per step; the summary takes one of its own level's
  - Why: GitHub drops the rest without notice, so the summary says how many are shown.
- The job summary, which the caller writes: a table of every finding

## Policy file

`living-doc-policy.yaml`, at the repository root, is one file for all of a project's living-doc gates:

```yaml
check:
  warn:            # these codes still print, but no longer fail
    - AUTHORING_WARNING
```

- Without a file, with an empty one, or with `check:` or `warn:` left empty, every code of the default fail list fails
- `check.warn` names the codes that only warn; a code outside the default fail list is an error
- A key written twice in one mapping is an error
  - Why: YAML would keep only its last value, and drop the first without a word.
- An unknown key under `check` is an error; another top-level section is left to the gate that reads it
  - Why: the other gates add their own sections to the same file.
- The default fail list: `AUTHORING_ERROR`, `AUTHORING_WARNING`, `FEATURE_WITHOUT_FUNCTIONALITY`, `HTML_CONTENT_DROPPED`, `IGNORED_AUTHORED_KEY`, `LEGACY_AC_STATE`, `MALFORMED_AC`, `MALFORMED_STATUS`, `MISINDENTED_LINE`, `MISSING_ENTITY_ID`, `MISSING_REQUIRED_KEY`, `MISSING_STATUS`, `RELATION_MISMATCH`, `RELATION_TYPE_MISMATCH`, `STATUS_AC_MISMATCH`, `UNKNOWN_SECTION`, `UNPARSED_AC_LINE`, `UNPARSED_BULLET_LINE`, `UNRESOLVED_RELATION` → [Errors and warnings](contracts/errors.md#codes)
  - Why: it is every code the authoring parsers and checks raise; each one drops or misreads authored text.
- The check never raises `UNKNOWN_SECTION` or `HTML_CONTENT_DROPPED`; they stay in the list for the gates that read issue bodies

## Required keys

One table holds every header's required keys; `living-doc`'s corpus checker reads it too. The check reports a missing
key as `MISSING_REQUIRED_KEY`, on the header's title line.

| Header | Required keys |
|---|---|
| User Story `.feature` | `status`, `business_value`, `acceptance_criteria` |
| Functionality `.feature` | `status`, `parent`, `func_type`, `acceptance_criteria` |
| Feature PageObject, full header | `surface_type`, `route`, `owners`, `purpose`, `user_stories`, `functionalities`, `external_dependencies`, `page-object` |
| PageObject, cross-reference header (with `parent-feat:`) | `parent-feat`, `route`, `owners`, `purpose`, `page-object` |
| User Story issue body | `## Description`, `## Status`, `## Business Value`, `## Acceptance Criteria` |
| Feature issue body | `## Description`, `## Surface Type`, `## Owners`, `## User Stories`, `## Functionalities` |
| Functionality issue body | `## Description`, `## Status`, `## Parent Feature`, `## Func Type`, `## Acceptance Criteria` |

- The check reads `.feature` and PageObject headers only; the issue-body rows serve the readers of issue bodies

## Example

```python
from living_doc_utilities.check.engine import AuthoredFile, check
from living_doc_utilities.check.report import fails, format_line
from living_doc_utilities.policy import Policy

story = AuthoredFile("features/us-001.feature", "DocumentedUserStory", "Feature: Borrow a book\n")
(finding,) = check([story], changed={"features/us-001.feature"})

assert (finding.line, finding.code) == (1, "MISSING_ENTITY_ID")  # a story with no living-doc header
assert " MISSING_ENTITY_ID No living-doc header found" in format_line(finding)
assert fails([finding], Policy().check.fail_codes)
```
