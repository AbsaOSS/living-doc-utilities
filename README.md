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
`entities[]`. The runtime read/validate helpers are not implemented yet; they land in a later
release.

## Authoring normalisation and the acceptance-criterion grammar

`living_doc_utilities.authoring` is the one place that reconciles the small formatting variance
real authors introduce — dash style, bullet marker, case, spacing, version form — across the five
authoring surfaces a collector reads (a GitHub issue body, a `.feature` file's header comment
block and its scenario body, a PageObject header, and Azure DevOps' HTML-converted markdown), and
the one grammar for an acceptance-criterion header and its extensions. Both are pure `text -> data`
functions with no I/O, and never touch code, Gherkin step text, or free prose:

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
