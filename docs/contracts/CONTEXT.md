# docs/contracts

Parent: ../CONTEXT.md

## Purpose

The code maps of the seven contract pages: for each fact a page states, where the code realises it.

## Code map

### Entities and state

What realises each fact of [entities-and-state.md](entities-and-state.md):

- `entity_id` is the authored id (`US-001`, `FEAT-001`, `FUNC-001`) and the only join key → `contracts/common.py::EntityCore`
- An item whose title has no parseable `entity_id` is not emitted → `contracts/envelope.py::Cardinality`
- `source_ref` is provenance only: `system`, `native_id`, `native_type`, `url`, `tracker_state`, `area_path`, `iteration_path` → `contracts/common.py::SourceRef`
- Cross-project identity is the pair (`metadata.source.project_id`, `entity_id`) → `contracts/envelope.py::Source`
- An `entity_id` is unique within a project; a repeat in one run is `DUPLICATE_ENTITY_ID`, never settled by precedence → `contracts/codes.py::Code`
- `source_ref.tracker_state` holds the tracker's own state and never decides the documented state → `contracts/common.py::SourceRef`
- An acceptance-criterion id is its entity's id, a hyphen and a sequence number (`US-001-01`) → `contracts/common.py::check_ac_ids_owned`
- An entity's and an acceptance criterion's `state` is one of four values, as the glossary defines them → `contracts/common.py::LifecycleState`
- Every entity also carries `state_origin` → `contracts/common.py::StateOrigin`
- The type decides the origin; any other pairing fails validation → `contracts/doc_entities.py::Entity._check_state_origin`
- A written Feature status is reported as `IGNORED_AUTHORED_KEY` and dropped → `authoring/issue_body.py::IGNORED_AUTHORED_KEYS`
- A Feature that exists but is not instrumented yet says so with `stub_reason`: a fact about the surface, not a status → `contracts/doc_entities.py::Entity._check_stub_reason_is_feature_only`
- A stored version has no leading `v`: `1.4.0`, never `v1.4.0` → `contracts/common.py::VERSION_PATTERN`
- The contract id is the one stored string with a `v`, as a literal part of the id: `doc-entities-v1.0.0` → `contracts/envelope.py::CONTRACT_ID_PATTERN`
- `source_ref.native_type`: work-item type → `contracts/common.py::SourceRef`
- `source_ref.area_path`, `source_ref.iteration_path`: Azure DevOps classification nodes → `contracts/common.py::SourceRef`
- `source_ref.native_id`, typed as a string: Azure DevOps ids and GitHub issue numbers in one field → `contracts/common.py::SourceRef`
- `metadata.source.organizations[]`: Azure DevOps organisations → `contracts/envelope.py::Source`
- `metadata.source.repositories[]`: `org/project` entries → `contracts/envelope.py::Source`
- `metadata.source.systems` accepting `AzureDevOps`: mixed-system pipelines → `contracts/envelope.py::Source`
- `metadata.source.extraction_mode`: `markdown` or `field-map` extraction → `contracts/envelope.py::Source`
- `cardinality.entities_skipped`: work items dropped in an excluded state → `contracts/envelope.py::Cardinality`
- Only the string type of `native_id` could not be deferred → `contracts/common.py::SourceRef`

### Schema rules

What realises each fact of [schema-rules.md](schema-rules.md):

