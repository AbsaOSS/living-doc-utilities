# Copilot Instructions — Living Documentation Utilities

This file tells a coding agent how to work in this repository. It describes this repo's
own layout, contract, and workflow; it is not shared with or copied from other repos.

**Section order** — keep the sections below in exactly this order:
Overview → Repo specifics → Coding guidelines → Inputs → Language and style →
Logging and string formatting → Docstrings and comments → Patterns → Testing →
Tooling and quality gates → Common pitfalls → Learned rules.

**House rules for this file**

- Must write every guidance bullet as a constraint led by one of `Must`, `Must not`, `Prefer`, `Avoid`.
- Must not put a colon after the leading keyword, and Must not use any other keyword style such as `Do`, `Should`, or a two-keyword `Do` / `Avoid` variant.
- Prefer bullet lists over paragraphs.
- Must end the file with a single trailing newline.

## Overview

`Living Documentation Utilities` is the shared Python library for the `living-doc-*` ecosystem —
the data models, serde helpers, and GitHub utilities that the collectors and generators import
instead of re-implementing.

- Must treat this repo as a library that is consumed by the other `living-doc-*` repos; it is not run directly, has no CLI, and has no GitHub Action entry point.
- Must treat every public class and function as an import surface — there is no `main.py` / `run()`.
- Must keep the library AI-free — deterministic Python only, no LLM call anywhere.
- Must keep environment access confined to `logging_config.setup_logging()` and `github/utils.get_action_input()`; Must keep the models, factory, and serde free of environment reads.

## Repo specifics

Module map — the `living_doc_utilities/` package:

| Path | Responsibility |
|---|---|
| `constants.py` | Shared constants — the `GITHUB_TOKEN` input name, the `OUTPUT_PATH` default, the `NO_PROJECT_DATA` sentinel |
| `decorators.py` | `debug_log_decorator` (debug logging around a call) and `safe_call_decorator(rate_limiter)` (wraps a GitHub call — rate-limited, returns `None` and logs on `ConnectionError` / `Timeout` / `GithubException` / `RequestException` / any `Exception`) |
| `logging_config.py` | `setup_logging()` — reads `INPUT_VERBOSE_LOGGING` and `RUNNER_DEBUG` from the environment, configures the root logger to stdout |
| `exporter/exporter.py` | `Exporter` base class — `export(**kwargs) -> bool`; subclasses implement one output format |
| `factory/issue_factory.py` | `IssueFactory.get(class_name, values)` — rebuilds the correct `Issue` subtype by name (`match` on the `type` string; base `Issue` fallback) |
| `github/utils.py` | `get_action_input(name, default="")` (reads `INPUT_<NAME>` from the environment), `set_action_output(name, value)` (appends `name=value` to `$GITHUB_OUTPUT`) |
| `github/rate_limiter.py` | `GithubRateLimiter` — callable class that sleeps until the GitHub rate-limit reset when `remaining < 5`, capped at 48 reset-time adjustments |
| `inputs/action_inputs.py` | `BaseActionInputs(ABC)` — the input-layer contract every action subclasses: `get_github_token()`, `validate_user_configuration()` → abstract `_validate() -> int`, `print_effective_configuration()` → abstract `_print_effective_configuration()` |
| `model/issue.py` | `Issue` — the core issue model: field-name constants, `to_dict()` / `from_dict()`, the `organization_name` / `repository_name` / `errors` properties, `add_errors()`, `is_valid_issue()` |
| `model/issues.py` | `Issues` — collection wrapper: `save_to_json()` / `load_from_json()` (via `IssueFactory`), `add_issue()` / `get_issue()` / `all_issues()` / `count()`, the static `make_issue_key(org, repo, number)` |
| `model/user_story_issue.py`, `model/feature_issue.py`, `model/functionality_issue.py` | `Issue` subtypes; `FunctionalityIssue.get_related_feature_ids()` parses the `### Associated Feature` list from the issue body |
| `model/project_status.py` | `ProjectStatus` — per-issue GitHub Project fields (`project_title` / `status` / `priority` / `size` / `moscow`), `to_dict()` / `from_dict()` |

- Must treat the library as having no entry point — consumers import the classes and functions above directly.

Inputs — this repo owns no `INPUT_*` contract of its own; it provides the helper consumers use:

- Must read consumer action inputs through `github.utils.get_action_input(name)`, which maps `name` to `INPUT_` + upper-case with `-` replaced by `_`.
- Must keep `setup_logging()` the only place that reads `INPUT_VERBOSE_LOGGING` / `RUNNER_DEBUG`.

Contract-sensitive outputs — downstream repos depend on these exactly:

- Must keep the serialized issue JSON shape stable — the field-name constants on `Issue` (`type`, `repository_id`, `title`, `issue_number`, `state`, `created_at`, `updated_at`, `closed_at`, `html_url`, `body`, `labels`, `linked_to_project`, `project_status`), the `type` discriminator that `IssueFactory` switches on, and the nested `ProjectStatus` keys.
- Must keep `Issues.make_issue_key()` output as `"{organization_name}/{repository_name}/{issue_number}"`.
- Must keep `get_action_input()` env-var mapping and `set_action_output()`'s `name=value\n` line format stable.
- Must keep the `ValueError` / log message text in `Issue.from_dict()` and `Issues.get_issue()` stable — downstream tests assert exact strings.
- Must treat any change to a public signature or to the serialized JSON shape as a breaking change that needs a version bump in `pyproject.toml`.

