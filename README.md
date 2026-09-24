# Living Documentation Utilities

[![Static analysis & tests](https://github.com/AbsaOSS/living-doc-utilities/actions/workflows/test.yml/badge.svg)](https://github.com/AbsaOSS/living-doc-utilities/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![PyPI](https://img.shields.io/pypi/v/living-doc-utilities.svg)](https://pypi.org/project/living-doc-utilities/)

## Purpose

`living-doc-utilities` is the shared Python library of the Living Documentation ecosystem. The `living-doc-*`
collectors, transforms and generators import it as a pinned PyPI package; it has no CLI and no GitHub Action.
This page gives the overview, a usage tip, and the page to read next.

## Contents

- [Overview](#overview)
- [Usage tip](#usage-tip)
- [Where next](#where-next)
- [Developer guide](#developer-guide)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## Overview

- **Contracts** (`living_doc_utilities.contracts`): typed models of the six documentation contracts, their JSON Schemas, and the helpers every component shares → [Documentation contracts](docs/contracts.md)
- **Authoring** (`living_doc_utilities.authoring`): normalisation, the acceptance-criterion grammar, and the parsers for every authoring surface → [Authoring](docs/authoring.md)
- **GitHub** (`living_doc_utilities.github`): action input and output, a rate limiter, a call decorator that never swallows a failure → [GitHub helpers](docs/api.md#github-helpers)
- **Inputs** (`living_doc_utilities.inputs`): a base class for a GitHub Action's inputs → [Action inputs and logging](docs/api.md#action-inputs-and-logging)
- **Runtime helpers**: `setup_logging()` and shared constants → [Action inputs and logging](docs/api.md#action-inputs-and-logging)
- **AI-free**: every pipeline step is deterministic tooling, with no LLM call → [AI-free principle](CONTRIBUTING.md#ai-free-principle)

## Usage tip

Python 3.10 or later. Pin the version exactly, and add an extra only for the module that needs it:

```shell
pip install "living-doc-utilities==0.5.0"          # contracts, authoring, github.utils, inputs
pip install "living-doc-utilities[github]==0.5.0"  # adds the GitHub rate limiter and decorators
pip install "living-doc-utilities[html]==0.5.0"    # adds the HTML sanitiser
```

```python
from living_doc_utilities.contracts.io import read_artifact, write_artifact
```

Which module needs which extra: [Extras](docs/api.md#extras). Pinning rules: [Versioning](docs/api.md#versioning).

## Where next

| I want to… | Read |
|---|---|
| find a module and what it needs installed | [API](docs/api.md) |
| read or write a contract file | [Documentation contracts](docs/contracts.md) |
| parse authored documents | [Authoring](docs/authoring.md) |
| look up an error or warning code | [Errors and warnings](docs/contracts/errors.md) |
| set up the repository, run the gates, release | [Developer guide](DEVELOPER.md) |
| contribute a change | [Contributing](CONTRIBUTING.md) |

## Developer guide

Setup, quality gates, regeneration, release and documentation rules: [DEVELOPER.md](DEVELOPER.md).

## Contributing

Issues, branches, pull requests and the AI-free principle: [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Apache License 2.0; see [LICENSE](LICENSE).

## Contact

Questions, bugs and feature requests: [GitHub Issues](https://github.com/AbsaOSS/living-doc-utilities/issues).
