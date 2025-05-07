# Living Documentation Utilities

- [Motivation](#motivation)
- [Usage](#usage)
    - [Prerequisites](#prerequisites)
    - [Installation](#installation)
        - [Option 1: Local Development (editable mode)](#option-1-local-development-editable-mode)
        - [Option 2: From GitHub (using a release tag)](#option-2-from-github-using-a-release-tag)
        - [Option 3: From PyPI](#option-3-from-pypi)
- [Developer Guide](#developer-guide)
- [Contribution Guidelines](#contribution-guidelines)
    - [How to Contribute](#how-to-contribute)
    - [License Information](#license-information)
    - [Contact or Support Information](#contact-or-support-information)


## Motivation

The `living-doc-utilities` library contains core utility functions and shared data models used across the Living Documentation GitHub Actions ecosystem.
It provides:

- Reusable transformation and helper logic
- Serialization and deserialization (serde) utilities
- Common structured data models for consistent cross-action communication
- A foundation for expanding shared functionality in the future

It is designed to reduce duplication, improve testability, and simplify maintenance across the ecosystem.


---
## Usage

### Prerequisites

Before installing this library, ensure you have:

- Python 3.12 or later
- pip package installer
- (Recommended) Virtual environment setup in your project

### Installation

You can install the utilities locally or directly from GitHub.

#### Option 1: Local Development (editable mode)

If you are developing the library alongside another project:

```bash
pip install -e ../living-doc-utilities
```

Make sure you activate the virtual environment in your main project before installing.

#### Option 2: From GitHub (using a release tag)

```bash
pip install git+https://github.com/AbsaOSS/living-doc-utilities@v0.1.0
```

#### Option 3: From PyPI

Once published to PyPI, simply run:

```bash
pip install living-doc-utilities
```

To pin a specific version:

```bash
pip install living-doc-utilities==0.1.0
```

---

## Developer Guide

See this [Developer Guide](DEVELOPER.md) for more technical, development-related information.

---
## Contribution Guidelines

We welcome contributions to the Living Documentation Generator! Whether you're fixing bugs, improving documentation, or proposing new features, your help is appreciated.

#### How to Contribute

Before contributing, please review our [contribution guidelines](https://github.com/AbsaOSS/living-doc-utilities/blob/master/CONTRIBUTING.md) for more detailed information.

### License Information

This project is licensed under the Apache License 2.0. It is a liberal license that allows you great freedom in using, modifying, and distributing this software, while also providing an express grant of patent rights from contributors to users.

For more details, see the [LICENSE](https://github.com/AbsaOSS/living-doc-utilities/blob/master/LICENSE) file in the repository.

### Contact or Support Information

If you need help with using or contributing to the Living Documentation Generator Action, or if you have any questions or feedback, don't hesitate to reach out:

- **Issue Tracker**: For technical issues or feature requests, use the [GitHub Issues page](https://github.com/AbsaOSS/living-doc-utilities/issues).
- **Discussion Forum**: For general questions and discussions, join our [GitHub Discussions forum](https://github.com/AbsaOSS/living-doc-utilities/discussions).
