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
the six documentation contracts, the authoring parsers that produce them, and the GitHub helpers
that the collectors and generators import instead of re-implementing.

- Must treat this repo as a library that is consumed by the other `living-doc-*` repos; it is not run directly, has no CLI, and has no GitHub Action entry point.
- Must treat every public class and function as an import surface — there is no `main.py` / `run()`.
- Must keep the library AI-free — deterministic Python only, no LLM call anywhere.
- Must keep environment access confined to `logging_config.setup_logging()`, `github/utils.get_action_input()`, and `github/utils.set_action_output()` (which writes to the file named by `GITHUB_OUTPUT`); Must keep `contracts/` and `authoring/` free of environment reads.
- Must treat `contracts/` as the shared, typed pydantic models of the doc-entities / doc-source / ui-tests / generator-ready / coverage-matrix / ui-test-catalog contracts (see `docs/contracts.md`), and `authoring/` as the pure `text -> data` layer that reads authored documents into them (see `docs/authoring.md`).
- Must not import from any collector, toolkit, or generator package — dependencies run one way, from those repos into this one.

## Repo specifics

Module map — the `living_doc_utilities/` package:

| Path | Responsibility |
|---|---|
| `constants.py` | Shared constants — the `GITHUB_TOKEN` input name, the `OUTPUT_PATH` default, the `NO_PROJECT_DATA` sentinel |
| `logging_config.py` | `setup_logging()` — reads `INPUT_VERBOSE_LOGGING` and `RUNNER_DEBUG` from the environment, configures the root logger to stdout |
| `contracts/common.py` | `ContractModel` (`extra="forbid"` pydantic base every contract model extends), `AcceptanceCriterion` (plus its `canonical_header()` renderer), `EntityCore`, `SourceRef`, `Timestamps` |
| `contracts/envelope.py` | The shared metadata envelope — `Metadata`, `Producer`, `Run`, `Source`, `Cardinality`, `Stats` / `AuditStats`, `SourceInputEntry`, `ContractWarning` — one model imported unchanged by every contract |
| `contracts/doc_entities.py`, `contracts/doc_source.py`, `contracts/ui_tests.py` | The `doc-entities` / `doc-source` / `ui-tests` collector-output contract result models (`Entity`, `PageRef`, `Scenario`, `AcLink`) and each contract's `RECORD_ROOTS` declaration (docs/contracts.md, section 1) |
| `contracts/generator_ready.py`, `contracts/coverage_matrix.py`, `contracts/ui_test_catalog.py` | The `generator-ready` / `coverage-matrix` / `ui-test-catalog` transform-output contract result models — reuse `doc_entities.Entity` / `common.AcceptanceCriterion` / `ui_tests.Scenario` directly rather than redeclaring them — and each contract's `RECORD_ROOTS` declaration (docs/contracts.md, section 1) |
| `contracts/schema_export.py` | Generates `contracts/schemas/*.json` from the models — `python -m living_doc_utilities.contracts.schema_export`, or `make schemas` — and `load_schema(contract_id)` |
| `contracts/codes.py` | `ALL_CODES` — the single registry of every error and warning code, with its kind and emitting component (docs/contracts.md, section 5) |
| `contracts/validation.py`, `contracts/compat.py` | The one structural-validation helper (`jsonschema.validators.validator_for`, never a hardcoded validator class) and the R5 compatibility check every consumer runs before trusting an input file |
| `contracts/io.py` | `read_artifact()` / `write_artifact()` — the only sanctioned way to read or write a contract artifact (docs/contracts.md, R12): compatibility check on read, in-memory validation then temp file and atomic rename on write |
| `contracts/stats.py`, `contracts/lineage.py`, `contracts/testing.py` | The R11 / R12 helpers every component builds its own tests on — `metadata.stats` computation, the lineage-table machinery (`LineageTable`, `assert_complete`, `check_field_loss`), and `full_sample()` / `shown_paths()` |
| `contracts/check_no_vendored_schemas.py` | R12 check 1 — `python -m living_doc_utilities.contracts.check_no_vendored_schemas [--allow DIR]`, or `make no-vendored-schemas` |
| `authoring/normalize.py` | `normalize(text, fmt, entity_type)` and `normalize_title(title)` — rewrites non-canonical dashes, bullet markers, case, version form and whitespace per `SourceFormat`, never touching code, Gherkin step text, or free prose; `TYPE_PROFILES` is the only place holding which of an entity type's sections are bullet sections |
| `authoring/ac_grammar.py` | `parse_acceptance_criteria(text, entity_id)` — the one acceptance-criterion header and extension grammar, canonical form only; the only module that validates the AC state vocabulary and version shape, and the only place that maps a legacy acceptance-criterion state onto `planned` |
| `authoring/issue_body.py`, `authoring/feature_header.py`, `authoring/page_object.py`, `authoring/scenario.py` | The parsers — a GitHub issue body, a `.feature` file's header block, a PageObject header, and a `.feature` file's scenarios with their `@AC:` tags; each returns `(parsed, warnings)` and never raises on malformed input |
| `authoring/identity.py`, `authoring/status.py`, `authoring/relations.py` | `entity_id` derivation from a title, `derive_statuses()` (final `state` / `state_origin`, run once over a whole run), and cross-entity relation checks |
| `authoring/url_policy.py`, `authoring/html_to_markdown.py` | Which links survive into rendered documentation (`safe_href`, `sanitize_html_fragment`) and Azure DevOps rich-text HTML into the Markdown-like text the other parsers read (`convert_html_to_markdown`); both need the `html` extra at call time |
| `authoring/docs_export.py`, `authoring/normalisation_cases.yaml` | `make docs` regenerates `docs/authoring.md`'s worked-examples table from `normalize`'s only test data, read by `tests/authoring/test_normalize_cases.py` |
| `github/utils.py` | `get_action_input(name, default="")` (reads `INPUT_<NAME>` from the environment), `set_action_output(name, value)` (appends `name=value` to `$GITHUB_OUTPUT`) — imports nothing outside the standard library |
| `github/rate_limiter.py` | `GithubRateLimiter` — callable class that sleeps until the GitHub rate-limit reset when `remaining < 5`, capped at 48 reset-time adjustments; needs the `github` extra |
| `github/decorators.py` | `debug_log_decorator` (debug logging around a call) and `safe_call_decorator(rate_limiter)` (rate-limited call that logs `ConnectionError` / `Timeout` / `GithubException` / `RequestException` / any `Exception` and **re-raises** it); needs the `github` extra |
| `inputs/action_inputs.py` | `BaseActionInputs(ABC)` — the input-layer contract every action subclasses: `get_github_token()`, `validate_user_configuration()` → abstract `_validate() -> int`, `print_effective_configuration()` → abstract `_print_effective_configuration()` |

