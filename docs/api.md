# API

## Purpose

Consumers of the library read this page. It lists every module, what it does and which extra it needs, and it
defines how to pin the package.

Read before: [README](../README.md)

## Contents

- [Modules](#modules)
- [Extras](#extras)
- [Contract models](#contract-models)
- [GitHub helpers](#github-helpers)
- [Action inputs and logging](#action-inputs-and-logging)
- [Versioning](#versioning)

## Modules

Import from the module, e.g. `from living_doc_utilities.contracts.io import read_artifact`. A test keeps this
table complete → `tests/docs/test_anchors.py::test_api_page_lists_every_module`.

| Module | Purpose | Extra |
|---|---|---|
| `contracts.common` | the closed base model, `AcceptanceCriterion`, `EntityCore`, `SourceRef`, shared patterns | none |
| `contracts.envelope` | the metadata envelope: `Metadata`, `Producer`, `Run`, `Source`, `Stats`, `ContractWarning` | none |
| `contracts.doc_entities` | the `doc-entities` result model, `Entity`, `PageRef` | none |
| `contracts.doc_source` | the `doc-source` result model | none |
| `contracts.ui_tests` | the `ui-tests` result model, `Scenario`, `AcLink` | none |
| `contracts.generator_ready` | the `generator-ready` result model | none |
| `contracts.coverage_matrix` | the `coverage-matrix` result model | none |
| `contracts.ui_test_catalog` | the `ui-test-catalog` result model | none |
| `contracts.registry` | the one table of all six contracts: `CONTRACTS`, `record_roots()` | none |
| `contracts.schema_export` | generates the schemas; `load_schema(contract_id)` reads a bundled one | none |
| `contracts.codes` | `ALL_CODES`, `Code`, `ContractError` | none |
| `contracts.validation` | structural validation, validator picked from the schema | none |
| `contracts.compat` | the R5 input check, `installed_utilities_version()` | none |
| `contracts.io` | `read_artifact()`, `write_artifact()` | none |
| `contracts.stats` | `compute_stats()` for `metadata.stats` | none |
| `contracts.lineage` | `LineageTable`, `Dropped`, `assert_complete()`, `check_field_loss()` | none |
| `contracts.testing` | `full_sample()`, `shown_paths()` for component tests | none |
| `contracts.check_no_vendored_schemas` | the vendored-schema check, runnable with `python -m` | none |
| `authoring.normalize` | `normalize()`, `SourceFormat` | none |
| `authoring.ac_grammar` | `parse_acceptance_criteria()`, `is_valid_ac_id()` | none |
| `authoring.issue_body` | `parse_issue_body()`, `ParsedEntity` | none |
| `authoring.feature_header` | `parse_feature_header()` | none |
| `authoring.page_object` | `parse_page_object()`, `PageObjectResult` | none |
| `authoring.scenario` | `parse_scenarios()`, `ParsedScenario` | none |
| `authoring.identity` | `derive_entity_id()`, `extract_living_doc_title()` | none |
| `authoring.status` | `derive_statuses()` | none |
| `authoring.relations` | `check_relations()` | none |
| `authoring.url_policy` | `safe_href()`, `sanitize_html_fragment()` | `html`, to call `sanitize_html_fragment()` |
| `authoring.html_to_markdown` | `convert_html_to_markdown()` | `html`, to call it |
| `authoring.docs_export` | regenerates this repository's worked-examples table; not for consumers | none; needs PyYAML, a dev tool |
| `github.utils` | `get_action_input()`, `set_action_output()` | none |
| `github.rate_limiter` | `GithubRateLimiter` | `github` |
| `github.decorators` | `safe_call_decorator()`, `debug_log_decorator()` | `github` |
| `inputs.action_inputs` | `BaseActionInputs` | none |
| `logging_config` | `setup_logging()` | none |
| `constants` | `GITHUB_TOKEN`, `OUTPUT_PATH` | none |

Where each part is defined: [contracts](contracts.md) and [authoring](authoring.md).

## Extras

| Install | Adds | Needed for |
|---|---|---|
| `living-doc-utilities==0.5.0` | `pydantic`, `jsonschema` | every module marked "none" above |
| `living-doc-utilities[github]==0.5.0` | `PyGithub`, `requests` | `github.rate_limiter`, `github.decorators` |
| `living-doc-utilities[html]==0.5.0` | `nh3` | calling `convert_html_to_markdown()` or `sanitize_html_fragment()` |

- The extras are declared in `pyproject.toml` → `pyproject.toml::optional-dependencies`
- Extras combine: `pip install "living-doc-utilities[github,html]==0.5.0"` → `pyproject.toml::optional-dependencies`
- Importing a module never needs the `html` extra; only calling the sanitiser does → `tests/authoring/test_isolation.py::test_nh3_is_imported_only_inside_a_function_that_needs_it`
- A clean install of the wheel with each extra proves which module imports where → `Makefile::import-matrix`

## Contract models

```python
from living_doc_utilities.contracts.doc_entities import DocEntitiesResult
from living_doc_utilities.contracts.schema_export import load_schema
from living_doc_utilities.contracts.testing import full_sample

data = full_sample("doc-entities-v1.0.0").model_dump(mode="json")
result = DocEntitiesResult.model_validate(data)
schema = load_schema("doc-entities-v1.0.0")  # bundled with the package, read via importlib.resources

assert schema["$id"].endswith("doc-entities-v1.0.0-schema.json")
```

Reading and writing a file: [Artifact rules](contracts/artifact-rules.md#reading-and-writing).

## GitHub helpers

- `get_action_input(name, default="")` reads `INPUT_<NAME>`, with hyphens as underscores → `github/utils.py::get_action_input`
- `set_action_output(name, value)` appends one `name=value` line, LF-terminated, to the file `$GITHUB_OUTPUT` names → `github/utils.py::set_action_output`
- `set_action_output` raises `KeyError` when `GITHUB_OUTPUT` is unset, and `OSError` when the file cannot be written → `github/utils.py::set_action_output`
- `GithubRateLimiter(client)` wraps a call; with fewer than 5 calls left it sleeps until the reset time plus 5 seconds → `github/rate_limiter.py::GithubRateLimiter`
- `safe_call_decorator(rate_limiter)` rate-limits a call, logs any failure with its traceback, and re-raises it, as [R13](contracts/pipeline-rules.md#r13-a-collector-collects-everything-it-was-configured-for-or-fails) requires → `github/decorators.py::safe_call_decorator`
- `debug_log_decorator` logs a call's arguments and result at debug level → `github/decorators.py::debug_log_decorator`
- In 0.5.0 the decorators moved from `living_doc_utilities.decorators`, which no longer exists → `github/decorators.py::safe_call_decorator`

```python
from github import Auth, Github  # needs the github extra

from living_doc_utilities.github.decorators import safe_call_decorator
from living_doc_utilities.github.rate_limiter import GithubRateLimiter
from living_doc_utilities.github.utils import get_action_input

token = get_action_input("github-token")  # reads INPUT_GITHUB_TOKEN


@safe_call_decorator(GithubRateLimiter(Github(auth=Auth.Token(token))))
def fetch_issue(repository, number):
    return repository.get_issue(number)
```

## Action inputs and logging

- `BaseActionInputs` is the base class of a GitHub Action's inputs; a subclass implements `_validate()` and `_print_effective_configuration()` → `inputs/action_inputs.py::BaseActionInputs`
- `validate_user_configuration()` returns true when `_validate()` reports no errors → `inputs/action_inputs.py::BaseActionInputs.validate_user_configuration`
- `get_github_token()` reads the `GITHUB_TOKEN` input → `inputs/action_inputs.py::BaseActionInputs.get_github_token`
- `setup_logging()` logs to stdout at `DEBUG` when `INPUT_VERBOSE_LOGGING=true` or `RUNNER_DEBUG=1`, else at `INFO` → `logging_config.py::setup_logging`
- Shared constants: the `GITHUB_TOKEN` input name and the `OUTPUT_PATH` default `./output` → `constants.py::OUTPUT_PATH`

## Versioning

The version lives in `pyproject.toml` → `pyproject.toml::version`. The rules for pinning and changing it:

- Pin exactly: `living-doc-utilities==0.5.0` plus your extras; no ranges, pre-releases or git-SHA pins.
- The version stays `0.x` until every component of the ecosystem reaches `1.0` together, as one release.
- A contract or public-API change bumps the minor version (`0.5.0` → `0.6.0`).
- A parser or helper fix bumps the patch version (`0.5.0` → `0.5.1`).
- Every component sits on the same minor version; a released contract change means every reader and writer re-pins.
- Fleet CI reports each component's pin: a warning between release gates, an error at every gate, milestone and release → living-doc CI
- Patch versions may differ between components.
  - Why: this is cheap, and it catches the skews that [R5 validation](contracts/artifact-rules.md#r5-consumers-check-an-input-in-a-fixed-order) cannot see.
- A contract change made between gates follows the documented contract-change process.
- The package version and the contract version are independent: a contract id stays `-v1.0.0`.
