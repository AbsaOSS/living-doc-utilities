# Authoring

## Purpose

Collector authors start here. This page states how authored text becomes entity data, lists the design decisions
with the code that realises them, and links to the page that defines each part.

Read before: [README](../README.md) · Next: [Normalisation](authoring/normalisation.md)

## Contents

- [Principle](#principle)
- [Decisions](#decisions)
- [Pages](#pages)

## Principle

`living_doc_utilities.authoring` turns authored text into entity data with pure `text -> data` functions and no I/O.
Normalisation runs first and reshapes tokens by their position; the grammar alone knows what a valid value is.
Parsers never raise: every piece of lost information becomes a coded warning.
The canonical forms come from `AbsaOSS/living-doc`'s [glossary](https://github.com/AbsaOSS/living-doc/blob/master/docs/guides/living-doc-glossary.md) and [header types](https://github.com/AbsaOSS/living-doc/blob/master/docs/guides/living-doc-header-types.md).

## Decisions

- Every parser normalises a document's fields first and extracts them second, never the reverse → `authoring/normalize.py::normalize` · [normalisation](authoring/normalisation.md#where-normalisation-runs)
  - Why: a mis-cased or mis-dashed but well-formed header is corrected, not rejected.
- The entity id is the one exception: it is derived from the title before the document body is normalised, and a title with no id skips normalisation of the body entirely → `authoring/issue_body.py::parse_issue_body`
- Normalisation never validates meaning; only `ac_grammar.py` knows the state vocabulary and the strict version shape → `tests/authoring/test_isolation.py::test_no_module_other_than_ac_grammar_validates_ac_state_or_version` · [grammar](authoring/ac-grammar.md)
  - Why: two layers that both tolerated variance would disagree about what is valid.
- The parsers share one grammar instead of reimplementing it → `tests/authoring/test_normalize_first.py::test_feature_header_issue_body_and_scenario_import_ac_grammar` · [grammar](authoring/ac-grammar.md#header)
- One helper decides where a fenced code block starts and ends → `authoring/normalize.py::compute_fence_flags` · [normalisation](authoring/normalisation.md#where-normalisation-runs)
- Parsers report, never raise or log → `authoring/issue_body.py::parse_issue_body` · [parsers](authoring/parsers.md#common-behaviour)
- A warning is a `ContractWarning`, and its code is defined once → `contracts/envelope.py::ContractWarning` · [errors](contracts/errors.md#codes)
- `authoring` stays source-agnostic: no GitHub- or Azure-DevOps-specific import → `tests/authoring/test_isolation.py::test_authoring_imports_nothing_github_or_azure_devops_specific`
- `contracts` never imports `authoring`; the dependency runs one way → `tests/authoring/test_isolation.py::test_contracts_imports_nothing_from_authoring`
- Status and relations are settled once per run, over every parsed entity → `authoring/status.py::derive_statuses` · [parsers](authoring/parsers.md#status-derivation)
- One URL policy serves every consumer → `authoring/url_policy.py::safe_href` · [URLs and HTML](authoring/urls-and-html.md#url-policy)

## Pages

Read in this order; each page defines its facts once.

| Page | Defines |
|---|---|
| [Normalisation](authoring/normalisation.md) | where it runs, the five source formats, the eight rules, worked examples |
| [Acceptance-criterion grammar](authoring/ac-grammar.md) | header forms, block extensions, dropped and converted criteria |
| [Parsers](authoring/parsers.md) | each parser's layout, entity identity, status derivation, relations, golden fixtures |
| [URLs and HTML](authoring/urls-and-html.md) | the URL policy, HTML sanitising, HTML-to-Markdown conversion |
