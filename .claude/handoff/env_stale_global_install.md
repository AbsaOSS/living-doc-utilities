---
name: env-stale-global-install
description: This machine has a stale global living-doc-utilities 0.3.1 install that masks package-metadata bugs which only surface in clean CI
metadata: 
  node_type: memory
  type: project
  originSessionId: 71d5e621-09ad-4e90-ae50-21b162d59bb5
  modified: 2026-09-18T18:17:43.769Z
---

This dev machine's global site-packages (`/usr/local/lib/python3.14/site-packages/living_doc_utilities-0.3.1.dist-info`)
has an old, separately-`pip install`ed copy of `living-doc-utilities`, independent of any repo
checkout. The repo also carries its own `living_doc_utilities.egg-info/` (gitignored). Either one
makes `importlib.metadata.version("living-doc-utilities")` resolve locally even when nothing in
the current checkout or its `make install` actually installed the project itself.

**Why this matters:** `living_doc_utilities/contracts/compat.py`'s `installed_utilities_version()`
calls `importlib.metadata.version(...)` with no fallback. Locally this always "just works" and
hides that a fresh CI runner (clean venv, only `pip install -r requirements.txt`, no editable
install of the project) raises `PackageNotFoundError` there — this exact gap shipped in PR #141
(issue #140) and was caught by a CodeRabbit review, confirmed by verifying against
`tests/contracts/test_compat.py::test_installed_utilities_version_delegates_to_importlib_metadata`,
which calls the real (unmocked) lookup.

**How to apply:** Any test or manual check involving `compat.installed_utilities_version()` (or
anything that reads this package's own `importlib.metadata`) that passes locally is not proof it
passes in CI. Reproduce by temporarily moving `living_doc_utilities.egg-info` aside and checking
whether `importlib.metadata.version("living-doc-utilities")` still resolves (it will, from the
0.3.1 site-packages copy) — a genuinely clean venv is the only reliable check. The fix landed in
this repo's `Makefile`'s `install` target (`pip install -e . --no-deps`) plus a `DEVELOPER.md` note.