- The pydantic models are the source of truth; the schemas are generated from them → `contracts/schema_export.py::generate_schema`
- The six schemas are committed and shipped as package data in `living_doc_utilities/contracts/schemas/` → `contracts/schema_export.py::SCHEMAS_DIR`
- A model change without a regenerated schema fails CI → `tests/contracts/test_schema_export.py::test_committed_schema_is_up_to_date`
- The first key of every schema is `"$schema": "https://json-schema.org/draft/2020-12/schema"` → `contracts/schema_export.py::SCHEMA_DIALECT`
- Pydantic 2 emits 2020-12 shapes (`$defs`, `anyOf`) but no `$schema`; the export step adds it → `contracts/schema_export.py::generate_schema`
- Every schema sets `$id` to `https://absaoss.github.io/living-doc-utilities/schemas/<contract-id>-schema.json` → `contracts/schema_export.py::ID_TEMPLATE`
- The `$id` is an identifier, never a fetch target; validation uses the schema bundled with the installed library → `contracts/schema_export.py::load_schema`
- No schema carries `$schema_version`, and no custom `$`-prefixed key replaces it → `tests/contracts/test_schema_export.py::test_no_schema_version_dollar_key_anywhere_in_the_package`
- Every model rejects unknown fields (`extra="forbid"`) → `contracts/common.py::ContractModel`
- `additionalProperties: false` on a map would accept only `{}`, so every artifact with stats would fail → `contracts/schema_export.py::find_schema_violations`
- the file's own `metadata.stats.field_occupancy`: an `enum` of the contract's leaf paths, generated → `contracts/schema_export.py::_inject_own_field_occupancy_enum`
- `stats.cardinality.entities_by_type`: an `enum` of the documentation types → `contracts/common.py::DocType`
- `source_inputs[].stats.field_occupancy`, `selected_stats.field_occupancy`: the pattern `^[a-z][a-z0-9_]*(\[\])?(\.[a-z][a-z0-9_]*(\[\])?)*$` → `contracts/envelope.py::AUDIT_FIELD_PATH_PATTERN`
- `stats.cardinality.warnings_by_code`: the pattern `^[A-Z][A-Z0-9_]*$` → `contracts/envelope.py::WARNING_CODE_PATTERN`
- coverage-matrix `planned_summary.by_target_version`: the pattern `^\d+\.\d+\.\d+$` ([version format](entities-and-state.md#version-format)) → `contracts/common.py::VERSION_PATTERN`
- A file's own occupancy keys are enumerated, so a mistyped path fails validation → `tests/contracts/test_schema_export.py::test_mistyped_path_in_own_field_occupancy_fails_schema_validation`
- The audit copies in `source_inputs[]` hold another contract's paths (R7), so they get the generic pattern → `tests/contracts/test_schema_export.py::test_another_contracts_path_inside_source_inputs_audit_field_occupancy_passes`
- Warning codes are defined by each collector, so they are pattern-checked, not enumerated → `contracts/envelope.py::WARNING_CODE_PATTERN`
- Pydantic renders a pattern map as bare `patternProperties`; the export step rewrites it to typed `additionalProperties` plus `propertyNames` → `contracts/schema_export.py::_rewrite_pattern_maps`
- There is no third kind: a test fails on any object that is neither → `contracts/schema_export.py::find_schema_violations`
- A model rule JSON Schema can express is exported as `allOf` with `if`/`then`/`else` → `contracts/schema_export.py::_CROSS_FIELD_RULES`
- Each `doc-source` root's items are `allOf` the `Entity` reference and a `const` on that root's `type` → `contracts/schema_export.py::_ROOT_ITEM_RULES`
- A transform output's schema also requires at least one `source_inputs[]` entry (R7) → `contracts/schema_export.py::_inject_cross_field_constraints`
- Five rules stay Pydantic-only → `contracts/schema_export.py::_inject_cross_field_constraints`
- The read and write helpers re-validate with the model after the schema, so these five still fail → `contracts/io.py::_model_validate_or_raise`
- Every `date-time` field carries an RFC 3339 `pattern` beside its `format`, so a value needs its offset → `contracts/schema_export.py::_add_date_time_patterns`
- The pattern checks the shape only; the model rejects an impossible date, such as month 13 → `contracts/common.py::Timestamps`
- All structural validation goes through one helper, which picks the validator class with `validator_for(schema)` → `contracts/validation.py::validate`
- No call site hardcodes a validator class → `contracts/validation.py::validate`

### Artifact rules

What realises each fact of [artifact-rules.md](artifact-rules.md):

- Each contract module declares `CONTRACT_ID` and `RECORD_ROOTS`; one registry collects them → `contracts/registry.py::CONTRACTS`
- Each `doc-source` root holds one type: `user_stories[]` User Stories, `features[]` Features, `functionalities[]` Functionalities → `contracts/doc_source.py::DocSourceResult`
- Both issue-tracker collectors, GitHub and Azure DevOps, write `doc-entities.json` → `contracts/doc_entities.py::DocEntitiesResult`
- The file name is the contract, never the source system; the writer is named in `metadata.producer.name` (R6) → `contracts/envelope.py::Producer`
- `generator-ready` carries the `doc-entities` entity model unchanged under `content.entities[]` → `contracts/generator_ready.py::Content`
- `ui-test-catalog` carries the `ui-tests` scenario model unchanged → `contracts/ui_test_catalog.py::FeatureFileCatalog`
- Every artifact has a required top-level `schema_version` equal to its contract id → `contracts/doc_entities.py::DocEntitiesResult`
- In the schema it is a `const`, never an `enum`; no deprecated alias is accepted → `tests/contracts/test_schema_export.py::test_schema_header_keys_match_r1_through_r4`
- A consumer decides from the file alone, never from the tool that wrote it → `contracts/compat.py::check_input`
- A contract id has the form `<contract-name>-v<major>.<minor>.<patch>` → `contracts/envelope.py::CONTRACT_ID_PATTERN`
- Step 3 names the file's `metadata.producer.utilities_version` and the reader's own version → `contracts/compat.py::schema_validation_error`
- When the two versions differ, step 3 adds "the components run different utilities versions — align the pins" → `contracts/compat.py::schema_validation_error`
- A version of an expected contract this library does not ship has no bundled schema → `contracts/compat.py::check_input`
- `metadata.producer.version` and `utilities_version` are audit information: quoted in messages, never compared → `contracts/envelope.py::Producer`
- Every artifact has a top-level `schema_version`, a `metadata` envelope and a `warnings[]` array → `contracts/doc_entities.py::DocEntitiesResult`
- `metadata.producer` names the tool that wrote this file, not the tool the data came from → `contracts/envelope.py::Producer`
- A transform output has one `source_inputs[]` entry per input file → `contracts/envelope.py::SourceInputEntry`
- An entry holds the input's `schema_version`, `producer`, `run`, `source`, `stats` and `selected_stats` → `contracts/envelope.py::SourceInputEntry`
- A transform output has at least one entry; a collector output carries `source_inputs: []`, never an absent key → `contracts/envelope.py::check_transform_source_inputs`
- An entry is an audit record of the input's paths, so its `field_occupancy` keys are pattern-checked (R9) → `contracts/envelope.py::AuditStats`
- `stats` covers the whole input; `selected_stats` covers the records the view filter kept → `contracts/envelope.py::SourceInputEntry`
- No component reads or writes these, under any historical name; closed records reject them → `contracts/common.py::ContractModel`
- `metadata.stats` is `{cardinality, field_occupancy}` → `contracts/envelope.py::Stats`
- A count that does not apply is `0`, never absent → `contracts/envelope.py::Cardinality`
- `write_artifact` computes the first five and carries the last four over from the caller → `contracts/stats.py::compute_stats`
- `field_occupancy` is keyed by record-relative path: it starts at a record root and marks each array level `[]` → `contracts/schema_export.py::field_occupancy_paths`
- `metadata`, `document` and `warnings` are not counted → `contracts/stats.py::compute_stats`
- A value is the number of records at that level with a non-empty value; `null`, `""`, `[]` and `{}` are empty → `contracts/stats.py::_is_empty`
- `metadata` is one model shared by all six contracts; only the `field_occupancy` key enum differs → `contracts/envelope.py::Metadata`
- `producer`: `name`, `version`, `build`, `utilities_version` of the writing tool (R6) → `contracts/envelope.py::Producer`
- `run`: `run_id`, `run_attempt`, `actor`, `workflow`, `ref`, `sha`; audit only → `contracts/envelope.py::Run`
- `source`: `project_id`, `systems`, `organizations`, `repositories`, `extraction_mode` → `contracts/envelope.py::Source`
- `generated_at`: when the file was written → `contracts/envelope.py::Metadata`
- `stats`: the file's own stats (R11) → `contracts/envelope.py::Stats`
- `source_inputs`: one entry per transform input (R7) → `contracts/envelope.py::SourceInputEntry`
- One model means an envelope fix lands in all six contracts at once → `tests/contracts/test_schema_export.py::test_metadata_is_one_shared_model_across_all_six_contracts`
- `source` is required on every output, and `source.project_id` everywhere → `contracts/envelope.py::Source`
- `source.systems` values are `GitHub` and `AzureDevOps`; `extraction_mode` is `markdown`, `field-map` or `null` → `contracts/envelope.py::Source`
- `organizations[]` lists every configured `organization-name` once; an organisation may have no repository → `contracts/envelope.py::Source`
- A `repositories[]` entry's segment before the first `/` must be in `organizations[]`; nothing else of it is checked → `contracts/envelope.py::Source._check_repositories_reference_known_organizations`
- `document` exists only on `generator-ready`, `coverage-matrix` and `ui-test-catalog`, and holds `document.view` → `contracts/common.py::ViewDocument`
- `generator-ready`'s `document` adds `title`, `version` and `selection_summary` → `contracts/generator_ready.py::Document`
- In `selection_summary`, `total_entities` equals `included_entities` plus `excluded_entities` → `contracts/generator_ready.py::SelectionSummary`
- The envelope example validates as this model → `contracts/envelope.py::Metadata`
- `read_artifact(path, expected)` loads the file, runs R5 and returns the typed model, never a `dict` → `contracts/io.py::read_artifact`
- `write_artifact(result, path)` fills `metadata.stats` and `producer.utilities_version`, then validates in memory → `contracts/io.py::write_artifact`
- It writes to a temporary file in the destination directory, then renames it atomically, with LF line endings → `contracts/io.py::write_artifact`
- A failed validation never creates or modifies the destination: overwriting an existing artifact leaves it untouched → `contracts/io.py::write_artifact`

### Pipeline rules

What realises each fact of [pipeline-rules.md](pipeline-rules.md):

- Two documentation files in one run fail with `MULTIPLE_DOCUMENTATION_SOURCES` → `contracts/codes.py::Code`
- Two different kinds of documentation fail with `MIXED_DOCUMENTATION_SOURCES` → `contracts/codes.py::Code`
- Every collector has a required project-id input: lowercase letters, digits and hyphens, starting with a letter or digit → `contracts/envelope.py::PROJECT_ID_PATTERN`
- It is set once per pipeline, passed to every step and written to every artifact's `metadata.source.project_id` → `contracts/envelope.py::Source`
- A mismatch across inputs, or an input with no project id, is a hard `PROJECT_MISMATCH` → `contracts/codes.py::Code`
- A fetch still failing after retries, or a missing configured path, fails the whole source → `contracts/codes.py::Code`
- Configuration errors fail at start with `INVALID_CONFIGURATION`, naming the input and the reason → `contracts/codes.py::Code`
- `sources_configured` and `sources_failed` appear on every collector output → `contracts/envelope.py::Cardinality`
- A source that answers with zero entities is the warning `EMPTY_SOURCE`, not an error → `contracts/codes.py::Code`
- Shared code never turns a failure into `None`; the GitHub call decorator re-raises → `github/decorators.py::safe_call_decorator`

### Component checks

What realises each fact of [component-checks.md](component-checks.md):

- Components import the shared models and validate against the schemas shipped in the installed library → `contracts/schema_export.py::load_schema`
- The check fails on any git-tracked `*-schema.json` or `*.schema.json` outside `tests/` and an allow-list → `contracts/check_no_vendored_schemas.py::find_vendored_schemas`
- Run it from a repository root: `python -m living_doc_utilities.contracts.check_no_vendored_schemas [--allow DIR]` → `contracts/check_no_vendored_schemas.py::main`
- It reads git's index, so a file not yet added is not seen → `contracts/check_no_vendored_schemas.py::find_vendored_schemas`
- This library allows only its own schema folder → `Makefile::no-vendored-schemas`
- Artifacts are read only with `read_artifact` and written only with `write_artifact` → `contracts/io.py::read_artifact`
- Each entry point asserts, and mypy checks, that input and result are shared contract types, never a `dict` → `contracts/registry.py::ContractResult`
- `full_sample(contract_id)` returns a valid, deterministic instance of any contract → `contracts/testing.py::full_sample`
- No record carries a field its state or its type makes meaningless; a contract with a root per type holds each record in its type's root → `contracts/testing.py::full_sample`
- One id names one entity across the sample's roots → `contracts/testing.py::full_sample`
- Each `doc-source` root fills every path except those its type never carries → `contracts/testing.py::NEVER_CARRIED_PATHS`
- The contracts' samples agree on one entity set → `contracts/testing.py::full_sample`
- The sample takes no view: transforms filter it, generators set `document.view` → `contracts/testing.py::full_sample`
- A generator renders it per view and asserts what each view shows and hides → `contracts/testing.py::shown_paths`
- Each transform declares its own lineage table in its own repository: every input path maps to an output path or to `Dropped(reason)` → `contracts/lineage.py::LineageTable`
- This library ships only the machinery; no transform's table lives here → `contracts/lineage.py::Dropped`
- `assert_complete(table, input_contract)` fails on any input leaf path the table says nothing about → `contracts/lineage.py::assert_complete`
- The transform-time check compares the input's `selected_stats` (R7) with the output's stats → `contracts/lineage.py::check_field_loss`
- A mapped path with input occupancy above 0 and output occupancy 0 is a hard `FIELD_LOSS`, naming each path → `contracts/lineage.py::check_field_loss`
- A transform without a documentation input compares against its one input → `contracts/lineage.py::check_field_loss`
- R11 guards transforms only; the authoring-to-collector stage, with no JSON input to compare, has golden-entity tests and snapshot CI → `tests/authoring/golden/test_golden_entities.py::test_golden_entities_match_hand_written_json`

### Rendering

What realises each fact of [rendering.md](rendering.md):

- Every authored field is carried at its authored level in `generator-ready`; nothing is expanded, inherited or flattened → `contracts/generator_ready.py::Content`
- A generator decides presentation from the document's declared view, `inner` or `release` → `contracts/common.py::View`
- `shown_paths(contract_id, view)` encodes which cells are shown, as field paths → `contracts/testing.py::shown_paths`
- What was not loaded is the canon's rule; this row only maps it onto the warning's fields → `contracts/envelope.py::ContractWarning`
- A warning's `ac_id` and `context` are never shown; `entity_id` only places it → `contracts/testing.py::shown_paths`
- It covers the three contracts a generator renders; `ui-test-catalog` has no view-dependent field → `contracts/testing.py::shown_paths`
- The canonical AC header is rendered by the model, with the `v` added back → `contracts/common.py::AcceptanceCriterion.canonical_header`
- Coverage is computed per aspect → `contracts/coverage_matrix.py::AcCoverage._check_status_matches_aspects`
- A `partially_covered` criterion shows covered/declared aspects, e.g. **1/3**, before its per-aspect breakdown → `contracts/coverage_matrix.py::AcCoverage.covered_aspects`
- A row with a `keyword` lists that keyword's values as aspects; one without aspects fails validation → `contracts/coverage_matrix.py::AcCoverage._check_keyword_has_aspects`
- An aspect's own status is `covered` or `not_covered` → `contracts/coverage_matrix.py::AspectCoverage`
- `covered` is evidence-backed by `scenario_ids` for an `AspectCoverage` and for an `AcCoverage` with no aspects → `contracts/coverage_matrix.py::_check_status_evidence`
- When an `AcCoverage` has aspects, its `status` is derived from them, and its own top-level `scenario_ids` is not checked → `contracts/testing.py::_coverage_matrix_sample`
- Counted criteria are `active` and `deprecated`, in both views → `contracts/coverage_matrix.py::CountedState`
- `in_review` criteria are not counted; a linked scenario is the warning `IN_REVIEW_AC_HAS_TESTS` → `contracts/codes.py::Code`
- `planned` criteria, backlog or targeted, are not counted; a linked scenario is the warning `PLANNED_AC_HAS_TESTS` → `contracts/codes.py::Code`
- The coverage matrix holds no row for an `in_review` or `planned` criterion → `contracts/coverage_matrix.py::CountedState`
- A scenario linked to one keeps its `@AC:` link in `ui-test-catalog` → `contracts/ui_test_catalog.py::FeatureFileCatalog`
- Every entity and the whole matrix carry a required `summary` → `contracts/coverage_matrix.py::CoverageSummary`
- Each counted row weighs: `covered` 1, `not_covered` 0, `partially_covered` its covered aspects over its declared aspects → `contracts/coverage_matrix.py::AcCoverage.weight`
- `coverage_pct` is the sum of the weights over `counted_acs`, times 100 → `contracts/coverage_matrix.py::CoverageSummary.from_rows`
- A `deprecated` row counts like an `active` one → `contracts/coverage_matrix.py::CountedState`
- The matrix summary is computed from every row of every entity, never from the entities' percentages → `contracts/coverage_matrix.py::CoverageMatrixResult._check_summary_matches_every_row`
- Every field is recomputed from the rows; a summary that disagrees with them fails validation → `contracts/coverage_matrix.py::EntityCoverage._check_summary_matches_rows`
- A producer writes exactly what `CoverageSummary.from_rows` returns, so no generator computes a figure → `contracts/coverage_matrix.py::CoverageSummary.from_rows`
- Both views show every summary → `contracts/testing.py::shown_paths`
- The coverage matrix always carries a planned-work summary: `total`, `backlog` and `by_target_version` → `contracts/coverage_matrix.py::PlannedSummary`
- Only the inner view renders it → `contracts/testing.py::shown_paths`
- Each planned criterion is backlog (no target version) or targets exactly one version → `contracts/coverage_matrix.py::PlannedSummary`
- So `total` equals `backlog` plus the sum of `by_target_version` → `contracts/coverage_matrix.py::PlannedSummary._check_total_equals_backlog_plus_targeted`

### Errors and warnings

What realises each fact of [errors.md](errors.md):

- Every code is registered once, with its kind and emitter → `contracts/codes.py::ALL_CODES`
- A test keeps the code table equal to the registry, kind and emitter included → `tests/contracts/test_codes.py::test_error_page_lists_exactly_the_registered_codes`
- A hard error is raised with a code, a message and an optional context → `contracts/codes.py::ContractError`
- A warning is an entry in the artifact's `warnings[]`: `code`, `message`, `context`, and five optional fields for where it belongs → `contracts/envelope.py::ContractWarning`
- Kinds and emitters are the values of `CodeKind` and `Emitter` → `contracts/codes.py::CodeKind`, `contracts/codes.py::Emitter`
- Generators read through `read_artifact`, so R5's three errors apply to them unchanged → `contracts/io.py::read_artifact`