## Coding guidelines

- Must keep changes small and scoped to the task.
- Prefer explicit code over clever constructs.
- Must keep externally visible behaviour stable unless the task is an intentional contract change.
- Must not change existing log texts or error messages without a stated reason.
- Prefer pure functions for model, factory, and serde logic, and Avoid reading the environment outside `setup_logging()` and `get_action_input()`.

## Inputs

- Must route every consumer input read through `get_action_input()`; Must not call `os.getenv("INPUT_...")` from the models or the factory.
- Must keep input validation in the consumer's `BaseActionInputs` subclass (`_validate()`), not in the shared models.
- Avoid duplicating validation logic across modules.

## Language and style

- Must target Python 3.10+ (the ecosystem floor).
- Must add type hints for new public functions and classes.
- Must keep imports at module top — no imports inside functions or methods.
- Must keep `X | Y` unions and `match` / `case` where they already appear — both are 3.10-native; Must guard any 3.11+ standard-library use behind a `sys.version_info` fallback.
- Must not disable a linter rule inline unless this file records the exception under Learned rules.

## Logging and string formatting

- Must use `logging`, never `print`.
- Must use lazy `%` formatting in logging calls — `logger.info("msg %s", value)`.
- Must not use f-strings inside logging calls.
- Prefer the clearest formatting when constructing exception and failure messages, and Must keep contract-sensitive strings stable.

## Docstrings and comments

- Must match the existing module docstring style — a short summary of what the module contains.
- Prefer a one-line docstring summary for functions, with `@param` / `@return` / `@raises` lines where they add information, matching the surrounding code.
- Prefer self-explanatory code, and Prefer comments only for intent, edge cases, and the "why".
- Avoid tutorial-style prose or long examples in docstrings.

## Patterns

- Prefer leaf modules raising exceptions (`ValueError`, `TypeError`, `KeyError`) with a clear message; Must let the consuming action translate them into Action-failure output.
- Prefer the `to_dict()` / `from_dict()` pair on every model, and Must keep the round trip loss-free.
- Must route new `Issue` subtypes through `IssueFactory` — add a `case` and keep the base `Issue` fallback.
- Prefer private helpers (`_name`) for internal behaviour.
- Must keep integration boundaries — the GitHub API via `PyGithub`, `requests`, and the filesystem — explicit and mockable.

## Testing

- Must use `pytest` with `pytest-mock` (`mocker`), and Must not use `unittest`.
- Must keep tests under `tests/`, mirroring the package layout — `tests/model/`, `tests/github/`, `tests/inputs/`, `tests/exporter/`, plus `tests/test_decorators.py` and `tests/test_logging_config.py`.
- Must test behaviour — return values, raised exceptions, log messages.
- Must mock `INPUT_*` environment variables and the GitHub API in unit tests; Must not call external services or the real GitHub API.
- Prefer the shared fixtures in `tests/conftest.py` — `rate_limiter`, `mock_rate_limiter`, `mock_logging_setup`.
- Must bind PyGithub mocks with `spec=` (`mocker.Mock(spec=Github)`, `mocker.Mock(spec=Rate)`) as `conftest.py` does.

## Tooling and quality gates

- Must run `make qa` before finishing a code change — it runs `format-check` → `lint` → `types` → `test` and fails on the first failing gate.
- Must use the individual targets while iterating — `make format`, `make format-check`, `make lint`, `make types`, `make test`, `make coverage`.
- Must keep `make lint` clean — it runs ruff (`E` / `F` / `I` / `B` over tracked `*.py`, config in `pyproject.toml`) then Pylint, and Pylint must score 9.5 or higher.
- Must keep `make format-check` (Black, line length 120, config in `pyproject.toml`) clean, and Prefer `make format` (ruff autofix + Black) to fix import order and formatting in one step.
- Must keep `make types` (mypy, config in `pyproject.toml`) clean, and Prefer fixing types over adding ignores.
- Must keep `make coverage` (pytest, `--cov-fail-under=80`) passing.

## Common pitfalls

- Must verify a new dependency supports Python 3.10 before adding it, and Must keep it available on PyPI for the widest consumer base.
- Must remove unused imports and variables in the same change, and Avoid leaving dead code.
- Avoid changing the serialized JSON field names, the `type` discriminator, `make_issue_key()`'s format, or public signatures unless the task calls for it — every `living-doc-*` repo consumes them.
- Must bump `pyproject.toml` `version` when a change alters the public API or the wire format.

## Learned rules

- Must keep error messages stable where downstream tests assert exact strings — `Issue.from_dict()` and `Issues.get_issue()` in particular.
- Must keep the `# pylint: disable=broad-exception-caught` handlers in `decorators.safe_call_decorator` and `Issues.load_from_json` — they are the deliberate "log and degrade" boundary.
