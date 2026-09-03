# Copilot Review Rules — Living Documentation Utilities

This file defines how Copilot reviews pull requests in this repository. It describes this
repo's own risk areas and review expectations; it is not shared with other repos.

**House rules for this file**

- Must write every guidance bullet as a constraint led by one of `Must`, `Must not`, `Prefer`, `Avoid`.
- Must not put a colon after the leading keyword, and Must not use any other keyword style.
- Prefer short headings and bullet lists over prose.
- Prefer verifiable checks — a reviewer can point to the code and the impact.
- Avoid long audit reports unless they are explicitly requested.

## Review modes

- Must support two modes — Default review for standard PR risk, and Double-check review for elevated-risk PRs.

## Mode — Default review

- Must treat the change as a single PR with normal risk.
- Must prioritise in this order — correctness, security, tests, maintainability, style.

**Checks**

- Must flag logic bugs, missing edge cases, regressions, and unintended contract changes.
- Must flag unsafe input handling, secret exposure, and insecure defaults.
- Must check that tests exist for changed logic and cover the success and failure paths.
- Prefer calling out unnecessary complexity, duplication, and unclear naming or structure.
- Avoid style notes unless they reduce readability or break a repo convention.

**Response format**

- Must use short bullet points.
- Prefer referencing files and line ranges.
- Must group comments by severity — Blocker (must fix), Important (should fix), Nit (optional).
- Prefer actionable suggestions over rewrites.
- Must not rewrite the whole PR or produce a long report.

## Mode — Double-check review

- Must treat the change as higher risk — changes to the serialized JSON shape, public class or function signatures, the `IssueFactory` dispatch, or the `GithubRateLimiter` sleep logic.

**Additional focus**

- Prefer confirming that previous review comments were addressed correctly.
- Must re-check high-risk areas — the `Issue` / `ProjectStatus` `to_dict()` / `from_dict()` round trip, `Issues.load_from_json()`'s broad-except fallback, `get_action_input()` / `set_action_output()`, and the rate-limiter reset math.
- Prefer looking for hidden side effects — backward compatibility for downstream repos, behaviour on missing or malformed JSON, a new required field breaking old payloads.
- Prefer validating safe defaults — `load_from_json()` returning an empty `Issues` on error, sensible fallbacks in `from_dict()`.

**Response format**

- Prefer commenting only where risk or impact is non-trivial.
- Avoid repeating minor style notes already covered by Default review.
- Prefer stating risk acceptance explicitly when something is left as-is — the risk, why it is acceptable, and the mitigation that exists.

## Commenting rules — all modes

- Must include for every comment — what the issue is (one line), why it matters (impact or risk), and how to fix it (a minimal actionable suggestion).
- Prefer linking to an existing pattern in the repo over introducing a new one.
- Must ask a targeted question instead of assuming when context is missing.

## Non-goals

- Must not request refactors unrelated to the PR's intent.
- Must not bikeshed formatting that Black or Pylint already enforces.
- Avoid proposing architectural rewrites unless they are explicitly requested.

## Repo specifics

- Must treat these as high-risk areas — the serde round trip in `model/issue.py` / `model/project_status.py`, the `type`-string dispatch in `factory/issue_factory.py`, `Issues.load_from_json()` / `save_to_json()`, `github/utils.py`, and `github/rate_limiter.py`.
- Must treat these as contract-sensitive — the serialized JSON field names and the `type` discriminator, `Issues.make_issue_key()`'s `"{org}/{repo}/{number}"` format, `set_action_output()`'s `name=value` line, and the exact `ValueError` / log strings tests assert on.
- Must flag any public signature change or wire-format change that lacks a matching `pyproject.toml` `version` bump — this is a published PyPI library and every `living-doc-*` repo consumes it.
- Must expect tests under `tests/`, mirroring the package layout, using `pytest` + `pytest-mock`.
- Must expect QA to run through the root `Makefile` — `make qa` covers `format-check`, `lint`, `types`, and `test`.
