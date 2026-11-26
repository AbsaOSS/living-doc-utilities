# living_doc_utilities/check

Parent: ../../CONTEXT.md

## Purpose

The authored-input check a caller runs before a merge: the collectors' parsers over a corpus, each finding placed on a file and line with a fix hint, and the report a caller prints.

Not responsible for: finding or reading the files, the exit code, printing, or reading the environment. The caller does that: `living-doc-collector-gh`'s `doc-check` mode.

## How it fits

- Entry points: `engine.py::check`, the four functions of `report.py`, and `policy.py::Policy` one level up for the fail list.
- Depends on: `authoring/` (the parsers, `required_keys.py`, `status.py`, `relations.py`), `contracts/codes.py`.
- Docs: [Check](../../docs/check.md); its code map: [docs/CONTEXT.md](../../docs/CONTEXT.md)

## Conventions

- A library only: no `main`, argument parsing, file reading or `os.environ` here (AGENTS.md "This project", Rules).
- The entity type comes from the caller's configuration, never from the file's id prefix: it must match what the collector parses the file as.
- Per-file findings are reported for the changed paths only; every relation finding of the corpus is reported, whatever file holds it.

## Invariants and gotchas

- Text in a finding is authored, so untrusted: `report.py` escapes it for each sink (one log line, workflow-command data and properties, Markdown cells), and the GitHub report prints the lines inside a `::stop-commands::` block with a fresh random token. Keep every new sink escaped.
- GitHub shows at most 10 annotations per level per step and drops the rest silently: `report.py::_ANNOTATIONS_PER_LEVEL`.
- A missing tag and a missing key share `MISSING_REQUIRED_KEY`; `report.py::_with_hint` gives the tag `hints.py::MISSING_TAG_HINT` by its message's opening, `Required tag `. Change that message in `required_keys.py::missing_required_tag` and the report together.
