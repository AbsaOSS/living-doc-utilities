# docs

Parent: ../CONTEXT.md

## Purpose

The code maps of the three hub pages, `api.md`, `contracts.md` and `authoring.md`, and of the leaf page `check.md`: for each fact a page states, where the code realises it. The pages carry no anchor; the maps of the pages below them sit in [contracts/CONTEXT.md](contracts/CONTEXT.md) and [authoring/CONTEXT.md](authoring/CONTEXT.md).

## Code map

### API

What realises each fact of [api.md](api.md):

- A test keeps the module table complete → `tests/docs/test_anchors.py::test_api_page_lists_every_module`
- The extras are declared in `pyproject.toml` → `pyproject.toml::optional-dependencies`
- Extras combine in one install, e.g. `living-doc-utilities[github,html]` → `pyproject.toml::optional-dependencies`
- Importing a module never needs the `html` extra; calling `convert_html_to_markdown()` or `sanitize_html_fragment()` does → `tests/authoring/test_isolation.py::test_nh3_is_imported_only_inside_a_function_that_needs_it`
- A clean install of the wheel with each extra proves which module imports where → `Makefile::import-matrix`
- `get_action_input(name, default="")` reads `INPUT_<NAME>`, with hyphens as underscores → `github/utils.py::get_action_input`
- `set_action_output(name, value)` appends one `name=value` line, LF-terminated, to the file `$GITHUB_OUTPUT` names → `github/utils.py::set_action_output`
- `set_action_output` raises `KeyError` when `GITHUB_OUTPUT` is unset, and `OSError` when the file cannot be written → `github/utils.py::set_action_output`
- `GithubRateLimiter(client)` wraps a call; with fewer than 5 calls left it sleeps until the reset time plus 5 seconds → `github/rate_limiter.py::GithubRateLimiter`
- `safe_call_decorator(rate_limiter)` rate-limits a call, logs any failure with its traceback, and re-raises it, as R13 requires → `github/decorators.py::safe_call_decorator`
- `debug_log_decorator` logs a call's arguments and result at debug level → `github/decorators.py::debug_log_decorator`
- In 0.5.0 the decorators moved from `living_doc_utilities.decorators`, which no longer exists → `github/decorators.py::safe_call_decorator`
- `BaseActionInputs` is the base class of a GitHub Action's inputs; a subclass implements `_validate()` and `_print_effective_configuration()` → `inputs/action_inputs.py::BaseActionInputs`
- `validate_user_configuration()` returns true when `_validate()` reports no errors → `inputs/action_inputs.py::BaseActionInputs.validate_user_configuration`
- `get_github_token()` reads the `GITHUB_TOKEN` input → `inputs/action_inputs.py::BaseActionInputs.get_github_token`
- `setup_logging()` logs to stdout at `DEBUG` when `INPUT_VERBOSE_LOGGING=true` or `RUNNER_DEBUG=1`, else at `INFO` → `logging_config.py::setup_logging`
- Shared constant: the `GITHUB_TOKEN` input name → `constants.py::GITHUB_TOKEN`
- The version lives in `pyproject.toml` → `pyproject.toml::version`
- A release candidate is published as `X.Y.ZrcN`, which PyPI holds as a pre-release → [Release candidate](../DEVELOPER.md#release-candidate)

### Documentation contracts

What realises each fact of [contracts.md](contracts.md):

- `doc-entities-v1.0.0`, issue-tracker collector output → `contracts/doc_entities.py::CONTRACT_ID`
- `doc-source-v1.0.0`, source-scanning collector output → `contracts/doc_source.py::CONTRACT_ID`
- `ui-tests-v1.0.0`, source-scanning collector output → `contracts/ui_tests.py::CONTRACT_ID`
- `generator-ready-v1.0.0`, transform output → `contracts/generator_ready.py::CONTRACT_ID`
- `coverage-matrix-v1.0.0`, transform output → `contracts/coverage_matrix.py::CONTRACT_ID`
- `ui-test-catalog-v1.0.0`, transform output → `contracts/ui_test_catalog.py::CONTRACT_ID`
- R1: a schema declares its dialect → `contracts/schema_export.py::SCHEMA_DIALECT`
- R2: a schema identifies itself with `$id` → `contracts/schema_export.py::ID_TEMPLATE`
- R3: no `$schema_version` key → `tests/contracts/test_schema_export.py::test_no_schema_version_dollar_key_anywhere_in_the_package`
- R4: a file declares its contract in `schema_version` → `contracts/doc_entities.py::DocEntitiesResult`
- R5: consumers check an input in a fixed order → `contracts/compat.py::check_input`
- R6: every file carries `schema_version` and the metadata envelope → `contracts/envelope.py::Metadata`
- R7: transform provenance in `metadata.source_inputs[]` → `contracts/envelope.py::SourceInputEntry`
- R8: legacy provenance shapes are retired outright → `contracts/common.py::ContractModel`
- R9: records are closed; maps are typed and keyed → `contracts/schema_export.py::find_schema_violations`
- R10: validators are selected from the schema → `contracts/validation.py::validate`
- R11: every file carries its own stats → `contracts/stats.py::compute_stats`
- R11: a transform proves it lost nothing → `contracts/lineage.py::check_field_loss`
- R12: no component mirrors a contract; each proves it carries every field → `contracts/testing.py::full_sample`
- R13: a collector collects everything it was configured for, or fails → `github/decorators.py::safe_call_decorator`
- Each contract declares its record roots in its own module → `contracts/registry.py::CONTRACTS`
- Entity identity: `entity_id` joins, `source_ref` only points back → `contracts/common.py::EntityCore`
- State and `state_origin`: a Feature's state is always derived → `contracts/doc_entities.py::Entity._check_state_origin`
- Version format: no leading `v` in a stored version → `contracts/common.py::VERSION_PATTERN`
- Fields prepared for Azure DevOps → `contracts/common.py::SourceRef`
- The metadata envelope is one model for all six contracts → `contracts/envelope.py::Metadata`
- One read path and one write path → `contracts/io.py::write_artifact`
- Project id → `contracts/envelope.py::PROJECT_ID_PATTERN`
- Rendering rules: the view filter selects records, the generator presents → `contracts/testing.py::shown_paths`
- Coverage is computed per aspect and backed by evidence → `contracts/coverage_matrix.py::AcCoverage`
- Every entity and the whole matrix carry a coverage summary computed from the rows → `contracts/coverage_matrix.py::CoverageSummary`
- Errors and warnings: one registry, one page → `contracts/codes.py::ALL_CODES`

### Authoring

What realises each fact of [authoring.md](authoring.md):

- Every parser normalises a document's fields first and extracts them second, never the reverse → `authoring/normalize.py::normalize`
- The issue-body parser derives the entity id from the (normalised) title before the body is normalised, and a title with no id skips body normalisation entirely → `authoring/issue_body.py::parse_issue_body`
- The feature-header and PageObject parsers find the header first → `authoring/framing.py::names_an_entity`
- Where a section begins and ends is decided once, by position, before any rule rewrites a line or any parser reads one → `authoring/framing.py::Frame`
- Normalisation never validates meaning; only `ac_grammar.py` knows the state vocabulary and the strict version shape → `tests/authoring/test_isolation.py::test_no_module_other_than_ac_grammar_validates_ac_state_or_version`
- The parsers share one grammar instead of reimplementing it → `tests/authoring/test_normalize_first.py::test_feature_header_issue_body_and_scenario_import_ac_grammar`
- One helper decides where a fenced code block starts and ends → `authoring/normalize.py::compute_fence_flags`
- Parsers report, never raise or log → `authoring/issue_body.py::parse_issue_body`
- A warning is a `ContractWarning`, and its code is defined once → `contracts/envelope.py::ContractWarning`
- `authoring` stays source-agnostic: no GitHub- or Azure-DevOps-specific import → `tests/authoring/test_isolation.py::test_authoring_imports_nothing_github_or_azure_devops_specific`
- `contracts` never imports `authoring`; the dependency runs one way → `tests/authoring/test_isolation.py::test_contracts_imports_nothing_from_authoring`
- Status and relations are settled once per run, over every parsed entity → `authoring/status.py::derive_statuses`
- One URL policy serves every consumer → `authoring/url_policy.py::safe_href`
- The parsers never report a missing required key; one table serves the check that does → `authoring/required_keys.py::REQUIRED_KEYS`

### Check

What realises each fact of [check.md](check.md):

- The caller gives every authored file with its path, entity type and text, and the changed paths → `check/engine.py::AuthoredFile`
- The entity type picks the parser: a `.feature` header and scenarios, or a PageObject → `check/engine.py::_parse`
- Only the changed files' own findings are reported → `tests/check/test_engine.py::test_per_file_findings_of_an_unchanged_file_are_not_reported`
- Every relation finding of the corpus is reported, on the title line of the entity's file → `tests/check/test_engine.py::test_a_deleted_file_is_reported_on_the_unchanged_file_whose_relation_it_breaks`
- A cross-reference page whose `parent-feat:` names no Feature gets `UNRESOLVED_RELATION`, as the collector reports it → `check/engine.py::_unattached_page`
- `FEATURE_WITHOUT_FUNCTIONALITY` is a relation finding; `MISSING_STATUS` and `STATUS_AC_MISMATCH` are per file → `check/engine.py::check`
- A finding with no line sits on the title line and shows its context → `check/engine.py::_finding`
- A changed path that is not a file, or a path given twice, raises `ValueError` → `check/engine.py::check`
- One line per finding, a line break escaped → `check/report.py::format_line`
- Every code of the default fail list has a fix hint → `tests/check/test_hints.py::test_every_default_fail_code_has_a_fix_hint_and_nothing_else_does`
- The findings fail when a code is in the fail list → `check/report.py::fails`
- The GitHub Actions report: the shielded lines, the summary annotation, one annotation per finding → `check/report.py::github_report`
- In Actions the caller prints the GitHub report as it is, and no finding line outside it → collectors
- At most 10 annotations of a level per step; the summary takes one → `check/report.py::_ANNOTATIONS_PER_LEVEL`
- The job summary lists every finding → `check/report.py::job_summary`
- The policy file's name → `policy.py::POLICY_FILE`
- Without a file, or with `check:` or `warn:` empty, every default code fails; `check.warn` relaxes codes of the default list only → `policy.py::CheckPolicy`
- An unknown key under `check` fails; another top-level section is ignored → `policy.py::Policy`
- The default fail list is every code the authoring layer raises, and `MISSING_REQUIRED_KEY` → `tests/test_policy.py::test_the_default_fail_list_is_every_code_the_authoring_layer_raises`
- The check never raises `UNKNOWN_SECTION` or `HTML_CONTENT_DROPPED`: it runs no issue-body parser → `check/engine.py::_parse`
- One table holds every header's required keys → `authoring/required_keys.py::REQUIRED_KEYS`
- A missing key is `MISSING_REQUIRED_KEY` on the title line → `authoring/required_keys.py::missing_required_keys`
- The example runs → `tests/docs/test_examples.py::test_python_example_runs`
