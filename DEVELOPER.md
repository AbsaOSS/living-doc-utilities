# Living Documentation Utilities - for Developers

- [Project Setup](#project-setup)
- [Quality Gates (`make`)](#quality-gates-make)
- [Run Pylint Check Locally](#run-pylint-check-locally)
- [Run Black Tool Locally](#run-black-tool-locally)
- [Run mypy Tool Locally](#run-mypy-tool-locally)
- [Run Unit Test](#run-unit-test)
- [Code Coverage](#code-coverage)
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
pip install -r requirements.txt
```
---
## Quality Gates (`make`)

The root `Makefile` is the canonical command vocabulary shared across every `living-doc-*`
repo. Run the whole gate before opening a pull request:

```shell
make qa
```

`make qa` runs `format-check` → `lint` → `types` → `coverage` and fails on the first
failing gate. The individual targets are also available while iterating:

| Target | Runs | Gate |
|---|---|---|
| `make lint` | Pylint over all tracked `*.py` | score ≥ 9.5 / 10 |
| `make format` | Black, rewriting files in place | line length 120 |
| `make format-check` | Black in `--check` mode | line length 120 |
| `make types` | mypy | clean |
| `make test` | pytest, unit tests only | pass |
| `make coverage` | pytest with the coverage gate | `--cov-fail-under=80` |

The sections below explain each tool in more detail and how to scope it to a single file.

---
## Run Pylint Check Locally

This project uses the [Pylint](https://pypi.org/project/pylint/) tool for static code analysis.
Pylint analyses your code without actually running it.
It checks for errors, enforces coding standards, looks for code smells, etc.
We do exclude the `tests/` file from the Pylint check.

Pylint displays a global evaluation score for the code, rated out of a maximum score of 10.0.
We are aiming to keep our code quality high above the score 9.5.

Follow these steps to run Pylint check locally:

- Perform the [setup of python venv](#set-up-python-environment).

### Run Pylint

Run Pylint on all files that are currently tracked by Git in the project.
```shell
pylint $(git ls-files '*.py')
```

To run Pylint on a specific file, follow the pattern `pylint <path_to_file>/<name_of_file>.py`.

Example:
```shell
pylint src/living_doc_utilities/inputs/action_inputs.py
``` 

### Expected Output

This is an example of the expected console output after running the tool:
```bash
************* Module main
main.py:30:0: C0116: Missing function or method docstring (missing-function-docstring)

------------------------------------------------------------------
Your code has been rated at 9.41/10 (previous run: 8.82/10, +0.59)
```

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
   mypy living_doc_utilities/decorators.py
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
pytest tests/utils/test_utils.py::test_make_issue_key
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

## How to Release

All releases are handled entirely through GitHub Actions via a manual dispatch — no local tagging or manual PyPI upload is required.

### 🔁 Steps to Release

1. Update the version in `pyproject.toml`:

```toml
version = "0.1.1"
```

2. Commit the change (use IDE or command line):

```bash
git commit -am "Release v0.1.1"
git push origin main
```

3. Trigger the release workflow:
   - Go to your repository **→ Actions**
   - Select **"Release - Build & Publish"**
   - Click **"Run workflow"**
   - Fill in the inputs:
     - `tag-name`: `v0.1.1` ← this must match the version in pyproject.toml
     - `from-tag-name` (optional): a previous tag like `v0.1.0`
       - This is used to generate changelog entries **only for changes** since that tag. If omitted, the most recent existing tag will be used automatically.


4. The workflow will:
   - Validate the version tag format
   - Generate structured release notes
   - Create and push a Git tag for the current commit
   - Build the Python package
   - Upload the package to PyPI
   - Create a draft GitHub release using the generated changelog


5. Review and publish the draft release:
   - Go to your repository **→ Releases**
   - Click the newly created Draft release for v0.1.1
   - Make any final edits (if needed)
   - Click **“Publish release”** to make it public
