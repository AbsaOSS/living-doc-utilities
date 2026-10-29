# living_doc_utilities/contracts

Parent: ../../CONTEXT.md

## Purpose

The shared, typed pydantic models of the six contracts, the JSON Schemas generated from them, and the helpers every component uses to read, write, validate and test contract artifacts.

Not responsible for: reading authored text; `authoring/` does that and produces these models.

## How it fits

- Entry points: `io.py::read_artifact`, `io.py::write_artifact`, the models, `registry.py::CONTRACTS`, `codes.py::ALL_CODES`, `schema_export.py::load_schema`.
- Used by: every collector, transformer and generator, and `authoring/`.
- Depends on: `pydantic` and `jsonschema` only; every module imports with no extra.
- Contracts: `schemas/*-schema.json`, generated → [Contracts](../../docs/contracts.md), [Schema rules](../../docs/contracts/schema-rules.md)

## Conventions

- Every model extends `common.py::ContractModel` (`extra="forbid"`).
- Serialise with pydantic's `model_dump()` and `model_validate()`. Never add a hand-rolled `to_dict()` or `from_dict()`: the pydantic models are the only shared data model.
- Write a cross-field invariant as a `_`-prefixed `@model_validator(mode="after")` method, like `doc_entities.py::Entity._check_state_origin`.
- A new contract declares a module-level `RECORD_ROOTS: dict[str, type[BaseModel]]`, like `doc_entities.py`, and gets a row in `registry.py::CONTRACTS` → [Contracts](../../docs/contracts/artifact-rules.md#contracts)
- The transform-output models reuse `doc_entities.Entity`, `common.AcceptanceCriterion` and `ui_tests.Scenario` instead of redeclaring them.
- Structural validation goes through `validation.py`, which picks the validator with `jsonschema.validators.validator_for`, never a hardcoded validator class.
- Never import from `authoring/`.

## Invariants and gotchas

- Read and write a contract artifact only with `read_artifact()` and `write_artifact()`, never `json.load()` or `json.dump()` (R12). The read runs the compatibility check; the write validates in memory, then writes a temp file and renames it atomically.
- A model change and its regenerated `schemas/*.json` (`make schemas`) land in the same commit. Never hand-edit a schema: the next regeneration overwrites it, and the edit masks a real mismatch between the model and its schema.
- Check a new field name against `AbsaOSS/living-doc`'s canon before inventing one: `tools/examples_check.py`'s `PAIR_FIELD_MAP`, `REQUIRED_PO_KEYS_FULL` and `REQUIRED_PO_KEYS_XREF`, and `docs/guides/living-doc-header-types.md`.
  - Several first-version names were renamed to match it: `description` to `narrative`/`purpose`, `parent_feature` to `parent`, `user_story_ids` to `user_stories`, `functionality_ids` to `functionalities`.
  - Don't trust `living-doc`'s `docs/examples/_expected/*.json` for this: they predate this repo's contracts rewrite and are stale.
- `docs/contracts/errors.md` lists exactly `ALL_CODES`, and a test keeps the two equal, so a new code needs its row there.
- `check_no_vendored_schemas.py` (R12 check 1, `make no-vendored-schemas`) fails on any tracked schema file outside `tests/` and `schemas/`.
