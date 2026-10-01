<!--
Golden fixture. Copied verbatim from AbsaOSS/living-doc's docs/examples/gh-issues/func-001-validate-password-strength.md
at commit eccbc9e72970e10e8d7e61ffc400c66c252229bd (canon HEAD; the `## Notes` corpus round, PR #43).
-->
<!--
GitHub issue body for a Functionality mined by collector-gh `doc-issues`.
Label: DocumentedFunctionality    Title: FUNC-001 · Login Page - Validate Password Strength
Layout: see ../README.md (GitHub issue-body layout)
-->

## Description

Validates a candidate password against the account complexity policy before the login form is submitted.

## Status

active

## Parent Feature

FEAT-001

## Func Type

field_validation

## Rationale

- Password strength is checked client-side before submit so the customer gets immediate feedback; the
  account complexity policy remains the server-side source of truth.

## Acceptance Criteria

### AC:FUNC-001-01 (v1.0.0 - active)

- Returns valid=false when the candidate password fails a complexity rule.

### AC:FUNC-001-02 (v1.0.0 - active)

- Returns valid=true when the candidate password satisfies every complexity rule.
