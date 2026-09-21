# Living Documentation Utilities - for Developers

- [Project Setup](#project-setup)
- [Quality Gates (`make`)](#quality-gates-make)
- [Run Pylint Check Locally](#run-pylint-check-locally)
- [Run Black Tool Locally](#run-black-tool-locally)
- [Run mypy Tool Locally](#run-mypy-tool-locally)
- [Run Unit Test](#run-unit-test)
- [Code Coverage](#code-coverage)
- [Dependencies and Extras](#dependencies-and-extras)
- [Regenerate Contract Schemas](#regenerate-contract-schemas)
- [Regenerate Authoring Docs](#regenerate-authoring-docs)
- [How to Release](#how-to-release)

## Project Setup

If you need to set up the project locally, follow these steps:

### Prepare the Environment

```shell
python3 --version
```

### Set Up Python Environment

```shell
python3 -m venv .venv
source .venv/bin/activate
make install
```

`make install` is `pip install -r requirements-dev.txt` followed by `pip install -e . --no-deps`.
`requirements.txt` holds only the runtime dependencies of this repository's own CI tooling
(`make schemas`, `make docs`, `make no-vendored-schemas`); `requirements-dev.txt` includes it and
adds the test, lint, type, and packaging tools. Neither is the package's install-time dependency
list — that is `pyproject.toml` (see [Dependencies and Extras](#dependencies-and-extras)).

The editable install of the package itself (not just its dependencies) is required: some
of the code (e.g. `compat.installed_utilities_version()`) reads this package's own version
via `importlib.metadata`, which only finds it once it's installed.

---
## Quality Gates (`make`)

The root `Makefile` is the canonical command vocabulary shared across every `living-doc-*`
repo. Run the whole gate before opening a pull request:

```shell
make qa
```

`make qa` runs `format-check` → `lint` → `types` → `deptry` → `coverage` → `no-vendored-schemas` and fails on the first
failing gate. The individual targets are also available while iterating:

| Target | Runs | Gate |
|---|---|---|
| `make lint` | ruff, then Pylint over the tracked files outside `tests/` and over `tests/` (rules that do not suit tests are off, see `PYLINT_TESTS_DISABLE` in the `Makefile`) | each Pylint run scores ≥ 9.5 / 10 |
| `make format` | Black, rewriting files in place | line length 120 |
| `make format-check` | Black in `--check` mode | line length 120 |
| `make types` | mypy | clean |
| `make deptry` | deptry over the package | no import that is used but not declared in `pyproject.toml` (DEP001) and no development-only tool imported by the library (DEP004) |
| `make test` | pytest over `tests/` | pass |
| `make coverage` | pytest with the coverage gate | `--cov-fail-under=80` |
| `make schemas` | regenerates `living_doc_utilities/contracts/schemas/*.json` from the pydantic contract models | committed schemas byte-for-byte up to date |
| `make no-vendored-schemas` | `python -m living_doc_utilities.contracts.check_no_vendored_schemas --allow living_doc_utilities/contracts/schemas` (R12 check 1) | no git-tracked `*-schema.json` / `*.schema.json` outside `tests/` and this package's own schemas dir; files not yet `git add`ed are not seen |
| `make docs` | regenerates `docs/authoring.md`'s worked-examples table from `normalisation_cases.yaml` | committed table byte-for-byte up to date |
| `make import-matrix` (Windows: `scripts\import_matrix.bat`) | builds the wheel and installs it into three clean virtual environments (no extra / `github` / `html`) — not part of `make qa`, CI runs it as its own job | every module imports with only the extras it needs, `pip check` clean in each |

The sections below explain each tool in more detail and how to scope it to a single file.

---
## Run Pylint Check Locally

This project uses the [Pylint](https://pypi.org/project/pylint/) tool for static code analysis.
Pylint analyses your code without actually running it.
It checks for errors, enforces coding standards, looks for code smells, etc.
Pylint runs twice: over every tracked file outside `tests/` with every rule, and over `tests/` with the rules that do not suit tests switched off (`PYLINT_TESTS_DISABLE` in the `Makefile`, explained in [Rules switched off for tests](#rules-switched-off-for-tests)).
Both passes take their files from `git ls-files`, so a new `.py` file is linted once it is tracked (`git add`), not before.
The root project file `pyproject.toml` defines the Pylint configuration (`[tool.pylint.*]`).

Pylint displays a global evaluation score for the code, rated out of a maximum score of 10.0.
We are aiming to keep our code quality high above the score 9.5.

Follow these steps to run Pylint check locally:

- Perform the [setup of python venv](#set-up-python-environment).

### Run Pylint

Run both Pylint passes, as CI does (ruff runs first).
```shell
make lint
```

To run Pylint on a specific package file, follow the pattern `pylint <path_to_file>/<name_of_file>.py`.
A test file also needs the `--disable` list from `PYLINT_TESTS_DISABLE`, otherwise the rules that do not suit tests are reported.

Example:
```shell
pylint living_doc_utilities/inputs/action_inputs.py
``` 

### Expected Output

This is an example of the expected console output after running the tool:
```bash
************* Module main
main.py:30:0: C0116: Missing function or method docstring (missing-function-docstring)

------------------------------------------------------------------
Your code has been rated at 9.41/10 (previous run: 8.82/10, +0.59)
```

### Rules switched off for tests

`make lint` checks `tests/` with fewer Pylint rules than the package. Below, each switched-off rule is explained in plain words:
what Pylint complains about, and why that does not help in tests.
The list itself is `PYLINT_TESTS_DISABLE` in the `Makefile`. Change the list and this section together.

Every rule that is not listed here stays on for tests, so unused imports, undefined names and similar mistakes are still caught.

**Off because tests do these things on purpose**

| Rule | What Pylint complains about | Why it is off for tests |
|---|---|---|
| `use-implicit-booleaness-not-comparison` | `assert result == []`. Pylint says: write `assert not result`. | A test should also fail when `result` is `None` or `{}`. `assert not result` passes for both, so it checks less. |
| `redefined-outer-name` | A function argument has the same name as something defined above it. | This is how pytest fixtures (shared test setup) work. The fixture is defined once, and a test asks for it by using its name as an argument. |
| `protected-access` | Code uses a name that starts with `_`, which means "private". | Some tests check a private helper or constant on purpose. |
| `unsupported-membership-test`, `unsubscriptable-object` | `"x" in Model.model_fields` and `Model.model_fields["x"]`. Pylint says the object does not support that. | False alarm. `model_fields` is a normal dict, but Pylint does not understand how pydantic builds its classes and guesses wrong. A real mistake would fail when the test runs. |
| `unidiomatic-typecheck` | `type(x) is Foo`. Pylint says: use `isinstance(x, Foo)`. | A test sometimes has to check the exact type: a `Foo`, not a subclass. `isinstance` also accepts subclasses. Pylint also flags the harmless `type(None)`. |
| `unused-argument` | A function argument is never used. | pytest fills in the arguments. A test can receive a `parametrize` value (one of several inputs it runs with) that it does not need, or a fixture it needs only for its side effect, such as a temporary folder. |

**Off for now**

| Rule | What Pylint complains about | Why it is off for now |
|---|---|---|
| `missing-function-docstring`, `missing-module-docstring`, `missing-class-docstring` | A function, module or class has no docstring. | Each test should get a one-line docstring that says what it protects, so whoever changes the code later can see the target. Many tests have none yet, and the suite is still being merged and trimmed, so writing them now would be wasted work. When the suite is settled, delete the line marked `TEMPORARY` in the `Makefile` and this table, and add the missing docstrings. |

---
## Run Black Tool Locally

This project uses the [Black](https://github.com/psf/black) tool for code formatting.
Black aims for consistency, generality, readability and reducing git diffs.
The coding style used can be viewed as a strict subset of PEP 8.

The root project file `pyproject.toml` defines the Black tool configuration.
In this project we are accept a line length of 120 characters.
We also exclude the `tests/` files from black formatting.

Follow these steps to format your code with Black locally:

- Perform the [setup of python venv](#set-up-python-environment).

### Run Black

Run Black on all files that are currently tracked by Git in the project.
```shell
black $(git ls-files '*.py')
```

To run Black on a specific file, follow the pattern `black <path_to_file>/<name_of_file>.py`.

Example:
```shell
black ./src/living_doc_utilities/inputs/action_inputs.py 
``` 

### Expected Output

This is an example of the expected console output after running the tool:
```
All done! ✨ 🍰 ✨
1 file reformatted.
```

---

## Run mypy Tool Locally

This project uses the [mypy](https://mypy.readthedocs.io/en/stable/) 
tool which is a static type checker for Python.

> Type checkers help ensure that you’re using variables and functions in your code correctly.
> With mypy, add type hints (PEP 484) to your Python programs, 
> and mypy will warn you when you use those types incorrectly.

The my[py] configuration is in the `pyproject.toml` file.
Follow these steps to run my[py] locally:

### Run my[py]

Run my[py] on all files in the project.
```shell
  mypy .
```

To run my[py] check on a specific file, follow the pattern `mypy <path_to_file>/<name_of_file>.py --check-untyped-defs`.

Example:
```shell
   mypy living_doc_utilities/github/decorators.py
``` 

### Expected Output

This is an example of the expected console output after running the tool:
```
Success: no issues found in 1 source file
```

---


## Run Unit Test

Unit tests are written using the Pytest framework. To run all the tests, use the following command:
```shell
pytest tests/
```

You can modify the directory to control the level of detail or granularity as per your needs.

To run a specific test, run the command following the pattern below:
```shell
pytest tests/github/test_decorators.py::test_safe_call_decorator_success
```

---
## Code Coverage

This project uses the [pytest-cov](https://pypi.org/project/pytest-cov/) plugin to generate test coverage reports.
The objective of the project is to achieve a minimum score of 80 %. We do exclude the `tests/` file from the coverage report.

To generate the coverage report, run the following command:
```shell
pytest --cov=. tests/ --cov-fail-under=80 --cov-report=html
```

See the coverage report on the path:

```shell
open htmlcov/index.html
```

---

## Dependencies and Extras

Where a dependency is declared depends on which modules import it:

| Declared in | For | Today |
|---|---|---|
| `pyproject.toml` `dependencies` | a module that has to import with no extra installed — `contracts`, `authoring`, `github.utils`, `inputs` | `pydantic`, `jsonschema` |
| `pyproject.toml` extra `github` | `github.rate_limiter`, `github.decorators` | `PyGithub`, `requests` |
| `pyproject.toml` extra `html` | calling `authoring.html_to_markdown` or `authoring.url_policy.sanitize_html_fragment` (the `nh3` import is inside the function) | `nh3` |
| `requirements.txt` | the runtime of this repository's own CI tooling | `pydantic`, `jsonschema`, and `PyYAML` (only for `make docs` and the tests, not a package dependency), pinned |
| `requirements-dev.txt` | everything else `make qa` and CI need, plus the libraries behind the extras so the tests can import them | pinned |

When you add a third-party import:

- Declare it in `pyproject.toml` (in the core list only if a no-extra module needs it, otherwise in the extra it belongs to) and pin it in `requirements-dev.txt`.
- Run `make deptry` — it fails on an undeclared import (DEP001) and on a development-only tool imported by the library (DEP004). The one accepted DEP004 is `yaml`: `authoring/docs_export.py` is a repository script and imports PyYAML inside `_load_cases()`, so it is ignored per rule in `pyproject.toml`. deptry treats an extra as declared for the whole package, so it cannot tell that a no-extra module imported a `github`-extra library.
- Run `make import-matrix` (on Windows `scripts\import_matrix.bat`, which needs no POSIX shell; set `PYTHON` to choose the interpreter) — it builds the wheel and imports every module in three clean environments, so a no-extra module that reaches for PyGithub, `requests`, or `nh3` fails here.

`requirements-dev.txt` and the `[dependency-groups] dev` list in `pyproject.toml` name the same
tools: the pinned versions live in the requirements file, and deptry reads the group's names to
classify a development-only import. Add a new development tool to both.

---

## Regenerate Contract Schemas

The JSON Schemas under `living_doc_utilities/contracts/schemas/` are generated from the
pydantic models in `living_doc_utilities/contracts/` — see [Documentation contracts](docs/contracts.md)
for the rules they implement. The models are the source of truth; a model change without a
regenerated schema is a bug, not a style choice.

Follow these steps whenever a contract model changes:

- Perform the [setup of python venv](#set-up-python-environment).

### Run the schema export

```shell
make schemas
```

This runs `python -m living_doc_utilities.contracts.schema_export`, which overwrites all
six `*-schema.json` files in place, always with LF line endings whatever the OS. Commit the result alongside the model change.

A CI job (`Schema Regeneration Check`) runs the same command and fails the build if the
regenerated files differ from what is committed, so a forgotten regeneration is caught
before review rather than downstream.

---

## Regenerate Authoring Docs

[`docs/authoring.md`](docs/authoring.md)'s "Worked examples" table is generated from
`living_doc_utilities/authoring/normalisation_cases.yaml` — the same file
`tests/authoring/test_normalize_cases.py` runs every row of — so the table a reader sees can
never drift from what the test suite actually proves. The rest of the document is hand-maintained
prose; only the table between its `<!-- BEGIN GENERATED -->` / `<!-- END GENERATED -->` markers is
overwritten.

Follow these steps whenever `normalisation_cases.yaml` changes:

- Perform the [setup of python venv](#set-up-python-environment).

### Run the docs export

```shell
make docs
```

This runs `python -m living_doc_utilities.authoring.docs_export`, which rewrites the generated
table in place, always with LF line endings whatever the OS. Commit the result alongside the cases-file change.

A CI job (`Authoring Docs Regeneration Check`) runs the same command and fails the build if the
regenerated table differs from what is committed, so a forgotten regeneration is caught before
review rather than downstream.

---

## How to Release

Releasing is a **two-stage GitHub Actions pipeline**. No local tagging or manual PyPI upload is
required.

| Stage | Workflow | Trigger | What it does |
|---|---|---|---|
| 1 | **Draft Release** (`release_draft.yml`) | Manual dispatch | Quality gate, tag, draft GitHub release with generated notes. Nothing irreversible. |
| 2 | **Release - Build & Publish** (`release.yml`) | You publish the draft release | Builds the package from the tag and uploads it to PyPI. |

Publishing the draft release is the human approval gate for the PyPI upload — until you click
**"Publish release"**, nothing has been pushed to PyPI and the tag/draft can still be deleted.

### 🔁 Steps to Release

1. Update the version in `pyproject.toml`:

```toml
version = "0.1.1"
```

2. Land the version bump on `master` through a pull request (run `make qa` first).

```bash
git commit -am "Release v0.1.1"
git push origin <your-branch>
```

3. **Stage 1 — draft the release.** Go to your repository **→ Actions → "Draft Release" →
   Run workflow** and fill in the inputs:
     - `tag-name`: `v0.1.1` ← must match the version in `pyproject.toml` exactly; the
       workflow fails fast if it does not.
     - `from-tag-name` (optional): a previous tag like `v0.1.0`. Used to scope changelog
       entries to changes since that tag. If omitted, the most recent existing tag is used.

   This workflow will:
   - Verify `tag-name` matches the `pyproject.toml` version
   - Run the full quality gate (`make qa`)
   - Validate the version tag format
   - Generate structured release notes
   - Create and push the Git tag on the current `master` commit
   - Create a **draft** GitHub release using the generated changelog

4. **Review the draft release.** Go to **Releases**, open the draft for `v0.1.1`, and make any
   final edits to the notes.

5. **Stage 2 — publish.** Click **"Publish release"**. This fires `release.yml`, which:
   - Checks out the released tag and re-verifies it against `pyproject.toml`
   - Builds the Python package
   - Uploads it to PyPI
   - Generates the Aqua security manifest

   If you need to abort before this point, delete the draft release and the `v0.1.1` tag.
