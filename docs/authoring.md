# Authoring

## Purpose

This page is the hub of the authoring rules: it states how authored text becomes entity data, lists the design
decisions, and links to the page that defines each part.

Read before: [README](../README.md) · Next: [Normalisation](authoring/normalisation.md)

## Contents

- [Principle](#principle)
- [Decisions](#decisions)
- [Pages](#pages)

## Principle

`living_doc_utilities.authoring` turns authored text into entity data with pure `text -> data` functions and no I/O.
Normalisation runs first and reshapes tokens by their position; the grammar alone knows what a valid value is.
Parsers never raise: every piece of lost information becomes a coded warning.
The canonical forms come from `AbsaOSS/living-doc`'s [glossary](https://github.com/AbsaOSS/living-doc/blob/master/docs/reference/glossary.md) and [header types](https://github.com/AbsaOSS/living-doc/blob/master/docs/reference/authoring-formats.md).

## Decisions

- Every parser normalises a document's fields first and extracts them second, never the reverse · [normalisation](authoring/normalisation.md#where-normalisation-runs)
  - Why: a mis-cased or mis-dashed but well-formed header is corrected, not rejected.
- The issue-body parser derives the entity id from the (normalised) title before the body is normalised, and a title with no id skips body normalisation entirely
  - The feature-header and PageObject parsers find the header first: only a header whose title names an entity is normalised and read, and nothing outside it
- Where a section begins and ends is decided once, by position, before any rule rewrites a line or any parser reads one · [normalisation](authoring/normalisation.md#where-normalisation-runs)
  - Why: when the normaliser and the parser each found boundaries, they disagreed, and a note's text dropped data silently.
- Normalisation never validates meaning; only `ac_grammar.py` knows the state vocabulary and the strict version shape · [grammar](authoring/ac-grammar.md)
  - Why: two layers that both tolerated variance would disagree about what is valid.
- The parsers share one grammar instead of reimplementing it · [grammar](authoring/ac-grammar.md#header)
- One helper decides where a fenced code block starts and ends · [normalisation](authoring/normalisation.md#where-normalisation-runs)
- Parsers report, never raise or log · [parsers](authoring/parsers.md#common-behaviour)
- A warning is a `ContractWarning`, and its code is defined once · [errors](contracts/errors.md#codes)
- `authoring` stays source-agnostic: no GitHub- or Azure-DevOps-specific import
- `contracts` never imports `authoring`; the dependency runs one way
- Status and relations are settled once per run, over every parsed entity · [parsers](authoring/parsers.md#status-derivation)
- One URL policy serves every consumer · [URLs and HTML](authoring/urls-and-html.md#url-policy)

## Pages

Read in this order; each page defines its facts once.

| Page | Defines |
|---|---|
| [Normalisation](authoring/normalisation.md) | where it runs, the five source formats, the eight rules, worked examples |
| [Acceptance-criterion grammar](authoring/ac-grammar.md) | header forms, block extensions, dropped and converted criteria |
| [Parsers](authoring/parsers.md) | each parser's layout, entity identity, status derivation, relations, golden fixtures |
| [URLs and HTML](authoring/urls-and-html.md) | the URL policy, HTML sanitising, HTML-to-Markdown conversion |
