## Overview

Every authoring parser now reads a line's indent before it decides what the line belongs to (DEC-44). Until
now each parser stripped the line first, so what a line belonged to followed line order alone. A nested item
became a sibling, a wrapped line reading `key: value` opened a key, and a criterion field after a
`preconditions:` list joined that list, all without a warning.

- **One line model.** `normalize.py::IndentedLine` / `indented()` removes only the comment marker and one
  following space. The criterion grammar, both header parsers, `extract_bullets` and the `.feature` header
  normaliser all read through it.
- **Wrapped lines.** In a `.feature` or PageObject header, a line deeper than an open bullet item's `- ` is
  that item's text. It is never read as a key or an `AC:` header (`normalize.py::BulletItemTracker`). An
  indented key outside a bullet item is still a key. A PageObject header has no bullet-list key yet, so
  there the tracker has nothing to guard until `notes:` (#168). A wrapped line at the item's own indent
  (no indent) is joined onto the item as before, with no warning.
- **Nested items**, owner's decision on the issue: a nested item is kept in its parent's string as
  extracted, on its own line and indented relative to the parent's `- ` (`"Parent.\n  - Child."`).
  Nothing between the collector and a generator rewrites the string, so the toolkit and the generators decide
  how to render it. Wrapped text before any nested item is still joined with a space.
- **Criterion blocks.** A sub-list whose items sit deeper than its key ends where the indent returns to the
  key's. A sub-list whose items sit at the key's own indent (every issue body) keeps today's line-order rule.
  An unknown bare sub-key with lines deeper than it (e.g. an AC-level `notes:`) is reported as
  `UNPARSED_AC_LINE` together with exactly those lines. A bare `<key>:` with nothing deeper under it is the end
  of a wrapped line (`…shows the` / `following:`) and is joined as before.
- **Criterion headers keep their indent.** The `.feature` normaliser used to rebuild a header it rewrote
  (e.g. `Active` → `active`) at a fixed `#   `, moving it away from its own bullets. It now keeps the author's
  indent, as the issue-body and scenario normalisers already did; a rule-7 split description goes two spaces
  deeper than its header.
- **Misindented lines**, owner's decision: a new warning `MISINDENTED_LINE` (collector). It covers a line
  shallower than its list's item level, a nested `- ` that returns between two open levels, and, in a
  criterion block, a line below the content level or between a sub-key and its items. The line is dropped
  together with every line deeper than it.
- **Rule 6** (tab/NBSP in an indent) now runs on every authored input, as the canon's Indentation rule says.
  In a `.feature` header a tab becomes one space, as in a PageObject header; the comment prefix is now `# ?`,
  so a tab right after `#` counts as indentation. In an issue body a tab moves to GitHub's tab stop of 4, so
  the parser sees the levels the reader sees; fenced code is untouched. Each rewrite is recorded as a
  `whitespace` change.

### Inputs whose output changes

Flat input parses exactly as before. The only edit to an existing test is the code count in `tests/contracts/test_codes.py`, 37 → 38, for the new code.

| Input | Before | After |
|---|---|---|
| a nested `- ` in any bullet field (issue body or `.feature` header) | a sibling item | part of its parent's entry, `"Parent.\n  - Child."` |
| a wrapped bullet line reading `status: …` or `AC:<id> (…)` in a `.feature` header | a new key, or a new criterion | the item's text |
| `- Aspect: …` back at criterion level after an indented `preconditions:` list | joined `preconditions` | `aspect` |
| an AC-level `notes:` and its deeper bullets | appended to the previous field, or read as placeholders | `UNPARSED_AC_LINE` for each line |
| a line whose indent fits no level | attached to a neighbour, silently | dropped with `MISINDENTED_LINE` |
| a tab/NBSP in a `.feature` header indent | kept | one space, recorded as rule 6 |
| a tab/NBSP in an issue-body indent, outside fenced code | kept | spaces to the next multiple of 4 (NBSP: one space), recorded as rule 6 |
| a `.feature` criterion header rewritten by rules 2–4, not at indent 2 | moved to `#   ` | kept at the author's indent |

### Contract

No field or schema changes. A nested item stays inside its parent's `list[str]` entry. The version stays
`0.5.0` (DEC-41). `MISINDENTED_LINE` is a new entry in `contracts.codes.ALL_CODES`.

### Acceptance criteria

- [x] No parser strips a line before its level is decided; one shared model serves `extract_bullets`, both
      header parsers, the criterion grammar and both normalisers: `authoring/normalize.py:138` (`IndentedLine`),
      `issue_body.py:162`, `feature_header.py:121`, `page_object.py:132`, `ac_grammar.py:145`,
      `normalize.py:518`. The PageObject normaliser has no key or `AC:` logic, so its only indent step is rule 6.
- [x] A nested item in any bullet field, in an issue body and in a `.feature` header, is part of its parent
      item, stored as extracted; no schema changes: `authoring/normalize.py:182` (`ItemText`),
      `authoring/issue_body.py:162`
- [x] A wrapped line deeper than an open bullet item's `- ` is never read as a key or an `AC:` header in
      either header parser or the normaliser; an indented key outside a bullet item still is:
      `authoring/normalize.py:159`, `feature_header.py:121`, `feature_header.py:205`, `ac_grammar.py:433`;
      a rewritten criterion header keeps its indent, so its next header is never taken for item text:
      `normalize.py:531`
- [x] The criterion example yields `aspect = ["security"]` and `preconditions = ["An account exists."]`, with
      no warning: `authoring/ac_grammar.py:125` (`_SubList`)
- [x] An unknown bare sub-key in a criterion block is reported with exactly the lines deeper than it; the next
      content-level line is read normally: `authoring/ac_grammar.py:221`
- [x] Flat input parses exactly as today: no existing test changed, apart from the code count for the new code;
      an unindented wrapped line (including one ending in `:`) and a flush criterion block parse as before
- [x] A misindented line is reported as `MISINDENTED_LINE`: `contracts/codes.py:88`, `docs/contracts/errors.md:52`,
      `tests/contracts/test_codes.py`, and two cases in `tests/authoring/test_warning_coverage.py`
- [x] Rule 6 covers `.feature` headers, with cases in `normalisation_cases.yaml`:
      `authoring/normalize.py:518`, `normalisation_cases.yaml:283`; and issue bodies, per the canon:
      `normalize.py:430`, `normalisation_cases.yaml:299`
- [x] `ac-grammar.md`, `parsers.md`, `normalisation.md` (and `rendering.md`, `errors.md`) updated; `make qa`
      green

## Framework

Stays inside the frame (DEC-43): parsing in F5 Utilities only. No new derivation and no contract field; the
new warning code is a parsing outcome.

## Release Notes
- Every authoring parser honours indentation: a nested item in a bullet-list field stays part of its parent
  item, kept as authored (`"Parent.\n  - Child."`), instead of becoming a sibling.
- A wrapped bullet line that reads like `key: value` or `AC:<id> (…)` in a `.feature` header is the item's text,
  never a new key or criterion.
- In a criterion block, a field back at criterion level after an indented `preconditions:` / `not_in_scope:`
  list is read as a criterion field; an unknown sub-key such as `notes:` is reported with its deeper lines.
- New warning `MISINDENTED_LINE` for a line whose indent fits no level.
- Rule 6 (tab/NBSP indent) now also normalises `.feature` headers (one space per tab) and issue bodies (GitHub's
  tab stop of 4).
- The `.feature` normaliser keeps a rewritten criterion header at its author's indent.

## Related
Closes #173

🤖 Generated with [Claude Code](https://claude.com/claude-code)
