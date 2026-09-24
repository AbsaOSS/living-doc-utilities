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

- Must treat the change as higher risk — changes to a contract model or its generated schema, public class or function signatures, the `authoring` grammar and parsers, the extras boundaries in `pyproject.toml`, or the `GithubRateLimiter` sleep logic.

**Additional focus**

- Prefer confirming that previous review comments were addressed correctly.
- Must re-check high-risk areas — `read_artifact()` / `write_artifact()` (the compatibility check, the validate-then-atomic-rename sequence), the `safe_call_decorator` log-and-re-raise behaviour, `get_action_input()` / `set_action_output()`, and the rate-limiter reset math.
- Prefer looking for hidden side effects — backward compatibility for downstream repos, behaviour on a missing or malformed artifact, a new required field breaking old payloads, a new import that needs an extra a no-extra caller does not have.
- Prefer validating safe failure behaviour — a parser reporting a registered warning code instead of raising, a failed GitHub call surfacing as an exception and never as `None`.

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

## Documentation

- Must review a change to `README.md`, `DEVELOPER.md`, `CONTRIBUTING.md` or a page under `docs/` against `DEVELOPER.md`, "Writing documentation" — depth, Purpose then Contents, one fact on one page, the parts and their limits.
- Must check a sample of ten decision- or fact-list items per changed page against the code their `path::symbol` names, and flag any item the code does not bear out.
- Must flag a fact defined on two pages, a hub that defines instead of naming and linking, a limit exceeded without an `<!-- over limit: … -->` reason, and an anchor by line number.
- Must flag a new page missing from `tests/docs/pages.py::APPROVED_PAGES` or not linked from its hub.

## Repo specifics

- Must treat these as high-risk areas — `contracts/io.py`, `contracts/compat.py` and `contracts/validation.py`, the `authoring/ac_grammar.py` grammar and `authoring/normalize.py`, `github/utils.py`, `github/rate_limiter.py`, `github/decorators.py`, and any `contracts/` model change that lacks a regenerated `contracts/schemas/*.json`.
- Must treat these as contract-sensitive — the contract ids and generated schemas, `contracts/codes.ALL_CODES`, the acceptance-criterion canonical header form, `set_action_output()`'s `name=value` line, `safe_call_decorator`'s log strings, the exact `ValueError` / log strings tests assert on, and a `contracts/` model's field names/shapes against `AbsaOSS/living-doc`'s canon (`tools/examples_check.py`'s `PAIR_FIELD_MAP`, `docs/guides/living-doc-header-types.md`) rather than `living-doc`'s `docs/examples/_expected/*.json`, which is known stale.
- Must flag any public signature change or contract change that lacks a matching `pyproject.toml` `version` bump — this is a published PyPI library and every `living-doc-*` repo consumes it — and Must flag a release tag created in the same PR.
- Must flag a third-party import that `pyproject.toml` does not declare, a PyGithub or `requests` import outside `github/rate_limiter.py` and `github/decorators.py`, an `nh3` import outside the `authoring/url_policy.py` functions that call it, and a test, lint, or type tool added to `requirements.txt` instead of `requirements-dev.txt`.
- Must flag any import from a collector, toolkit, or generator package.
- Must expect tests under `tests/`, mirroring the package layout, using `pytest` + `pytest-mock`.
- Must expect QA to run through the root `Makefile` — `make qa` covers `format-check`, `lint`, `types`, `deptry`, `coverage`, and `no-vendored-schemas`; a dependency or import change must also pass `make import-matrix`, and a `contracts/` model change must also carry a regenerated `contracts/schemas/*.json` (`make schemas`).