- Must treat the library as having no entry point — consumers import the classes and functions above directly.
- Must keep `authoring/normalize.py` free of `if entity_type == ...` branching — type differences are data in `TYPE_PROFILES`.
- Must keep `authoring/normalize.py` free of any regex that validates the acceptance-criterion state vocabulary or version shape — that validation lives in `authoring/ac_grammar.py` alone.
- Must keep `contracts/` free of imports from `authoring/`, and `authoring/` free of any tracker-specific SDK — a parser only ever sees document text.
- Must regenerate `contracts/schemas/*.json` (`make schemas`) in the same change as any `contracts/` model edit — CI's Schema Regeneration Check fails the build on any diff.

Extras — what a module may import at module level, checked by `make deptry` and `make import-matrix`:

- Must keep `contracts/`, `authoring/`, `github/utils.py`, `inputs/`, `constants.py`, and `logging_config.py` importable with no extra installed — third-party imports there are limited to the core `dependencies` in `pyproject.toml` (`pydantic`, `jsonschema`); the one exception is `yaml` (PyYAML, a development dependency) inside `authoring/docs_export.py::_load_cases`, a repository script.
- Must import PyGithub and `requests` only in `github/rate_limiter.py` and `github/decorators.py` — they need the `github` extra.
- Must import `nh3` only inside the `url_policy` functions that call it — the `html` extra is needed to call `sanitize_html_fragment` or `convert_html_to_markdown`, never to import a module.

Inputs — this repo owns no `INPUT_*` contract of its own; it provides the helper consumers use:

- Must read consumer action inputs through `github.utils.get_action_input(name)`, which maps `name` to `INPUT_` + upper-case with `-` replaced by `_`.
- Must keep `setup_logging()` the only place that reads `INPUT_VERBOSE_LOGGING` / `RUNNER_DEBUG`.

Contract-sensitive outputs — downstream repos depend on these exactly:

