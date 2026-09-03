# Rule: docs lifecycle — design docs shrink as code ships

A design/spec document describes what does **not** exist yet. Once a section is
implemented, that section stops being a spec and becomes a fact about the codebase — so it
belongs in the live docs, not in the design doc.

## The rule

When a PR implements a design-doc section, that same PR must:

1. **Delete** the implemented content from the design doc (the whole section, or the
   specific subsections that are now shipped).
2. **Add** the equivalent, "what actually exists" description to the live docs:
   - `README.md` for the public API surface, install/import, and usage examples;
   - `DEVELOPER.md` for the local-dev and release workflow.

This is a **move**, not a copy. After the PR, the information exists in exactly one place —
the live docs — and the design doc is smaller. Design docs trend toward empty as the
library fills in.

## What "move" means

- Do not leave the section in the design doc with a "✅ implemented" marker. Remove it.
- Do not duplicate the schema/flow/table in both the design doc and the live docs. One home.
- If only part of a section shipped, split it: the shipped part moves to live docs, the
  unshipped part stays in the design doc.
- Cross-references that pointed at the moved section must be repointed to its new home in
  the same PR (keep link checking green).

## Current state of this repo

`living-doc-utilities` has **no `SPEC.md`** today — its behaviour is documented directly in
`README.md` and `DEVELOPER.md`. If a design doc is ever added (for a new model family, a
new serde format, a new helper package), this rule governs how its sections graduate into
those live docs. A design doc with nothing prospective left in it is drift waiting to
happen — delete it or reduce it to a one-line pointer.
