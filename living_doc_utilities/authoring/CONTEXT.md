# living_doc_utilities/authoring

Parent: ../../CONTEXT.md

## Purpose

The pure `text -> data` layer: reads authored documents (GitHub issue bodies, `.feature` headers and scenarios, PageObject headers) into the contract models.

Not responsible for: fetching documents from a tracker. A parser sees document text only and imports no tracker SDK.

## How it fits

- Entry points: the `frame_*` functions in `framing.py`, `normalize.py::normalize`, `ac_grammar.py::parse_acceptance_criteria`, and the parsers in `issue_body.py`, `feature_header.py`, `page_object.py` and `scenario.py`.
- Depends on: `contracts/`; `nh3` (the `html` extra) only at call time.
- Docs: [Authoring](../../docs/authoring.md)

## Conventions

- A parser returns `(parsed, warnings)` and never raises on malformed authored input: it reports a code registered in `contracts/codes.py::ALL_CODES`.
- Every boundary decision (where a header, section, key or criterion starts and ends) lives in `framing.py`, decided once per input and by position. No normaliser or parser derives a boundary of its own.
- `accounting.py` reports every authored line no field reads, each naming its input line: `AUTHORING_ERROR` for a line that breaks the header format, `AUTHORING_WARNING` for any other.
- Entity-type differences are data in `normalize.py::TYPE_PROFILES`; never branch on `entity_type == ...`.
- `ac_grammar.py` alone validates the acceptance-criterion state vocabulary and version shape, and alone maps a legacy state onto `planned`. `normalize.py` holds no regex for either.
- `normalize` never rewrites code, Gherkin step text or free prose.

## Invariants and gotchas

- Every module imports with no extra. `nh3` is imported only inside the `url_policy.py` functions that call it, so only calling `sanitize_html_fragment` or `convert_html_to_markdown` needs the `html` extra.
- `normalisation_cases.yaml` is `normalize`'s only test data (`tests/authoring/test_normalize_cases.py`) and the source of the worked-examples table in `docs/authoring/normalisation.md`, which `docs_export.py` (`make docs`) regenerates.
- `docs_export.py` imports `yaml` inside `_load_cases`, because PyYAML is a development dependency and the module must import without it.
