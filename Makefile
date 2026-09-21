# Quality-gate command vocabulary for living-doc-utilities.
#
# These targets are the single source of truth for local and CI checks -
# .github/workflows/test.yml calls the same targets so the
# two never drift. Run `make qa` before opening a pull request.

PYTHON      ?= python3
PIP         ?= $(PYTHON) -m pip
PY_FILES     = $(shell git ls-files '*.py')
PYLINT_MIN  ?= 9.5
COV_MIN     ?= 80

# Off for tests/ only: they flag deliberate test idioms (fixture names, white-box reads, exact asserts) and misread pydantic's model_fields.
PYLINT_TESTS_DISABLE = use-implicit-booleaness-not-comparison,redefined-outer-name,protected-access,unsupported-membership-test,unsubscriptable-object,unidiomatic-typecheck,unused-argument
# TEMPORARY: docstring checks stay off for tests while the suite is being merged and trimmed. Delete this line to enforce them.
PYLINT_TESTS_DISABLE := $(PYLINT_TESTS_DISABLE),missing-function-docstring,missing-module-docstring,missing-class-docstring

.DEFAULT_GOAL := help
.PHONY: help install qa lint format format-check types deptry test coverage test-unit test-integration schemas docs no-vendored-schemas import-matrix

help: ## Show this help.
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Install runtime and development dependencies.
	$(PIP) install -r requirements-dev.txt
	$(PIP) install -e . --no-deps

qa: format-check lint types deptry coverage no-vendored-schemas ## Run the full quality gate (format, lint, types, undeclared imports, tests + coverage).

format: ## Reformat all tracked Python files (ruff autofix + Black).
	ruff check --fix $(PY_FILES)
	black $(PY_FILES)

format-check: ## Check Black formatting without modifying files.
	black --check $(PY_FILES)

lint: ## Run ruff, then Pylint over the package and over tests/ (each enforces the minimum score).
	ruff check $(PY_FILES)
	pylint --fail-under=$(PYLINT_MIN) living_doc_utilities
	pylint --fail-under=$(PYLINT_MIN) --disable=$(PYLINT_TESTS_DISABLE) tests

types: ## Run the mypy static type checker.
	mypy .

deptry: ## Fail on an import that is used but not declared (DEP001) or a dev-only tool imported by the library (DEP004).
	deptry .

test: ## Run the unit test suite (integration tests excluded).
	pytest --ignore=tests/integration -v tests/

coverage: ## Run the unit test suite with the coverage gate.
	pytest --ignore=tests/integration --cov=. -v tests/ --cov-fail-under=$(COV_MIN)

test-unit: ## Run only unit tests (fast local loop, no cross-module chaining).
	pytest -m "not integration" -v tests/

test-integration: ## Run only integration tests (cross-authoring-module, still synthetic/fast - no separate CI lane).
	pytest -m integration -v tests/

schemas: ## Regenerate the contract JSON Schemas from the pydantic models (docs/contracts.md).
	$(PYTHON) -m living_doc_utilities.contracts.schema_export

no-vendored-schemas: ## R12 check 1: fail on any committed schema file outside tests/ and this package's own schemas dir.
	$(PYTHON) -m living_doc_utilities.contracts.check_no_vendored_schemas --allow living_doc_utilities/contracts/schemas

docs: ## Regenerate docs/authoring.md's worked-examples table from normalisation_cases.yaml.
	$(PYTHON) -m living_doc_utilities.authoring.docs_export

import-matrix: ## Build the wheel and prove in three clean venvs (no extra / github / html) which modules import and which need an extra.
	PYTHON=$(PYTHON) scripts/import_matrix.sh
