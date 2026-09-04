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
pip install git+https://github.com/AbsaOSS/living-doc-utilities@v0.3.1
```

#### Option 3: From PyPI

```bash
pip install living-doc-utilities
```

To pin a specific version:

```bash
pip install living-doc-utilities==0.3.1
```

### Importing

```python
from living_doc_utilities.model.issues import Issues
from living_doc_utilities.github.utils import get_action_input, set_action_output

issues = Issues.load_from_json("doc-issues.json")
print(issues.count())
```

## Releasing

Releases are published to PyPI entirely through GitHub Actions. The `.github/workflows/release.yml`
workflow runs on manual dispatch: it validates the version tag, generates release notes, tags the
commit, builds the package, uploads it to PyPI, and drafts a GitHub release. No local tagging or
manual upload is required. See the [How to Release](DEVELOPER.md#how-to-release) section of the
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

- **Issue Tracker**: For technical issues or feature requests, use the [GitHub Issues page](https://github.com/AbsaOSS/living-doc-utilities/issues).
- **Discussion Forum**: For general questions and discussions, join our [GitHub Discussions forum](https://github.com/AbsaOSS/living-doc-utilities/discussions).
