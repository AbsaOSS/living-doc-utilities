# Living Documentation Utilities: developer guide

## Purpose

Anyone who changes this repository reads this page. It covers setup, the quality gates, the generated files, the
release, and the rules for writing documentation.

Read before: [README](README.md)

## Contents

- [Setup](#setup)
- [Gates](#gates)
- [Rules switched off for tests](#rules-switched-off-for-tests)
- [Dependencies](#dependencies)
- [Regenerate](#regenerate)
- [Release](#release)
- [Writing documentation](#writing-documentation)

## Setup

1. Use Python 3.10 or later: `python3 --version`.
2. Create and activate a virtual environment: `python3 -m venv .venv`, then `source .venv/bin/activate`.
3. Run `make install`: `pip install -r requirements-dev.txt`, then `pip install -e . --no-deps` → `Makefile::install`

- The editable install of the package itself is required → `contracts/compat.py::installed_utilities_version`
  - Why: that function reads this package's own version from its installed metadata.
- `requirements.txt` holds only the runtime of this repository's CI tooling: `make schemas`, `make docs`, `make no-vendored-schemas`.
- `requirements-dev.txt` includes it and adds the test, lint, type and packaging tools.
- Neither file is the package's install-time dependency list; that is `pyproject.toml` → [Dependencies](#dependencies)
- To develop the library alongside another project, run `pip install -e ../living-doc-utilities` in that project's environment.

## Gates

`make qa` runs `format-check`, `lint`, `types`, `deptry`, `coverage` and `no-vendored-schemas`, and stops at the
first failure → `Makefile::qa`. Run it before opening a pull request.

| Target | Runs | Gate | One file |
|---|---|---|---|
| `make lint` | ruff, then Pylint over tracked files outside `tests/`, and over `tests/` with the [rules for tests](#rules-switched-off-for-tests) off | each Pylint run scores ≥ 9.5 / 10 | `pylint path/to/module.py`; a test file also needs `--disable=` with the list in `PYLINT_TESTS_DISABLE` |
| `make format` | ruff autofix, then Black, rewriting files | line length 120 | `black path/to/module.py` |
| `make format-check` | Black in check mode | clean | `black --check path/to/module.py` |
| `make types` | mypy | clean | `mypy path/to/module.py` |
| `make deptry` | deptry over the package | no undeclared import (DEP001), no dev tool in the library (DEP004) | not scoped |
| `make test` | pytest over `tests/` | pass | `pytest tests/github/test_decorators.py::test_safe_call_decorator_success` |
| `make coverage` | pytest with coverage | ≥ 80 % | `pytest --cov=. --cov-report=html tests/`, then open `htmlcov/index.html` |
| `make no-vendored-schemas` | the vendored-schema check, allowing `living_doc_utilities/contracts/schemas` | no tracked schema file elsewhere, except under `tests/` | not scoped |
| `make import-matrix` | builds the wheel and imports every module in three clean environments: no extra, `github`, `html` | every module imports with only its extras; `pip check` clean | not scoped |

- Pylint and Black take their files from `git ls-files`, so a new file is checked once it is tracked → `Makefile::PY_FILES`
- Black skips `tests/`; Black, Pylint and mypy read their settings from `pyproject.toml` → `pyproject.toml::force-exclude`
- `make import-matrix` is not part of `make qa`; CI runs it as its own job, and it needs a POSIX shell (Linux, macOS, WSL) → `Makefile::import-matrix`
- The documentation checks are pytest tests, so `make test` and `make coverage` run them → [Checks](#checks)

## Rules switched off for tests

`make lint` checks `tests/` with fewer Pylint rules → `Makefile::PYLINT_TESTS_DISABLE`. Change that list and this
table together; every other rule stays on for tests.

| Rule | What Pylint complains about | Why it is off for tests |
|---|---|---|
| `use-implicit-booleaness-not-comparison` | `assert result == []`; it wants `assert not result` | a test should also fail on `None` or `{}`, which `assert not result` accepts |
| `redefined-outer-name` | an argument has the same name as something defined above | this is how a test asks for a pytest fixture |
| `protected-access` | code uses a `_`-prefixed name | some tests check a private helper or constant on purpose |
| `unsupported-membership-test`, `unsubscriptable-object` | `"x" in Model.model_fields`, `Model.model_fields["x"]` | a false alarm: Pylint misreads how pydantic builds classes |
| `unidiomatic-typecheck` | `type(x) is Foo`; it wants `isinstance` | a test sometimes needs the exact type, not a subclass |
| `unused-argument` | an argument is never used | pytest passes `parametrize` values and side-effect fixtures a test may not read |

## Dependencies

| Declared in | For | Today |
|---|---|---|
| `pyproject.toml` `dependencies` | modules that import with no extra ([Extras](docs/api.md#extras)) | `pydantic`, `jsonschema` |
| `pyproject.toml` extra `github` | `github.rate_limiter`, `github.decorators` | `PyGithub`, `requests` |
| `pyproject.toml` extra `html` | calling the HTML sanitiser; `nh3` is imported inside the function | `nh3` |
| `requirements.txt` | this repository's CI tooling | `pydantic`, `jsonschema`, `PyYAML` (for `make docs` and the tests only), pinned |
| `requirements-dev.txt` | everything else `make qa` and CI need, plus the extras' libraries for the tests | pinned |

To add a third-party import:

1. Declare it in `pyproject.toml`: in the core list only if a no-extra module needs it, else in its extra.
2. Pin it in `requirements-dev.txt`.
3. Run `make deptry`; it fails on an undeclared import or a dev tool imported by the library.
4. Run `make import-matrix`; it fails when a no-extra module reaches for PyGithub, `requests` or `nh3`.

- deptry treats an extra as declared for the whole package, so only the import matrix catches a wrong extra.
- The one accepted DEP004 is `yaml`, imported inside `_load_cases()` of a repository script → `authoring/docs_export.py::_load_cases`
- A new development tool goes into both `requirements-dev.txt` (pinned) and `[dependency-groups] dev` → `pyproject.toml::dependency-groups`
  - Why: deptry reads the group's names to classify a development-only import.

## Regenerate

Two files are generated and committed; CI regenerates each and fails on any difference.

| Command | Rewrites | From | CI job |
|---|---|---|---|
| `make schemas` | the six `living_doc_utilities/contracts/schemas/*-schema.json` | the pydantic contract models | `.github/workflows/test.yml::schema-regeneration-check` |
| `make docs` | the worked-examples table in [Normalisation](docs/authoring/normalisation.md#worked-examples), between its markers | `living_doc_utilities/authoring/normalisation_cases.yaml` | `.github/workflows/test.yml::docs-regeneration-check` |

- Run the command after changing its source, and commit the result in the same change.
- A model change without a regenerated schema is a bug, not a style choice → [Schema rules](docs/contracts/schema-rules.md#generated-schemas)
- Both write LF line endings on every OS → `authoring/docs_export.py::main`

## Release

Releasing is a two-stage GitHub Actions pipeline; no local tag or manual upload is needed.

1. Set `version` in `pyproject.toml` ([Versioning](docs/api.md#versioning)) and the pin in `README.md`; merge it through a pull request after `make qa`.
2. Actions → **Draft Release** → Run workflow, with `tag-name` `v<version>` and, optionally, `from-tag-name` → `.github/workflows/release_draft.yml::tag-name`
3. The workflow checks the tag against `pyproject.toml`, runs `make qa`, tags `master`, and creates a draft release with notes.
4. Review and edit the draft under **Releases**.
5. Click **Publish release** → `.github/workflows/release.yml::build-and-publish`
6. `release.yml` re-checks the tag, builds, uploads to PyPI, attaches the six schema files, and writes the Aqua manifest.

- Publishing the draft is the approval gate for the PyPI upload.
- To abort before step 5, delete the draft release and its tag.
- `from-tag-name` scopes the release notes; without it, the latest tag is used.

## Writing documentation

> **Provisional.** These rules are a pilot; the owner tunes them after this first rebuild, and a skill may replace
> this section. This section is their only copy in the repository.

### Depth

Depth is where a page sits in the folder tree. Deeper means more detail.

| Depth | Pages | Rule |
|---|---|---|
| 1 | `README.md`; `DEVELOPER.md` and `CONTRIBUTING.md` | `README.md` is the entry: overview, usage tip, "where next". The other two are solo: one page each, no child pages |
| 2 | `docs/<topic>.md` | a hub: principle, decision list, routing to depth 3; it names and links facts, and defines none |
| 2 leaf | `docs/<topic>.md` with no `docs/<topic>/` folder | a leaf may define, like a depth-3 page |
| 3 | `docs/<topic>/<page>.md` | detail: fact lists, option lists, examples |

- One fact, one page: define a fact on the deepest page that needs it; shallower pages name it and link.

### Every page

1. `# Title`.
2. `## Purpose`: 1 to 3 sentences, who reads the page and what they get; then `Read before:` and `Next:` links where the page sits on a reading path.
3. `## Contents`: links to every other `##` chapter of the page, and nothing else.
4. Only the parts the page needs.

A one-line redirect stub is exempt.

### Parts

| Part | Form | Checked against |
|---|---|---|
| Principle | at most 5 short sentences: the core idea | review |
| Decision list | one line per decision: `decision → path::symbol` where the code realises it | code |
| Fact list | one line per fact the code relies on: `fact → path::symbol`, or a test | code |
| Why | one indented `Why:` line under a rule, decision or fact, at most 20 words | review |
| Option list | every available option with a one-line meaning; complete | the enum, extra, flag or code list in code |
| Example | at most 20 lines; run by a test or generated | tests, generators |
| Prose | only in Purpose, Principle and one-line list lead-ins; a block is at most 4 lines | review |
| Language | sentences of at most 20 words; active voice; one term per idea, the glossary's | review |

### Limits

- The limits (prose block 4 lines, sentence 20 words, example 20 lines) are targets, not hard caps.
- Exceed one only with a reason, stated next to the block: `<!-- over limit: <reason> -->`.
- Keep the overrun small; split the block when you can.

### Anchors

- `path` is relative to the repository root; `living_doc_utilities/` may be left out: `contracts/io.py::read_artifact`.
- `symbol` is a module-level name, or a dotted one for a member: `Entity._check_state_origin`.
- A test is `tests/<path>.py::test_name`; a non-Python file names a text it contains: `Makefile::qa`.
- Never use line numbers; they drift.
- A fact realised outside this repository names the component instead of an anchor: `→ collectors`, `→ toolkit`.

### Examples

- A test runs every `python` block of a page, each in a fresh namespace and a temporary directory.
- A `json` block must parse; with `<!-- example: path::Model -->` right above it, it must also validate as that model.
- Write each example self-contained: it builds its own input, and an `assert` states what it shows.
- A `shell` block is a command line, not an example; it is not run.

### Checks

| Check | Where |
|---|---|
| page list, `Purpose` then `Contents`, Contents links, no orphan page | `tests/docs/test_page_structure.py` |
| every `path::symbol` resolves; no line-number anchor; `docs/api.md` lists every module | `tests/docs/test_anchors.py` |
| every example runs or validates | `tests/docs/test_examples.py` |
| the error page lists exactly `ALL_CODES`, kind and emitter included | `tests/contracts/test_codes.py::test_error_page_lists_exactly_the_registered_codes` |
| links and `#fragments` resolve | `.github/workflows/link-check.yml::lychee` |
| the generated table is current | `.github/workflows/test.yml::docs-regeneration-check` |

To add a page: put it at its depth, add it to `tests/docs/pages.py::APPROVED_PAGES`, and link it from its hub.