- Must keep the contract ids (`doc-entities-v1.0.0` and its five siblings) and the `contracts/schemas/*.json` files stable — the contract id is independent of the package version.
- Must keep every code in `contracts/codes.ALL_CODES` and the acceptance-criterion canonical header form (`AC:<id> (v<x.y.z> - <state>)`, `AC:<id> (planned)`) stable.
- Must keep `get_action_input()` env-var mapping and `set_action_output()`'s `name=value\n` line format stable.
- Must keep `safe_call_decorator`'s log message texts stable, and Must keep it re-raising — a caller relies on a failed fetch surfacing as an exception, never as `None`.
- Must treat any change to a public signature or to a contract as a breaking change that needs a `pyproject.toml` version bump — a contract or public-API change bumps the minor version, a parser or helper fix bumps the patch version.
- Must treat `contracts/schemas/*.json` as generated output, never hand-edited — a `contracts/` model change and its regenerated schema (`make schemas`) land in the same commit.

## Coding guidelines

- Must keep changes small and scoped to the task.
- Prefer explicit code over clever constructs.
- Must keep externally visible behaviour stable unless the task is an intentional contract change.
- Must not change existing log texts or error messages without a stated reason.
- Prefer pure functions for contract and parser logic, and Avoid reading the environment outside `setup_logging()`, `get_action_input()`, and `set_action_output()`.

## Inputs

- Must route every consumer input read through `get_action_input()`; Must not call `os.getenv("INPUT_...")` from `contracts/` or `authoring/`.
- Must keep input validation in the consumer's `BaseActionInputs` subclass (`_validate()`), not in the shared contract models.
- Avoid duplicating validation logic across modules.

## Language and style

- Must target Python 3.10+ (the ecosystem floor).
- Must add type hints for new public functions and classes.
- Must keep imports at module top — no imports inside functions or methods, except the one recorded under Learned rules.
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
- Prefer parsers that return `(parsed, warnings)` and never raise on malformed authored input — Must report it as a registered warning code instead.
- Prefer private helpers (`_name`) for internal behaviour.
- Must keep integration boundaries — the GitHub API via `PyGithub`, `requests`, and the filesystem — explicit and mockable.
- Must use pydantic's own serde (`model_dump()` / `model_validate()`) on every `contracts/` model; Must not add a hand-rolled `to_dict()` / `from_dict()` there.
- Must express a `contracts/` model's cross-field invariant as a leading-underscore `@model_validator(mode="after")` method, matching `doc_entities.Entity`'s `_check_state_origin` / `_check_stub_reason_is_feature_only` / `_check_acceptance_criteria_belong_to_this_entity`.
- Must declare a new contract's record roots as a module-level `RECORD_ROOTS: dict[str, type[BaseModel]]`, matching `doc_entities.py` (docs/contracts.md, "Each contract declares its own record roots in its contract module").
- Must read and write a contract artifact through `contracts.io.read_artifact()` / `write_artifact()`, never a plain `json.load()` / `json.dump()`.

## Testing

- Must use `pytest` with `pytest-mock` (`mocker`), and Must not use `unittest`.
- Must keep tests under `tests/`, mirroring the package layout — `tests/contracts/`, `tests/authoring/` (with `golden/`), `tests/github/` (including `test_decorators.py`), and `tests/inputs/`, plus `tests/test_logging_config.py` and the shared `tests/fixtures/`.
- Must test behaviour — return values, raised exceptions, log messages.
- Must mock `INPUT_*` environment variables and the GitHub API in unit tests; Must not call external services or the real GitHub API.
- Prefer the shared fixtures in `tests/conftest.py` — `rate_limiter`, `mock_rate_limiter`, `mock_logging_setup`.
- Must bind PyGithub mocks with `spec=` (`mocker.Mock(spec=Github)`, `mocker.Mock(spec=Rate)`) as `conftest.py` does.
- Prefer `tests/contracts/factories.py`'s builder functions over hand-written pydantic instances in a `contracts/` test; Must assert a schema-shape claim (map typing, `field_occupancy` keys, header keys) against the generated `contracts/schemas/*.json` via `jsonschema.validate`, not against the pydantic model alone.
- Must cover both the success and the re-raise path of a decorator that wraps a failing call.

## Tooling and quality gates

