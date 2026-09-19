# Living Documentation Utilities

[![Static analysis & tests](https://github.com/AbsaOSS/living-doc-utilities/actions/workflows/test.yml/badge.svg)](https://github.com/AbsaOSS/living-doc-utilities/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![PyPI](https://img.shields.io/pypi/v/living-doc-utilities.svg)](https://pypi.org/project/living-doc-utilities/)

`living-doc-utilities` is the shared Python library for the Living Documentation ecosystem — the
data models, serialization helpers, and GitHub utilities that the `living-doc-*` collectors and
generators import instead of re-implementing.

## Overview

The library provides the pieces every `living-doc-*` repository would otherwise duplicate:

- **Structured data models** — `Issue` and its subtypes (`UserStoryIssue`, `FeatureIssue`,
  `FunctionalityIssue`), the `Issues` collection, and `ProjectStatus`, so every action exchanges the
  same JSON shape.
- **Serialization / deserialization (serde)** — `Issues.save_to_json()` / `Issues.load_from_json()`
  and the `IssueFactory` that rebuilds the correct subtype by name.
- **GitHub helpers** — `get_action_input()` / `set_action_output()`, the `GithubRateLimiter`, and the
  `safe_call_decorator` retry wrapper.
- **Shared plumbing** — `setup_logging()`, the `BaseActionInputs` contract, and common constants.

It is designed to reduce duplication, improve testability, and simplify maintenance across the
ecosystem.

> **Usage model.** `living-doc-utilities` is consumed as a library by the other `living-doc-*` repos; it is not run directly. There is no CLI and no GitHub Action entry point in this repository — the collectors and generators depend on it as a pinned PyPI package and import from it.

> **The Living Documentation pipeline runs AI-free.** Every step — collect → normalize → generate — is deterministic tooling (Python, JSON Schema validation, Jinja2/Markdown templates) with no LLM call anywhere in that path. [`AbsaOSS/agentic-toolkit`](https://github.com/AbsaOSS/agentic-toolkit) can accelerate the upstream *authoring* of GitHub Issues and `.feature` files, but it is never a runtime dependency of this pipeline: a human writing the same input by hand is a fully supported, identical path.

## Documentation contracts

The six documentation contracts exchanged across the ecosystem — `doc-entities`, `doc-source`,
`ui-tests`, `generator-ready`, `coverage-matrix`, `ui-test-catalog` — are defined normatively in
[Documentation contracts](docs/contracts.md): the schema authoring rules, the shared metadata
envelope, the artifact and rendering rules, and the catalogue of error and warning codes. Every
collector, transform and generator in the ecosystem is written against that document.

All six contracts — the three collector-output contracts (`doc-entities`, `doc-source`,
`ui-tests`) and the three transform-output contracts (`generator-ready`, `coverage-matrix`,
`ui-test-catalog`) — are implemented as typed, `extra="forbid"` pydantic models in
`living_doc_utilities.contracts`, with their JSON Schemas generated from those models and shipped
as package data under `living_doc_utilities/contracts/schemas/`:

```python
from living_doc_utilities.contracts.doc_entities import DocEntitiesResult
from living_doc_utilities.contracts.generator_ready import GeneratorReadyResult
from living_doc_utilities.contracts.schema_export import load_schema

result = DocEntitiesResult.model_validate(data)
schema = load_schema("doc-entities-v1.0.0")  # loaded via importlib.resources
```

The transform-output contracts build directly on the shared metadata envelope and reuse the
`doc-entities` entity and acceptance-criterion models rather than redeclaring them —
`generator-ready`'s `content.entities[]` carries the exact same `Entity` model as `doc-entities`'
`entities[]`.

`living_doc_utilities.contracts.io.read_artifact()` and `write_artifact()` are the only sanctioned
way to read or write a contract artifact anywhere in the ecosystem (docs/contracts.md, R12):
`read_artifact` runs the R5 compatibility check (`schema_version` parses, names a contract the
caller accepts, and validates against the bundled schema) before returning a typed model;
`write_artifact` fills in `metadata.stats` and `metadata.producer.utilities_version`, validates the
result in memory, and only then writes it — to a temporary file in the destination's own directory,
then an atomic rename — so a crash mid-write never leaves a partial or corrupt artifact behind:

```python
from living_doc_utilities.contracts.io import read_artifact, write_artifact
from living_doc_utilities.contracts.codes import ContractError

try:
    result = read_artifact("doc-entities.json", expected={"doc-entities", "doc-source"})
except ContractError as error:
    print(error.code, error.message)  # e.g. CONTRACT_MISMATCH, SCHEMA_VALIDATION_FAILED

write_artifact(result, "out/doc-entities.json")  # stats + producer version filled in for you
```

Three shared helpers back the R12 checks every component runs (docs/contracts.md, R11 and R12):

- `living_doc_utilities.contracts.testing.full_sample(contract_id)` returns a deterministic, valid instance of
  any of the six contracts, built from state-consistent records that jointly populate every optional
  field; it takes no `view` (transforms filter it, generators set `document.view`).
  `shown_paths(contract_id, view)` returns the field paths the rendering rules (section 4) show in
  `"inner"` or `"release"`, for the three contracts a generator renders (`generator-ready`,
  `coverage-matrix`, `ui-test-catalog`).
- `living_doc_utilities.contracts.lineage` holds the machinery for a transform's own field-lineage
  table: `LineageTable`, `Dropped`, `assert_complete(table, input_contract)` (takes a contract id or its `RECORD_ROOTS`; fails on any
  input leaf path the table says nothing about) and `check_field_loss(table, input_selected_stats,
  output_stats)` (raises one `FIELD_LOSS` naming every mapped path with input occupancy above 0 and output 0).
  The tables themselves live with the transform, not here.
- `python -m living_doc_utilities.contracts.check_no_vendored_schemas [--allow DIR]`, run from a
  repository root, fails on any git-tracked `*-schema.json` / `*.schema.json` outside `tests/` and the
  allowed directories; this package runs it with `--allow living_doc_utilities/contracts/schemas`.

Every error and warning code either of these — or any other component in the ecosystem — can
raise or emit is registered once, with its kind and its emitting component, in
`living_doc_utilities.contracts.codes.ALL_CODES`.

## Authoring normalisation and the acceptance-criterion grammar

`living_doc_utilities.authoring` is the one place that reconciles the small formatting variance
real authors introduce — dash style, bullet marker, case, spacing, version form — across the five
authoring surfaces a collector reads (a GitHub issue body, a `.feature` file's header comment
block and its scenario body, a PageObject header, and Azure DevOps' HTML-converted markdown), and
the one grammar for an acceptance-criterion header and its extensions. Both are pure `text -> data`
functions with no I/O, and never touch code, Gherkin step text, or free prose. Normalisation (per
rule), the acceptance-criterion grammar, every parser's accepted layout, entity-identity
derivation, status derivation and the URL policy are all defined normatively in
[Authoring](docs/authoring.md):

```python
from living_doc_utilities.authoring.normalize import SourceFormat, normalize
from living_doc_utilities.authoring.ac_grammar import parse_acceptance_criteria

normalized = normalize(issue_body_text, SourceFormat.ISSUE_BODY, "DocumentedUserStory")
acceptance_criteria, warnings = parse_acceptance_criteria(normalized.text, entity_id="US-001")

# AcceptanceCriterion.canonical_header() renders "AC:<id> (v<x.y.z> - <state>)" (or
# "AC:<id> (planned)" for a version-less backlog item) without importing this package again.
acceptance_criteria[0].canonical_header()
```

The four acceptance-criterion states and every warning code (`MALFORMED_AC`, `LEGACY_AC_STATE`,
`UNPARSED_AC_LINE`, …) are defined normatively in [Documentation contracts](docs/contracts.md).
The seven normalisation rules (plus one for an entity id's title separator) implement the
canonical form established in `AbsaOSS/living-doc`'s `docs/guides/living-doc-glossary.md` and
`docs/guides/living-doc-header-types.md`; `living_doc_utilities/authoring/normalisation_cases.yaml`
is both the normalisation rules' test data and a worked example of every rule and source format.

## Authoring parsers

Built on top of normalisation and the acceptance-criterion grammar, `living_doc_utilities.authoring`
also parses every authoring surface into entity data. Every parser returns `(parsed, warnings)`
without ever raising on malformed input, and none of them fills `source_ref` — that is always the
calling collector's job, since a parser only ever sees document text:

```python
from living_doc_utilities.authoring.issue_body import parse_issue_body
from living_doc_utilities.authoring.status import derive_statuses

parsed, warnings = parse_issue_body(issue_body_text, issue_title, "DocumentedUserStory")
entities, status_warnings = derive_statuses([parsed, ...])  # run once, over every entity in a run
```

| Module | Parses |
|---|---|
| `issue_body` | A GitHub issue body's `##` sections into a `ParsedEntity` |
| `feature_header` | A `.feature` file's header comment block for a User Story / Functionality |
| `page_object` | A PageObject file's header for a Feature (full or cross-reference) |
| `scenario` | A `.feature` file's `Scenario:`/`Scenario Outline:` blocks and their `@AC:` tags |
| `identity` | `entity_id` from a title (`derive_entity_id`) |
| `status` | Final `state`/`state_origin` for every entity in a run (`derive_statuses`) |
| `relations` | Cross-entity relation checks (`UNRESOLVED_RELATION`, `RELATION_MISMATCH`) |
| `url_policy` | Which links survive into rendered documentation (`safe_href`, `sanitize_html_fragment`) |
| `html_to_markdown` | Azure DevOps rich-text HTML into the same Markdown-like text the other parsers understand (`convert_html_to_markdown`) |

`tests/fixtures/golden/` holds this project's own three canonical example documents (copied
verbatim from `AbsaOSS/living-doc`'s `docs/examples/`) alongside hand-written expected-entity JSON
files. They are the reference other repos' parsers (`living-doc-collector-gh`, `living-doc-toolkit`,
`living-doc-collector-ad`) compare their own output against.

`html_to_markdown` needs the optional `html` extra (`pip install living-doc-utilities[html]`) for
its `nh3`-based HTML sanitiser — nothing else in this package requires it:

```python
from living_doc_utilities.authoring.html_to_markdown import convert_html_to_markdown
from living_doc_utilities.authoring.normalize import SourceFormat, normalize
from living_doc_utilities.authoring.issue_body import parse_issue_body

markdown_text, html_warnings = convert_html_to_markdown(azure_devops_html)
normalized = normalize(markdown_text, SourceFormat.HTML_MARKDOWN, "DocumentedUserStory")
parsed, warnings = parse_issue_body(normalized.text, issue_title, "DocumentedUserStory")
```

## Usage

### Prerequisites

Before installing this library, ensure you have:

- Python 3.10 or later
- pip package installer
- (Recommended) Virtual environment setup in your project

### Installation

You can install the utilities locally, directly from GitHub, or from PyPI.

#### Option 1: Local Development (editable mode)

If you are developing the library alongside another project:

```bash
pip install -e ../living-doc-utilities
```

Make sure you activate the virtual environment in your main project before installing.

#### Option 2: From GitHub (using a release tag)

```bash
pip install git+https://github.com/AbsaOSS/living-doc-utilities@v0.4.0
```

#### Option 3: From PyPI

```bash
pip install living-doc-utilities
```

To pin a specific version:

```bash
pip install living-doc-utilities==0.4.0
```

### Importing

```python
from living_doc_utilities.model.issues import Issues
from living_doc_utilities.github.utils import get_action_input, set_action_output

issues = Issues.load_from_json("doc-issues.json")
print(issues.count())
```

## Releasing

Releases run through a two-stage GitHub Actions pipeline. Stage 1
(`.github/workflows/release_draft.yml`, manual dispatch) runs the quality gate, tags the commit, and
creates a **draft** GitHub release with generated notes — nothing irreversible. Stage 2
(`.github/workflows/release.yml`) fires when a maintainer **publishes** that draft release: it builds
the package from the tag and uploads it to PyPI. Publishing the draft is the approval gate for the
PyPI upload. No local tagging or manual upload is required. See the [How to Release](DEVELOPER.md#how-to-release) section of the
Developer Guide for the step-by-step.

## Developer Guide

See this [Developer Guide](DEVELOPER.md) for more technical, development-related information.

## Contribution Guidelines

We welcome contributions to the Living Documentation ecosystem! Whether you're fixing bugs, improving
documentation, or proposing new features, your help is appreciated.

### How to Contribute

Before contributing, please review our [contribution guidelines](CONTRIBUTING.md) for more detailed
information.

### License Information

This project is licensed under the Apache License 2.0. It is a liberal license that allows you great
freedom in using, modifying, and distributing this software, while also providing an express grant of
patent rights from contributors to users.

For more details, see the [LICENSE](LICENSE) file in the repository.

### Contact or Support Information

If you need help with using or contributing to the `living-doc-utilities` library, or if you have any
questions or feedback, don't hesitate to reach out:

- **Issue Tracker**: For technical issues, feature requests, and general questions, use the [GitHub Issues page](https://github.com/AbsaOSS/living-doc-utilities/issues).
