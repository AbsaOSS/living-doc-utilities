<!-- What problem does it solve or what feature does it add? -->
## Overview

`0.7.0` adds two optional contract fields and fixes one read-side error, all needed before the first generator
renders. Every contract id stays; all six schemas regenerate. A file carrying either new field is rejected by a
`0.6.x` reader (`extra="forbid"`), so this is a minor.

- **`AcCoverage.keyword`** (`contracts/coverage_matrix.py`). A keyword criterion's name: its one
  `placeholder_values` key, folded (`payment_field` for `{payment-field}`), with the same pattern as that key.
  `None` for an `Aspect:` criterion and for one without variants. A row with a `keyword` needs aspects: the
  validator `_check_keyword_has_aspects`, and the same rule in `schema_export.py::_CROSS_FIELD_RULES`. A generator
  now labels the coverage breakdown from the row alone; before, it had to join the matrix with the documentation
  input by criterion id. The contract id stays `coverage-matrix-v1.0.0`.
- **`ContractWarning.source_url`** (`contracts/envelope.py`). The permalink of the file the warning's line is in,
  at the collected commit (`<server>/<org>/<repo>/blob/<sha>/<path>` on GitHub). Set only by an emitter that knows
  it, a collector, never `authoring`. Before, a generator could only build a link from the entity's
  `source_ref.url`, which opens the wrong file when the line is in another one (a PageObject page naming a Feature
  whose URL points at the Feature's own file).
- **`check_input`** (`contracts/compat.py`). After the name check, a `schema_version` this `utilities` does not ship
  raises `INVALID_CONTRACT_ID` before any schema is loaded. Before, `load_schema` raised `FileNotFoundError` on the
  bundled file, and `read_artifact` passed it on. The message names the id, the file's
  `metadata.producer.utilities_version` and the installed one, and always ends with the pin hint. The wording is
  shared with `schema_validation_error` through one helper, `_with_utilities_versions`, so the two never drift.
  `CONTRACT_MISMATCH`'s message keeps its exact shape.
- **Samples** (`contracts/testing.py`). The coverage sample's `US-001-04` row carries `keyword="payment_field"`,
  the one constant the `generator-ready` sample stores as that criterion's `placeholder_values` key; every other row
  is `None`. Each of the three not-loaded warnings carries a `blob` permalink of its `path`; the sample's entities
  link GitHub issues, so the sample itself shows why an entity's URL cannot place a line. `shown_paths` adds
  `entities[].acceptance_criteria[].keyword` to both coverage views and `warnings[].source_url` to the inner
  `generator-ready` view.
- **Docs.**
  - `docs/contracts/rendering.md` § Coverage: the label is the row's `keyword`, "Aspect" when it is `null`.
    § Fields by view: a warning's line links as `source_url` plus `#L<line_no>`, as text without it. The
    deprecation date and reason are an entity's only; a deprecated criterion shows its state in its header and its
    `removal_planned` row.
  - `docs/contracts/component-checks.md` § Check 3: the samples agree on the keyword too, and the "Why" names the
    toolkit's computation, not a generator join.
  - `docs/contracts/errors.md`: `source_url` beside `path`; the `INVALID_CONTRACT_ID` row names the read side.
  - `docs/contracts/artifact-rules.md` § R5: one bullet places the unshipped-version check before step 3.
  - `0.7.0` in `pyproject.toml`, `README.md`, `docs/api.md` and `.github/copilot-instructions.md`. The bump example
    in `docs/api.md` § Versioning (`0.5.0` → `0.6.0`) is a generic example, not a pin, and stays, as it did in `0.6.0`.

<!-- Summarize the key changes for release notes. -->
## Release Notes
- **Breaking:** coverage rows may carry `keyword` and warnings `source_url`; a `0.6.x` reader rejects a file with either field. Migration: pin `living-doc-utilities==0.7.0` in every reader and writer.
- **Breaking:** for a version of an expected contract this `utilities` does not ship, `check_input` and `read_artifact` raise `ContractError` `INVALID_CONTRACT_ID` with the pin-alignment hint, not `FileNotFoundError`. Migration: catch `ContractError` and branch on `Code.INVALID_CONTRACT_ID` instead of `FileNotFoundError`.
- `AcCoverage.keyword`: a keyword criterion's name (its folded `placeholder_values` key, e.g. `payment_field`), `null` for an `Aspect:` criterion; a row with a `keyword` needs aspects, in the model and the schema.
- `ContractWarning.source_url`: the permalink of the file the warning's line is in, at the collected commit; a collector fills it.
- `full_sample` and `shown_paths` carry both fields: the coverage `keyword` shows in both views, `warnings[].source_url` in the inner view.
- `docs/contracts/rendering.md` § Fields by view no longer promises an acceptance criterion a deprecation date and reason.

<!-- Add attached issue that this PR solves. -->
## Related
Closes #192

## Re-pins
- `living-doc-collector-gh`: pin `0.7.0`; fill `source_url` wherever it fills `path`, as the file's `blob` permalink at the collected commit.
- `living-doc`: re-pin the snapshot job, bump `COLLECTOR_GH_REF`, regenerate the collector snapshots.
- `living-doc-generator-markdown`: pin `0.7.0`; label the coverage breakdown with the row's `keyword`; link a warning's line as `source_url#L<line_no>`; its `FileNotFoundError` branch can go (`CONTRACT_MISMATCH`'s message is unchanged).
- `living-doc-toolkit`: takes `0.7.0` as its first pin, and fills `keyword` when it computes the matrix.

## Framework
Inside the frame (`living-doc` `docs/introduction/principles.md` § The frame):
- `keyword` moves a join a generator would make (F4: a generator reads only toolkit outputs, never enriches them) into the matrix the toolkit computes (F3: cross-referencing, including the coverage matrix).
- `source_url` is provenance a collector records (F2): which file it read, at which commit; nothing is interpreted.
- Both are Pydantic model fields with generated schemas (F5, F7); no component mirrors them.
- The `check_input` fix is shared validation logic in `utilities` (F5); no pipeline stage moves.

## Acceptance criteria
<!-- filled in after the tests land -->
