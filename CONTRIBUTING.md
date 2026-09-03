# How to Contribute?

## **Identifying and Reporting Bugs**
* **Ensure the bug has not already been reported** by searching our **[GitHub Issues](https://github.com/AbsaOSS/living-doc-utilities/issues)**.
* If you cannot find an open issue describing the problem, use the **Bug report** template to open a new one. Tag it with the **bug** label.

## **Proposing New Features**

* **Check if the feature has already been requested** by searching through our **[GitHub Issues](https://github.com/AbsaOSS/living-doc-utilities/issues)**.
* If the feature request doesn't exist, feel free to create a new one. Tag it with the **request** label.

## AI-free Principle

This pipeline runs AI-free; contributions must keep every collect → normalize → generate step deterministic — no LLM call in that path.

## Contributing to Development

* Check _Issues_ for the desired feature or bug and make sure no one else is already working on it. If it is not filed yet, create a detailed issue first.
* Fork the repository and create a working branch off an issue (see **Branch Naming** below).
* Write the code and include tests for it.
* Commit messages should reference the GitHub Issue and give a concise description, e.g. `#34 - Implement Feature X`.
* Push to your fork and open a Pull Request (see **PR Naming**, **PR Description**, and **Target Branches** below).

## Branch Naming

Branches have to start with one of the allowed prefixes — `feature/`, `fix/`, `docs/`, `chore/` — followed immediately by the issue number, then a kebab-case scope: `<prefix>/<issue>-<scope>`.

Examples:
- `feature/542-add-hierarchy-support`
- `fix/567-handle-empty-response`
- `docs/203-contributing-rework`
- `chore/318-update-ci-python-version`

Use lowercase kebab-case and reflect the actual scope. The `check-pr-requirements` CI check rejects a branch that has no issue number.

Rename before pushing if needed:
```shell
git branch -m <prefix>/<issue>-<new-scope>
```

## PR Naming

PR titles have to carry the related issue number, using one of these formats: `#123: Title` or `123 - Title`.

Examples:
- `#567: Handle empty response`
- `203 - Rework contribution guide`

## PR Description

The PR body has to include these sections: `## Overview`, `## Release Notes`, `## Related`.
- **Overview** – what changed and why.
- **Release Notes** – short, user-facing summary for the changelog.
- **Related** – link the issue with a closing keyword, e.g. `Closes #123` or `Fixes AB#12345`.

## Target Branches

PRs have to target `main`, `master`, `support/*`, or `release/*`.

### Community and Communication

If you have any questions or need help, don't hesitate to reach out through our GitHub discussion section. We're here to help!

#### Thanks!

Your contributions are invaluable to us. Thank you for being part of the AbsaOSS community and helping us grow and improve!

The AbsaOSS Team
