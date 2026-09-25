# Pipeline rules

## Purpose

Collector and transform authors read this page. It defines what one pipeline run covers, where a collector
writes, and how a collector fails and retries (R13). Most of these rules bind the collectors and the toolkit,
so a line with no `path::symbol` names the component that must realise it.

Read before: [Artifact rules](artifact-rules.md) · Next: [Component checks](component-checks.md)

## Contents

- [One project, one pipeline, one documentation source](#one-project-one-pipeline-one-documentation-source)
- [Project id](#project-id)
- [Collector output layout](#collector-output-layout)
- [R13: a collector collects everything it was configured for, or fails](#r13-a-collector-collects-everything-it-was-configured-for-or-fails)
- [Retries](#retries)

## One project, one pipeline, one documentation source

- A pipeline run documents exactly one project → toolkit shared input validation
- A transform run takes exactly one documentation file: the issue-tracker document or the source-scanned one, never both → toolkit
- Several repositories or organisations of one project are collected in one collector run → collectors
  - Why: one run is where they can be de-duplicated coherently.
- Test data may come from another system: Azure DevOps work items with `.feature` files on GitHub is supported → toolkit
- Two documentation files in one run fail with `MULTIPLE_DOCUMENTATION_SOURCES` → `contracts/codes.py::Code`
- Two different kinds of documentation fail with `MIXED_DOCUMENTATION_SOURCES` → `contracts/codes.py::Code`
- Several documentation sources per run are deferred until a transform has merge logic → toolkit
  - Why: merging decides what happens when both describe one entity; without it, a winner is picked silently.

## Project id

- Every collector has a required project-id input: lowercase letters, digits and hyphens, starting with a letter or digit → `contracts/envelope.py::PROJECT_ID_PATTERN`
- It is set once per pipeline, passed to every step and written to every artifact's `metadata.source.project_id` → `contracts/envelope.py::Source`
- A transform and every generator take the project id from their own inputs, never from separate configuration → toolkit, generators
  - Why: configuration that restates a value in the data can contradict it.
- A mismatch across inputs, or an input with no project id, is a hard `PROJECT_MISMATCH` → `contracts/codes.py::Code`

## Collector output layout

- A collector writes `<output-path>/<mode>/<artifact>.json`, e.g. `output/collector-gh/doc-issues/doc-entities.json` → collectors
- `output-path` is an input on both collectors, with a per-collector default under `./output` → collectors; the base is `constants.py::OUTPUT_PATH`
- A collector clears only its own `<output-path>/<mode>/` directory, never a shared parent → collectors
  - Why: two collectors writing into one output tree cannot delete each other's results.
- The file name is always the contract name; the source system lives in `metadata` → [Contracts](artifact-rules.md#contracts)
- Project separation is pipeline configuration (one output location per project), not a path convention in the tools → pipeline workflows

## R13: a collector collects everything it was configured for, or fails

- The unit of failure is a configured source: one repository, one repository path, or one project plus query → collectors
- A fetch still failing after retries, or a missing configured path, fails the whole source → `contracts/codes.py::Code`
  - Why: a document quietly missing half a repository looks like a document about a smaller project.
- Each source is collected by its own function; the run decides success only after every source was tried → collectors
  - Why: one failure never discards sources already collected.
- Configuration errors fail at start with `INVALID_CONFIGURATION`, naming the input and the reason → `contracts/codes.py::Code`
- A missing or malformed project id, repository or project entry fails before any network request → collectors
- A token rejected by the first request fails the same way, and no further request is made → collectors
  - Why: a typo should not spend a rate limit.
- By default a failure is hard: the run names the source and cause, exits non-zero and writes no output file → collectors
  - Why: a short file with exit code zero turns an outage into a silent documentation regression.
- Opt-in partial mode records a failed source as a warning and continues; it still fails if every source failed → collectors
- `sources_configured` and `sources_failed` appear on every collector output → `contracts/envelope.py::Cardinality`
- A transform copies them into its audit record and forwards every input warning, naming its input → toolkit
  - Why: a partial collection stays visible in the final document, several steps later.
- A source that answers with zero entities is the warning `EMPTY_SOURCE`, not an error → `contracts/codes.py::Code`
  - Why: a repository with no documentation yet is a normal state.
- Shared code never turns a failure into `None`; the GitHub call decorator re-raises ([GitHub helpers](../api.md#github-helpers)) → `github/decorators.py::safe_call_decorator`
  - Why: a `None` for "failed" and one for "absent" look the same, and a retry policy cannot act on a value.

## Retries

One retry policy is shared by every collector → collectors.

- Up to 5 attempts, with exponential backoff from 2 seconds plus jitter.
- One wait is capped at 60 seconds; a rate-limit reset wait at 15 minutes.
- Every HTTP call has a 10-second connect timeout and a 60-second read timeout.

| Signal | Action |
|---|---|
| connection error, timeout | retry |
| HTTP 429, 500, 502, 503, 504 | retry, honouring `Retry-After` |
| HTTP 403 with rate-limit-remaining at 0 | wait until the reset time, retry |
| HTTP 403 or 429 with `Retry-After` (secondary rate limit) | wait `Retry-After`, retry |
| a rate-limited GraphQL error returned with HTTP 200 | treat as a primary rate limit |
| HTTP 401 on the first request | no retry; the run fails at start with `INVALID_CONFIGURATION` |
| HTTP 401 after the first request, or a GraphQL scope or permission error | no retry; the source fails; the message names the missing scope |
| GraphQL not-found error, HTTP 404 | no retry; the source fails |