- Must run `make qa` before finishing a code change — it runs `format-check` → `lint` → `types` → `deptry` → `coverage` → `no-vendored-schemas` and fails on the first failing gate.
- Must use the individual targets while iterating — `make format`, `make format-check`, `make lint`, `make types`, `make deptry`, `make test`, `make coverage`.
- Must install the development environment with `make install` — it installs `requirements-dev.txt` (the tooling on top of the runtime `requirements.txt`) and this package in editable mode.
- Must keep `make lint` clean — it runs ruff (`E` / `F` / `I` / `B` over tracked `*.py`, config in `pyproject.toml`) then Pylint over the tracked files outside `tests/` and over `tests/` (the rules that do not suit tests are switched off in the `Makefile`), and each Pylint run must score 9.5 or higher; Must scope both Pylint passes by `git ls-files`, not by directory, so a new tracked `.py` file is always linted.
- Must keep `make format-check` (Black, line length 120, config in `pyproject.toml`) clean, and Prefer `make format` (ruff autofix + Black) to fix import order and formatting in one step.
- Must keep `make types` (mypy, config in `pyproject.toml`) clean, and Prefer fixing types over adding ignores.
- Must keep `make deptry` clean — it fails on an import that is used but not declared in `pyproject.toml` (DEP001) and on a development-only tool imported by the library (DEP004).
- Must keep `make coverage` (pytest, `--cov-fail-under=80`) passing.
- Must not add an `integration` marker, a `test-unit` / `test-integration` target or `--ignore=tests/integration` to `test` / `coverage` — this repo has no integration tests, a deliberate difference from the shared `Makefile` vocabulary in `AbsaOSS/living-doc`.
- Must run `make import-matrix` after touching an import or `pyproject.toml` dependencies — it builds the wheel and proves, in three clean virtual environments (no extra, `github`, `html`), which modules import and which need an extra; CI runs the same target; it needs a POSIX shell (Linux, macOS, or WSL on Windows).
- Must run `make schemas` and commit the regenerated `contracts/schemas/*.json` when a `contracts/` model changes — `make qa` does not regenerate them itself, and CI's Schema Regeneration Check fails the build on any diff.

## Common pitfalls

- Must verify a new dependency supports Python 3.10 before adding it, and Must keep it available on PyPI for the widest consumer base.
- Must declare every new third-party import in `pyproject.toml` — in the core `dependencies` only when a module that has to import with no extra needs it, otherwise in the `github` or `html` extra it belongs to — and Must add its pinned version to `requirements-dev.txt`.
- Must keep `requirements.txt` to the runtime dependencies of this repo's own CI tooling; Must not put a test, lint, or type tool in it.
- Must remove unused imports and variables in the same change, and Avoid leaving dead code.
- Avoid changing contract ids, generated schemas, `ALL_CODES`, or public signatures unless the task calls for it — every `living-doc-*` repo consumes them.
- Must bump `pyproject.toml` `version` when a change alters the public API or a contract, and Must not create a release tag in the same change — the owner cuts `vX.Y.Z` after merge, and both release workflows check it against `pyproject.toml`.
- Avoid hand-editing a file under `contracts/schemas/` — edit the pydantic model and run `make schemas` instead; a hand-edit is overwritten by the next regeneration and masks a real mismatch between the model and its schema.
- Must check a `contracts/` field name against `AbsaOSS/living-doc`'s canon (`tools/examples_check.py`'s `PAIR_FIELD_MAP` / `REQUIRED_PO_KEYS_FULL` / `REQUIRED_PO_KEYS_XREF`, and `docs/guides/living-doc-header-types.md`) before inventing one — several field names in the first version of this package (`description`, `parent_feature`, `user_story_ids`, `functionality_ids`) were later renamed to match canon (`narrative`/`purpose`, `parent`, `user_stories`, `functionalities`); Avoid trusting `living-doc`'s `docs/examples/_expected/*.json` fixtures for this — they predate this repo's `docs/contracts.md` rewrite and are stale.
- Must not reintroduce a hand-rolled `to_dict()` / `from_dict()` issue-model layer — the pydantic `contracts/` models are the only shared data model.

## Learned rules

- Must keep `safe_call_decorator` logging with `exc_info=True` and then re-raising each of `ConnectionError` / `Timeout`, `GithubException`, `RequestException`, and any other `Exception`, including one raised by the rate limiter's own lookup — Must keep the rate limiter inside the `try`; a swallowed or unlogged failure hides a real error behind a `None` (or nothing) that a caller reads as "no data".
- Must keep the function-level `import nh3  # pylint: disable=import-outside-toplevel` in `authoring/url_policy.py` — it is what lets every `authoring` module import without the `html` extra; Must not add another function-level import elsewhere, except `import yaml` in `authoring/docs_export.py::_load_cases` (PyYAML is a development dependency, so that module must import without it).
- Must write every generated or contract file (`make schemas`, `make docs`, `write_artifact`, `set_action_output`) with an explicit `newline="\n"`, so the same file is byte-identical on every OS — text mode writes CRLF on Windows, and the committed files (and CI's `git diff`) are LF; Must check it by reading the file as bytes, since a text-mode read hides the difference; Must not restate this in code comments or docstrings.
- Must keep error messages stable where downstream tests assert exact strings.
